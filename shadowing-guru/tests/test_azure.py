"""Azure 결과 파서 검증.

API 키 없이 돈다. Azure 응답 형태를 목으로 만들어 파싱만 검증한다 —
이 프로젝트에서 미검증 코드가 첫 실행에 터진 게 두 번이라, 키 없이
검증 가능한 부분은 전부 테스트로 덮는다.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linking.azure_align import parse_result, ticks_to_seconds, TICKS_PER_SECOND
from linking.detect import evaluate


def _word(text, start_s, dur_s, accuracy=90, error="None"):
    return {
        "Word": text,
        "Offset": int(start_s * TICKS_PER_SECOND),
        "Duration": int(dur_s * TICKS_PER_SECOND),
        "PronunciationAssessment": {"AccuracyScore": accuracy, "ErrorType": error},
        "Phonemes": [],
    }


def mock(words, overall=None):
    return {
        "RecognitionStatus": "Success",
        "NBest": [{
            "Lexical": " ".join(w["Word"] for w in words),
            "PronunciationAssessment": overall or {
                "AccuracyScore": 88.0, "FluencyScore": 74.0,
                "CompletenessScore": 100.0, "PronScore": 82.0,
                "ProsodyScore": 79.0,
            },
            "Words": words,
        }],
    }


def test_tick_conversion():
    assert ticks_to_seconds(TICKS_PER_SECOND) == 1.0
    assert ticks_to_seconds(12_300_000) == 1.23
    assert ticks_to_seconds(0) == 0.0


def test_basic_parse_times():
    payload = mock([
        _word("turn", 0.20, 0.25),
        _word("it",   0.46, 0.11),
        _word("off",  0.58, 0.22),
    ])
    words, scores = parse_result(payload)
    assert [w.text for w in words] == ["turn", "it", "off"]
    assert abs(words[0].start - 0.20) < 1e-6
    assert abs(words[0].end - 0.45) < 1e-6
    assert abs(words[2].end - 0.80) < 1e-6


def test_scores_extracted():
    words, scores = parse_result(mock([_word("turn", 0.2, 0.25)]))
    assert scores["accuracy"] == 88.0
    assert scores["fluency"] == 74.0
    assert scores["pronunciation"] == 82.0
    assert scores["prosody"] == 79.0
    assert scores["word_accuracy"]["turn"] == 90


def test_json_string_accepted():
    import json
    payload = mock([_word("turn", 0.2, 0.25), _word("it", 0.46, 0.11)])
    a, _ = parse_result(payload)
    b, _ = parse_result(json.dumps(payload))
    assert [w.text for w in a] == [w.text for w in b]
    assert a[0].start == b[0].start


def test_omission_is_dropped():
    """발화되지 않은 단어는 타이밍이 무의미하다 — 경계 계산을 오염시킨다."""
    payload = mock([
        _word("turn", 0.20, 0.25),
        _word("it",   0.00, 0.00, accuracy=0, error="Omission"),
        _word("off",  0.58, 0.22),
    ])
    words, scores = parse_result(payload)
    assert [w.text for w in words] == ["turn", "off"]
    assert scores["omitted"] == ["it"]


def test_missing_timing_is_dropped():
    """Offset/Duration이 없는 단어는 버린다. 0으로 채우면 경계가 뒤집힌다."""
    payload = mock([_word("turn", 0.20, 0.25), _word("off", 0.58, 0.22)])
    del payload["NBest"][0]["Words"][1]["Offset"]
    words, scores = parse_result(payload)
    assert [w.text for w in words] == ["turn"]
    assert "off" in scores["omitted"]


def test_empty_nbest_raises_clearly():
    for bad in ({"NBest": []}, {"RecognitionStatus": "NoMatch"}):
        try:
            parse_result(bad)
            raise AssertionError("빈 결과인데 통과했다")
        except ValueError as e:
            assert "NBest" in str(e)


def test_all_words_unusable_raises():
    payload = mock([_word("it", 0.0, 0.0, error="Omission")])
    try:
        parse_result(payload)
        raise AssertionError("쓸 단어가 없는데 통과했다")
    except ValueError as e:
        assert "타임스탬프" in str(e)


def test_feeds_into_linking_engine():
    """Azure 출력이 연음 엔진에 그대로 들어가야 한다."""
    linked = mock([
        _word("turn", 0.200, 0.250),
        _word("it",   0.452, 0.110),
        _word("off",  0.564, 0.220),
    ])
    broken = mock([
        _word("turn", 0.200, 0.250),
        _word("it",   0.640, 0.110),
        _word("off",  0.900, 0.220),
    ])
    ws_l, _ = parse_result(linked)
    ws_b, _ = parse_result(broken)
    s_l = evaluate(ws_l).score
    s_b = evaluate(ws_b).score
    assert s_l > s_b, f"이어 읽기 {s_l:.1f} <= 끊어 읽기 {s_b:.1f}"
    assert s_l > 80 and s_b < 60, f"{s_l:.1f} / {s_b:.1f}"


def test_missing_pronunciation_block_is_tolerated():
    """발음 채점이 꺼진 일반 인식 결과로도 정렬만은 얻어야 한다."""
    payload = {
        "NBest": [{
            "Lexical": "turn it off",
            "Words": [
                {"Word": "turn", "Offset": 2_000_000, "Duration": 2_500_000},
                {"Word": "it",   "Offset": 4_600_000, "Duration": 1_100_000},
            ],
        }],
    }
    words, scores = parse_result(payload)
    assert [w.text for w in words] == ["turn", "it"]
    assert scores["accuracy"] is None


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
