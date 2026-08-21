"""파이썬 엔진의 출력을 골든 픽스처로 내보낸다.

Swift 포팅이 파이썬과 같은 결과를 내는지 검사할 계약이다. 작성 환경에
Swift 툴체인이 없어 컴파일 검증을 못 하므로, 대신 이 픽스처가 번역 오류를
이름 붙은 테스트 실패로 드러나게 한다.

    python3 tools/export_golden.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linking import lexicon as L
from linking.rules import analyze_boundary, analyze_text, link_density
from linking.detect import Word, evaluate
from samples.synth import synthesize

OUT = (Path(__file__).resolve().parent.parent
       / "ios/Tests/ShadowingGuruDomainTests/Resources/golden.json")

R = 6  # 부동소수 비교 자릿수


def r(x):
    return None if x is None else round(float(x), R)


# ---- 사전 조회 ---------------------------------------------------------

LEXICON_WORDS = [
    "turn", "it", "off", "and", "take", "a", "look", "next", "day",
    "did", "you", "get", "go", "on", "he", "is", "in", "bed", "big",
    "girl", "with", "an", "old", "man", "want", "to", "talk", "about",
    "the", "news", "tell", "him", "said", "hello", "this", "sunday",
    "at", "eight", "far", "away", "from", "her", "own", "home",
    "strength", "don't", "well-known", "cars", "time", "miss", "cat",
    "Turn", "off,", "look.", "I", "zzqqx",
]


def lexicon_cases():
    out = []
    for w in LEXICON_WORDS:
        p = L.primary(w)
        out.append({
            "word": w,
            "phones": list(p) if p else None,
            "syllables": L.syllable_count(w),
            "normalized": L.normalize(w),
        })
    return out


# ---- 규칙 -------------------------------------------------------------

RULE_PAIRS = [
    # LINK_CV
    ("turn", "it"), ("talk", "about"), ("an", "old"), ("him", "I"),
    ("far", "away"), ("at", "eight"), ("with", "an"), ("is", "in"),
    # 비대상
    ("you", "get"), ("the", "news"), ("I", "want"), ("to", "talk"),
    ("girl", "with"), ("own", "home"), ("a", "look"), ("said", "hello"),
    # 활음
    ("he", "is"), ("go", "on"), ("sunday", "at"),
    # r 연결
    ("her", "own"),
    # 겹자음
    ("big", "girl"), ("this", "sunday"), ("want", "to"),
    # 탈락
    ("next", "day"), ("old", "man"), ("and", "take"),
    # 탄설음
    ("get", "it"), ("it", "off"),
    # 구개음화
    ("did", "you"), ("miss", "you"), ("did", "it"),
    # 미파음
    ("big", "cat"), ("big", "man"),
    # h 탈락
    ("tell", "him"),
    # 비음 동화
    ("in", "bed"), ("in", "cars"), ("in", "time"),
    # 기능어 축약
    ("about", "the"), ("take", "a"), ("from", "her"),
    # OOV
    ("zzqqx", "it"), ("turn", "zzqqx"),
    # 표기 변형
    ("Turn", "it,"), ("off,", "and"),
]


def rule_cases():
    out = []
    for w1, w2 in RULE_PAIRS:
        b = analyze_boundary(0, w1, w2)
        out.append({
            "left": w1,
            "right": w2,
            "skipped": b.skipped,
            "tags": [t.rule for t in b.tags],
            "expectsLink": b.expects_link,
            "weight": r(b.weight),
            "primaryTag": b.primary_tag.rule if b.primary_tag else None,
        })
    return out


SENTENCES = [
    "turn it off",
    "turn it off and take a look",
    "I want to talk about the news",
    "I want to talk about the news today",
    "he is in bed with an old man",
    "did you get it at eight",
    "next day delivery",
    "far away from her own home",
    "big girl with an old man",
    "this sunday at eight",
    "tell him I said hello",
    "go on and take a look",
]


def sentence_cases():
    out = []
    for s in SENTENCES:
        ws = s.split()
        bs = analyze_text(ws)
        out.append({
            "sentence": s,
            "boundaryCount": len(bs),
            "linkDensity": r(link_density(bs)),
            "requiredIndices": [b.index for b in bs if b.expects_link],
        })
    return out


# ---- 검출 -------------------------------------------------------------

def detect_case(name, words):
    rep = evaluate(words)
    return {
        "name": name,
        "words": [{"text": w.text, "start": r(w.start), "end": r(w.end)}
                  for w in words],
        "meanPhone": r(rep.mean_phone),
        "speechRate": r(rep.speech_rate),
        "score": r(rep.score),
        "focusIndex": rep.focus.boundary.index if rep.focus else None,
        "results": [{
            "index": res.boundary.index,
            "verdict": res.verdict,
            "gap": r(res.gap),
            "normGap": r(res.norm_gap),
            "inflation": r(res.inflation),
            "credit": r(res.credit),
        } for res in rep.results],
    }


def detect_cases():
    out = []

    # 합성 프로파일 — 결정적 시드
    for sentence in ("turn it off and take a look",
                     "I want to talk about the news",
                     "he is in bed with an old man"):
        for prof in ("native", "intermediate", "learner"):
            for seed in (0, 1, 2):
                ws = synthesize(sentence, prof, seed=seed)
                out.append(detect_case(f"{prof}|{seed}|{sentence}", ws))

    # 손으로 만든 경계 조건
    out.append(detect_case("pause", [
        Word("turn", 0.00, 0.30), Word("it", 0.60, 0.75), Word("off", 0.78, 1.00)]))
    out.append(detect_case("epenthesis", [
        Word("turn", 0.00, 0.62), Word("it", 0.62, 0.74), Word("off", 0.74, 0.92)]))
    out.append(detect_case("oov-mixed", [
        Word("turn", 0.0, 0.25), Word("it", 0.26, 0.38),
        Word("zzqqx", 0.39, 0.60), Word("off", 0.61, 0.80)]))
    out.append(detect_case("clean", [
        Word("turn", 0.200, 0.450), Word("it", 0.452, 0.562),
        Word("off", 0.564, 0.784)]))

    # 속도 정규화 — 2배 느린 화자는 같은 점수여야 한다
    fast = synthesize("turn it off and take a look", "native", seed=3)
    slow = [Word(w.text, w.start * 2, w.end * 2) for w in fast]
    out.append(detect_case("rate-fast", fast))
    out.append(detect_case("rate-slow-2x", slow))

    return out


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "note": "linking 엔진 파이썬 구현의 출력. Swift 포팅은 이와 일치해야 한다.",
        "tolerance": 1e-6,
        "lexicon": lexicon_cases(),
        "rules": rule_cases(),
        "sentences": sentence_cases(),
        "detect": detect_cases(),
    }
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    print(f"{OUT.name}  {OUT.stat().st_size/1024:.0f}KB")
    for k in ("lexicon", "rules", "sentences", "detect"):
        print(f"  {k:<10} {len(data[k]):>4}개")
    print(f"  검출 경계 합계 {sum(len(c['results']) for c in data['detect']):>4}개")


if __name__ == "__main__":
    main()
