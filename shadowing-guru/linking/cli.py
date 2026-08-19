"""연음 엔진 CLI.

  predict "turn it off"          텍스트만으로 기대 연결 표시 (오디오 불필요)
  score aligned.json             정렬 결과 채점 (WhisperX/MFA/words)
  demo                           합성 프로파일 비교 (로직 검증)
  align audio.wav script.txt     강제 정렬 후 채점 (torch 필요)
"""

import argparse
import json
import sys

from .rules import analyze_text, link_density
from .detect import Word, evaluate

_V = {"linked": "연결", "partial": "약함", "broken": "끊김", "n/a": "  - "}


def cmd_predict(args):
    words = args.text.split()
    bs = analyze_text(words)
    print(f'"{args.text}"')
    print(f"연음 밀도 {link_density(bs):.2f}   경계 {len(bs)}개\n")
    for b in bs:
        if b.skipped:
            print(f"  {b.left:>12} | {b.right:<12}  건너뜀 ({b.skipped})")
            continue
        if not b.tags:
            print(f"  {b.left:>12} | {b.right:<12}  -")
            continue
        req = "필수" if b.expects_link else "선택"
        rules = ", ".join(t.rule for t in b.tags)
        print(f"  {b.left:>12} | {b.right:<12}  {req} w={b.weight:.1f}  {rules}")
        t = b.primary_tag
        if t:
            print(f"  {'':>12} | {'':<12}    → {t.hint}")


def _load_words(path, fmt="auto"):
    from .importers import load
    return load(path, fmt)


def _report(rep, title=""):
    if title:
        print(title)
    print(f"연음 점수 {rep.score:.1f}/100   "
          f"발화속도 {rep.speech_rate:.2f}음절/초   "
          f"평균음소 {rep.mean_phone*1000:.0f}ms\n")
    print(f"  {'경계':<26} {'판정':<6} {'간격':>8} {'정규화':>7} {'팽창':>6}")
    print("  " + "-" * 60)
    for r in rep.results:
        pair = f"{r.boundary.left} | {r.boundary.right}"
        infl = f"{r.inflation:.2f}" if r.inflation is not None else "  -"
        print(f"  {pair:<26} {_V[r.verdict]:<6} "
              f"{r.gap*1000:7.0f}ms {r.norm_gap:7.2f} {infl:>6}")
    if rep.focus:
        f = rep.focus
        print(f"\n  고칠 점 → {f.boundary.left} {f.boundary.right}")
        print(f"     {f.reason}")
        t = f.boundary.primary_tag
        if t:
            print(f"     {t.hint}")


def cmd_score(args):
    _report(evaluate(_load_words(args.words, args.format)))


def cmd_demo(args):
    sys.path.insert(0, __file__.rsplit("/", 2)[0])
    from samples.synth import synthesize

    sentence = args.text
    print(f'문장: "{sentence}"\n')
    print(f"  {'프로파일':<14} {'점수':>7} {'속도':>10} {'실패':>5}")
    print("  " + "-" * 42)
    for prof in ("native", "intermediate", "learner"):
        scores = []
        for seed in range(args.trials):
            r = evaluate(synthesize(sentence, prof, seed=seed))
            scores.append(r.score)
        rep = evaluate(synthesize(sentence, prof, seed=0))
        lo, hi = min(scores), max(scores)
        print(f"  {prof:<14} {sum(scores)/len(scores):7.1f} "
              f"{rep.speech_rate:8.2f}/s {len(rep.failures):5d}"
              f"   [{lo:.0f}–{hi:.0f}]")

    if args.detail:
        print()
        _report(evaluate(synthesize(sentence, args.detail, seed=0)),
                f"--- {args.detail} 상세 ---")


def cmd_align(args):
    from .align import align_audio
    words = align_audio(args.audio, open(args.script, encoding="utf-8").read())
    if args.dump:
        from samples.synth import to_json
        with open(args.dump, "w", encoding="utf-8") as f:
            json.dump({"words": to_json(words)}, f, ensure_ascii=False, indent=2)
        print(f"정렬 결과 저장: {args.dump}\n")
    _report(evaluate(words))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="linking", description="연음 분석 엔진")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("predict", help="텍스트만으로 기대 연결 표시")
    p.add_argument("text")
    p.set_defaults(fn=cmd_predict)

    p = sub.add_parser("score", help="정렬 결과 채점")
    p.add_argument("words", help="WhisperX JSON · words JSON · MFA TextGrid")
    p.add_argument("--format", default="auto",
                   choices=["auto", "whisperx", "words", "textgrid"])
    p.set_defaults(fn=cmd_score)

    p = sub.add_parser("demo", help="합성 프로파일 비교")
    p.add_argument("text", nargs="?", default="turn it off and take a look")
    p.add_argument("--trials", type=int, default=8)
    p.add_argument("--detail", choices=["native", "intermediate", "learner"])
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("align", help="오디오 강제 정렬 후 채점")
    p.add_argument("audio")
    p.add_argument("script")
    p.add_argument("--dump", help="정렬 결과를 JSON으로 저장")
    p.set_defaults(fn=cmd_align)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
