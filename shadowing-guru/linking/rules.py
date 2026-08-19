"""연음(connected speech) 규칙 엔진.

텍스트만으로 "이 경계는 이어져야 한다"를 판정한다. 원본 오디오가 필요 없으므로
YouTube 임베드(몰입 모드)에서도 동작한다.

가중치는 **한국인 학습자 기준 중요도**다. 두 축을 곱해서 정했다.
  (1) 못 지켰을 때 비원어민으로 들리는 정도
  (2) 한국어 음운 체계 때문에 실제로 자주 틀리는 정도

한국어는 어말 자음군이 없고 폐음절 뒤에 /ɯ/를 삽입하는 경향이 강하다.
그래서 LINK_CV와 기능어 축약이 압도적으로 중요하고, 탄설음화나 구개음화는
안 해도 의사소통에 지장이 없어 후순위다.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from . import phones as P
from . import lexicon as L


@dataclass
class LinkTag:
    rule: str
    name_ko: str
    weight: float          # 0..1 — 채점 기여도
    required: bool         # True면 미실현 시 확실한 비원어민 신호
    hint: str              # 학습자 피드백 문구
    surface: str = ""      # 연결 시 기대 표면형 (음소 표기)


@dataclass
class Boundary:
    index: int             # 앞 단어의 인덱스
    left: str
    right: str
    tags: List[LinkTag] = field(default_factory=list)
    skipped: Optional[str] = None   # OOV 등으로 판정 불가한 사유

    @property
    def expects_link(self) -> bool:
        return any(t.required for t in self.tags)

    @property
    def weight(self) -> float:
        return max((t.weight for t in self.tags), default=0.0)

    @property
    def primary_tag(self) -> Optional[LinkTag]:
        if not self.tags:
            return None
        return max(self.tags, key=lambda t: t.weight)


# ---------------------------------------------------------------- 경계 규칙

def _r_link_cv(p1, p2, w1, w2):
    """자음 + 모음 → 재음절화. 한국인 학습자 최대 약점."""
    if P.is_consonant(p1) and P.is_vowel(p2):
        return LinkTag(
            "LINK_CV", "자음-모음 연결", 1.0, True,
            f"'{w1}'의 끝소리 /{p1}/를 '{w2}'에 붙여 한 덩어리로 발음하세요",
            f"…{p1}·{p2}…",
        )
    return None


def _r_reduce_target(p1, p2, w1, w2):
    """기능어 앞 경계 — 뒤 단어가 축약되어야 한다."""
    if L.normalize(w2) in P.FUNCTION_WORDS and L.syllable_count(w2) == 1:
        return LinkTag(
            "REDUCE", "기능어 축약", 0.8, True,
            f"'{w2}'는 힘을 빼고 짧게 흘리세요. 또박또박 읽으면 어색합니다",
        )
    return None


def _r_glide_y(p1, p2, w1, w2):
    """전설·고모음 + 모음 → /j/ 활음 삽입. he is → heyiz"""
    if p1 in P.FRONT_HIGH and P.is_vowel(p2):
        return LinkTag(
            "GLIDE_Y", "y 활음 연결", 0.7, True,
            f"'{w1}'와 '{w2}' 사이에 살짝 /y/를 넣어 이으세요",
            f"…{p1}·Y·{p2}…",
        )
    return None


def _r_glide_w(p1, p2, w1, w2):
    """후설·원순모음 + 모음 → /w/ 활음 삽입. go on → gowon"""
    if p1 in P.BACK_ROUND and P.is_vowel(p2):
        return LinkTag(
            "GLIDE_W", "w 활음 연결", 0.7, True,
            f"'{w1}'와 '{w2}' 사이에 살짝 /w/를 넣어 이으세요",
            f"…{p1}·W·{p2}…",
        )
    return None


def _r_link_r(p1, p2, w1, w2):
    """ER(r성 모음) + 모음 → /r/로 이어진다. her own, far away"""
    if p1 == "ER" and P.is_vowel(p2):
        return LinkTag(
            "LINK_R", "r 연결", 0.6, True,
            f"'{w1}'의 r 소리를 '{w2}'로 굴려 넘기세요",
            f"…ER·R·{p2}…",
        )
    return None


def _r_geminate(p1, p2, w1, w2):
    """동일 자음 연쇄 → 하나로 길게. big girl, this Sunday"""
    if p1 == p2 and P.is_consonant(p1):
        return LinkTag(
            "GEMINATE", "겹자음 축약", 0.6, True,
            f"/{p1}/를 두 번 발음하지 말고 한 번 길게 내세요",
            f"…{p1}ː…",
        )
    return None


def _r_elide_t(p1, p2, w1, w2):
    """자음군 뒤 /t/ 탈락. next day → nex day"""
    pron = L.primary(w1)
    if not pron or len(pron) < 2:
        return None
    if p1 == "T" and P.is_consonant(pron[-2]) and P.is_consonant(p2):
        return LinkTag(
            "ELIDE_T", "t 탈락", 0.5, False,
            f"'{w1}'의 끝 t는 거의 들리지 않게 생략하세요",
        )
    return None


def _r_elide_d(p1, p2, w1, w2):
    """자음군 뒤 /d/ 탈락. old man → ol man"""
    pron = L.primary(w1)
    if not pron or len(pron) < 2:
        return None
    if p1 == "D" and P.is_consonant(pron[-2]) and P.is_consonant(p2):
        return LinkTag(
            "ELIDE_D", "d 탈락", 0.5, False,
            f"'{w1}'의 끝 d는 거의 들리지 않게 생략하세요",
        )
    return None


def _r_flap(p1, p2, w1, w2):
    """모음 사이 /t,d/ → 탄설음. get it → gedit (미국식)"""
    pron = L.primary(w1)
    if not pron or len(pron) < 2:
        return None
    if p1 in ("T", "D") and P.is_vowel(pron[-2]) and P.is_vowel(p2):
        return LinkTag(
            "FLAP", "탄설음화", 0.4, False,
            f"'{w1}'의 t/d를 한국어 'ㄹ'에 가깝게 굴리세요 (미국식)",
        )
    return None


def _r_palatalize(p1, p2, w1, w2):
    """치경음 + /j/ → 구개음화. did you → didja"""
    if p1 in ("T", "D", "S", "Z") and p2 == "Y":
        table = {"T": "CH", "D": "JH", "S": "SH", "Z": "ZH"}
        return LinkTag(
            "PALATALIZE", "구개음화", 0.4, False,
            f"'{w1} {w2}'를 붙여 /{table[p1]}/ 소리로 뭉치세요",
            f"…{table[p1]}…",
        )
    return None


def _r_unreleased(p1, p2, w1, w2):
    """파열음 + 파열음/파찰음 → 앞 파열음 미파. big cat"""
    if p1 in P.STOPS and (p2 in P.STOPS or p2 in P.AFFRICATES):
        return LinkTag(
            "UNRELEASED", "미파음", 0.4, False,
            f"'{w1}'의 끝 /{p1}/를 터뜨리지 말고 멈춘 채 넘어가세요",
        )
    return None


def _r_h_drop(p1, p2, w1, w2):
    """강세 없는 기능어의 /h/ 탈락. tell him → tell'im"""
    if p2 == "HH" and L.normalize(w2) in P.H_DROP_WORDS:
        return LinkTag(
            "H_DROP", "h 탈락", 0.4, False,
            f"'{w2}'의 h를 빼고 앞 단어에 붙이세요",
        )
    return None


