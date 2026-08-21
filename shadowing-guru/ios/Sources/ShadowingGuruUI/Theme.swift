import SwiftUI
import ShadowingGuruDomain

/// 연음 판정의 의미색.
///
/// 이 앱에서 색은 장식이 아니라 판정 결과다. 연결·약함·끊김이 한눈에
/// 구분되어야 하고, 라이트/다크 양쪽에서 대비가 유지되어야 한다.
public enum Palette {
    public static let linked  = Color(red: 0.05, green: 0.55, blue: 0.52)
    public static let partial = Color(red: 0.72, green: 0.47, blue: 0.10)
    public static let broken  = Color(red: 0.72, green: 0.24, blue: 0.24)
    public static let neutral = Color.secondary

    public static func color(for verdict: Verdict) -> Color {
        switch verdict {
        case .linked:         return linked
        case .partial:        return partial
        case .broken:         return broken
        case .notApplicable:  return neutral
        }
    }

    /// 0…100 점수대별 색. 채점 결과를 한 눈에 읽히게 한다.
    public static func color(forScore score: Double) -> Color {
        switch score {
        case 80...:  return linked
        case 50..<80: return partial
        default:      return broken
        }
    }
}

extension Verdict {
    /// 화면에 쓰는 한국어 이름.
    public var koreanLabel: String {
        switch self {
        case .linked:        return "연결"
        case .partial:       return "약함"
        case .broken:        return "끊김"
        case .notApplicable: return "해당 없음"
        }
    }
}
