from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any
import numpy as np

from app.ai.pipeline import RuntimeAdapter

logger = logging.getLogger("sentinel.onnx_runtime_adapter")


class ONNXRuntimeAdapter(RuntimeAdapter):
    """
    ONNX Runtime session manager with Qualcomm QNN Execution Provider
    and CPU Execution Provider fallback.
    """

    def __init__(self) -> None:
        self._session: Any = None
        self._active_provider: str = "NONE"
        self._is_npu_verified: bool = False
        self._model_path: Path | None = None
        self._input_names: list[str] = []
        self._output_names: list[str] = []

    def initialize(
        self,
        model_path: str,
        provider: str | None = None,
        provider_options: dict[str, Any] | None = None,
    ) -> None:
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError(
                "onnxruntime package is not installed. Run 'pip install onnxruntime'."
            ) from e

        p = Path(model_path)
        if not p.exists():
            raise FileNotFoundError(f"Model file not found at: {p.resolve()}")

        available = ort.get_available_providers()
        chosen_providers: list[str] = []

        # Target provider resolution
        if provider and provider in available:
            chosen_providers.append(provider)
        elif "QNNExecutionProvider" in available:
            chosen_providers.append("QNNExecutionProvider")

        # Always include CPUExecutionProvider as reliable fallback
        if "CPUExecutionProvider" in available and "CPUExecutionProvider" not in chosen_providers:
            chosen_providers.append("CPUExecutionProvider")

        if not chosen_providers:
            raise RuntimeError("No compatible ONNX Runtime execution providers available.")

        logger.info("Initializing ONNX session with providers: %s", chosen_providers)

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self._session = ort.InferenceSession(
            str(p.resolve()),
            sess_options=sess_options,
            providers=chosen_providers,
        )

        active_providers = self._session.get_providers()
        self._active_provider = active_providers[0] if active_providers else "UNKNOWN"
        self._model_path = p
        self._input_names = [i.name for i in self._session.get_inputs()]
        self._output_names = [o.name for o in self._session.get_outputs()]

        # NPU verification is NEVER marked True merely because session opened
        self._is_npu_verified = False

        logger.info(
            "ONNX Session initialized successfully. Model: %s, Active Provider: %s",
            p.name,
            self._active_provider,
        )

    def run_inference(self, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        if self._session is None:
            raise RuntimeError("InferenceSession is not initialized. Call initialize() first.")

        # Match input name if single input
        feed_dict: dict[str, np.ndarray] = {}
        if len(self._input_names) == 1 and len(inputs) == 1:
            feed_dict[self._input_names[0]] = list(inputs.values())[0]
        else:
            feed_dict = inputs

        start_time = time.perf_counter()
        raw_outputs = self._session.run(self._output_names, feed_dict)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 3)

        output_dict = {
            name: arr for name, arr in zip(self._output_names, raw_outputs)
        }
        output_dict["_inference_time_ms"] = np.array([elapsed_ms])
        return output_dict

    def get_active_provider(self) -> str:
        return self._active_provider

    def is_npu_verified(self) -> bool:
        return self._is_npu_verified

    def is_loaded(self) -> bool:
        return self._session is not None

    def close(self) -> None:
        self._session = None
        self._active_provider = "NONE"
        self._is_npu_verified = False
