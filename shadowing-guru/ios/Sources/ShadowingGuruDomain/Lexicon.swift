import Foundation

/// CMUdict 조회.
///
/// 사전에 없는 단어(OOV)는 nil을 돌려주고, 호출부가 해당 경계를 판정에서 제외한다.
/// 추측하지 않는다 — 틀린 음소열로 만든 기대 태그는 그대로 오채점이 되기 때문이다.
///
/// 리소스 `cmudict.txt`는 대표 발음만, 강세를 미리 제거한 상태로 담겨 있다
/// (`tools/export_cmudict.py`가 생성). 파이썬 `lexicon.primary()`와 동작이 일치한다.
public final class Lexicon {

    public static let shared = Lexicon()

    private var table: [String: [String]] = [:]
    private var loaded = false
    private let lock = NSLock()

    /// 테스트에서 사전을 직접 주입할 때 쓴다.
    public init(entries: [String: [String]]? = nil) {
        if let entries {
            table = entries
            loaded = true
        }
    }

    // MARK: 적재

    private func ensureLoaded() {
        lock.lock()
        defer { lock.unlock() }
        guard !loaded else { return }
        loaded = true

        guard let url = Bundle.module.url(forResource: "cmudict", withExtension: "txt"),
              let text = try? String(contentsOf: url, encoding: .utf8) else {
            assertionFailure("cmudict.txt를 번들에서 찾지 못했습니다")
            return
        }

        var t: [String: [String]] = [:]
        t.reserveCapacity(130_000)
        for line in text.split(separator: "\n", omittingEmptySubsequences: true) {
            guard let tab = line.firstIndex(of: "\t") else { continue }
            let word = String(line[line.startIndex..<tab])
            let phones = line[line.index(after: tab)...]
                .split(separator: " ")
                .map(String.init)
            if !phones.isEmpty { t[word] = phones }
        }
        table = t
    }

    // MARK: 조회

    /// 표기를 사전 조회용으로 정리한다. 파이썬 `[^a-z']+` 제거와 같다.
    public static func normalize(_ word: String) -> String {
        String(word.lowercased().unicodeScalars.filter {
            ($0 >= "a" && $0 <= "z") || $0 == "'"
        }.map(Character.init))
    }

    /// 대표 발음(사전 첫 항목). 없으면 nil.
    public func primary(_ word: String) -> [String]? {
        ensureLoaded()
        let w = Lexicon.normalize(word)
        guard !w.isEmpty else { return nil }
        return table[w]
    }

    /// 단어 마지막 음소. OOV면 nil.
    public func finalPhone(_ word: String) -> String? { primary(word)?.last }

    /// 단어 첫 음소. OOV면 nil.
    public func initialPhone(_ word: String) -> String? { primary(word)?.first }

    /// 모음 개수로 음절을 센다. OOV면 0.
    public func syllableCount(_ word: String) -> Int {
        guard let p = primary(word) else { return 0 }
        return p.reduce(0) { $0 + (Phones.vowels.contains($1) ? 1 : 0) }
    }
}
