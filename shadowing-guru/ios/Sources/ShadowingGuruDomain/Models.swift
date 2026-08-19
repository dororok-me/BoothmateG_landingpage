import Foundation

/// 한 경계에서 기대되는 연결 하나.
public struct LinkTag: Equatable, Sendable {
    public let rule: String
    public let nameKo: String
    /// 0…1 — 한국인 학습자 기준 채점 기여도
    public let weight: Double
    /// true면 미실현 시 확실한 비원어민 신호
    public let required: Bool
    /// 학습자 피드백 문구
    public let hint: String
    /// 연결 시 기대 표면형 (음소 표기)
    public let surface: String

    public init(rule: String, nameKo: String, weight: Double,
                required: Bool, hint: String, surface: String = "") {
        self.rule = rule
        self.nameKo = nameKo
        self.weight = weight
        self.required = required
        self.hint = hint
        self.surface = surface
    }
}

/// 단어 두 개 사이의 판정 결과.
public struct Boundary: Equatable, Sendable {
    /// 앞 단어의 인덱스
    public let index: Int
    public let left: String
    public let right: String
    public let tags: [LinkTag]
    /// OOV 등으로 판정 불가한 사유
    public let skipped: String?

    public var expectsLink: Bool { tags.contains { $0.required } }

    public var weight: Double { tags.map(\.weight).max() ?? 0 }

    /// 가중치가 가장 큰 태그. 동점이면 앞선 것 —
    /// 파이썬 `max()`와 Swift `max(by:)` 모두 첫 번째를 유지한다.
    public var primaryTag: LinkTag? {
        tags.max { $0.weight < $1.weight }
    }
}

/// 타임스탬프가 붙은 단어. 정렬기가 채운다.
public struct Word: Equatable, Sendable {
    public let text: String
    public let start: Double
    public let end: Double

    public init(text: String, start: Double, end: Double) {
        self.text = text
        self.start = start
        self.end = end
    }

    public var duration: Double { end - start }
}

public enum Verdict: String, Sendable {
    case linked, partial, broken
    case notApplicable = "n/a"
}

public struct BoundaryResult: Sendable {
    public let boundary: Boundary
    /// 초
    public let gap: Double
    /// 평균 음소 길이 배수
    public let normGap: Double
    /// 앞 단어 길이 / 기대 길이
    public let inflation: Double?
    public let verdict: Verdict
    /// 0…1 연속 실현도
    public let credit: Double
    public let reason: String

    public var isFailure: Bool {
        boundary.expectsLink && verdict == .broken
    }
}

public struct Report: Sendable {
    public let words: [Word]
    public let results: [BoundaryResult]
    public let meanPhone: Double
    /// 음절/초
    public let speechRate: Double
    /// 0…100
    public let score: Double

    public var judged: [BoundaryResult] { results.filter { $0.verdict != .notApplicable } }
    public var failures: [BoundaryResult] { results.filter(\.isFailure) }

    /// 고칠 점 하나 — 가장 무거운 실패 경계.
    public var focus: BoundaryResult? {
        failures.max { $0.boundary.weight < $1.boundary.weight }
    }
}
