#!/usr/bin/env python3
"""
SENTINEL Pre-Flight Installation & Environment Verification Tool
Checks Python version, required packages, Node/npm tools, model configs,
database connectivity, backend imports, and frontend readiness.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def print_header(title: str) -> None:
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def check_python() -> bool:
    print(f"[*] Python Version: {sys.version.split()[0]}")
    if sys.version_info < (3, 10):
        print("    [!] WARNING: SENTINEL requires Python 3.10+")
        return False
    print("    [OK] Python version compatible.")
    return True


def check_packages() -> bool:
    required = [
        ("fastapi", "FastAPI web framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data schemas & validation"),
        ("sqlalchemy", "SQLite ORM & vector persistence"),
        ("onnxruntime", "ONNX execution provider"),
        ("torch", "PyTorch local neural runtime"),
        ("transformers", "Hugging Face transformer pipelines"),
        ("cv2", "OpenCV image processing (opencv-python)"),
        ("easyocr", "Local OCR engine"),
        ("numpy", "Numerical computing"),
        ("pypdf", "PDF parsing & document ingestion"),
        ("pptx", "Presentation packaging (python-pptx)"),
        ("reportlab", "PDF document generation (reportlab)"),
    ]
    all_ok = True
    for mod_name, desc in required:
        try:
            __import__(mod_name)
            print(f"    [OK] {mod_name:<16} - {desc}")
        except ImportError:
            print(f"    [X]  {mod_name:<16} - NOT INSTALLED ({desc})")
            all_ok = False
    return all_ok


def check_node_npm() -> bool:
    node = shutil.which("node") or shutil.which("node.exe")
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    npx = shutil.which("npx") or shutil.which("npx.cmd")

    print(f"[*] Node.js Binary : {node or 'NOT FOUND'}")
    print(f"[*] NPM Binary     : {npm or 'NOT FOUND'}")
    print(f"[*] NPX Binary     : {npx or 'NOT FOUND'}")

    if not node or not npm:
        print("    [!] Node.js / NPM not found on PATH. Required for Next.js frontend.")
        return False

    try:
        ver_node = subprocess.check_output([node, "--version"], text=True).strip()
        ver_npm = subprocess.check_output([npm, "--version"], text=True).strip()
        print(f"    [OK] Node: {ver_node}, NPM: {ver_npm}")
        return True
    except Exception as e:
        print(f"    [!] Error running node/npm: {e}")
        return False


def check_paths_and_config() -> bool:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    uploads_dir = root / "data" / "uploads"
    models_dir = root / "models"
    env_example = root / ".env.example"
    env_file = root / ".env"

    print(f"[*] Root Directory : {root}")
    print(f"[*] Data Directory : {'[OK]' if data_dir.exists() else '[MISSING - will create]'}")
    print(f"[*] .env.example   : {'[OK]' if env_example.exists() else '[MISSING]'}")
    print(f"[*] Active .env    : {'[OK]' if env_file.exists() else '[NOT FOUND - copy from .env.example]'}")

    uploads_dir.mkdir(parents=True, exist_ok=True)
    return True


def check_backend_imports() -> bool:
    root = Path(__file__).resolve().parent.parent
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    modules_to_test = [
        "app.core.config",
        "app.database.connection",
        "app.database.models",
        "app.schemas.orchestrator",
        "app.services.sentinel_orchestrator",
        "app.services.demo_fixture_service",
        "app.ai.vision.inference_engine",
        "app.ai.speech.engine",
        "app.ai.memory.retriever",
        "app.ai.reasoning.engine",
        "main",
    ]

    all_ok = True
    for mod in modules_to_test:
        try:
            __import__(mod)
            print(f"    [OK] Import {mod}")
        except Exception as e:
            print(f"    [X]  Failed to import {mod}: {e}")
            all_ok = False
    return all_ok


def check_database() -> bool:
    root = Path(__file__).resolve().parent.parent
    backend_path = root / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

    try:
        from app.database.connection import Base, SessionLocal, engine
        import app.database.models  # register tables
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        from sqlalchemy import text
        res = db.execute(text("SELECT 1")).scalar()
        db.close()
        if res == 1:
            print("    [OK] SQLite database initialized and operational.")
            return True
        return False
    except Exception as e:
        print(f"    [X] Database check failed: {e}")
        return False


def main() -> int:
    print_header("SENTINEL PRE-FLIGHT VERIFICATION")
    
    results = {}
    print("\n--- 1. Python Environment ---")
    results["Python"] = check_python()

    print("\n--- 2. Required Python Dependencies ---")
    results["Packages"] = check_packages()

    print("\n--- 3. Node.js & Frontend Environment ---")
    results["Node/NPM"] = check_node_npm()

    print("\n--- 4. Configuration & Directories ---")
    results["Paths"] = check_paths_and_config()

    print("\n--- 5. Backend Modules Importability ---")
    results["Imports"] = check_backend_imports()

    print("\n--- 6. Local SQLite Storage Engine ---")
    results["Database"] = check_database()

    print_header("VERIFICATION SUMMARY")
    all_passed = True
    for component, passed in results.items():
        status = "[PASSED]" if passed else "[FAILED]"
        print(f"  {component:<25} {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n>>> ALL SYSTEMS READY. SENTINEL is ready for local execution.")
        return 0
    else:
        print("\n>>> SOME CHECKS FAILED. Please review the details above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
