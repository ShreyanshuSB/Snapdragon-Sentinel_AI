from __future__ import annotations

import pytest
from app.services.hardware_diagnostics import HardwareDiagnostics


def test_real_host_hardware_diagnostics() -> None:
    hw_service = HardwareDiagnostics()
    diag = hw_service.get_diagnostics()

    assert diag.os_name is not None
    assert diag.system_architecture is not None
    assert diag.processor_name is not None
    assert diag.ram_total_gb > 0
    assert diag.ram_available_gb >= 0
    assert len(diag.gpus) >= 1
    # Real host verification
    assert isinstance(diag.snapdragon_detected, bool)
    assert isinstance(diag.npu_detected, bool)
    assert diag.target_comparison is not None


def test_non_snapdragon_host_message() -> None:
    hw_service = HardwareDiagnostics()
    # Test on an x86/Intel processor
    is_snapdragon, platform_id = hw_service.identify_snapdragon(
        "12th Gen Intel(R) Core(TM) i5-12450H", "GenuineIntel", "AMD64"
    )
    assert is_snapdragon is False
    assert platform_id == "NONE"


def test_snapdragon_x_elite_identification() -> None:
    hw_service = HardwareDiagnostics()
    is_snapdragon, platform_id = hw_service.identify_snapdragon(
        "Snapdragon(R) X Elite - X1E80100 - Qualcomm(R) Oryon(TM) CPU",
        "Qualcomm",
        "ARM64",
    )
    assert is_snapdragon is True
    assert platform_id == "Qualcomm Snapdragon X Elite"


def test_snapdragon_x_plus_identification() -> None:
    hw_service = HardwareDiagnostics()
    is_snapdragon, platform_id = hw_service.identify_snapdragon(
        "Snapdragon(R) X Plus - X1P64100",
        "Qualcomm",
        "ARM64",
    )
    assert is_snapdragon is True
    assert platform_id == "Qualcomm Snapdragon X Plus"


def test_generic_arm_never_inferred_as_snapdragon() -> None:
    hw_service = HardwareDiagnostics()
    # Generic ARM processor without Qualcomm/Snapdragon strings
    is_snapdragon, platform_id = hw_service.identify_snapdragon(
        "ARMv8 (64-bit) generic processor",
        "ARM",
        "ARM64",
    )
    assert is_snapdragon is False
    assert platform_id == "NONE"


def test_unknown_qualcomm_chipset_returns_unknown() -> None:
    hw_service = HardwareDiagnostics()
    # Qualcomm processor with unrecognized part number
    is_snapdragon, platform_id = hw_service.identify_snapdragon(
        "Qualcomm Custom Prototype SoC",
        "Qualcomm",
        "ARM64",
    )
    assert is_snapdragon is True
    assert platform_id == "UNKNOWN"


def test_target_profile_comparison_logic() -> None:
    hw_service = HardwareDiagnostics()
    profile = hw_service.load_target_profile()

    assert profile.target_architecture == "ARM64"
    assert "Snapdragon" in profile.target_platform
    assert "Hexagon" in profile.target_npu
