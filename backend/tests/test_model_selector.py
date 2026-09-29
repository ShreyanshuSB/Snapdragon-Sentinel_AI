from __future__ import annotations

import pytest
from app.ai.model_selector import ModelSelector
from app.schemas.diagnostics import ModelCompatibilityRating


def test_model_selector_recommends_yolox_for_clean_engineering() -> None:
    selector = ModelSelector()
    selection = selector.select_first_candidate()

    assert selection.recommended_first_candidate == "yolo-x"
    assert "Apache 2.0" in selection.selection_rationale
    assert "object_detection_windows_cpp" in selection.selection_rationale
    assert len(selection.candidates) >= 4

    yolox_eval = next(c for c in selection.candidates if c.model_id == "yolo-x")
    assert yolox_eval.compatibility in [ModelCompatibilityRating.COMPATIBLE, ModelCompatibilityRating.LIKELY_COMPATIBLE]
    assert "NOT_VERIFIED" in yolox_eval.verification_status


def test_model_selector_technical_compatibility_breakdown() -> None:
    selector = ModelSelector()
    selection = selector.select_first_candidate()

    for cand in selection.candidates:
        assert cand.hardware_compatibility != ""
        assert cand.runtime_compatibility != ""
        assert cand.provider_compatibility != ""
        assert cand.license_status != ""
        assert "NOT_VERIFIED" in cand.verification_status
