import SwiftUI
import ShadowingGuruDomain

/// 단어 사이의 연결 상태를 그리는 표식.
///
/// 연음은 *단어와 단어 사이*의 현상이므로, 단어가 아니라 그 사이를 칠한다.
/// 이어졌으면 두 단어를 잇는 선이, 끊겼으면 끊어진 두 토막이 보인다.
struct BoundaryConnector: View {
    let verdict: Verdict
    let isSelected: Bool

    private var color: Color { Palette.color(for: verdict) }

    private var width: CGFloat {
        switch verdict {
        case .linked:        return 12
        case .partial:       return 16
        case .broken:        return 20
        case .notApplicable: return 10
        }
    }

    var body: some View {
        ZStack {
            switch verdict {
            case .linked:
                Capsule()
                    .fill(color)
                    .frame(width: width, height: 3)

            case .partial:
                Capsule()
                    .fill(color.opacity(0.55))
                    .frame(width: width, height: 3)
                    .overlay(
                        Capsule()
                            .fill(Color.clear)
                            .frame(width: 4, height: 3)
                    )

            case .broken:
                // 끊긴 두 토막 — 사이가 비어 있다는 것이 곧 판정이다
                HStack(spacing: width - 8) {
                    Capsule().fill(color).frame(width: 4, height: 3)
                    Capsule().fill(color).frame(width: 4, height: 3)
                }
                .frame(width: width)

            case .notApplicable:
                Color.clear.frame(width: width, height: 3)
            }
        }
        .frame(width: width, height: 3)
        .padding(.horizontal, 2)
        .opacity(isSelected ? 1 : 0.9)
        .scaleEffect(isSelected ? 1.3 : 1, anchor: .center)
        .animation(.easeOut(duration: 0.15), value: isSelected)
    }
}

/// 단어 하나 + 그 뒤에 오는 경계.
///
/// 경계를 뒤따르는 단어에 묶어두면 줄바꿈 때 경계만 홀로 떨어지지 않는다.
struct WordToken: View {
    let word: String
    let result: BoundaryResult?
    let isSelected: Bool
    let onTapBoundary: () -> Void

    var body: some View {
        HStack(spacing: 0) {
            Text(word)
                .font(.system(size: 26, weight: .regular, design: .serif))
                .foregroundStyle(.primary)

            if let result {
                Button(action: onTapBoundary) {
                    BoundaryConnector(verdict: result.verdict, isSelected: isSelected)
                        .frame(width: 34, height: 40)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("\(word) 다음 경계, \(result.verdict.koreanLabel)")
            }
        }
    }
}

/// 문장 전체. 단어는 검고, 판정은 그 사이에 있다.
struct SentenceView: View {
    let words: [String]
    let results: [BoundaryResult]
    @Binding var selectedIndex: Int?

    var body: some View {
        FlowLayout(spacing: 0, lineSpacing: 14) {
            ForEach(Array(words.enumerated()), id: \.offset) { index, word in
                WordToken(
                    word: word,
                    result: index < results.count ? results[index] : nil,
                    isSelected: selectedIndex == index,
                    onTapBoundary: {
                        selectedIndex = (selectedIndex == index) ? nil : index
                    }
                )
            }
        }
    }
}
