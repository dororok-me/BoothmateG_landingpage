import SwiftUI

/// 가로로 채우다 넘치면 다음 줄로 내리는 배치.
///
/// 문장을 단어 단위로 흘려야 하는데 SwiftUI에 기본 제공되는 것이 없다.
/// 가로 스크롤로 대신하면 문장을 한눈에 못 읽어 쉐도잉 화면으로는 쓸 수 없다.
struct FlowLayout: Layout {
    var spacing: CGFloat = 0
    var lineSpacing: CGFloat = 12

    /// 주어진 폭에 맞춰 각 줄에 들어갈 subview 인덱스를 계산한다.
    private func rows(maxWidth: CGFloat, subviews: Subviews) -> [[Int]] {
        var result: [[Int]] = []
        var current: [Int] = []
        var x: CGFloat = 0

        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let advance = current.isEmpty ? size.width : spacing + size.width

            if !current.isEmpty && x + advance > maxWidth {
                result.append(current)
                current = []
                x = 0
                current.append(index)
                x = size.width
            } else {
                current.append(index)
                x += advance
            }
        }
        if !current.isEmpty { result.append(current) }
        return result
    }

    private func rowHeight(_ row: [Int], _ subviews: Subviews) -> CGFloat {
        row.map { subviews[$0].sizeThatFits(.unspecified).height }.max() ?? 0
    }

    private func rowWidth(_ row: [Int], _ subviews: Subviews) -> CGFloat {
        let widths = row.reduce(CGFloat.zero) { $0 + subviews[$1].sizeThatFits(.unspecified).width }
        return widths + CGFloat(max(0, row.count - 1)) * spacing
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        guard !subviews.isEmpty else { return .zero }
        let maxWidth = proposal.width ?? .infinity
        let lines = rows(maxWidth: maxWidth, subviews: subviews)

        var height: CGFloat = 0
        var widest: CGFloat = 0
        for (index, row) in lines.enumerated() {
            if index > 0 { height += lineSpacing }
            height += rowHeight(row, subviews)
            widest = max(widest, rowWidth(row, subviews))
        }
        return CGSize(width: proposal.width ?? widest, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize,
                       subviews: Subviews, cache: inout ()) {
        guard !subviews.isEmpty else { return }
        let lines = rows(maxWidth: bounds.width, subviews: subviews)

        var y = bounds.minY
        for (index, row) in lines.enumerated() {
            if index > 0 { y += lineSpacing }
            let height = rowHeight(row, subviews)
            var x = bounds.minX

            for subviewIndex in row {
                let size = subviews[subviewIndex].sizeThatFits(.unspecified)
                subviews[subviewIndex].place(
                    at: CGPoint(x: x, y: y + (height - size.height) / 2),
                    proposal: ProposedViewSize(size)
                )
                x += size.width + spacing
            }
            y += height
        }
    }
}
