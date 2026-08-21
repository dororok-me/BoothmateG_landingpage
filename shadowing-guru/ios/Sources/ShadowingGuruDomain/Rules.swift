import Foundation

/// 연음(connected speech) 규칙 엔진.
///
/// 텍스트만으로 "이 경계는 이어져야 한다"를 판정한다. 원본 오디오가 필요 없으므로
/// YouTube 임베드(몰입 모드)에서도 동작한다.
///
/// 가중치는 **한국인 학습자 기준 중요도**다. 두 축을 곱해서 정했다.
///   (1) 못 지켰을 때 비원어민으로 들리는 정도
///   (2) 한국어 음운 체계 때문에 실제로 자주 틀리는 정도
///
/// 한국어는 어말 자음군이 없고 폐음절 뒤에 /ɯ/를 삽입하는 경향이 강하다.
/// 그래서 LINK_CV와 기능어 축약이 압도적으로 중요하고, 탄설음화나 구개음화는
/// 안 해도 의사소통에 지장이 없어 후순위다.
public struct Rules {

    public let lexicon: Lexicon

    public init(lexicon: Lexicon = .shared) {
        self.lexicon = lexicon
    }

    /// 규칙 하나: (앞 음소, 뒤 음소, 앞 단어, 뒤 단어) → 태그 또는 nil
    private typealias Rule = (String, String, String, String) -> LinkTag?

    /// 적용 순서. **이 순서가 곧 `Boundary.tags`의 순서**이므로 바꾸면
    /// 골든 픽스처가 깨진다.
    private var boundaryRules: [Rule] {
        [linkCV, reduceTarget, glideY, glideW, linkR, geminate,
         elideT, elideD, flap, palatalize, unreleased, hDrop,
         nasalAssim, dhAssim]
    }

    // MARK: - 경계 규칙

    /// 자음 + 모음 → 재음절화. 한국인 학습자 최대 약점.
    private func linkCV(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard Phones.isConsonant(p1), Phones.isVowel(p2) else { return nil }
        return LinkTag(
            rule: "LINK_CV", nameKo: "자음-모음 연결", weight: 1.0, required: true,
            hint: "'\(w1)'의 끝소리 /\(p1)/를 '\(w2)'에 붙여 한 덩어리로 발음하세요",
            surface: "…\(p1)·\(p2)…")
    }

    /// 기능어 앞 경계 — 뒤 단어가 축약되어야 한다.
    private func reduceTarget(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard Phones.functionWords.contains(Lexicon.normalize(w2)),
              lexicon.syllableCount(w2) == 1 else { return nil }
        return LinkTag(
            rule: "REDUCE", nameKo: "기능어 축약", weight: 0.8, required: true,
            hint: "'\(w2)'는 힘을 빼고 짧게 흘리세요. 또박또박 읽으면 어색합니다")
    }

    /// 전설·고모음 + 모음 → /j/ 활음 삽입. he is → heyiz
    private func glideY(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard Phones.frontHigh.contains(p1), Phones.isVowel(p2) else { return nil }
        return LinkTag(
            rule: "GLIDE_Y", nameKo: "y 활음 연결", weight: 0.7, required: true,
            hint: "'\(w1)'와 '\(w2)' 사이에 살짝 /y/를 넣어 이으세요",
            surface: "…\(p1)·Y·\(p2)…")
    }

    /// 후설·원순모음 + 모음 → /w/ 활음 삽입. go on → gowon
    private func glideW(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard Phones.backRound.contains(p1), Phones.isVowel(p2) else { return nil }
        return LinkTag(
            rule: "GLIDE_W", nameKo: "w 활음 연결", weight: 0.7, required: true,
            hint: "'\(w1)'와 '\(w2)' 사이에 살짝 /w/를 넣어 이으세요",
            surface: "…\(p1)·W·\(p2)…")
    }

    /// ER(r성 모음) + 모음 → /r/로 이어진다. her own, far away
    private func linkR(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard p1 == "ER", Phones.isVowel(p2) else { return nil }
        return LinkTag(
            rule: "LINK_R", nameKo: "r 연결", weight: 0.6, required: true,
            hint: "'\(w1)'의 r 소리를 '\(w2)'로 굴려 넘기세요",
            surface: "…ER·R·\(p2)…")
    }

    /// 동일 자음 연쇄 → 하나로 길게. big girl, this Sunday
    private func geminate(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard p1 == p2, Phones.isConsonant(p1) else { return nil }
        return LinkTag(
            rule: "GEMINATE", nameKo: "겹자음 축약", weight: 0.6, required: true,
            hint: "/\(p1)/를 두 번 발음하지 말고 한 번 길게 내세요",
            surface: "…\(p1)ː…")
    }

    /// 자음군 뒤 /t/ 탈락. next day → nex day
    private func elideT(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard let pron = lexicon.primary(w1), pron.count >= 2,
              p1 == "T",
              Phones.isConsonant(pron[pron.count - 2]),
              Phones.isConsonant(p2) else { return nil }
        return LinkTag(
            rule: "ELIDE_T", nameKo: "t 탈락", weight: 0.5, required: false,
            hint: "'\(w1)'의 끝 t는 거의 들리지 않게 생략하세요")
    }

