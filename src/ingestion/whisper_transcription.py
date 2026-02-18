# whisper_transcription.py
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import whisper

def _project_root() -> Path:

    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    return _project_root() / "data"


def _audio_dir() -> Path:
    p = _data_dir() / "audio"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _transcripts_dir() -> Path:
    p = _data_dir() / "transcripts"
    p.mkdir(parents=True, exist_ok=True)
    return p

def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_ffmpeg_to_wav_16k_mono(src: Path, dst: Path) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-ac", "1",       
        "-ar", "16000",   
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        err = (r.stderr or "").strip() or "ffmpeg conversion failed"
        raise RuntimeError(err)

def transcribe_audio(
    video_id: str,
    model_name: str = "base",
    language: str = "sr",
    use_word_timestamps: bool = True,
) -> bool:
    audio_mp3 = _audio_dir() / f"{video_id}.mp3"
    out_path = _transcripts_dir() / f"{video_id}.json"

    if out_path.exists():
        print(f"Cached transcript: {out_path.name}")
        return True

    if not audio_mp3.exists():
        print(f"Missing audio: {audio_mp3}")
        return False

    print(f"Preparing audio: {audio_mp3.name}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_wav = Path(tmpdir) / f"{video_id}.wav"

        try:
            _run_ffmpeg_to_wav_16k_mono(audio_mp3, tmp_wav)
        except Exception as e:
            print(f"ffmpeg failed: {e}")
            return False

        print(f"Whisper ({model_name}, lang={language}) -> {audio_mp3.name}")

        try:
            model = whisper.load_model(model_name)
        except Exception as e:
            print(f"Whisper model load failed: {type(e).__name__}: {e}")
            return False

        transcribe_kwargs: Dict[str, Any] = dict(
            fp16=False,
            verbose=False,
            language=language,
            task="transcribe",
            temperature=[0.0, 0.2, 0.4, 0.6],
            beam_size=5,
            patience=1.0,
            condition_on_previous_text=True,
            no_speech_threshold=0.6,
            logprob_threshold=-1.0,
            compression_ratio_threshold=2.4,
        )

        if use_word_timestamps:
            transcribe_kwargs["word_timestamps"] = True

        try:
            result = model.transcribe(str(tmp_wav), **transcribe_kwargs)
        except TypeError as e:
            if "word_timestamps" in str(e):
                transcribe_kwargs.pop("word_timestamps", None)
                try:
                    result = model.transcribe(str(tmp_wav), **transcribe_kwargs)
                except Exception as e2:
                    print(f"Whisper failed: {type(e2).__name__}: {e2}")
                    return False
            else:
                print(f"Whisper TypeError: {e}")
                return False
        except Exception as e:
            print(f"Whisper failed: {type(e).__name__}: {e}")
            return False

    payload = {
        "video_id": video_id,
        "source": "whisper",
        "model": model_name,
        "language_forced": language,
        "audio": {
            "mp3": str(audio_mp3),
        },
        "text": (result.get("text") or "").strip(),
        "segments": result.get("segments", []),
    }

    try:
        _write_json(out_path, payload)
    except Exception as e:
        print(f"Failed to write transcript JSON: {type(e).__name__}: {e}")
        return False

    print(f"Whisper transcript saved: {out_path.name}")
    return True


if __name__ == "__main__":
    test_video_id = "ChgE6c7Ongs"
    transcribe_audio(test_video_id, model_name="base", language="sr")