def _r_nasal_assim(p1, p2, w1, w2):
    """/n/ 조음위치 동화. in bed → im bed"""
    if p1 == "N" and (p2 in P.LABIAL or p2 in P.VELAR):
        target = "M" if p2 in P.LABIAL else "NG"
        return LinkTag(
            "NASAL_ASSIM", "비음 동화", 0.3, False,
            f"'{w1}'의 n을 /{target}/에 가깝게 바꿔 이으세요",
        )
    return None


def _r_dh_assim(p1, p2, w1, w2):
    """/n,l,s,z/ + /ð/ 동화. in the"""
    if p1 in ("N", "L", "S", "Z") and p2 == "DH":
        return LinkTag(
            "DH_ASSIM", "th 동화", 0.3, False,
            f"'{w2}'의 th를 앞 자음에 녹여 이으세요",
        )
    return None


BOUNDARY_RULES = [
    _r_link_cv,
    _r_reduce_target,
    _r_glide_y,
    _r_glide_w,
    _r_link_r,
    _r_geminate,
    _r_elide_t,
    _r_elide_d,
    _r_flap,
    _r_palatalize,
    _r_unreleased,
    _r_h_drop,
    _r_nasal_assim,
    _r_dh_assim,
]


def analyze_boundary(index: int, w1: str, w2: str) -> Boundary:
    """단어 두 개 사이의 기대 연결을 판정한다."""
    b = Boundary(index=index, left=w1, right=w2)

    p1 = L.final_phone(w1)
    p2 = L.initial_phone(w2)
    if p1 is None or p2 is None:
        missing = w1 if p1 is None else w2
        b.skipped = f"OOV:{missing}"
        return b

    for rule in BOUNDARY_RULES:
        tag = rule(p1, p2, w1, w2)
        if tag:
            b.tags.append(tag)

    return b


def analyze_text(words: List[str]) -> List[Boundary]:
    """문장 전체의 경계를 판정한다."""
    return [
        analyze_boundary(i, words[i], words[i + 1])
        for i in range(len(words) - 1)
    ]


def link_density(boundaries: List[Boundary]) -> float:
    """연음 밀도 — 난이도 산출(스펙 §5)에 쓰인다."""
    judged = [b for b in boundaries if not b.skipped]
    if not judged:
        return 0.0
    return sum(1 for b in judged if b.expects_link) / len(judged)
