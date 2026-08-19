"""자체 강제 정렬 (선택 경로).

기본 경로는 importers.py — WhisperX 등 외부 정렬 결과를 받는 것이다.
이 모듈은 오디오 하나만 있을 때 쓰는 보조 경로다.

torchaudio의 MMS_FA 번들을 쓴다. 모델 가중치를 download.pytorch.org에서
받으므로 해당 호스트가 막힌 환경에서는 동작하지 않는다.
(그 경우 WhisperX로 정렬한 뒤 importers.load()를 쓴다.)

    pip install torch torchaudio soundfile
"""

from typing import List

from .detect import Word


def _require():
    try:
        import torch, torchaudio  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "torch/torchaudio가 필요합니다: pip install torch torchaudio soundfile\n"
            "설치가 어려우면 WhisperX로 정렬한 뒤 "
            "`linking score --format whisperx <파일>`을 쓰세요."
        ) from e


def align_audio(audio_path: str, script: str) -> List[Word]:
    """오디오 + 스크립트 → 단어 타임스탬프."""
    _require()
    import torch
    import torchaudio
    from torchaudio.pipelines import MMS_FA as bundle

    words = [w for w in script.split() if w.strip()]
    if not words:
        raise ValueError("스크립트가 비어 있습니다")

    waveform, sr = torchaudio.load(audio_path)
    if waveform.size(0) > 1:                       # 스테레오 → 모노
        waveform = waveform.mean(dim=0, keepdim=True)
    if sr != bundle.sample_rate:
        waveform = torchaudio.functional.resample(waveform, sr, bundle.sample_rate)

    try:
        model = bundle.get_model()
        tokenizer = bundle.get_tokenizer()
        aligner = bundle.get_aligner()
    except Exception as e:
        raise RuntimeError(
            f"정렬 모델을 받지 못했습니다 ({e}).\n"
            "download.pytorch.org 접근이 막힌 환경일 수 있습니다. "
            "WhisperX로 정렬한 뒤 importers.load()를 쓰세요."
        ) from e

    with torch.inference_mode():
        emission, _ = model(waveform)
        spans = aligner(emission[0], tokenizer(words))

    # 프레임 인덱스 → 초
    ratio = waveform.size(1) / emission.size(1) / bundle.sample_rate

    out = []
    for word, span in zip(words, spans):
        out.append(Word(
            text=word,
            start=round(span[0].start * ratio, 4),
            end=round(span[-1].end * ratio, 4),
        ))
    return out
