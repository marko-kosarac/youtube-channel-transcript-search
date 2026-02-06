from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict

import whisper


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


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
        raise RuntimeError((r.stderr or "").strip() or "ffmpeg conversion failed")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def transcribe_audio(
    video_id: str,
    model_name: str = "base",
    language: str = "sr",
    use_word_timestamps: bool = True,
) -> bool:

    repo_root = _repo_root()

    audio_mp3 = repo_root / "audio" / f"{video_id}.mp3"
    out_dir = _ensure_dir(repo_root / "transcripts")
    out_path = out_dir / f"{video_id}.json"

    if out_path.exists():
        print(f"✅ Cached transcript: {out_path.name}")
        return True

    if not audio_mp3.exists():
        print(f"❌ Missing audio: {audio_mp3}")
        return False

    print(f"🎛️  Preparing audio: {audio_mp3.name}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        tmp_wav = Path(tmp.name)

        try:
            _run_ffmpeg_to_wav_16k_mono(audio_mp3, tmp_wav)
        except Exception as e:
            print(f"❌ ffmpeg failed: {e}")
            return False

        print(f"🧠 Whisper ({model_name}, lang={language}) -> {audio_mp3.name}")
        model = whisper.load_model(model_name)

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
                result = model.transcribe(str(tmp_wav), **transcribe_kwargs)
            else:
                print(f"❌ Whisper TypeError: {e}")
                return False
        except Exception as e:
            print(f"❌ Whisper failed: {type(e).__name__}: {e}")
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

    _write_json(out_path, payload)
    print(f"✅ Whisper transcript saved: {out_path.name}")
    return True


if __name__ == "__main__":
    test_video_id = "ChgE6c7Ongs"
    transcribe_audio(test_video_id, model_name="medium", language="sr")
