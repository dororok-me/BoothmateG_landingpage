import SwiftUI
import ShadowingGuruDomain

/// 연습할 클립 목록.
///
/// 실제 앱에서는 카탈로그·팟캐스트·임포트 파일이 섞여 들어오는 자리다.
/// 지금은 번들 샘플만 보여준다.
public struct LibraryView: View {
    private let library: SampleLibrary

    public init(library: SampleLibrary = .load()) {
        self.library = library
    }

    public var body: some View {
        NavigationStack {
            List(library.clips) { clip in
                NavigationLink {
                    ResultView(clip: clip)
                } label: {
                    ClipRow(clip: clip)
                }
            }
            .navigationTitle("Shadowing Guru")
        }
    }
}

struct ClipRow: View {
    let clip: SampleClip

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(clip.transcript)
                .font(.system(size: 17, design: .serif))
                .foregroundStyle(.primary)

            HStack(spacing: 8) {
                Chip(text: clip.kind)
                Chip(text: "난이도 \(clip.difficulty)")
            }
        }
        .padding(.vertical, 4)
    }
}

struct Chip: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption2.weight(.medium))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(.quaternary, in: Capsule())
    }
}

#Preview {
    LibraryView()
}
