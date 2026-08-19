"""CMUdict를 Swift용 리소스로 추출한다.

엔진은 대표 발음(사전 첫 항목)만 쓰므로 그것만 내보낸다 — 파이썬 lexicon.primary()와
동작이 정확히 일치한다. 강세 숫자는 미리 제거해 런타임 파싱을 줄인다.

형식: 한 줄에 `단어<TAB>음소 음소 음소`

CMUdict는 카네기멜론대가 BSD 유사 라이선스로 배포하는 공개 발음사전이다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cmudict
from linking.phones import strip_stress

OUT = (Path(__file__).resolve().parent.parent
       / "ios/Sources/ShadowingGuruDomain/Resources/cmudict.txt")


def main():
    d = cmudict.dict()
    OUT.parent.mkdir(parents=True, exist_ok=True)

    n = 0
    with OUT.open("w", encoding="utf-8") as f:
        for word in sorted(d):
            prons = d[word]
            if not prons:
                continue
            phones = " ".join(strip_stress(p) for p in prons[0])
            f.write(f"{word}\t{phones}\n")
            n += 1

    size = OUT.stat().st_size
    print(f"{OUT.relative_to(OUT.parents[4])}")
    print(f"  표제어 {n:,}   {size/1024/1024:.2f}MB")


if __name__ == "__main__":
    main()
