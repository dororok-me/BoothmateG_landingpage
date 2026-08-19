"""검출·채점 로직 검증.

합성 타이밍으로 판별 로직이 동작하는지 확인한다.
**실제 정확도 검증이 아니다** — 실제 한국인 화자 녹음이 필요하다.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linking.detect import Word, evaluate, mean_phone_duration, speech_rate, _ramp
from samples.synth import synthesize

SENTENCES = [
    "turn it off and take a look",
    "I want to talk about the news",
    "he is in bed with an old man",
    "did you get it at eight",
]


def test_ramp():
    assert _ramp(0.0, 1.0, 2.0) == 0.0
    assert _ramp(1.5, 1.0, 2.0) == 0.5
    assert _ramp(9.9, 1.0, 2.0) == 1.0


def test_mean_phone_is_positive():
    ws = synthesize(SENTENCES[0], "native", seed=0)
    assert mean_phone_duration(ws) > 0
    assert speech_rate(ws) > 0


def test_profiles_separate():
    """원어민 > 중급 > 초급 순서가 모든 문장에서 유지되어야 한다."""
    for s in SENTENCES:
        def avg(p):
            return sum(evaluate(synthesize(s, p, seed=k)).score
                       for k in range(12)) / 12
        n, i, l = avg("native"), avg("intermediate"), avg("learner")
        assert n > i > l, f"{s}: native={n:.1f} inter={i:.1f} learner={l:.1f}"
        assert n > 85, f"{s}: 원어민 점수가 낮다 {n:.1f}"
        assert l < 30, f"{s}: 초급 점수가 높다 {l:.1f}"


def test_native_has_no_failures():
    for s in SENTENCES:
        for k in range(12):
            rep = evaluate(synthesize(s, "native", seed=k))
            assert not rep.failures, f"{s} seed={k}: {rep.failures}"


def test_learner_focus_points_at_required_boundary():
    """고칠 점은 반드시 '필수 연결' 경계를 지목해야 한다."""
    for s in SENTENCES:
        rep = evaluate(synthesize(s, "learner", seed=0))
        assert rep.focus is not None, s
        assert rep.focus.boundary.expects_link


def test_pause_is_detected():
    """이어야 할 자리의 긴 휴지는 broken으로 잡혀야 한다."""
    ws = [Word("turn", 0.00, 0.30), Word("it", 0.60, 0.75), Word("off", 0.78, 1.00)]
    rep = evaluate(ws)
    first = rep.results[0]
    assert first.verdict == "broken"
    assert "끊어" in first.reason


def test_epenthesis_is_detected():
    """간격이 없어도 앞 단어가 부풀면 모음 삽입으로 잡혀야 한다."""
    # 'turn'(T ER N) 기대 길이보다 2배 이상 길지만 간격은 0
    ws = [Word("turn", 0.00, 0.62), Word("it", 0.62, 0.74), Word("off", 0.74, 0.92)]
    rep = evaluate(ws)
    first = rep.results[0]
    assert first.inflation > 1.75
    assert first.verdict == "broken"
    assert "삽입" in first.reason


def test_rate_normalization():
    """느린 화자와 빠른 화자가 같은 비율로 끊으면 같은 점수여야 한다."""
    fast = synthesize(SENTENCES[0], "native", seed=3)
    slow = [Word(w.text, w.start * 2, w.end * 2) for w in fast]
    a, b = evaluate(fast).score, evaluate(slow).score
    assert abs(a - b) < 0.01, f"{a:.2f} vs {b:.2f}"


def test_oov_excluded_from_score():
    """사전에 없는 단어가 섞여도 점수가 왜곡되지 않는다."""
    ws = [Word("turn", 0.0, 0.25), Word("it", 0.26, 0.38),
          Word("zzqqx", 0.39, 0.60), Word("off", 0.61, 0.80)]
    rep = evaluate(ws)
    assert any(r.verdict == "n/a" for r in rep.results)
    assert 0 <= rep.score <= 100


def test_score_bounds():
    for s in SENTENCES:
        for p in ("native", "intermediate", "learner"):
            sc = evaluate(synthesize(s, p, seed=0)).score
            assert 0.0 <= sc <= 100.0


if __name__ == "__main__":
    import traceback
    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for name, fn in fns:
        try:
            fn(); passed += 1; print(f"  PASS  {name}")
        except Exception:
            failed += 1; print(f"  FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
