import XCTest
@testable import ShadowingGuruDomain

/// 검출·채점 로직의 읽히는 명세. 파이썬 `tests/test_detect.py`와 대응한다.
final class DetectorTests: XCTestCase {

    private let detector = Detector()

    func testRamp() {
        XCTAssertEqual(Detector.ramp(0.0, 1.0, 2.0), 0.0)
        XCTAssertEqual(Detector.ramp(1.5, 1.0, 2.0), 0.5, accuracy: 1e-9)
        XCTAssertEqual(Detector.ramp(9.9, 1.0, 2.0), 1.0)
    }

    func testPhoneFactorOrderMatters() {
        // 이중모음은 일반 모음보다 먼저 판정되어야 한다. 두 집합이 겹치므로
        // classFactors를 사전으로 바꾸면 여기가 깨진다.
        XCTAssertEqual(Detector.phoneFactor("AY"), 1.40, accuracy: 1e-9)
        XCTAssertEqual(Detector.phoneFactor("IH"), 1.00, accuracy: 1e-9)
        XCTAssertEqual(Detector.phoneFactor("T"), 0.55, accuracy: 1e-9)
    }

    func testPauseIsDetected() {
        let words = [Word(text: "turn", start: 0.00, end: 0.30),
                     Word(text: "it",   start: 0.60, end: 0.75),
                     Word(text: "off",  start: 0.78, end: 1.00)]
        let rep = detector.evaluate(words)
        XCTAssertEqual(rep.results[0].verdict, .broken)
        XCTAssertTrue(rep.results[0].reason.contains("끊어"))
    }

    func testEpenthesisIsDetected() {
        // 간격이 0이어도 앞 단어가 부풀면 모음 삽입으로 잡혀야 한다
        let words = [Word(text: "turn", start: 0.00, end: 0.62),
                     Word(text: "it",   start: 0.62, end: 0.74),
                     Word(text: "off",  start: 0.74, end: 0.92)]
        let rep = detector.evaluate(words)
        let first = rep.results[0]
        XCTAssertGreaterThan(first.inflation ?? 0, Detector.inflationBad)
        XCTAssertEqual(first.verdict, .broken)
        XCTAssertTrue(first.reason.contains("삽입"))
    }

    func testRateNormalization() {
        // 2배 느린 화자가 같은 비율로 끊으면 점수가 같아야 한다.
        // 고정 ms 임계값이었다면 실패하는 케이스다.
        let fast = [Word(text: "turn", start: 0.200, end: 0.450),
                    Word(text: "it",   start: 0.452, end: 0.562),
                    Word(text: "off",  start: 0.564, end: 0.784)]
        let slow = fast.map { Word(text: $0.text, start: $0.start * 2, end: $0.end * 2) }
        XCTAssertEqual(detector.evaluate(fast).score,
                       detector.evaluate(slow).score, accuracy: 1e-9)
    }

    func testOOVExcludedFromScore() {
        let words = [Word(text: "turn",  start: 0.00, end: 0.25),
                     Word(text: "it",    start: 0.26, end: 0.38),
                     Word(text: "zzqqx", start: 0.39, end: 0.60),
                     Word(text: "off",   start: 0.61, end: 0.80)]
        let rep = detector.evaluate(words)
        XCTAssertTrue(rep.results.contains { $0.verdict == .notApplicable })
        XCTAssertTrue((0...100).contains(rep.score))
    }

    func testScoreBounds() {
        let words = [Word(text: "turn", start: 0.200, end: 0.450),
                     Word(text: "it",   start: 0.452, end: 0.562),
                     Word(text: "off",  start: 0.564, end: 0.784)]
        let rep = detector.evaluate(words)
        XCTAssertTrue((0...100).contains(rep.score))
        XCTAssertGreaterThan(rep.score, 80)   // 깨끗하게 이어진 발화
    }

    func testFocusPointsAtRequiredBoundary() {
        let words = [Word(text: "turn", start: 0.00, end: 0.30),
                     Word(text: "it",   start: 0.60, end: 0.75),
                     Word(text: "off",  start: 1.10, end: 1.32)]
        let rep = detector.evaluate(words)
        XCTAssertNotNil(rep.focus)
        XCTAssertTrue(rep.focus?.boundary.expectsLink ?? false)
    }

    func testEmptyAndSingleWordAreSafe() {
        XCTAssertEqual(detector.evaluate([]).score, 0)
        XCTAssertEqual(detector.evaluate([Word(text: "turn", start: 0, end: 0.3)]).score, 0)
    }
}
