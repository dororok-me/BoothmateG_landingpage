import Foundation

/// 학습자 발화의 연음 실현 여부 검출.
///
/// 입력은 강제 정렬된 단어 타임스탬프. 두 신호를 본다.
///
///   1) 경계 간격(gap) — 이어져야 할 자리에서 끊어 읽었는가
///   2) 길이 팽창(inflation) — 어말 자음 뒤에 모음을 삽입했는가
///
/// 한국어는 폐음절 뒤에 /ɯ/를 삽입하는 경향이 강하다. 정렬기는 그 삽입 모음을
/// 앞 단어 끝에 흡수시키거나 경계 간격으로 밀어내므로, 두 신호 중 하나에는 잡힌다.
///
/// 임계값은 **절대 시간이 아니라 화자의 평균 음소 길이로 정규화**한다.
/// 느리게 말하는 사람은 모든 간격이 길기 때문에 고정 ms 임계값은 오판한다.
public struct Detector {

    // MARK: 임계값 — 평균 음소 길이 배수. 튜닝 대상.
    //
    // 정상 발화의 평균 음소 길이는 70~80ms다. 청자가 "끊어 읽었다"고 느끼는
    // 단어 간 휴지는 대략 100ms 이상이므로 평균 음소의 1.3배 근방을 단절선으로 둔다.

    public static let gapLinked     = 0.35   // 이하면 완전 연결
    public static let gapBroken     = 1.30   // 이상이면 완전 단절

    // 어말 자음 뒤 /ɯ/ 삽입은 앞 단어를 음소 하나만큼 늘린다.
    public static let inflationOK   = 1.25   // 이하면 삽입 없음
    public static let inflationBad  = 1.75   // 이상이면 명백한 삽입

    public static let linkedAt      = 0.75   // credit → verdict 경계
    public static let partialAt     = 0.35

    /// 음소 부류별 상대 길이.
    ///
    /// **순서가 중요하다.** 이중모음이 일반 모음보다 먼저 와야 하고, 두 집합은
    /// 겹친다. 사전(Dictionary)으로 바꾸면 순서가 사라져 판정이 달라진다.
    private static let classFactors: [(Set<String>, Double)] = [
        (Phones.diphthongs, 1.40),
        (Phones.vowels,     1.00),
        (Phones.fricatives, 0.85),
        (Phones.affricates, 0.90),
        (Phones.nasals,     0.70),
        (Phones.liquids,    0.70),
        (Phones.glides,     0.60),
        (Phones.stops,      0.55),
    ]

    public static func phoneFactor(_ phone: String) -> Double {
        for (group, f) in classFactors where group.contains(phone) { return f }
        return 1.0
    }

    public let rules: Rules
    private var lexicon: Lexicon { rules.lexicon }

    public init(rules: Rules = Rules()) {
        self.rules = rules
    }

    // MARK: - 화자 특성

    /// 화자의 평균 음소 길이. 무음 구간은 제외하고 발화 구간만 센다.
    public func meanPhoneDuration(_ words: [Word]) -> Double {
        var totalPhones = 0
        var totalTime = 0.0
        for w in words {
            guard let p = lexicon.primary(w.text), !p.isEmpty else { continue }
            totalPhones += p.count
            totalTime += w.duration
        }
        guard totalPhones > 0 else { return 0 }
        return totalTime / Double(totalPhones)
    }

    /// 음절/초. 첫 단어 시작부터 마지막 단어 끝까지를 분모로 쓴다.
    public func speechRate(_ words: [Word]) -> Double {
        guard words.count >= 2 else { return 0 }
        let span = words[words.count - 1].end - words[0].start
        guard span > 0 else { return 0 }
        let syl = words.reduce(0) { $0 + lexicon.syllableCount($1.text) }
        return Double(syl) / span
    }

    /// 음소 구성으로 추정한 기대 길이. OOV면 nil.
    public func expectedDuration(_ word: Word, meanPhone: Double) -> Double? {
        guard let p = lexicon.primary(word.text), !p.isEmpty else { return nil }
        return p.reduce(0) { $0 + Detector.phoneFactor($1) } * meanPhone
    }

    // MARK: - 채점

    /// lo 이하 0, hi 이상 1, 그 사이는 선형. 연속 감점을 만든다.
    static func ramp(_ x: Double, _ lo: Double, _ hi: Double) -> Double {
        if x <= lo { return 0 }
        if x >= hi { return 1 }
        return (x - lo) / (hi - lo)
    }

    /// 단어 타임스탬프에서 연음 실현 여부를 판정하고 점수를 매긴다.
    public func evaluate(_ words: [Word]) -> Report {
        let meanPhone = meanPhoneDuration(words)
        let rate = speechRate(words)

        guard meanPhone > 0, words.count >= 2 else {
            return Report(words: words, results: [], meanPhone: meanPhone,
                          speechRate: rate, score: 0)
        }

        var results: [BoundaryResult] = []
        results.reserveCapacity(words.count - 1)

        for i in 0..<(words.count - 1) {
            let w1 = words[i], w2 = words[i + 1]
            let b = rules.analyzeBoundary(index: i, w1.text, w2.text)

            let gap = w2.start - w1.end
            let normGap = gap / meanPhone

            let expected = expectedDuration(w1, meanPhone: meanPhone)
            let inflation: Double? = {
                guard let e = expected, e > 0 else { return nil }
                return w1.duration / e
            }()

            if b.skipped != nil || b.tags.isEmpty {
                results.append(BoundaryResult(
                    boundary: b, gap: gap, normGap: normGap, inflation: inflation,
                    verdict: .notApplicable, credit: 0,
                    reason: b.skipped ?? "기대 연결 없음"))
                continue
            }

            let gapCredit = 1 - Detector.ramp(normGap, Detector.gapLinked, Detector.gapBroken)
            let inflCredit = inflation.map {
                1 - Detector.ramp($0, Detector.inflationOK, Detector.inflationBad)
            } ?? 1
            let credit = min(gapCredit, inflCredit)

            let verdict: Verdict
            let reason: String
            if credit >= Detector.linkedAt {
                verdict = .linked
                reason = "연결됨"
            } else if credit >= Detector.partialAt {
                verdict = .partial
                reason = "간격 \(Int((gap * 1000).rounded()))ms — 약하게 끊김"
            } else {
                verdict = .broken
                if inflCredit < gapCredit, let inf = inflation {
                    reason = "'\(w1.text)' 길이 \(String(format: "%.2f", inf))배 — 모음 삽입 의심"
                } else {
                    reason = "간격 \(Int((gap * 1000).rounded()))ms — 끊어 읽음"
                }
            }

            results.append(BoundaryResult(
                boundary: b, gap: gap, normGap: normGap, inflation: inflation,
                verdict: verdict, credit: credit, reason: reason))
        }

        return Report(words: words, results: results, meanPhone: meanPhone,
                      speechRate: rate, score: Detector.score(results))
    }

    /// 기대 연결의 가중 실현률. 판정 불가 경계는 분모에서 뺀다.
    static func score(_ results: [BoundaryResult]) -> Double {
        var num = 0.0, den = 0.0
        for r in results where r.verdict != .notApplicable {
            let w = r.boundary.weight
            guard w > 0 else { continue }
            den += w
            num += w * r.credit
        }
        return den > 0 ? 100 * num / den : 0
    }
}
