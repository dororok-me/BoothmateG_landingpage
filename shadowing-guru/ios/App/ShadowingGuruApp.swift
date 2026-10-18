import SwiftUI
import ShadowingGuruUI

/// 앱 진입점.
///
/// 이 파일만 Xcode 앱 타겟에 있고, 나머지 화면과 로직은 전부 Swift 패키지에
/// 있다. 그래야 `swift test` 한 줄로 검증되고, 앱 타겟은 껍데기로 남는다.
@main
struct ShadowingGuruApp: App {
    var body: some Scene {
        WindowGroup {
            LibraryView()
        }
    }
}
