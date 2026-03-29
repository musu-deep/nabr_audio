from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import librosa
import noisereduce as nr
import numpy as np
import soundfile as sf
from pydub import AudioSegment, effects, silence
from scipy.signal import butter, lfilter


SUPPORTED = {".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac"}


@dataclass
class AudioInfo:
    duration_sec: float
    channels: int
    frame_rate: int
    sample_width: int
    rms: float
    dBFS: float
    ext: str


def ensure_supported(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"Unsupported file type: {path.suffix}")


def analyze_audio(path: Path) -> Dict:
    ensure_supported(path)
    seg = AudioSegment.from_file(path)
    info = AudioInfo(
        duration_sec=round(len(seg) / 1000.0, 2),
        channels=seg.channels,
        frame_rate=seg.frame_rate,
        sample_width=seg.sample_width,
        rms=float(seg.rms),
        dBFS=float(seg.dBFS) if seg.dBFS != float("-inf") else -90.0,
        ext=path.suffix.lower(),
    )

    diagnosis = []
    if info.dBFS < -24:
        diagnosis.append("مستوى الصوت منخفض نسبيًا")
    if info.duration_sec > 60:
        diagnosis.append("الملف طويل نسبيًا وقد يستفيد من حذف السكتات")
    if not diagnosis:
        diagnosis.append("جودة أولية مقبولة")

    ffmpeg_hint = None
    if path.suffix.lower() != ".wav":
        ffmpeg_hint = "تنسيقات MP3/M4A قد تحتاج FFmpeg على ويندوز إذا لم يكن مثبتًا بالفعل."

    return {
        "duration_sec": info.duration_sec,
        "channels": info.channels,
        "frame_rate": info.frame_rate,
        "sample_width": info.sample_width,
        "rms": info.rms,
        "dbfs": round(info.dBFS, 2),
        "diagnosis": diagnosis,
        "ffmpeg_hint": ffmpeg_hint,
    }


def _highpass(data: np.ndarray, sr: int, cutoff: float = 90.0) -> np.ndarray:
    nyq = 0.5 * sr
    normal_cutoff = cutoff / nyq
    b, a = butter(2, normal_cutoff, btype="high", analog=False)
    return lfilter(b, a, data)


def _trim_silence(seg: AudioSegment, silence_min_ms: int, silence_keep_ms: int) -> AudioSegment:
    chunks = silence.split_on_silence(
        seg,
        min_silence_len=max(250, silence_min_ms),
        silence_thresh=seg.dBFS - 16,
        keep_silence=max(40, silence_keep_ms),
    )
    if not chunks:
        return seg
    out = chunks[0]
    for c in chunks[1:]:
        out += c
    return out


def _trim_edges(seg: AudioSegment) -> AudioSegment:
    nonsilent = silence.detect_nonsilent(seg, min_silence_len=250, silence_thresh=seg.dBFS - 16)
    if not nonsilent:
        return seg
    start, end = nonsilent[0][0], nonsilent[-1][1]
    return seg[start:end]


def _to_mono_float(path: Path):
    y, sr = librosa.load(path.as_posix(), sr=None, mono=True)
    return y, sr


def _write_temp_wav(data: np.ndarray, sr: int, out_path: Path):
    sf.write(out_path.as_posix(), data, sr)


def process_audio(
    input_path: Path,
    output_dir: Path,
    actions: List[str],
    silence_min_ms: int = 900,
    silence_keep_ms: int = 120,
) -> Dict:
    ensure_supported(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    logs: List[str] = []
    work_path = input_path

    if any(a in actions for a in ["denoise", "clarity"]):
        y, sr = _to_mono_float(work_path)
        if "denoise" in actions:
            y = nr.reduce_noise(y=y, sr=sr, prop_decrease=0.8)
            logs.append("تم تقليل ضوضاء الخلفية بدرجة متوازنة.")
        if "clarity" in actions:
            y = _highpass(y, sr, cutoff=90.0)
            logs.append("تم تطبيق تحسين طفيف لوضوح الكلام بإزالة الترددات المنخفضة جدًا.")

        tmp = output_dir / f"tmp_{uuid.uuid4().hex}.wav"
        _write_temp_wav(y, sr, tmp)
        work_path = tmp

    seg = AudioSegment.from_file(work_path)

    if "trim_edges" in actions:
        seg = _trim_edges(seg)
        logs.append("تم قص الصمت من البداية والنهاية.")

    if "trim_silence" in actions:
        before_ms = len(seg)
        seg = _trim_silence(seg, silence_min_ms=silence_min_ms, silence_keep_ms=silence_keep_ms)
        removed = max(0, before_ms - len(seg))
        logs.append(f"تم تقليص السكتات الطويلة وإزالة نحو {removed/1000:.2f} ثانية من الصمت.")

    if "normalize" in actions:
        seg = effects.normalize(seg)
        logs.append("تمت موازنة مستوى الصوت ورفع الجهارة بشكل آمن.")

    output_name = f"processed_{input_path.stem}_{uuid.uuid4().hex[:8]}.wav"
    output_path = output_dir / output_name
    seg.export(output_path, format="wav")

    if work_path != input_path and work_path.exists():
        try:
            os.remove(work_path)
        except OSError:
            pass

    return {
        "output_filename": output_name,
        "output_path": output_path.as_posix(),
        "logs": logs,
        "analysis": analyze_audio(output_path),
    }
