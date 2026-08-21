# ShadowingGuru (iOS)

Swift 패키지 두 개로 되어 있다.

| 타겟 | 내용 |
|---|---|
| `ShadowingGuruDomain` | 연음 판정·채점. **순수 Swift** — AVFoundation·UIKit·CoreML 의존 없음 |
| `ShadowingGuruUI` | SwiftUI 화면. Domain에만 의존 |

앱 타겟(`App/ShadowingGuruApp.swift`)은 `LibraryView()`를 띄우는 것이 전부다.
화면과 로직을 전부 패키지에 두면 `swift test` 한 줄로 검증되고, Xcode 프로젝트
파일에 손댈 일이 거의 없다.

Domain은 파이썬 프로토타입 `linking/` 을 포팅한 것이다. 프로토타입의 가치는
코드가 아니라 **검증된 규칙·임계값과 테스트 케이스**이고, 그것이 여기로 넘어왔다.

## 실행

```bash
cd ios
swift build                # 컴파일만 확인 (빠름)
swift test                 # 전체 테스트
open Package.swift         # Xcode에서 열기 — ⌘U
```

`swift build`가 먼저다. 이 포팅은 컴파일 검증 없이 작성됐으므로(아래 참조)
첫 빌드에서 오류가 나오는 것이 정상이다.

### 아이폰에서 띄우기

패키지에는 앱 타겟이 없다. Xcode 프로젝트 파일은 손으로 쓰면 깨지기 쉬워
직접 만들지 않았다.

1. Xcode → File → New → Project → **iOS App** (Interface: SwiftUI)
2. 만들어진 프로젝트에 File → Add Package Dependencies → **Add Local** → 이 `ios/` 폴더 선택
3. 타겟의 Frameworks에 `ShadowingGuruUI` 추가
4. Xcode가 만든 `ContentView.swift`와 `<이름>App.swift`를 지우고
   `App/ShadowingGuruApp.swift`를 타겟에 추가
5. 실행

## 구성

```
Sources/ShadowingGuruDomain/
  Phones.swift       ARPAbet 음소 분류
  Lexicon.swift      CMUdict 조회 (126,052 표제어)
  Models.swift       LinkTag · Boundary · Word · BoundaryResult · Report
  Rules.swift        연음 규칙 14종
  Detector.swift     경계 검출 + 채점
  Resources/cmudict.txt        대표 발음, 강세 제거 (2.9MB)

Sources/ShadowingGuruUI/
  LibraryView.swift  클립 목록
  ResultView.swift   연습 결과 — 점수 · 문장 · 고칠 점
  SentenceView.swift 단어와 경계 렌더링
  FlowLayout.swift   문장 줄바꿈 배치
  Theme.swift        판정 의미색
  SampleData.swift   번들 픽스처 적재
  Resources/samples.json       파이썬이 생성한 샘플 정렬 결과

App/
  ShadowingGuruApp.swift       Xcode 앱 타겟에 넣을 진입점

Tests/
  ShadowingGuruDomainTests/    골든 대조 · 규칙 · 검출
  ShadowingGuruUITests/        번들 적재 · 파이썬 점수 일치
```

## 화면 설계의 요점

연음은 *단어와 단어 사이*의 현상이다. 그래서 단어를 칠하지 않고
**그 사이를 칠한다.**

| 표시 | 뜻 |
|---|---|
| 이어진 선 | 연결됨 |
| 흐린 선 | 약하게 끊김 |
| 끊긴 두 토막 | 끊어 읽음 |

사이를 누르면 어떤 규칙이 걸렸고 무엇을 고쳐야 하는지 나온다.
점수는 요약이고, 화면의 본체는 **고칠 점 하나**다 (기준서 §4.9).

5축 중 지금 구현된 것은 연음뿐이라 연음만 보여준다. 없는 점수를 자리만
채워 보여주면 사용자가 그것을 실제 평가로 읽는다.

## 골든 대조가 왜 핵심인가

이 포팅은 **컴파일 검증 없이 작성됐다.** 작성 환경(Linux 컨테이너)에 Swift
툴체인을 설치할 수 없었다. 이 프로젝트에서 미검증 코드가 첫 실행에 터진 사례가
이미 두 번 있었으므로, 대신 **번역 오류가 이름 붙은 테스트 실패로 드러나도록**
설계했다.

`golden.json`은 파이썬 엔진을 실제로 돌려 만든 기대값이다.

| 대상 | 케이스 |
|---|---|
| 사전 조회 | 56 |
| 규칙 판정 | 44쌍 |
| 문장 분석 | 12 |
| 검출·채점 | 33 (경계 192개) |

첫 `swift test`에서 실패가 나면 그것이 곧 포팅 오류 목록이다. 실패 메시지에
어느 단어쌍·어느 경계인지가 찍힌다.

### 픽스처 재생성

파이썬 쪽 규칙이나 임계값을 고쳤다면 함께 갱신한다.

```bash
python3 tools/export_golden.py     # golden.json
python3 tools/export_cmudict.py    # cmudict.txt
python3 tools/export_samples.py    # samples.json
python3 tools/check_golden_shape.py  # JSON ↔ Swift Decodable 구조 대조
```

## 포팅에서 어긋나기 쉬운 지점

컴파일러가 잡아주지 않는 것들이라 주석과 테스트로 못 박아 두었다.

- **`Detector.classFactors`는 배열이어야 한다.** 이중모음과 일반 모음 집합이
  겹치므로 순서가 판정을 바꾼다. 사전으로 바꾸면 순서가 사라진다.
  → `DetectorTests.testPhoneFactorOrderMatters`
- **`Rules.boundaryRules`의 순서가 곧 `tags` 순서다.** 골든 픽스처가 순서까지 본다.
- **동점 처리.** `primaryTag`·`focus`는 가중치가 같으면 앞선 것을 택한다.
  파이썬 `max()`와 Swift `max(by:)` 모두 첫 번째를 유지하므로 일치한다.
- **임계값은 화자 평균 음소 길이로 정규화한다.** 고정 ms가 아니다.
  → `DetectorTests.testRateNormalization`

## 아직 없는 것

Domain의 나머지 축은 미착수다 — 이 모듈은 5축 중 **연음** 하나만 담는다.

- `Prosody/` F0 정규화 · DTW · prominence
- `Scoring/` 5축 통합 · 레벨별 가중 · 상관 분리
- `Difficulty/` 난이도 산출

오디오도 없다. 첫 슬라이스는 결과 화면만 다룬다 — 녹음·재생·실시간 피치는
다음 슬라이스다.

임계값(`gapLinked` 0.35 / `gapBroken` 1.30 / `inflationOK` 1.25 /
`inflationBad` 1.75)은 전부 **음향적 추정치**다. 실제 한국인 화자 녹음으로
재조정해야 한다.
