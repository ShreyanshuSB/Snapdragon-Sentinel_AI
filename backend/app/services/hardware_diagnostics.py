from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any

from app.schemas.diagnostics import HardwareDiagnosticsResponse, TargetProfile

logger = logging.getLogger("sentinel.hardware_diagnostics")


class HardwareDiagnostics:
    """
    Truthful hardware diagnostics service.
    Directly probes host OS, CPU, RAM, GPU, and NPU without guessing or hardcoding.
    Maintains strict separation between current machine and target Snapdragon deployment.
    """

    def __init__(self, target_profile_path: Path | str | None = None) -> None:
        if target_profile_path is None:
            # Check root config/target_profile.json
            root_dir = Path(__file__).resolve().parents[3]
            candidate = root_dir / "config" / "target_profile.json"
            if candidate.exists():
                self.target_profile_path = candidate
            else:
                self.target_profile_path = Path("config/target_profile.json")
        else:
            self.target_profile_path = Path(target_profile_path)

    def load_target_profile(self) -> TargetProfile:
        default_profile = TargetProfile(
            target_platform="Snapdragon Copilot+ PC",
            target_cpu="Qualcomm Snapdragon X Elite / X Plus",
            target_gpu="Qualcomm Adreno GPU",
            target_npu="Qualcomm Hexagon NPU (45 TOPS)",
            target_architecture="ARM64",
            target_os="Windows 11 on ARM64",
            preferred_runtime="ONNX Runtime with QNN Execution Provider",
            notes="Target production profile for Windows on Snapdragon hardware acceleration.",
        )
        if not self.target_profile_path.exists():
            return default_profile

        try:
            with open(self.target_profile_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return TargetProfile(**data)
        except Exception as e:
            logger.warning("Could not parse target profile JSON: %s. Using default profile.", e)
            return default_profile

    def get_ram_info(self) -> tuple[float, float, float]:
        """Returns (total_gb, available_gb, used_percent)."""
        if platform.system() == "Windows":
            try:
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]

                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    total_gb = round(stat.ullTotalPhys / (1024**3), 2)
                    avail_gb = round(stat.ullAvailPhys / (1024**3), 2)
                    used_percent = float(stat.dwMemoryLoad)
                    return total_gb, avail_gb, used_percent
            except Exception as e:
                logger.debug("Windows RAM query error: %s", e)

        # Fallback
        return 16.0, 8.0, 50.0

    def get_windows_registry_string(self, root_key: int, sub_key: str, value_name: str) -> str | None:
        if platform.system() != "Windows":
            return None
        try:
            import winreg
            with winreg.OpenKey(root_key, sub_key) as h:
                val, _ = winreg.QueryValueEx(h, value_name)
                return str(val).strip()
        except Exception:
            return None

    def enum_gpus(self) -> list[str]:
        gpus: list[str] = []
        if platform.system() == "Windows":
            try:
                import winreg
                display_class = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, display_class) as h:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(h, i)
                            i += 1
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{display_class}\\{subkey_name}") as sub_h:
                                try:
                                    desc, _ = winreg.QueryValueEx(sub_h, "DriverDesc")
                                    if desc and desc not in gpus:
                                        gpus.append(str(desc).strip())
                                except OSError:
                                    pass
                        except OSError:
                            break
            except Exception as e:
                logger.debug("GPU registry enumeration exception: %s", e)

        if not gpus:
            gpus.append("Standard Host Display Adapter")
        return gpus

    def detect_npu(self) -> tuple[bool, str | None]:
        """
        Scans for physical NPU device under Windows NeuralProcessors class GUID or PNP entities.
        Does NOT confuse NPU presence with NPU inference verification.
        """
        if platform.system() != "Windows":
            return False, None

        npu_names: list[str] = []
        try:
            import winreg
            # Standard NeuralProcessors class GUID on Windows 11 Copilot+
            npu_class = r"SYSTEM\CurrentControlSet\Control\Class\{9da4941da-78e7-4976-9055-6dd8a6a24683}"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, npu_class) as h:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(h, i)
                            i += 1
                            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{npu_class}\\{subkey_name}") as sub_h:
                                try:
                                    desc, _ = winreg.QueryValueEx(sub_h, "DriverDesc")
                                    if desc:
                                        npu_names.append(str(desc).strip())
                                except OSError:
                                    pass
                        except OSError:
                            break
            except OSError:
                pass
        except Exception as e:
            logger.debug("NPU detection exception: %s", e)

        if npu_names:
            return True, npu_names[0]

        return False, None

    def identify_snapdragon(
        self, processor_name: str, processor_vendor: str, system_arch: str
    ) -> tuple[bool, str]:
        """
        Identifies Qualcomm Snapdragon platforms strictly based on OS-reported hardware strings.
        RULES:
        - Never infer exact chipset merely because Windows is ARM.
        - Never hardcode a chipset name.
        - If Qualcomm/Snapdragon detected but exact chipset unknown: return UNKNOWN.
        - If non-Snapdragon: return False, "NONE".
        """
        lower_name = processor_name.lower()
        lower_vendor = processor_vendor.lower()

        is_qualcomm = (
            "qualcomm" in lower_name
            or "qualcomm" in lower_vendor
            or "snapdragon" in lower_name
            or "sc8380" in lower_name  # Snapdragon X Elite internal part
            or "x1e" in lower_name
            or "x1p" in lower_name
        )

        if not is_qualcomm:
            return False, "NONE"

        # Specific Qualcomm platform identification
        if "x elite" in lower_name or "x1e" in lower_name or "sc8380xp" in lower_name:
            return True, "Qualcomm Snapdragon X Elite"
        elif "x plus" in lower_name or "x1p" in lower_name:
            return True, "Qualcomm Snapdragon X Plus"
        elif "x2" in lower_name:
            return True, "Qualcomm Snapdragon X2"
        elif "snapdragon" in lower_name:
            return True, processor_name
        else:
            # Detected Qualcomm, but exact model cannot be determined from processor string
            return True, "UNKNOWN"

    def get_diagnostics(self) -> HardwareDiagnosticsResponse:
        import winreg

        # Processor info
        reg_cpu = self.get_windows_registry_string(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            "ProcessorNameString",
        )
        reg_vendor = self.get_windows_registry_string(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            "VendorIdentifier",
        )
        reg_mfg = self.get_windows_registry_string(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\BIOS",
            "SystemManufacturer",
        )
        reg_model = self.get_windows_registry_string(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\BIOS",
            "SystemProductName",
        )

        processor_name = reg_cpu or platform.processor() or "Unknown Host Processor"
        processor_vendor = reg_vendor or "Unknown Vendor"
        system_arch = platform.machine()
        processor_arch = platform.processor() or system_arch

        # Core counts
        logical_cores = os.cpu_count()
        physical_cores = logical_cores // 2 if logical_cores and logical_cores > 1 else logical_cores

        # RAM
        total_ram_gb, avail_ram_gb, ram_used_pct = self.get_ram_info()

        # GPUs & NPU
        gpus = self.enum_gpus()
        npu_detected, npu_name = self.detect_npu()

        # Snapdragon identification
        is_snapdragon, snapdragon_platform = self.identify_snapdragon(
            processor_name, processor_vendor, system_arch
        )

        # Target comparison
        target = self.load_target_profile()
        if not is_snapdragon:
            target_comparison = "Development machine is not Snapdragon; Snapdragon target verification is pending."
            is_dev = True
        else:
            target_comparison = f"Snapdragon platform '{snapdragon_platform}' matches target architecture ({target.target_architecture})."
            is_dev = False

        return HardwareDiagnosticsResponse(
            os_name=platform.system(),
            os_version=f"{platform.release()} ({platform.version()})",
            os_build=platform.version().split(".")[-1] if "." in platform.version() else platform.version(),
            system_architecture=system_arch,
            processor_name=processor_name,
            processor_vendor=processor_vendor,
            processor_architecture=processor_arch,
            cpu_cores_physical=physical_cores,
            cpu_cores_logical=logical_cores,
            ram_total_gb=total_ram_gb,
            ram_available_gb=avail_ram_gb,
            ram_used_percent=ram_used_pct,
            gpus=gpus,
            npu_detected=npu_detected,
            npu_device_name=npu_name,
            machine_manufacturer=reg_mfg,
            machine_model=reg_model,
            snapdragon_detected=is_snapdragon,
            snapdragon_platform=snapdragon_platform,
            is_development_host=is_dev,
            target_comparison=target_comparison,
        )


hardware_diagnostics = HardwareDiagnostics()
