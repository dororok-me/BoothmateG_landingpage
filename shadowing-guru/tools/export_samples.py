"""UI가 쓸 샘플 시도(attempt) 데이터를 만든다.

첫 슬라이스는 오디오·정렬기 없이 결과 화면만 구현한다. 실제 정렬 결과가
들어올 자리에 이 픽스처를 끼워 넣어, 화면과 채점 파이프라인을 먼저 완성한다.
아키텍처 문서의 FixtureAligner 개념과 같은 역할이다.

    python3 tools/export_samples.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linking.detect import evaluate
from samples.synth import synthesize

OUT = (Path(__file__).resolve().parent.parent
       / "ios/Sources/ShadowingGuruUI/Resources/samples.json")

# 규칙을 골고루 태우는 문장들. 실제 뉴스·학습용 클립에서 나올 법한 길이로 골랐다.
CLIPS = [
    ("turn it off and take a look",        "일상 대화",   1),
    ("I want to talk about the news",      "뉴스 도입",   2),
    ("he is in bed with an old man",       "서술문",     2),
    ("did you get it at eight",            "질문",      3),
    ("far away from her own home",         "묘사",      3),
]

PROFILES = [
    ("native",       "원어민"),
    ("intermediate", "중급 학습자"),
    ("learner",      "입문 학습자"),
]


def build():
    clips = []
    for ci, (sentence, kind, difficulty) in enumerate(CLIPS):
        attempts = []
        for pi, (profile, label) in enumerate(PROFILES):
            words = synthesize(sentence, profile, seed=ci * 10 + pi)
            rep = evaluate(words)
            attempts.append({
                "id": f"{ci}-{profile}",
                "label": label,
                "profile": profile,
                "linkingScore": round(rep.score, 2),
                "speechRate": round(rep.speech_rate, 3),
                "words": [
                    {"text": w.text, "start": round(w.start, 4), "end": round(w.end, 4)}
                    for w in words
                ],
            })
        clips.append({
            "id": f"clip-{ci}",
            "transcript": sentence,
            "kind": kind,
            "difficulty": difficulty,
            "attempts": attempts,
        })
    return {"version": 1, "clips": clips}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = build()
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)

    n_att = sum(len(c["attempts"]) for c in data["clips"])
    print(f"{OUT.name}  {OUT.stat().st_size/1024:.0f}KB")
    print(f"  클립 {len(data['clips'])}개 · 시도 {n_att}개")
    for c in data["clips"]:
        scores = "  ".join(f"{a['label']} {a['linkingScore']:.0f}" for a in c["attempts"])
        print(f'  "{c["transcript"]}"  →  {scores}')


if __name__ == "__main__":
    main()
