import XCTest
@testable import ShadowingGuruDomain

/// 규칙 엔진의 읽히는 명세. 파이썬 `tests/test_rules.py`와 1:1 대응한다.
///
/// 골든 대조(GoldenParityTests)가 값 일치를 보장한다면, 이쪽은 *왜* 그 값이어야
/// 하는지를 남긴다. 규칙을 고칠 때 여기부터 읽으면 된다.
final class RulesTests: XCTestCase {

    private let rules = Rules()

    private func tags(_ w1: String, _ w2: String) -> Set<String> {
        Set(rules.analyzeBoundary(index: 0, w1, w2).tags.map(\.rule))
    }

    func testLinkCV() {
        // 자음 + 모음 → 재음절화
        XCTAssertTrue(tags("turn", "it").contains("LINK_CV"))
        XCTAssertTrue(tags("talk", "about").contains("LINK_CV"))
        XCTAssertTrue(tags("an", "old").contains("LINK_CV"))
        // 모음 + 자음은 연결 대상이 아니다
        XCTAssertFalse(tags("you", "get").contains("LINK_CV"))
        XCTAssertFalse(tags("the", "news").contains("LINK_CV"))
    }

    func testGlides() {
        // 모음 충돌 → 활음 삽입
        XCTAssertTrue(tags("he", "is").contains("GLIDE_Y"))      // IY + IH
        XCTAssertTrue(tags("go", "on").contains("GLIDE_W"))      // OW + AA
        XCTAssertFalse(tags("he", "is").contains("GLIDE_W"))
    }

    func testLinkR() {
        XCTAssertTrue(tags("her", "own").contains("LINK_R"))
    }

    func testGeminate() {
        XCTAssertTrue(tags("big", "girl").contains("GEMINATE"))      // G + G
        XCTAssertTrue(tags("this", "sunday").contains("GEMINATE"))   // S + S
        XCTAssertFalse(tags("big", "cat").contains("GEMINATE"))
    }

    func testElision() {
        XCTAssertTrue(tags("next", "day").contains("ELIDE_T"))   // K S T + D
        XCTAssertTrue(tags("old", "man").contains("ELIDE_D"))    // L D + M
        XCTAssertFalse(tags("it", "off").contains("ELIDE_T"))    // 자음군이 아니다
    }

    func testFlap() {
        XCTAssertTrue(tags("get", "it").contains("FLAP"))        // EH T + IH
        XCTAssertTrue(tags("at", "eight").contains("FLAP"))
        XCTAssertFalse(tags("next", "day").contains("FLAP"))     // 앞이 자음
    }

    func testPalatalize() {
        XCTAssertTrue(tags("did", "you").contains("PALATALIZE"))
        XCTAssertTrue(tags("miss", "you").contains("PALATALIZE"))
        XCTAssertFalse(tags("did", "it").contains("PALATALIZE"))
    }

    func testUnreleased() {
        XCTAssertTrue(tags("big", "cat").contains("UNRELEASED"))
        XCTAssertFalse(tags("big", "man").contains("UNRELEASED"))  // 뒤가 비음
    }

    func testHDrop() {
        XCTAssertTrue(tags("tell", "him").contains("H_DROP"))
        XCTAssertFalse(tags("said", "hello").contains("H_DROP"))   // 기능어가 아니다
    }

    func testNasalAssimilation() {
        XCTAssertTrue(tags("in", "bed").contains("NASAL_ASSIM"))   // N + B 순음
        XCTAssertTrue(tags("in", "cars").contains("NASAL_ASSIM"))  // N + K 연구개음
        XCTAssertFalse(tags("in", "time").contains("NASAL_ASSIM")) // 같은 조음위치
    }

    func testReduction() {
        XCTAssertTrue(tags("want", "to").contains("REDUCE"))
        XCTAssertTrue(tags("about", "the").contains("REDUCE"))
        XCTAssertFalse(tags("the", "news").contains("REDUCE"))     // news는 기능어가 아니다
    }

    func testOOVIsSkippedNotGuessed() {
        // 틀린 음소열로 만든 기대 태그는 그대로 오채점이 된다. 추측하지 않는다.
        let b = rules.analyzeBoundary(index: 0, "zzqqx", "it")
        XCTAssertNotNil(b.skipped)
        XCTAssertTrue(b.tags.isEmpty)
        XCTAssertFalse(b.expectsLink)
    }

    func testRequiredFlag() {
        XCTAssertTrue(rules.analyzeBoundary(index: 0, "turn", "it").expectsLink)
        XCTAssertFalse(rules.analyzeBoundary(index: 0, "big", "cat").expectsLink)
    }

    func testLinkDensity() {
        XCTAssertEqual(rules.linkDensity(rules.analyzeText(["turn", "it", "off"])), 1.0)
        let d = rules.linkDensity(rules.analyzeText(["the", "news", "was", "good"]))
        XCTAssertTrue((0...1).contains(d))
    }

    func testWeightOrdering() {
        // 한국인 학습자 기준 중요도 — LINK_CV가 최상위
        let cv = rules.analyzeBoundary(index: 0, "turn", "it").weight
        let flap = rules.analyzeBoundary(index: 0, "next", "day").weight
        XCTAssertGreaterThan(cv, flap)
    }

    func testPunctuationAndCaseTolerated() {
        // 정렬기가 원본 표기를 그대로 넘겨도 사전 조회가 되어야 한다
        XCTAssertTrue(tags("Turn", "it,").contains("LINK_CV"))
        XCTAssertEqual(Lexicon.shared.primary("look."), ["L", "UH", "K"])
    }
}
