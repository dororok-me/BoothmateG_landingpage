import Foundation

/// ARPAbet 음소 분류. CMUdict 표기 기준.
///
/// 파이썬 `linking/phones.py`의 포팅. 집합 구성이 바뀌면 규칙 판정이 통째로
/// 달라지므로 골든 픽스처가 이를 감시한다.
public enum Phones {

    public static let vowels: Set<String> = [
        "AA", "AE", "AH", "AO", "AW", "AY",
        "EH", "ER", "EY", "IH", "IY",
        "OW", "OY", "UH", "UW",
    ]

    public static let stops: Set<String>      = ["P", "B", "T", "D", "K", "G"]
    public static let affricates: Set<String> = ["CH", "JH"]
    public static let fricatives: Set<String> = ["F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH"]
    public static let nasals: Set<String>     = ["M", "N", "NG"]
    public static let liquids: Set<String>    = ["L", "R"]
    public static let glides: Set<String>     = ["W", "Y"]

    public static let consonants: Set<String> =
        stops.union(affricates).union(fricatives)
             .union(nasals).union(liquids).union(glides)

    /// 조음위치 — 비음 동화 판정용
    public static let labial: Set<String> = ["P", "B", "M", "F", "V"]
    public static let velar: Set<String>  = ["K", "G", "NG"]

    /// 전설·고모음 — 뒤에 모음이 오면 /j/ 활음이 삽입된다 (he is → heyiz)
    public static let frontHigh: Set<String> = ["IY", "IH", "EY", "AY", "OY"]

    /// 후설·원순모음 — 뒤에 모음이 오면 /w/ 활음이 삽입된다 (go on → gowon)
    public static let backRound: Set<String> = ["UW", "UH", "OW", "AW"]

    /// 이중모음 — 길이 추정에서 단모음보다 길게 잡는다
    public static let diphthongs: Set<String> = ["AW", "AY", "EY", "OW", "OY"]

    /// 축약되는 기능어. 한국인 학습자는 이들을 또박또박 완전형으로 발음하는 경향이 있다.
    public static let functionWords: Set<String> = [
        "a", "an", "the", "and", "or", "but", "of", "to", "for", "from",
        "at", "in", "on", "as", "that", "than", "is", "are", "was", "were",
        "am", "be", "been", "have", "has", "had", "do", "does", "did",
        "can", "could", "will", "would", "shall", "should", "must",
        "he", "him", "his", "her", "them", "us", "you", "your", "some",
    ]

    /// /h/ 탈락 대상 — 강세 없는 대명사·조동사
    public static let hDropWords: Set<String> = [
        "he", "him", "his", "her", "have", "has", "had",
    ]

    /// `AH0` → `AH`
    public static func stripStress(_ phone: String) -> String {
        var s = Substring(phone)
        while let last = s.last, last.isNumber { s = s.dropLast() }
        return String(s)
    }

    public static func isVowel(_ phone: String) -> Bool {
        vowels.contains(stripStress(phone))
    }

    public static func isConsonant(_ phone: String) -> Bool {
        consonants.contains(stripStress(phone))
    }
}
