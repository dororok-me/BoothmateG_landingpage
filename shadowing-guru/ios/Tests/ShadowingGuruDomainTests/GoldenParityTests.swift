import XCTest
@testable import ShadowingGuruDomain

/// 파이썬 구현과의 출력 일치 검증.
///
/// `tools/export_golden.py`가 파이썬 엔진을 돌려 만든 픽스처를 읽고, Swift 포팅이
/// 같은 값을 내는지 검사한다. 포팅 작성 환경에 Swift 툴체인이 없어 컴파일 검증을
/// 하지 못했으므로, 번역 오류는 여기서 이름 붙은 실패로 드러나야 한다.
///
/// 픽스처를 다시 만들려면: `python3 tools/export_golden.py`
final class GoldenParityTests: XCTestCase {

    // MARK: 픽스처 모델

    struct Golden: Decodable {
        let version: Int
        let tolerance: Double
        let lexicon: [LexiconCase]
        let rules: [RuleCase]
        let sentences: [SentenceCase]
        let detect: [DetectCase]
    }

    struct LexiconCase: Decodable {
        let word: String
        let phones: [String]?
        let syllables: Int
        let normalized: String
    }

    struct RuleCase: Decodable {
        let left: String
        let right: String
        let skipped: String?
        let tags: [String]
        let expectsLink: Bool
        let weight: Double
        let primaryTag: String?
    }

    struct SentenceCase: Decodable {
        let sentence: String
        let boundaryCount: Int
        let linkDensity: Double
        let requiredIndices: [Int]
    }

    struct DetectCase: Decodable {
        struct W: Decodable { let text: String; let start: Double; let end: Double }
        struct R: Decodable {
            let index: Int
            let verdict: String
            let gap: Double
            let normGap: Double
            let inflation: Double?
            let credit: Double
        }
        let name: String
        let words: [W]
        let meanPhone: Double
        let speechRate: Double
        let score: Double
        let focusIndex: Int?
        let results: [R]
    }

    // MARK: 적재

    private static let loadedGolden: Golden = {
        guard let url = Bundle.module.url(forResource: "golden", withExtension: "json") else {
            fatalError("golden.json을 번들에서 찾지 못했습니다")
        }
        do {
            return try JSONDecoder().decode(Golden.self, from: Data(contentsOf: url))
        } catch {
            fatalError("golden.json 디코딩 실패: \(error)")
        }
    }()

    private var golden: Golden { Self.loadedGolden }
    private var tol: Double { max(golden.tolerance, 1e-6) }

    private let rules = Rules()
    private let detector = Detector()

    // MARK: 사전

    func testLexiconParity() {
        for c in golden.lexicon {
            XCTAssertEqual(Lexicon.normalize(c.word), c.normalized,
                           "normalize(\(c.word))")

            let phones = Lexicon.shared.primary(c.word)
            if let expected = c.phones {
                XCTAssertEqual(phones, expected, "primary(\(c.word))")
            } else {
                XCTAssertNil(phones, "primary(\(c.word))는 OOV여야 한다")
            }

            XCTAssertEqual(Lexicon.shared.syllableCount(c.word), c.syllables,
                           "syllableCount(\(c.word))")
        }
    }

    // MARK: 규칙

    func testRuleParity() {
        for c in golden.rules {
            let b = rules.analyzeBoundary(index: 0, c.left, c.right)
            let label = "\(c.left) | \(c.right)"

            XCTAssertEqual(b.skipped, c.skipped, "skipped — \(label)")

            // 태그 순서까지 일치해야 한다. 순서는 boundaryRules 배열이 정한다.
            XCTAssertEqual(b.tags.map(\.rule), c.tags, "tags — \(label)")

            XCTAssertEqual(b.expectsLink, c.expectsLink, "expectsLink — \(label)")
            XCTAssertEqual(b.weight, c.weight, accuracy: tol, "weight — \(label)")
            XCTAssertEqual(b.primaryTag?.rule, c.primaryTag, "primaryTag — \(label)")
        }
    }

    // MARK: 문장

    func testSentenceParity() {
        for c in golden.sentences {
            let words = c.sentence.split(separator: " ").map(String.init)
            let bs = rules.analyzeText(words)

            XCTAssertEqual(bs.count, c.boundaryCount, "경계 수 — \(c.sentence)")
            XCTAssertEqual(rules.linkDensity(bs), c.linkDensity, accuracy: tol,
                           "linkDensity — \(c.sentence)")
            XCTAssertEqual(bs.filter(\.expectsLink).map(\.index), c.requiredIndices,
                           "필수 연결 위치 — \(c.sentence)")
        }
    }

    // MARK: 검출

    func testDetectParity() {
        for c in golden.detect {
            let words = c.words.map { Word(text: $0.text, start: $0.start, end: $0.end) }
            let rep = detector.evaluate(words)

            XCTAssertEqual(rep.meanPhone, c.meanPhone, accuracy: tol,
                           "meanPhone — \(c.name)")
            XCTAssertEqual(rep.speechRate, c.speechRate, accuracy: tol,
                           "speechRate — \(c.name)")
            XCTAssertEqual(rep.score, c.score, accuracy: tol,
                           "score — \(c.name)")
            XCTAssertEqual(rep.focus?.boundary.index, c.focusIndex,
                           "focus — \(c.name)")

            XCTAssertEqual(rep.results.count, c.results.count, "결과 수 — \(c.name)")
            for (got, want) in zip(rep.results, c.results) {
                let label = "\(c.name) #\(want.index)"
                XCTAssertEqual(got.boundary.index, want.index, "index — \(label)")
                XCTAssertEqual(got.verdict.rawValue, want.verdict, "verdict — \(label)")
                XCTAssertEqual(got.gap, want.gap, accuracy: tol, "gap — \(label)")
                XCTAssertEqual(got.normGap, want.normGap, accuracy: tol, "normGap — \(label)")
                XCTAssertEqual(got.credit, want.credit, accuracy: tol, "credit — \(label)")

                if let wantInf = want.inflation {
                    XCTAssertNotNil(got.inflation, "inflation 누락 — \(label)")
                    XCTAssertEqual(got.inflation ?? .nan, wantInf, accuracy: tol,
                                   "inflation — \(label)")
                } else {
                    XCTAssertNil(got.inflation, "inflation은 nil이어야 한다 — \(label)")
                }
            }
        }
    }

    // MARK: 픽스처 자체 점검

    func testFixtureLoaded() {
        XCTAssertEqual(golden.version, 1, "픽스처 버전이 바뀌었다면 테스트도 갱신하라")
        XCTAssertFalse(golden.lexicon.isEmpty)
        XCTAssertFalse(golden.rules.isEmpty)
        XCTAssertFalse(golden.sentences.isEmpty)
        XCTAssertFalse(golden.detect.isEmpty)
    }
}
