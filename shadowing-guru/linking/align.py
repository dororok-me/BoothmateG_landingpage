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


def _load_audio(path: str, target_sr: int):
    """오디오를 (1, N) 모노 텐서로 읽어 target_sr로 맞춘다.

    torchaudio 2.11부터 load()가 TorchCodec에 위임하는데, TorchCodec은
    별도 설치에 FFmpeg까지 요구한다. soundfile을 먼저 쓰고 실패할 때만
    torchaudio로 넘어간다 — soundfile은 wav/flac/ogg/mp3를 FFmpeg 없이 읽는다.
    """
    import os
    import torch
    import torchaudio

    if not os.path.exists(path):
        raise FileNotFoundError(f"오디오 파일이 없습니다: {path}")

    waveform = sr = None
    errors = []

    try:
        import soundfile as sf
        import numpy as np
        data, sr = sf.read(path, dtype="float32", always_2d=True)   # (N, ch)
        waveform = torch.from_numpy(np.ascontiguousarray(data.T))   # (ch, N)
    except Exception as e:
        errors.append(f"soundfile: {e}")
        try:
            waveform, sr = torchaudio.load(path)
        except Exception as e2:
            errors.append(f"torchaudio: {e2}")

    if waveform is None:
        raise RuntimeError(
            "오디오를 읽지 못했습니다.\n  " + "\n  ".join(errors) +
            "\n\nwav로 변환해 다시 시도하세요. m4a는 soundfile이 읽지 못합니다:"
            "\n  afconvert -f WAVE -d LEI16@16000 -c 1 입력.m4a 출력.wav"
        )

    if waveform.size(0) > 1:                        # 스테레오 → 모노
        waveform = waveform.mean(dim=0, keepdim=True)
    if waveform.dim() == 1:
        waveform = waveform.unsqueeze(0)
    if sr != target_sr:
        waveform = torchaudio.functional.resample(waveform, sr, target_sr)
    return waveform


def _normalize(word: str, charset) -> str:
    """MMS_FA 토크나이저용 표기 정리.

    사전은 소문자 a-z와 ' * - 만 담고 있다(29자). 대문자나 구두점이 하나라도
    섞이면 KeyError가 난다 — 정상 문장은 대부분 여기 걸린다.
    """
    return "".join(c for c in word.lower() if c in charset)


def align_audio(audio_path: str, script: str) -> List[Word]:
    """오디오 + 스크립트 → 단어 타임스탬프."""
    _require()
    import torch
    import torchaudio
    from torchaudio.pipelines import MMS_FA as bundle

    words = [w for w in script.split() if w.strip()]
    if not words:
        raise ValueError("스크립트가 비어 있습니다")

    waveform = _load_audio(audio_path, bundle.sample_rate)

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

    charset = set(tokenizer.dictionary)
    tokens_text = [_normalize(w, charset) for w in words]

    empty = [w for w, t in zip(words, tokens_text) if not t]
    if empty:
        raise ValueError(
            f"토큰으로 바꿀 수 없는 단어: {empty}\n"
            "숫자·기호는 철자로 풀어 쓰세요 (10 → ten, & → and)."
        )

    with torch.inference_mode():
        emission, _ = model(waveform)
        spans = aligner(emission[0], tokenizer(tokens_text))

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
