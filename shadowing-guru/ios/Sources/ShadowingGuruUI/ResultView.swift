import SwiftUI
import ShadowingGuruDomain

/// 연습 결과 화면.
///
/// 기준서 §4.9 원칙을 따른다 — 숫자를 나열하지 않고, 가장 낮은 축 하나를 골라
/// 문장 안 정확한 위치와 함께 고칠 점 한 가지만 제시한다. 점수는 요약이고
/// 진단이 본체다.
///
/// 지금은 5축 중 연음만 구현돼 있어 연음만 보여준다. 없는 점수를 자리만
/// 채워 보여주면 사용자가 그것을 실제 평가로 읽는다.
public struct ResultView: View {
    let clip: SampleClip

    @State private var attemptIndex: Int = 0
    @State private var selectedBoundary: Int?

    private let detector = Detector()

    public init(clip: SampleClip) {
        self.clip = clip
    }

    private var attempt: SampleAttempt {
        clip.attempts[min(attemptIndex, clip.attempts.count - 1)]
    }

    private var report: Report {
        detector.evaluate(attempt.domainWords)
    }

    public var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                profilePicker
                scoreHeader
                sentenceBlock
                if let index = selectedBoundary {
                    boundaryDetail(index: index)
                } else if let focus = report.focus {
                    diagnosisCard(focus)
                } else {
                    allClearCard
                }
                legend
            }
            .padding(24)
        }
        .navigationTitle("연습 결과")
    }

    // MARK: 구성 요소

    private var profilePicker: some View {
        Picker("발화 프로파일", selection: $attemptIndex) {
            ForEach(Array(clip.attempts.enumerated()), id: \.offset) { index, item in
                Text(item.label).tag(index)
            }
        }
        .pickerStyle(.segmented)
        .onChange(of: attemptIndex) { _, _ in selectedBoundary = nil }
    }

    private var scoreHeader: some View {
        let score = report.score
        return VStack(alignment: .leading, spacing: 6) {
            Text("연음")
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)

            HStack(alignment: .firstTextBaseline, spacing: 4) {
                Text("\(Int(score.rounded()))")
                    .font(.system(size: 56, weight: .semibold, design: .rounded))
                    .foregroundStyle(Palette.color(forScore: score))
                    .monospacedDigit()
                Text("/ 100")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }

            Text(String(format: "발화 속도 %.1f음절/초", report.speechRate))
                .font(.footnote)
                .foregroundStyle(.secondary)
                .monospacedDigit()
        }
    }

    private var sentenceBlock: some View {
        VStack(alignment: .leading, spacing: 12) {
            SentenceView(
                words: clip.words,
                results: report.results,
                selectedIndex: $selectedBoundary
            )
            Text("단어 사이를 눌러 판정을 확인하세요")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private func boundaryDetail(index: Int) -> some View {
        let result = report.results[index]
        let boundary = result.boundary
        return Card(accent: Palette.color(for: result.verdict)) {
            VStack(alignment: .leading, spacing: 10) {
                HStack {
                    Text("\(boundary.left) · \(boundary.right)")
                        .font(.headline)
                    Spacer()
                    Text(result.verdict.koreanLabel)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(Palette.color(for: result.verdict))
                }

                Text(result.reason)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                if let tag = boundary.primaryTag {
                    Divider()
                    Text(tag.nameKo)
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                    Text(tag.hint)
                        .font(.subheadline)
                }
            }
        }
    }

    private func diagnosisCard(_ focus: BoundaryResult) -> some View {
        Card(accent: Palette.broken) {
            VStack(alignment: .leading, spacing: 10) {
                Text("고칠 점")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(Palette.broken)

                Text("\(focus.boundary.left) \(focus.boundary.right)")
                    .font(.title3.weight(.semibold))

                Text(focus.reason)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                if let tag = focus.boundary.primaryTag {
                    Text(tag.hint)
                        .font(.subheadline)
                }
            }
        }
    }

    private var allClearCard: some View {
        Card(accent: Palette.linked) {
            VStack(alignment: .leading, spacing: 6) {
                Text("이어야 할 자리를 모두 이었습니다")
                    .font(.headline)
                Text("더 빠른 클립으로 넘어가 보세요")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var legend: some View {
        HStack(spacing: 18) {
            ForEach([Verdict.linked, .partial, .broken], id: \.rawValue) { verdict in
                HStack(spacing: 6) {
                    BoundaryConnector(verdict: verdict, isSelected: false)
                    Text(verdict.koreanLabel)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
    }
}

/// 화면 전반에서 쓰는 카드. 왼쪽 색띠가 의미를 나른다.
struct Card<Content: View>: View {
    let accent: Color
    let content: Content

    init(accent: Color, @ViewBuilder content: () -> Content) {
        self.accent = accent
        self.content = content()
    }

    var body: some View {
        HStack(spacing: 0) {
            Rectangle()
                .fill(accent)
                .frame(width: 3)
            content
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(16)
        }
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10, style: .continuous))
    }
}
