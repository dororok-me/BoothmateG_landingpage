# ShadowingGuruDomain

Shadowing Guru iOS 앱의 Domain 모듈. **순수 Swift** — AVFoundation·UIKit·CoreML에
의존하지 않는다. 정렬 결과(`Word` 배열)가 들어오면 연음을 판정하고 점수를 낸다.

파이썬 프로토타입 `linking/` 을 포팅한 것이다. 프로토타입의 가치는 코드가 아니라
**검증된 규칙·임계값과 테스트 케이스**이고, 그것이 여기로 넘어왔다.

## 실행

```bash
cd ios
swift test                 # macOS/Linux CLI
open Package.swift         # Xcode
```

Xcode에서는 ⌘U.

## 구성

```
Sources/ShadowingGuruDomain/
  Phones.swift       ARPAbet 음소 분류
  Lexicon.swift      CMUdict 조회 (126,052 표제어)
  Models.swift       LinkTag · Boundary · Word · BoundaryResult · Report
  Rules.swift        연음 규칙 14종
  Detector.swift     경계 검출 + 채점
  Resources/
    cmudict.txt      대표 발음, 강세 제거 (2.9MB)

Tests/ShadowingGuruDomainTests/
  GoldenParityTests.swift   파이썬과 출력 일치 검증   ← 핵심
  RulesTests.swift          규칙별 읽히는 명세
  DetectorTests.swift       검출·채점 명세
  Resources/golden.json     파이썬이 생성한 기대값
```

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

임계값(`gapLinked` 0.35 / `gapBroken` 1.30 / `inflationOK` 1.25 /
`inflationBad` 1.75)은 전부 **음향적 추정치**다. 실제 한국인 화자 녹음으로
재조정해야 한다.
