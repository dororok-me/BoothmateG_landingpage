import XCTest
@testable import ShadowingGuruUI
import ShadowingGuruDomain

/// 번들 샘플이 실제로 읽히고 Domain에 그대로 물리는지 확인한다.
///
/// UI 자체는 컴파일이 곧 검증이지만, 리소스 적재와 타입 변환은 조용히
/// 실패할 수 있어 테스트로 덮는다.
final class SampleDataTests: XCTestCase {

    func testLibraryLoadsFromBundle() {
        let library = SampleLibrary.load()
        XCTAssertEqual(library.version, 1)
        XCTAssertFalse(library.clips.isEmpty, "samples.json이 비어 있거나 읽히지 않았다")
    }

    func testEveryClipHasAttempts() {
        for clip in SampleLibrary.load().clips {
            XCTAssertFalse(clip.words.isEmpty, clip.id)
            XCTAssertFalse(clip.attempts.isEmpty, clip.id)
        }
    }

    func testWordCountMatchesTranscript() {
        // 문장 단어 수와 정렬 결과 단어 수가 어긋나면 경계가 통째로 밀린다.
        for clip in SampleLibrary.load().clips {
            for attempt in clip.attempts {
                XCTAssertEqual(attempt.words.count, clip.words.count,
                               "\(clip.id) / \(attempt.id)")
            }
        }
    }

    func testScoresMatchPythonExport() {
        // samples.json에 기록된 점수는 파이썬 엔진이 낸 값이다.
        // Swift Domain이 같은 값을 내야 한다.
        let detector = Detector()
        for clip in SampleLibrary.load().clips {
            for attempt in clip.attempts {
                let report = detector.evaluate(attempt.domainWords)
                XCTAssertEqual(report.score, attempt.linkingScore, accuracy: 0.01,
                               "\(clip.id) / \(attempt.label)")
            }
        }
    }

    func testProfilesSeparate() {
        // 원어민이 학습자보다 높아야 한다. 아니면 표시할 것이 없다.
        for clip in SampleLibrary.load().clips {
            let byProfile = Dictionary(
                uniqueKeysWithValues: clip.attempts.map { ($0.profile, $0.linkingScore) }
            )
            guard let native = byProfile["native"],
                  let learner = byProfile["learner"] else {
                XCTFail("프로파일 누락 — \(clip.id)")
                continue
            }
            XCTAssertGreaterThan(native, learner, clip.id)
        }
    }
}
