"""규칙 엔진 검증 — 알려진 연음 사례로 기대 태그를 확인한다."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linking.rules import analyze_boundary, analyze_text, link_density
from linking import lexicon as L


def tags(w1, w2):
    return {t.rule for t in analyze_boundary(0, w1, w2).tags}


def test_link_cv():
    """자음 + 모음 → 재음절화"""
    assert "LINK_CV" in tags("turn", "it")
    assert "LINK_CV" in tags("talk", "about")
    assert "LINK_CV" in tags("an", "old")
    # 모음 + 자음은 연결 대상이 아니다
    assert "LINK_CV" not in tags("you", "get")
    assert "LINK_CV" not in tags("the", "news")


def test_glides():
    """모음 충돌 → 활음 삽입"""
    assert "GLIDE_Y" in tags("he", "is")        # IY + IH
    assert "GLIDE_W" in tags("go", "on")        # OW + AA
    assert "GLIDE_W" not in tags("he", "is")


def test_link_r():
    """ER + 모음 → r 연결"""
    assert "LINK_R" in tags("her", "own")


def test_geminate():
    """동일 자음 연쇄 → 하나로"""
    assert "GEMINATE" in tags("big", "girl")     # G + G
    assert "GEMINATE" in tags("this", "Sunday")  # S + S
    assert "GEMINATE" not in tags("big", "cat")


def test_elision():
    """자음군 뒤 t/d 탈락"""
    assert "ELIDE_T" in tags("next", "day")      # K S T + D
    assert "ELIDE_D" in tags("old", "man")       # L D + M
    # 자음군이 아니면 탈락 대상이 아니다
    assert "ELIDE_T" not in tags("it", "off")


def test_flap():
    """모음 사이 t/d → 탄설음"""
    assert "FLAP" in tags("get", "it")           # EH T + IH
    assert "FLAP" in tags("at", "eight")
    assert "FLAP" not in tags("next", "day")     # 앞이 자음


def test_palatalize():
    """치경음 + y → 구개음화"""
    assert "PALATALIZE" in tags("did", "you")
    assert "PALATALIZE" in tags("miss", "you")
    assert "PALATALIZE" not in tags("did", "it")


def test_unreleased():
    """파열음 + 파열음 → 미파"""
    assert "UNRELEASED" in tags("big", "cat")
    assert "UNRELEASED" not in tags("big", "man")  # 뒤가 비음


def test_h_drop():
    """기능어 h 탈락 — 대상 단어에만 적용"""
    assert "H_DROP" in tags("tell", "him")
    assert "H_DROP" not in tags("said", "hello")   # hello는 기능어가 아니다


def test_nasal_assim():
    """n 조음위치 동화"""
    assert "NASAL_ASSIM" in tags("in", "bed")      # N + B (순음)
    assert "NASAL_ASSIM" in tags("in", "cars")     # N + K (연구개음)
    assert "NASAL_ASSIM" not in tags("in", "time") # N + T (같은 위치)


def test_reduce():
    """단음절 기능어는 축약 대상"""
    assert "REDUCE" in tags("want", "to")
    assert "REDUCE" in tags("about", "the")
    assert "REDUCE" not in tags("the", "news")     # news는 기능어가 아니다


def test_oov_is_skipped_not_guessed():
    """사전에 없는 단어는 추측하지 않고 건너뛴다"""
    b = analyze_boundary(0, "zzqqx", "it")
    assert b.skipped is not None
    assert b.tags == []
    assert not b.expects_link


def test_required_flag():
    """필수 연결과 선택 연결의 구분"""
    assert analyze_boundary(0, "turn", "it").expects_link       # LINK_CV
    assert not analyze_boundary(0, "big", "cat").expects_link   # UNRELEASED만


def test_link_density():
    """연음 밀도는 필수 연결 비율"""
    assert link_density(analyze_text("turn it off".split())) == 1.0
    d = link_density(analyze_text("the news was good".split()))
    assert 0.0 <= d <= 1.0


def test_weight_ordering():
    """한국인 학습자 기준 중요도 — LINK_CV가 최상위"""
    cv = analyze_boundary(0, "turn", "it").weight
    flap = analyze_boundary(0, "next", "day").weight
    assert cv > flap


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
