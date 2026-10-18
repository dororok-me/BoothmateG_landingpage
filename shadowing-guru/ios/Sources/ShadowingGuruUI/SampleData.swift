import Foundation
import ShadowingGuruDomain

/// 번들에 담긴 샘플 정렬 결과.
///
/// 첫 슬라이스는 오디오와 정렬기 없이 결과 화면만 만든다. 실제 정렬 결과가
/// 들어올 자리에 이 픽스처를 끼워, 화면과 채점 경로를 먼저 완성한다.
/// 아키텍처 문서의 FixtureAligner와 같은 역할이다.
///
/// `tools/export_samples.py`가 파이썬 엔진을 돌려 생성한다.
public struct SampleLibrary: Decodable, Sendable {
    public let version: Int
    public let clips: [SampleClip]

    /// 번들에서 읽는다. 실패하면 빈 라이브러리 — 화면이 비어 보일 뿐 죽지 않는다.
    public static func load() -> SampleLibrary {
        guard let url = Bundle.module.url(forResource: "samples", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let parsed = try? JSONDecoder().decode(SampleLibrary.self, from: data)
        else {
            assertionFailure("samples.json을 읽지 못했습니다")
            return SampleLibrary(version: 0, clips: [])
        }
        return parsed
    }
}

public struct SampleClip: Decodable, Identifiable, Sendable {
    public let id: String
    public let transcript: String
    public let kind: String
    public let difficulty: Int
    public let attempts: [SampleAttempt]

    public var words: [String] {
        transcript.split(separator: " ").map(String.init)
    }
}

public struct SampleAttempt: Decodable, Identifiable, Sendable {
    public let id: String
    public let label: String
    public let profile: String
    public let linkingScore: Double
    public let speechRate: Double
    public let words: [TimedWord]

    public struct TimedWord: Decodable, Sendable {
        public let text: String
        public let start: Double
        public let end: Double
    }

    /// Domain이 이해하는 형태로 바꾼다.
    public var domainWords: [Word] {
        words.map { Word(text: $0.text, start: $0.start, end: $0.end) }
    }
}
