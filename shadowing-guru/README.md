# 연음 분석 엔진 (P1 프로토타입)

Shadowing Guru 설계 기준서 **P1** — 5개 채점 항목 중 유일하게 기성 기술로
해결되지 않는 부분을 먼저 검증한다. 나머지 4개(발음·강세·속도·피치)는 이미
가능한 것이 확인됐으므로, **여기가 실패하면 제품 전제가 바뀐다.**

## 무엇을 하는가

영어 발화에서 **이어져야 할 자리를 이었는가**를 판정한다.

한국어는 어말 자음군이 없고 폐음절 뒤에 `/ɯ/`를 삽입하는 경향이 강하다.
그래서 한국인 학습자는 `turn it off`를 "턴-잇-오프"처럼 세 덩어리로 끊어 읽는다.
원어민은 "터-니-토프"에 가깝게 한 덩어리로 낸다. 이 차이를 잡아낸다.

```
$ python3 -m linking.cli predict "I want to talk about the news"

연음 밀도 0.43   경계 6개

          want | to            필수 w=0.8  REDUCE, GEMINATE, ELIDE_T, UNRELEASED
               |                 → 'to'는 힘을 빼고 짧게 흘리세요
          talk | about         필수 w=1.0  LINK_CV
               |                 → 'talk'의 끝소리 /K/를 'about'에 붙여 발음하세요
```

## 구조

```
linking/
  phones.py      ARPAbet 음소 분류
  lexicon.py     CMUdict 조회 (126k 엔트리). OOV는 추측하지 않고 건너뛴다
  rules.py       연음 규칙 14종 — 텍스트만으로 기대 연결 판정
  detect.py      경계 간격 + 길이 팽창으로 실현 여부 검출
  importers.py   WhisperX / MFA TextGrid / words JSON 수용   ← 기본 입력 경로
  align.py       자체 강제 정렬 (선택. torch + 모델 가중치 필요)
  cli.py
samples/synth.py 합성 타이밍 생성기 (로직 검증용)
tests/           25개
```

## 설치 · 실행

```bash
pip install cmudict numpy          # 필수는 이 둘뿐

python3 -m linking.cli predict "turn it off"        # 텍스트만 (오디오 불필요)
python3 -m linking.cli demo                         # 합성 프로파일 비교
python3 -m linking.cli score aligned.json           # 정렬 결과 채점
python3 tests/test_rules.py && python3 tests/test_detect.py
```

실제 오디오는 WhisperX로 정렬한 뒤 넣는다. 이게 스펙 §3의 실제 파이프라인이다.

```bash
whisperx clip.wav --output_format json --align_model WAV2VEC2_ASR_LARGE_LV60K_960H
python3 -m linking.cli score clip.json --format whisperx
```

## 설계상 중요한 결정 두 가지

### 1. 임계값을 절대 시간이 아니라 화자 평균 음소 길이로 정규화한다

기준서 초안의 "간격 50ms 초과 시 감점"은 **틀렸다.** 느리게 말하는 사람은 모든
간격이 길어서 무조건 감점된다. 화자의 평균 음소 길이로 나눈 배수로 판정한다.

`tests/test_detect.py::test_rate_normalization`이 이걸 지킨다 — 2배 느리게
말해도 끊는 비율이 같으면 점수가 동일해야 한다.

### 2. 신호를 두 개 본다

간격만 보면 놓치는 경우가 있다. 삽입 모음이 앞 단어에 흡수되면 간격은 0인데
연음은 실패한 상태다.

| 신호 | 잡아내는 것 |
|---|---|
| 경계 간격 (정규화) | 끊어 읽기 |
| 앞 단어 길이 팽창 | 어말 모음 삽입 (`/ɯ/`) |

둘 중 나쁜 쪽을 택한다. `test_epenthesis_is_detected`가 간격 0 + 팽창 2배
케이스를 검증한다.

## 규칙 14종

한국인 학습자 기준 중요도로 가중치를 매겼다. 두 축을 곱했다 —
못 지켰을 때 비원어민으로 들리는 정도 × 실제로 자주 틀리는 정도.

| 규칙 | 예 | 가중치 | 필수 |
|---|---|---|---|
| `LINK_CV` | turn it → 터-니 | 1.0 | ● |
| `REDUCE` | want **to** → tə | 0.8 | ● |
| `GLIDE_Y` | he is → heyiz | 0.7 | ● |
| `GLIDE_W` | go on → gowon | 0.7 | ● |
| `LINK_R` | her own | 0.6 | ● |
| `GEMINATE` | big girl → g 한 번 | 0.6 | ● |
| `ELIDE_T` | next day → nex day | 0.5 | |
| `ELIDE_D` | old man → ol man | 0.5 | |
| `FLAP` | get it → gedit | 0.4 | |
| `PALATALIZE` | did you → didja | 0.4 | |
| `UNRELEASED` | big cat | 0.4 | |
| `H_DROP` | tell him → tell'im | 0.4 | |
| `NASAL_ASSIM` | in bed → im bed | 0.3 | |
| `DH_ASSIM` | in the | 0.3 | |

탄설음화·구개음화를 낮게 둔 이유는 **안 해도 의사소통에 지장이 없기** 때문이다.
반면 `LINK_CV` 실패는 즉시 비원어민으로 들린다.

## 검증 상태

### 확인된 것

판별 로직이 동작한다. 합성 타이밍 3개 프로파일이 깨끗하게 분리된다.

| 프로파일 | 점수 (12회 평균) |
|---|---|
| 원어민 | 95–97 |
| 중급 | 37–58 |
| 초급 | 1–10 |

테스트 25개 전부 통과 (규칙 15 + 검출 10).

### 확인되지 않은 것 — 여기가 P1의 남은 절반

**합성 데이터는 실제 정확도를 증명하지 못한다.** `samples/synth.py`의 프로파일은
문헌과 관찰에 기반한 *가정*이다. 가정대로 만든 데이터를 가정대로 판별한 것에
가깝다. 다음이 필요하다.

- [ ] **실제 한국인 화자 녹음** — 같은 문장 20개 × 화자 10명 이상
- [ ] **원어민 대조군** — 동일 문장
- [ ] 임계값 재조정 — `GAP_LINKED` 0.35 / `GAP_BROKEN` 1.30 / `INFLATION_OK` 1.25 /
      `INFLATION_BAD` 1.75 는 전부 음향적 추정치다
- [ ] 정렬기 오차의 영향 — WhisperX 단어 경계 오차가 간격 측정을 얼마나 흔드는가
- [ ] `ELIDE_T`를 필수로 올릴지 판단 — 현재 `next day delivery`의 연음 밀도가
      0.00으로 나와 난이도(§5)를 과소평가한다

녹음만 확보되면 임계값 재조정은 하루면 끝난다. **판별 로직 자체는 서 있다.**

## 알려진 한계

- CMUdict에 없는 단어(고유명사·신조어)는 판정에서 제외한다. 추측하지 않는다 —
  틀린 음소열로 만든 기대 태그는 그대로 오채점이 되기 때문이다.
- 발음 변이형은 사전 첫 항목만 쓴다. `either` 같은 복수 발음 단어에서
  기대 태그가 달라질 수 있다.
- 미국식 기준이다. `FLAP`은 영국식에서 적용되지 않는다. 카탈로그에 `accent`
  필드가 있으므로 규칙 집합을 악센트별로 분기해야 한다 (미구현).
- 문장 경계·쉼표의 의도적 휴지를 아직 구분하지 않는다. 구두점이 있는 자리는
  간격 판정에서 빼야 한다.
