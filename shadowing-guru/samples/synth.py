"""합성 타이밍 생성기 — 검출 로직 검증용.

실제 오디오 없이 판별 로직이 동작하는지 확인한다.
**실제 정확도 검증이 아니다.** 아래 프로파일은 문헌과 관찰에 기반한 가정이며,
진짜 검증은 실제 한국인 화자 녹음으로 해야 한다 (README 참조).

프로파일 근거
  원어민   : 필수 연결 경계에서 간격이 사실상 0. 단어 길이는 음소 구성대로.
  학습자   : (a) 이어야 할 자리에서 끊어 읽음
             (b) 어말 자음 뒤 /ɯ/ 삽입 → 앞 단어 길이 팽창
             (c) 전반적으로 느림
             (d) 모든 경계를 틀리지는 않음 — 일부는 우연히 이어짐
"""

import random

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linking import lexicon as L
from linking import phones as P
from linking.detect import Word, phone_factor
from linking.rules import analyze_boundary


PROFILES = {
    "native": dict(
        mean_phone=0.075,
        gap_link=(0.000, 0.015),      # 필수 연결 경계
        gap_other=(0.005, 0.040),
        epenthesis_rate=0.0,
        jitter=0.08,
    ),
    "learner": dict(
        mean_phone=0.095,
        gap_link=(0.090, 0.260),      # 끊어 읽음
        gap_other=(0.040, 0.150),
        epenthesis_rate=0.55,         # 어말 자음 뒤 모음 삽입 확률
        jitter=0.15,
    ),
    "intermediate": dict(
        mean_phone=0.085,
        gap_link=(0.020, 0.110),
        gap_other=(0.020, 0.080),
        epenthesis_rate=0.20,
        jitter=0.11,
    ),
}


def synthesize(sentence: str, profile: str = "native", seed: int = 0):
    """문장과 프로파일로 단어 타임스탬프를 만든다."""
    cfg = PROFILES[profile]
    rng = random.Random(seed)
    words = sentence.split()

    # 어느 경계가 필수 연결인지 미리 계산
    required = set()
    for i in range(len(words) - 1):
        b = analyze_boundary(i, words[i], words[i + 1])
        if b.expects_link:
            required.add(i)

    out = []
    t = 0.20  # 선행 무음
    for i, w in enumerate(words):
        ph = L.primary(w) or ()
        base = sum(phone_factor(p) for p in ph) * cfg["mean_phone"]
        if base <= 0:
            base = 0.25
        dur = base * (1 + rng.uniform(-cfg["jitter"], cfg["jitter"]))

        # 모음 삽입 — 어말이 자음이고 다음 단어가 모음으로 시작할 때
        if ph and P.is_consonant(ph[-1]) and rng.random() < cfg["epenthesis_rate"]:
            nxt = L.initial_phone(words[i + 1]) if i + 1 < len(words) else None
            if nxt and P.is_vowel(nxt):
                dur += cfg["mean_phone"] * rng.uniform(0.7, 1.2)

        out.append(Word(text=w, start=round(t, 4), end=round(t + dur, 4)))
        t += dur

        if i < len(words) - 1:
            lo, hi = cfg["gap_link"] if i in required else cfg["gap_other"]
            t += rng.uniform(lo, hi)

    return out


def to_json(words):
    return [{"text": w.text, "start": round(w.start, 3), "end": round(w.end, 3)}
            for w in words]
