import tempfile
import os
from typing import Optional
from faster_whisper import WhisperModel

from app.config import settings


class WhisperService:
    _instance: Optional["WhisperService"] = None
    _model: Optional[WhisperModel] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            print(f"Loading Whisper model: {settings.whisper_model}")
            # Use CPU with int8 quantization for efficiency
            self._model = WhisperModel(
                settings.whisper_model,
                device="cpu",
                compute_type="int8",
            )
            print("Whisper model loaded")

    def transcribe_file(self, file_path: str) -> dict:
        """Transcribe audio file to text."""
        segments, info = self._model.transcribe(
            file_path,
            language="en",
            beam_size=5,
        )

        # Collect all segments into full text
        text = " ".join(segment.text.strip() for segment in segments)

        return {
            "text": text.strip(),
            "language": info.language,
        }

    def transcribe_wav_bytes(self, wav_bytes: bytes) -> dict:
        """Transcribe WAV file bytes."""
        # Save to temp file and transcribe
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            temp_path = f.name

        try:
            return self.transcribe_file(temp_path)
        finally:
            os.unlink(temp_path)


# Singleton instance - lazy loaded
_whisper_service: Optional[WhisperService] = None


def get_whisper_service() -> WhisperService:
    global _whisper_service
    if _whisper_service is None:
        _whisper_service = WhisperService()
    return _whisper_service
