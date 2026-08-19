"""정렬 경로 회귀 테스트.

torch/torchaudio가 없으면 전체를 건너뛴다. 모델 가중치는 필요 없다 —
합성 emission으로 토크나이저·정렬·시간 변환만 검증한다.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import torch
    from torchaudio.pipelines import MMS_FA as bundle
    HAVE_TORCH = True
except ImportError:
    HAVE_TORCH = False


def _skip():
    print("    (torch 없음 — 건너뜀)")
    return True


def test_normalize_strips_case_and_punctuation():
    """MMS_FA 사전은 소문자 a-z와 ' * - 만 받는다.

    이 정규화가 빠지면 대문자 하나에도 KeyError가 나서, 정상 문장은
    거의 전부 정렬에 실패한다.
    """
    if not HAVE_TORCH:
        return _skip()
    from linking.align import _normalize
    cs = set(bundle.get_tokenizer().dictionary)

    assert _normalize("Turn", cs) == "turn"
    assert _normalize("off,", cs) == "off"
    assert _normalize("look.", cs) == "look"
    assert _normalize("I", cs) == "i"
    assert _normalize("don't", cs) == "don't"      # 아포스트로피는 보존
    assert _normalize("well-known", cs) == "well-known"
    assert _normalize("10", cs) == ""              # 숫자는 사전에 없다


def test_tokenizer_accepts_normalized_words():
    if not HAVE_TORCH:
        return _skip()
    from linking.align import _normalize
    tok = bundle.get_tokenizer()
    cs = set(tok.dictionary)

    words = "Turn it off, and take a look.".split()
    tok([_normalize(w, cs) for w in words])        # 예외가 나면 실패

    try:
        tok(words)                                 # 정규화 없이는 터져야 정상
        raise AssertionError("정규화 없이 통과하면 안 된다")
    except KeyError:
        pass


def test_span_grouping_and_time_conversion():
    """aligner는 단어당 span 리스트를 돌려주고, 시간은 단조 증가해야 한다."""
    if not HAVE_TORCH:
        return _skip()
    from linking.align import _normalize

    tok, aligner = bundle.get_tokenizer(), bundle.get_aligner()
    cs = set(tok.dictionary)
    words = "Turn it off, and take a look.".split()
    ids = tok([_normalize(w, cs) for w in words])
    flat = [t for w in ids for t in w]

    C, per = len(tok.dictionary), 4
    T = len(flat) * per + 8
    em = torch.full((T, C), -20.0)
    em[:, 0] = -0.1
    for i, t in enumerate(flat):
        em[4 + i * per: 4 + (i + 1) * per, t] = 0.0
    em = torch.log_softmax(em, dim=-1)

    spans = aligner(em, ids)
    assert len(spans) == len(words), f"{len(spans)} != {len(words)}"

    ratio = (T * 320) / T / bundle.sample_rate
    times = [(s[0].start * ratio, s[-1].end * ratio) for s in spans]
    for (s, e) in times:
        assert e > s, f"구간이 뒤집혔다 {s} {e}"
    for i in range(len(times) - 1):
        assert times[i + 1][0] >= times[i][0], "시작 시각이 단조 증가하지 않는다"


def test_empty_token_word_is_rejected_not_dropped():
    """토큰화 불가 단어는 조용히 버리지 않고 명시적으로 알려야 한다.

    말없이 버리면 단어 수가 어긋나 경계 판정 전체가 밀린다.
    """
    if not HAVE_TORCH:
        return _skip()
    import inspect
    from linking import align
    src = inspect.getsource(align.align_audio)
    assert "토큰으로 바꿀 수 없는 단어" in src
    assert "raise ValueError" in src


if __name__ == "__main__":
    import traceback
    fns = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for name, fn in fns:
        try:
            fn(); passed += 1; print(f"  PASS  {name}")
        except Exception:
            failed += 1; print(f"  FAIL  {name}"); traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed"
          + ("" if HAVE_TORCH else "  (torch 없어 실질 검증은 건너뜀)"))
    sys.exit(1 if failed else 0)
