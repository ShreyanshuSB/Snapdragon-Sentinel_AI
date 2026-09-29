from __future__ import annotations

import base64
import io
import wave
import numpy as np
import scipy.io.wavfile
import scipy.signal


class AudioPreprocessingError(Exception):
    pass


class AudioPreprocessor:
    """
    Lightweight local audio preprocessor for speech-to-text.
    Converts arbitrary base64/raw audio into 16kHz single-channel float32 numpy arrays.
    Enforces maximum duration limits, privacy defaults, and silence detection.
    """

    TARGET_SAMPLE_RATE: int = 16000
    MAX_RECORDING_SECONDS: float = 30.0
    SILENCE_THRESHOLD_RMS: float = 0.0015

    def process(
        self,
        audio_input: bytes | str | np.ndarray,
        audio_format: str = "wav",
        sample_rate: int = 16000,
        max_duration_seconds: float | None = None,
    ) -> tuple[np.ndarray, float, bool]:
        """
        Process incoming audio into normalized 16kHz mono float32 array.

        Returns:
            tuple of (audio_float32, duration_seconds, is_silence)
        """
        max_sec = max_duration_seconds or self.MAX_RECORDING_SECONDS

        # 1. Decode base64 if needed
        if isinstance(audio_input, str):
            clean_str = audio_input.strip()
            # Strip data URL header if present (e.g. data:audio/wav;base64,...)
            if "," in clean_str:
                clean_str = clean_str.split(",", 1)[1]
            try:
                raw_bytes = base64.b64decode(clean_str)
            except Exception as e:
                raise AudioPreprocessingError(f"Failed to decode base64 audio: {e}")
        elif isinstance(audio_input, bytes):
            raw_bytes = audio_input
        elif isinstance(audio_input, np.ndarray):
            raw_bytes = None
            audio_arr = audio_input.astype(np.float32)
            orig_sr = sample_rate
        else:
            raise AudioPreprocessingError("Unsupported audio input type")

        # 2. Parse bytes into numpy array
        if raw_bytes is not None:
            if len(raw_bytes) == 0:
                raise AudioPreprocessingError("Empty audio buffer received")

            orig_sr, audio_arr = self._decode_audio_bytes(raw_bytes, audio_format, sample_rate)

        # 3. Handle stereo -> mono
        if audio_arr.ndim > 1:
            audio_arr = np.mean(audio_arr, axis=1)

        # 4. Resample to 16kHz if needed
        if orig_sr != self.TARGET_SAMPLE_RATE and len(audio_arr) > 0:
            target_samples = int(len(audio_arr) * (self.TARGET_SAMPLE_RATE / orig_sr))
            if target_samples > 0:
                audio_arr = scipy.signal.resample(audio_arr, target_samples).astype(np.float32)
            orig_sr = self.TARGET_SAMPLE_RATE

        # 5. Enforce maximum duration (trim excess)
        max_samples = int(self.TARGET_SAMPLE_RATE * max_sec)
        if len(audio_arr) > max_samples:
            audio_arr = audio_arr[:max_samples]

        duration_sec = len(audio_arr) / float(self.TARGET_SAMPLE_RATE) if len(audio_arr) > 0 else 0.0

        # 6. Normalize amplitude to [-1.0, 1.0] if not already normalized
        max_val = np.max(np.abs(audio_arr)) if len(audio_arr) > 0 else 0.0
        if max_val > 1.0:
            audio_arr = audio_arr / max_val
        elif max_val > 0.001 and max_val < 0.2:
            # Gentle boost for very quiet recordings
            audio_arr = audio_arr / (max_val + 1e-6) * 0.7

        # 7. Silence / energy detection
        rms = float(np.sqrt(np.mean(audio_arr ** 2))) if len(audio_arr) > 0 else 0.0
        is_silence = rms < self.SILENCE_THRESHOLD_RMS

        return audio_arr.astype(np.float32), duration_sec, is_silence

    def _decode_audio_bytes(
        self,
        raw_bytes: bytes,
        audio_format: str,
        fallback_sr: int,
    ) -> tuple[int, np.ndarray]:
        # Try WAV parsing first
        if raw_bytes.startswith(b"RIFF") or audio_format.lower() == "wav":
            try:
                sr, data = scipy.io.wavfile.read(io.BytesIO(raw_bytes))
                if data.dtype == np.int16:
                    float_data = data.astype(np.float32) / 32768.0
                elif data.dtype == np.int32:
                    float_data = data.astype(np.float32) / 2147483648.0
                elif data.dtype == np.uint8:
                    float_data = (data.astype(np.float32) - 128.0) / 128.0
                else:
                    float_data = data.astype(np.float32)
                return sr, float_data
            except Exception as e:
                # Fallback to wave module
                try:
                    with wave.open(io.BytesIO(raw_bytes), "rb") as wf:
                        channels = wf.getnchannels()
                        sampwidth = wf.getsampwidth()
                        sr = wf.getframerate()
                        nframes = wf.getnframes()
                        frames = wf.readframes(nframes)
                        if sampwidth == 2:
                            data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                        else:
                            data = np.frombuffer(frames, dtype=np.float32)
                        if channels > 1:
                            data = data.reshape(-1, channels)
                        return sr, data
                except Exception as inner_e:
                    raise AudioPreprocessingError(f"Corrupted or unsupported WAV audio: {e}; {inner_e}")

        # Raw PCM 16-bit LE
        if audio_format.lower() in ("pcm", "raw"):
            try:
                int_data = np.frombuffer(raw_bytes, dtype=np.int16)
                float_data = int_data.astype(np.float32) / 32768.0
                return fallback_sr, float_data
            except Exception as e:
                raise AudioPreprocessingError(f"Failed to parse raw PCM audio: {e}")

        # Attempt generic 16-bit PCM interpretation if length is even
        if len(raw_bytes) % 2 == 0:
            try:
                int_data = np.frombuffer(raw_bytes, dtype=np.int16)
                float_data = int_data.astype(np.float32) / 32768.0
                return fallback_sr, float_data
            except Exception:
                pass

        raise AudioPreprocessingError(f"Unsupported audio format '{audio_format}'. Please provide WAV or PCM audio.")


audio_preprocessor = AudioPreprocessor()
