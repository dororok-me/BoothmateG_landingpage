"""Azure Speech 정렬 + 발음 채점.

iOS 앱이 Azure Speech SDK를 쓰기로 했으므로, 프로토타입도 같은 정렬기로
튜닝해야 임계값이 그대로 이전된다. 정렬기가 다르면 단어 경계 정밀도가 달라
파이썬에서 맞춘 임계값이 Swift에서 어긋난다.

한 번의 호출로 두 가지를 얻는다.
  - 단어별 타임스탬프  → 연음·속도·강세의 입력
  - 음소별 정확도       → 발음 채점 (스펙 §4.1)

API 호출(`align_with_azure`)과 결과 파싱(`parse_result`)을 분리했다.
파싱은 순수 함수라 키 없이 테스트할 수 있다.

    pip install azure-cognitiveservices-speech
    export AZURE_SPEECH_KEY=...  AZURE_SPEECH_REGION=koreacentral
"""

import json
import os
from typing import Dict, List, Optional, Tuple

from .detect import Word

# Azure는 시간을 tick(100나노초) 단위로 준다.
TICKS_PER_SECOND = 10_000_000

# 실제로 발화되지 않은 단어 — 타이밍이 무의미하므로 경계 분석에서 뺀다.
NOT_SPOKEN = {"Omission"}


def ticks_to_seconds(ticks) -> float:
    return float(ticks) / TICKS_PER_SECOND


def parse_result(payload) -> Tuple[List[Word], Dict]:
    """Azure JSON 결과를 (단어 타임스탬프, 발음 점수)로 바꾼다.

    payload는 dict 또는 JSON 문자열.
    """
    data = json.loads(payload) if isinstance(payload, str) else payload

    nbest = data.get("NBest") or []
    if not nbest:
        raise ValueError(
            "Azure 결과에 NBest가 없습니다. 인식이 실패했거나 "
            "무음일 수 있습니다."
        )
    best = nbest[0]

    overall = best.get("PronunciationAssessment") or {}
    scores = {
        "accuracy": overall.get("AccuracyScore"),
        "fluency": overall.get("FluencyScore"),
        "completeness": overall.get("CompletenessScore"),
        "pronunciation": overall.get("PronScore"),
        "prosody": overall.get("ProsodyScore"),
    }

    words: List[Word] = []
    omitted: List[str] = []

    for w in best.get("Words") or []:
        text = w.get("Word") or ""
        if not text:
            continue

        pa = w.get("PronunciationAssessment") or {}
        if pa.get("ErrorType") in NOT_SPOKEN:
            omitted.append(text)
            continue

        # 발화됐지만 타이밍이 빠진 경우 — 경계 계산이 깨지므로 제외한다
        if w.get("Offset") is None or w.get("Duration") is None:
            omitted.append(text)
            continue

        start = ticks_to_seconds(w["Offset"])
        words.append(Word(
            text=text,
            start=round(start, 4),
            end=round(start + ticks_to_seconds(w["Duration"]), 4),
        ))

    if not words:
        raise ValueError("타임스탬프가 있는 단어가 하나도 없습니다.")

    scores["omitted"] = omitted
    scores["word_accuracy"] = {
        (w.get("Word") or ""): (w.get("PronunciationAssessment") or {}).get("AccuracyScore")
        for w in (best.get("Words") or [])
    }
    return words, scores


def align_with_azure(
    audio_path: str,
    script: str,
    key: Optional[str] = None,
    region: Optional[str] = None,
    language: str = "en-US",
    dump_path: Optional[str] = None,
) -> Tuple[List[Word], Dict]:
    """오디오 + 스크립트 → 단어 타임스탬프 + 발음 점수.

    오디오는 16kHz 16bit 모노 WAV를 권장한다:
        afconvert -f WAVE -d LEI16@16000 -c 1 입력 출력.wav

    dump_path를 주면 원본 응답을 그대로 저장한다. 저장해두면 Azure 키 없이도
    임계값을 다시 맞출 수 있어, 녹음한 사람과 튜닝하는 사람이 달라도 된다.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"오디오 파일이 없습니다: {audio_path}")

    key = key or os.environ.get("AZURE_SPEECH_KEY")
    region = region or os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise RuntimeError(
            "Azure 자격 증명이 없습니다.\n"
            "  export AZURE_SPEECH_KEY=...\n"
            "  export AZURE_SPEECH_REGION=koreacentral"
        )

    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError as e:
        raise RuntimeError(
            "pip install azure-cognitiveservices-speech"
        ) from e

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.speech_recognition_language = language

    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)

    pa_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=script.strip(),
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=True,
    )
    try:                                   # 운율 점수는 일부 지역/버전에서만
        pa_config.enable_prosody_assessment()
    except Exception:
        pass

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, audio_config=audio_config
    )
    pa_config.apply_to(recognizer)

    result = recognizer.recognize_once()

    if result.reason == speechsdk.ResultReason.Canceled:
        d = result.cancellation_details
        raise RuntimeError(f"Azure 요청 취소됨: {d.reason} — {d.error_details}")
    if result.reason != speechsdk.ResultReason.RecognizedSpeech:
        raise RuntimeError(f"인식 실패: {result.reason}")

    payload = result.properties.get(
        speechsdk.PropertyId.SpeechServiceResponse_JsonResult
    )
    if not payload:
        raise RuntimeError("Azure 응답에 JSON 결과가 없습니다.")

    if dump_path:
        with open(dump_path, "w", encoding="utf-8") as f:
            json.dump(json.loads(payload), f, ensure_ascii=False, indent=2)

    return parse_result(payload)
