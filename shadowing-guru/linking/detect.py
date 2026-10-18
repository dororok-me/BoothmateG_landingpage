"""학습자 발화의 연음 실현 여부 검출.

입력은 강제 정렬된 단어 타임스탬프. 두 신호를 본다.

  1) 경계 간격(gap) — 이어져야 할 자리에서 끊어 읽었는가
  2) 길이 팽창(inflation) — 어말 자음 뒤에 모음을 삽입했는가

한국어는 폐음절 뒤에 /ɯ/를 삽입하는 경향이 강하다. 정렬기는 그 삽입 모음을
앞 단어 끝에 흡수시키거나 경계 간격으로 밀어내므로, 두 신호 중 하나에는 잡힌다.

임계값은 **절대 시간이 아니라 화자의 평균 음소 길이로 정규화**한다.
느리게 말하는 사람은 모든 간격이 길기 때문에 고정 ms 임계값은 오판한다.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from . import lexicon as L
from . import phones as P
from .rules import Boundary, analyze_boundary

# 음소 부류별 상대 길이. 평균 음소 길이에 곱해 기대 길이를 만든다.
DIPHTHONGS = {"AW", "AY", "EY", "OW", "OY"}

_CLASS_FACTOR = [
    (DIPHTHONGS,     1.40),
    (P.VOWELS,       1.00),
    (P.FRICATIVES,   0.85),
    (P.AFFRICATES,   0.90),
    (P.NASALS,       0.70),
    (P.LIQUIDS,      0.70),
    (P.GLIDES,       0.60),
    (P.STOPS,        0.55),
]

# 판정 임계값 — 평균 음소 길이 배수. P1 튜닝 대상.
#
# 정상 발화의 평균 음소 길이는 70~80ms다. 청자가 "끊어 읽었다"고 느끼는
# 단어 간 휴지는 대략 100ms 이상이므로 평균 음소의 1.3배 근방을 단절선으로 둔다.
# 완전 연결은 25ms 이하 — 정렬 오차 수준.
GAP_LINKED    = 0.35   # 이하면 완전 연결
GAP_BROKEN    = 1.30   # 이상이면 완전 단절

# 어말 자음 뒤 /ɯ/ 삽입은 앞 단어를 음소 하나만큼 늘린다.
# 단어당 평균 3~4음소이므로 25~35% 팽창이 삽입 한 번에 해당한다.
INFLATION_OK  = 1.25   # 이하면 삽입 없음
INFLATION_BAD = 1.75   # 이상이면 명백한 삽입

# credit -> verdict 경계
LINKED_AT  = 0.75
PARTIAL_AT = 0.35


def phone_factor(ph: str) -> float:
    for group, f in _CLASS_FACTOR:
        if ph in group:
            return f
    return 1.0


@dataclass
class Word:
    text: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def phones(self):
        return L.primary(self.text) or ()

    def expected_duration(self, mean_phone: float) -> Optional[float]:
        ph = self.phones
        if not ph:
            return None
        return sum(phone_factor(p) for p in ph) * mean_phone


@dataclass
class BoundaryResult:
    boundary: Boundary
    gap: float                  # 초
    norm_gap: float             # 평균 음소 길이 배수
    inflation: Optional[float]  # 앞 단어 길이 / 기대 길이
    verdict: str                # linked | partial | broken | n/a
    credit: float = 0.0         # 0..1 연속 실현도
    reason: str = ""

    @property
    def is_failure(self) -> bool:
        return self.boundary.expects_link and self.verdict == "broken"


@dataclass
class Report:
    words: List[Word]
    results: List[BoundaryResult] = field(default_factory=list)
    mean_phone: float = 0.0
    speech_rate: float = 0.0        # 음절/초
    score: float = 0.0              # 0..100
    focus: Optional[BoundaryResult] = None

    @property
    def judged(self):
        return [r for r in self.results if r.verdict != "n/a"]

    @property
    def failures(self):
        return [r for r in self.results if r.is_failure]


def mean_phone_duration(words: List[Word]) -> float:
    """화자의 평균 음소 길이. 무음 구간은 제외하고 발화 구간만 센다."""
    total_phones = sum(len(w.phones) for w in words if w.phones)
    total_time = sum(w.duration for w in words if w.phones)
    if total_phones == 0:
        return 0.0
    return total_time / total_phones


def speech_rate(words: List[Word]) -> float:
    """음절/초. 첫 단어 시작부터 마지막 단어 끝까지를 분모로 쓴다."""
    if len(words) < 2:
        return 0.0
    span = words[-1].end - words[0].start
    if span <= 0:
        return 0.0
    syl = sum(L.syllable_count(w.text) for w in words)
    return syl / span


def evaluate(words: List[Word]) -> Report:
    """단어 타임스탬프에서 연음 실현 여부를 판정하고 점수를 매긴다."""
    rep = Report(words=words)
    rep.mean_phone = mean_phone_duration(words)
    rep.speech_rate = speech_rate(words)

    if rep.mean_phone <= 0:
        return rep

    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i + 1]
        b = analyze_boundary(i, w1.text, w2.text)

        gap = w2.start - w1.end
        norm_gap = gap / rep.mean_phone

        exp = w1.expected_duration(rep.mean_phone)
        inflation = (w1.duration / exp) if exp and exp > 0 else None

        if b.skipped or not b.tags:
            rep.results.append(BoundaryResult(
                b, gap, norm_gap, inflation, "n/a", 0.0,
                b.skipped or "기대 연결 없음"))
            continue

        gap_credit = 1.0 - _ramp(norm_gap, GAP_LINKED, GAP_BROKEN)
        if inflation is None:
            infl_credit = 1.0
        else:
            infl_credit = 1.0 - _ramp(inflation, INFLATION_OK, INFLATION_BAD)

        credit = min(gap_credit, infl_credit)

        if credit >= LINKED_AT:
            verdict, reason = "linked", "연결됨"
        elif credit >= PARTIAL_AT:
            verdict = "partial"
            reason = f"간격 {gap*1000:.0f}ms — 약하게 끊김"
        else:
            verdict = "broken"
            if infl_credit < gap_credit:
                reason = f"'{w1.text}' 길이 {inflation:.2f}배 — 모음 삽입 의심"
            else:
                reason = f"간격 {gap*1000:.0f}ms — 끊어 읽음"

        rep.results.append(
            BoundaryResult(b, gap, norm_gap, inflation, verdict, credit, reason)
        )

    rep.score = _score(rep)
    fails = rep.failures
    if fails:
        rep.focus = max(fails, key=lambda r: r.boundary.weight)
    return rep


def _ramp(x: float, lo: float, hi: float) -> float:
    """lo 이하 0, hi 이상 1, 그 사이는 선형. 연속 감점을 만든다."""
    if x <= lo:
        return 0.0
    if x >= hi:
        return 1.0
    return (x - lo) / (hi - lo)


def _score(rep: Report) -> float:
    """기대 연결의 가중 실현률. 판정 불가 경계는 분모에서 뺀다."""
    num = den = 0.0
    for r in rep.judged:
        w = r.boundary.weight
        if w <= 0:
            continue
        den += w
        num += w * r.credit
    return 100.0 * num / den if den > 0 else 0.0
