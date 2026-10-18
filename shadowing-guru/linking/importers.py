"""외부 강제 정렬 결과 임포터.

실제 파이프라인(스펙 §3)은 WhisperX로 단어 타임스탬프를 만든다.
이 엔진은 정렬을 직접 하지 않고 그 결과를 받는 것을 기본 경로로 삼는다.
정렬기를 갈아끼워도 엔진이 영향받지 않는다.

지원 형식
  whisperx   WhisperX --output_format json (segments[].words[])
  words      {"words":[{"text","start","end"}]} 또는 그 배열
  textgrid   Montreal Forced Aligner 출력 (words 티어)
  azure      Azure Speech PronunciationAssessment 원본 JSON
"""

import json
import re
from typing import List

from .detect import Word


def from_whisperx(path: str) -> List[Word]:
    """WhisperX JSON. 단어 단위 타임스탬프가 있어야 한다."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    words = []
    for seg in data.get("segments", []):
        for w in seg.get("words", []):
            # WhisperX는 무성 단어에 start/end를 안 붙이는 경우가 있다
            if "start" not in w or "end" not in w:
                continue
            text = (w.get("word") or w.get("text") or "").strip()
            if not text:
                continue
            words.append(Word(text, float(w["start"]), float(w["end"])))

    if not words:
        raise ValueError(
            "단어 타임스탬프가 없습니다. WhisperX를 --align_model 옵션과 함께 "
            "실행해 단어 단위 정렬을 켜세요."
        )
    return words


def from_words(path: str) -> List[Word]:
    """이 프로젝트의 기본 형식."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data["words"]
    return [Word(d["text"], float(d["start"]), float(d["end"])) for d in data]


_TG_ITEM = re.compile(
    r'xmin\s*=\s*([\d.]+)\s*xmax\s*=\s*([\d.]+)\s*text\s*=\s*"([^"]*)"',
    re.S,
)


def from_textgrid(path: str, tier: str = "words") -> List[Word]:
    """MFA TextGrid. 지정한 티어의 비어 있지 않은 구간만 가져온다."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    # 해당 티어 블록만 잘라낸다
    marker = f'name = "{tier}"'
    idx = raw.find(marker)
    if idx < 0:
        raise ValueError(f"'{tier}' 티어를 찾을 수 없습니다")
    nxt = raw.find('name = "', idx + len(marker))
    block = raw[idx: nxt if nxt > 0 else len(raw)]

    words = []
    for xmin, xmax, text in _TG_ITEM.findall(block):
        t = text.strip()
        if not t or t in ("sil", "sp", "spn", "<eps>"):
            continue
        words.append(Word(t, float(xmin), float(xmax)))
    return words


def from_azure(path: str) -> List[Word]:
    """Azure PronunciationAssessment 원본 JSON.

    한 번 저장해두면 키 없이도 임계값을 다시 맞출 수 있다.
    """
    from .azure_align import parse_result
    with open(path, encoding="utf-8") as f:
        words, _ = parse_result(f.read())
    return words


LOADERS = {
    "whisperx": from_whisperx,
    "words": from_words,
    "textgrid": from_textgrid,
    "azure": from_azure,
}


def load(path: str, fmt: str = "auto") -> List[Word]:
    if fmt != "auto":
        return LOADERS[fmt](path)

    if path.lower().endswith(".textgrid"):
        return from_textgrid(path)

    with open(path, encoding="utf-8") as f:
        head = f.read(4096)
    if '"NBest"' in head:
        return from_azure(path)
    if '"segments"' in head:
        return from_whisperx(path)
    return from_words(path)
