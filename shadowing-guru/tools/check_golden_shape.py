"""golden.json 구조가 Swift Decodable 정의와 맞는지 검사한다.

Swift 컴파일러가 없는 환경이라 키 이름·nullable 여부를 여기서 대조한다.
중첩 struct는 중괄호 매칭으로 잘라내고, `case a, b, c` 형태의 enum도 처리한다.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "ios/Tests/ShadowingGuruDomainTests/Resources/golden.json"
TESTS = ROOT / "ios/Tests/ShadowingGuruDomainTests/GoldenParityTests.swift"
MODELS = ROOT / "ios/Sources/ShadowingGuruDomain/Models.swift"


def block(src: str, header_re: str):
    """헤더 정규식에 맞는 선언의 본문을 중괄호 매칭으로 잘라낸다."""
    m = re.search(header_re, src)
    if not m:
        return None
    i = src.index("{", m.end() - 1 if src[m.end() - 1] == "{" else m.start())
    depth, j = 0, i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1:j]
        j += 1
    return None


def own_properties(body: str):
    """중첩 선언을 제거한 뒤 자기 자신의 let 프로퍼티만 뽑는다."""
    stripped, depth = [], 0
    for line in body.splitlines():
        opens, closes = line.count("{"), line.count("}")
        if depth == 0:
            stripped.append(line)
        depth += opens - closes
        depth = max(depth, 0)

    out = []
    for line in stripped:
        # 한 줄에 중첩 선언이 끝나는 경우(`struct W: Decodable { let a: A; ... }`)는
        # 부모의 프로퍼티가 아니므로 통째로 건너뛴다.
        if re.search(r"\b(struct|enum|class)\s+\w+", line):
            continue
        # 한 줄에 여러 개가 올 수 있으므로 findall 을 쓴다.
        for name, typ in re.findall(r"\blet\s+(\w+)\s*:\s*([^\s;=/]+)", line):
            typ = typ.rstrip(",;")
            out.append((name, typ.rstrip("?"), typ.endswith("?")))
    return out


def struct_props(src, name):
    b = block(src, rf"struct\s+{name}\s*:\s*Decodable\s*\{{")
    return own_properties(b) if b is not None else None


def check(src, struct, samples, label, problems):
    props = struct_props(src, struct)
    if props is None:
        problems.append(f"{struct}: Swift 정의를 찾지 못함")
        return

    swift_keys = {n for n, _, _ in props}
    json_keys = set()
    for s in samples:
        json_keys |= set(s.keys())

    missing = swift_keys - json_keys        # Swift가 요구하는데 JSON에 없음 → 디코딩 실패
    extra = json_keys - swift_keys          # JSON에만 있음 → 무시됨 (경고)

    for n, typ, optional in props:
        vals = [s.get(n) for s in samples if n in s]
        if any(v is None for v in vals) and not optional:
            problems.append(f"{label}.{n}: JSON에 null이 있는데 Swift가 비옵셔널({typ})")

    if missing:
        problems.append(f"{label}: Swift가 요구하나 JSON에 없음 {sorted(missing)}")

    note = f"  (JSON 여분 {sorted(extra)})" if extra else ""
    print(f"  {label:<16} Swift {len(swift_keys):>2}키 / JSON {len(json_keys):>2}키{note}")


def enum_raw_values(src, name):
    b = block(src, rf"enum\s+{name}\s*:\s*String")
    if b is None:
        return None
    raws = set()
    for line in b.splitlines():
        line = re.sub(r"//.*", "", line).strip()
        if not line.startswith("case "):
            continue
        for part in line[len("case "):].split(","):
            part = part.strip()
            if not part:
                continue
            m = re.match(r'(\w+)\s*=\s*"([^"]+)"', part)
            raws.add(m.group(2) if m else part)
    return raws


def main():
    g = json.loads(GOLDEN.read_text(encoding="utf-8"))
    tests = TESTS.read_text(encoding="utf-8")
    models = MODELS.read_text(encoding="utf-8")
    problems = []

    top = struct_props(tests, "Golden")
    missing_top = {n for n, _, _ in top} - set(g)
    if missing_top:
        problems.append(f"Golden: JSON에 없는 최상위 키 {sorted(missing_top)}")
    print(f"  {'Golden(top)':<16} Swift {len(top):>2}키 / JSON {len(g):>2}키")

    check(tests, "LexiconCase", g["lexicon"], "lexicon", problems)
    check(tests, "RuleCase", g["rules"], "rules", problems)
    check(tests, "SentenceCase", g["sentences"], "sentences", problems)
    check(tests, "DetectCase", g["detect"], "detect", problems)
    check(tests, "W", [w for c in g["detect"] for w in c["words"]],
          "detect.words", problems)
    check(tests, "R", [r for c in g["detect"] for r in c["results"]],
          "detect.results", problems)

    raws = enum_raw_values(models, "Verdict")
    verdicts = {r["verdict"] for c in g["detect"] for r in c["results"]}
    print(f"  {'Verdict':<16} Swift {sorted(raws)} / JSON {sorted(verdicts)}")
    if verdicts - raws:
        problems.append(f"Verdict: Swift enum에 없는 값 {sorted(verdicts - raws)}")

    print()
    if problems:
        print("불일치:")
        for p in problems:
            print("  ✗", p)
        return 1
    print("구조 일치 — golden.json은 Swift 정의로 디코딩 가능")
    return 0


if __name__ == "__main__":
    sys.exit(main())
