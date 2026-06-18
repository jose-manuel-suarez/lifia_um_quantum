# shared/venv_management.py
import os
import sys
import shutil
import logging
import subprocess
import venv
from pathlib import Path

def ensure_venv(venv_dir: Path, logger: logging.Logger) -> None:
    if venv_dir.exists():
        logger.info(f"Virtualenv already exists at {venv_dir}")
        return
    logger.info(f"Creating virtualenv at {venv_dir}")
    venv.EnvBuilder(with_pip=True).create(str(venv_dir))
    logger.info("Virtualenv created")


def get_venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def resolve_requirements_path(req: Path) -> Path:
    """Resuelve la ruta de requerimientos soportando directorios con o sin typos."""
    if req.is_absolute():
        return req

    cand = Path.cwd() / req
    if cand.exists():
        return cand

    for d in ("requeriments", "requirements"):
        alt = Path.cwd() / d / req.name
        if alt.exists():
            return alt

    return cand


def pip_install(venv_python: Path, requirements: Path, logger: logging.Logger):
    logger.info("Upgrading pip in venv")
    subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)

    req_path = resolve_requirements_path(Path(requirements))
    if req_path.exists():
        logger.info(f"Installing requirements from {req_path}")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(req_path.resolve())], check=True)
    else:
        logger.warning(f"No requirements file found at {req_path}; skipping install")


def find_suitable_python(min_version=(3, 10)):
    """Retorna el comando ejecutable para una versión de Python >= min_version o None."""
    candidates = [["py", "-3.10"], ["py", "-3.11"], ["python3.10"], ["python3"], ["python"]] if sys.platform.startswith("win") else [["python3.10"], ["python3"], ["python"]]

    for parts in candidates:
        exe = shutil.which(parts[0])
        if not exe and Path(parts[0]).exists():
            exe = str(Path(parts[0]))
        if not exe:
            continue

        cmd = [exe] + parts[1:] + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, universal_newlines=True)
            vals = out.strip().split()
            if len(vals) >= 2 and (int(vals[0]) > min_version[0] or (int(vals[0]) == min_version[0] and int(vals[1]) >= min_version[1])):
                return [exe] + parts[1:]
        except Exception:
            continue

    if sys.platform.startswith("win"):
        # 1. Intentar resolver usando variables de entorno nativas de Windows para AppData
        local_appdata = os.environ.get("LOCALAPPDATA")
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        system_drive = os.environ.get("SystemDrive", "C:")

        common_paths = [
            Path(system_drive) / "Windows" / "py.exe",
            Path(system_drive) / "Windows" / "System32" / "py.exe",
        ]

        # Agregar rutas dinámicas basadas en el LocalAppData del usuario activo actual
        if local_appdata:
            python_local_dir = Path(local_appdata) / "Programs" / "Python"
            if python_local_dir.exists():
                # Busca recursivamente ejecutables python.exe dentro de la carpeta de programas locales
                common_paths.extend(python_local_dir.glob("Python3*/python.exe"))

        # Agregar rutas compartidas en Program Files o raíz
        common_paths.extend(Path(program_files).glob("Python3*/python.exe"))
        common_paths.extend(Path(f"{system_drive}/").glob("Python3*/python.exe"))

        for p in common_paths:
            try:
                if p.exists():
                    out = subprocess.check_output([str(p), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"], stderr=subprocess.DEVNULL, universal_newlines=True)
                    vals = out.strip().split()
                    if len(vals) >= 2 and (int(vals[0]) > min_version[0] or (int(vals[0]) == min_version[0] and int(vals[1]) >= min_version[1])):
                        return [str(p)]
            except Exception:
                continue
    return None


def get_python_version(python_exe: Path):
    try:
        out = subprocess.check_output([str(python_exe), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"], stderr=subprocess.DEVNULL, universal_newlines=True)
        vals = out.strip().split()
        if len(vals) >= 2:
            return int(vals[0]), int(vals[1])
    except Exception:
        return None
    return None


def install_ecosystem_requirements(venv_py: Path, ecosystem: str, logger: logging.Logger):
    """Instala las dependencias específicas de los ecosistemas indicados."""
    if not ecosystem:
        return

    if ecosystem.upper() == "ALL":
        agg = resolve_requirements_path(Path("requeriments/requirements-all-ecosystems.txt"))
        if agg.exists():
            pip_install(venv_py, agg, logger)
        else:
            logger.warning(f"No aggregated requirements file found at {agg}; skipping")
    else:
        for e in [x.strip() for x in ecosystem.split(",") if x.strip()]:
            eco_req = resolve_requirements_path(Path(f"requeriments/requirements-{e.lower()}.txt"))
            if eco_req.exists():
                pip_install(venv_py, eco_req, logger)
            else:
                logger.warning(f"No requirements file for ecosystem {e} at {eco_req}; skipping")