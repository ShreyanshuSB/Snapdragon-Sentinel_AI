"""
SENTINEL Voice Engine Real Benchmark Utility
Usage:
    python scripts/benchmark_voice.py [--wav-file path/to/sample.wav] [--runs 3] [--json]

Measures real local Whisper speech-to-text latency, RTF, and resource utilization.
Does NOT require a microphone and does NOT upload audio anywhere.
Zero cloud dependencies.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import numpy as np


def run_benchmark(wav_file: str | None = None, runs: int = 3, as_json: bool = False) -> None:
    from app.ai.speech.engine import speech_engine
    from app.ai.speech.audio_preprocessor import audio_preprocessor
    from app.services.hardware_diagnostics import hardware_diagnostics

    hw_info = hardware_diagnostics.get_diagnostics()

    audio_data: np.ndarray | None = None
    audio_duration_sec: float = 3.0
    source_description = "Synthetic 16kHz multi-tone speech fixture"

    if wav_file and os.path.exists(wav_file):
        try:
            import wave
            with wave.open(wav_file, "rb") as wf:
                num_channels = wf.getnchannels()
                sample_width = wf.getsampwidth()
                framerate = wf.getframerate()
                num_frames = wf.getnframes()
                raw_bytes = wf.readframes(num_frames)
            
            # Use audio preprocessor to resample and normalize to 16kHz mono float32
            audio_data, audio_duration_sec, _ = audio_preprocessor.process(
                audio_input=raw_bytes,
                audio_format="wav",
                sample_rate=framerate,
            )
            source_description = f"Local WAV file: {os.path.basename(wav_file)}"
        except Exception as e:
            print(f"[Warning] Failed to read '{wav_file}': {e}. Falling back to standard synthetic fixture.")
            audio_data = None

    if audio_data is None:
        # Generate standard 3.0s synthetic speech-like multi-tone waveform
        sr = 16000
        audio_duration_sec = 3.0
        t = np.linspace(0, audio_duration_sec, int(sr * audio_duration_sec), dtype=np.float32)
        audio_data = 0.25 * np.sin(2 * np.pi * 320 * t) + 0.15 * np.sin(2 * np.pi * 700 * t)

    # Ensure speech engine model is loaded
    t_load_start = time.perf_counter()
    speech_engine.adapter.load()
    load_time_ms = (time.perf_counter() - t_load_start) * 1000

    # Execute warm evaluation runs
    latencies: list[float] = []
    transcripts: list[str] = []

    for i in range(runs):
        t0 = time.perf_counter()
        text, detected_lang, conf, infer_ms = speech_engine.adapter.transcribe(
            audio_16k=audio_data,
            language="en",
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies.append(elapsed_ms)
        transcripts.append(text)


    mean_ms = float(np.mean(latencies))

    min_ms = float(np.min(latencies))
    max_ms = float(np.max(latencies))
    rtf = (mean_ms / 1000.0) / audio_duration_sec

    report = {
        "benchmark": "SENTINEL Local Voice STT Benchmark",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "audio_source": source_description,
        "audio_duration_seconds": round(audio_duration_sec, 2),
        "evaluation_runs": runs,
        "model": speech_engine.adapter.name,
        "runtime": speech_engine.adapter.runtime,
        "execution_provider": "CPUExecutionProvider (Local PyTorch CPU)",
        "hardware": {
            "processor": hw_info.processor_name,
            "architecture": hw_info.system_architecture,
            "os": f"{platform.system()} {platform.release()}",
            "snapdragon_detected": hw_info.snapdragon_detected,
            "npu_detected": hw_info.npu_detected,
            "snapdragon_npu_verified": False,
        },
        "metrics": {
            "model_load_ms": round(load_time_ms, 2),
            "mean_pipeline_latency_ms": round(mean_ms, 2),
            "min_pipeline_latency_ms": round(min_ms, 2),
            "max_pipeline_latency_ms": round(max_ms, 2),
            "real_time_factor": round(rtf, 4),
            "is_faster_than_realtime": rtf < 1.0,
        },
        "sample_transcript": transcripts[0] if transcripts else "",
        "snapdragon_target": {
            "target_model": "whisper-base-snapdragon",
            "target_runtime": "Qualcomm AI Engine Direct (QAIRT) / QNN Execution Provider",
            "target_device": "Qualcomm Hexagon NPU (Snapdragon X Elite / Copilot+ PC)",
            "verification_status": "NOT VERIFIED (Host is Intel CPU)",
            "expected_reference_rtf": "< 0.08",
        },
    }

    if as_json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 65)
        print(" SENTINEL LOCAL VOICE ENGINE BENCHMARK REPORT")
        print("=" * 65)
        print(f" Source:              {source_description}")
        print(f" Audio Length:        {audio_duration_sec:.2f} seconds")
        print(f" Model:               {speech_engine.adapter.name} (Local FP32 CPU)")
        print(f" Hardware:            {hw_info.processor_name} ({hw_info.system_architecture})")
        print(f" Snapdragon Target:   Hexagon NPU (Status: NOT VERIFIED)")

        print("-" * 65)
        print(f" Model Load Time:     {load_time_ms:.1f} ms")
        print(f" Mean Latency:        {mean_ms:.1f} ms")
        print(f" Min / Max Latency:   {min_ms:.1f} ms / {max_ms:.1f} ms")
        print(f" Real-Time Factor:    {rtf:.4f} ({'FASTER than real-time' if rtf < 1.0 else 'Slower than real-time'})")
        print(f" Transcript:          \"{transcripts[0]}\"")
        print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark local SENTINEL speech engine.")
    parser.add_argument("--wav-file", type=str, default=None, help="Path to a 16kHz mono WAV file")
    parser.add_argument("--runs", type=int, default=3, help="Number of benchmark iterations")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    args = parser.parse_args()

    run_benchmark(wav_file=args.wav_file, runs=args.runs, as_json=args.json)