    /// 자음군 뒤 /d/ 탈락. old man → ol man
    private func elideD(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard let pron = lexicon.primary(w1), pron.count >= 2,
              p1 == "D",
              Phones.isConsonant(pron[pron.count - 2]),
              Phones.isConsonant(p2) else { return nil }
        return LinkTag(
            rule: "ELIDE_D", nameKo: "d 탈락", weight: 0.5, required: false,
            hint: "'\(w1)'의 끝 d는 거의 들리지 않게 생략하세요")
    }

    /// 모음 사이 /t,d/ → 탄설음. get it → gedit (미국식)
    private func flap(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard let pron = lexicon.primary(w1), pron.count >= 2,
              p1 == "T" || p1 == "D",
              Phones.isVowel(pron[pron.count - 2]),
              Phones.isVowel(p2) else { return nil }
        return LinkTag(
            rule: "FLAP", nameKo: "탄설음화", weight: 0.4, required: false,
            hint: "'\(w1)'의 t/d를 한국어 'ㄹ'에 가깝게 굴리세요 (미국식)")
    }

    /// 치경음 + /j/ → 구개음화. did you → didja
    private func palatalize(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        let table = ["T": "CH", "D": "JH", "S": "SH", "Z": "ZH"]
        guard let target = table[p1], p2 == "Y" else { return nil }
        return LinkTag(
            rule: "PALATALIZE", nameKo: "구개음화", weight: 0.4, required: false,
            hint: "'\(w1) \(w2)'를 붙여 /\(target)/ 소리로 뭉치세요",
            surface: "…\(target)…")
    }

    /// 파열음 + 파열음/파찰음 → 앞 파열음 미파. big cat
    private func unreleased(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard Phones.stops.contains(p1),
              Phones.stops.contains(p2) || Phones.affricates.contains(p2) else { return nil }
        return LinkTag(
            rule: "UNRELEASED", nameKo: "미파음", weight: 0.4, required: false,
            hint: "'\(w1)'의 끝 /\(p1)/를 터뜨리지 말고 멈춘 채 넘어가세요")
    }

    /// 강세 없는 기능어의 /h/ 탈락. tell him → tell'im
    private func hDrop(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard p2 == "HH", Phones.hDropWords.contains(Lexicon.normalize(w2)) else { return nil }
        return LinkTag(
            rule: "H_DROP", nameKo: "h 탈락", weight: 0.4, required: false,
            hint: "'\(w2)'의 h를 빼고 앞 단어에 붙이세요")
    }

    /// /n/ 조음위치 동화. in bed → im bed
    private func nasalAssim(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard p1 == "N",
              Phones.labial.contains(p2) || Phones.velar.contains(p2) else { return nil }
        let target = Phones.labial.contains(p2) ? "M" : "NG"
        return LinkTag(
            rule: "NASAL_ASSIM", nameKo: "비음 동화", weight: 0.3, required: false,
            hint: "'\(w1)'의 n을 /\(target)/에 가깝게 바꿔 이으세요")
    }

    /// /n,l,s,z/ + /ð/ 동화. in the
    private func dhAssim(_ p1: String, _ p2: String, _ w1: String, _ w2: String) -> LinkTag? {
        guard ["N", "L", "S", "Z"].contains(p1), p2 == "DH" else { return nil }
        return LinkTag(
            rule: "DH_ASSIM", nameKo: "th 동화", weight: 0.3, required: false,
            hint: "'\(w2)'의 th를 앞 자음에 녹여 이으세요")
    }

    // MARK: - 진입점

    /// 단어 두 개 사이의 기대 연결을 판정한다.
    public func analyzeBoundary(index: Int, _ w1: String, _ w2: String) -> Boundary {
        guard let p1 = lexicon.finalPhone(w1) else {
            return Boundary(index: index, left: w1, right: w2, tags: [], skipped: "OOV:\(w1)")
        }
        guard let p2 = lexicon.initialPhone(w2) else {
            return Boundary(index: index, left: w1, right: w2, tags: [], skipped: "OOV:\(w2)")
        }
        let tags = boundaryRules.compactMap { $0(p1, p2, w1, w2) }
        return Boundary(index: index, left: w1, right: w2, tags: tags, skipped: nil)
    }

    /// 문장 전체의 경계를 판정한다.
    public func analyzeText(_ words: [String]) -> [Boundary] {
        guard words.count >= 2 else { return [] }
        return (0..<(words.count - 1)).map {
            analyzeBoundary(index: $0, words[$0], words[$0 + 1])
        }
    }

    /// 연음 밀도 — 난이도 산출(기준서 §5)에 쓰인다.
    public func linkDensity(_ boundaries: [Boundary]) -> Double {
        let judged = boundaries.filter { $0.skipped == nil }
        guard !judged.isEmpty else { return 0 }
        return Double(judged.filter(\.expectsLink).count) / Double(judged.count)
    }
}
