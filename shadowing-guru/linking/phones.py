"""ARPAbet 음소 분류.

CMUdict 표기를 기준으로 한다. 모음에는 강세 숫자(0/1/2)가 붙으므로
비교 전에 strip_stress()로 제거한다.
"""

VOWELS = {
    "AA", "AE", "AH", "AO", "AW", "AY",
    "EH", "ER", "EY", "IH", "IY",
    "OW", "OY", "UH", "UW",
}

STOPS      = {"P", "B", "T", "D", "K", "G"}
AFFRICATES = {"CH", "JH"}
FRICATIVES = {"F", "V", "TH", "DH", "S", "Z", "SH", "ZH", "HH"}
NASALS     = {"M", "N", "NG"}
LIQUIDS    = {"L", "R"}
GLIDES     = {"W", "Y"}

CONSONANTS = STOPS | AFFRICATES | FRICATIVES | NASALS | LIQUIDS | GLIDES

# 치경음 — /j/ 앞에서 구개음화한다
ALVEOLAR = {"T", "D", "S", "Z", "N", "L"}

# 조음위치 — 비음 동화 판정용
LABIAL = {"P", "B", "M", "F", "V"}
VELAR  = {"K", "G", "NG"}

# 전설·고모음 — 뒤에 모음이 오면 /j/ 활음이 삽입된다 (he is → heyiz)
FRONT_HIGH = {"IY", "IH", "EY", "AY", "OY"}

# 후설·원순모음 — 뒤에 모음이 오면 /w/ 활음이 삽입된다 (go on → gowon)
BACK_ROUND = {"UW", "UH", "OW", "AW"}

# 축약되는 기능어. 한국인 학습자는 이들을 또박또박 완전형으로 발음하는 경향이 있다.
FUNCTION_WORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "for", "from",
    "at", "in", "on", "as", "that", "than", "is", "are", "was", "were",
    "am", "be", "been", "have", "has", "had", "do", "does", "did",
    "can", "could", "will", "would", "shall", "should", "must",
    "he", "him", "his", "her", "them", "us", "you", "your", "some",
}

# /h/ 탈락 대상 — 강세 없는 대명사·조동사
H_DROP_WORDS = {"he", "him", "his", "her", "have", "has", "had"}


def strip_stress(phone: str) -> str:
    """AH0 -> AH"""
    return phone.rstrip("012")


def is_vowel(phone: str) -> bool:
    return strip_stress(phone) in VOWELS


def is_consonant(phone: str) -> bool:
    return strip_stress(phone) in CONSONANTS


def base(phones):
    """음소열에서 강세를 제거한 리스트를 돌려준다."""
    return [strip_stress(p) for p in phones]
