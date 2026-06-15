import argparse
import json
import os
import subprocess
import sys
import venv
import logging
from pathlib import Path
from datetime import datetime
import shutil
import shlex

from shared.config import load_env
from shared.logger import get_logger
from shared.ecosystems import supports, max_supported
from shared.io import write_json_file
from convert import get_converter


def run_workflow(env_path: str = ".env", output_dir: str = "out", run_ts: str = None, logger: logging.Logger = None) -> dict:
    env = load_env(env_path)

    input_file = env.get("INPUT_FILE", "abstraction2.json")
    ecosystem = env.get("ECOSYSTEM", "DEFAULT")

    # Determine base output dir: env overrides function arg
    base_output_dir = env.get("OUTPUT_DIR", output_dir)
    if base_output_dir is None:
        base_output_dir = "out"

    os.makedirs(base_output_dir, exist_ok=True)

    # Use provided timestamp or generate one
    ts = run_ts or datetime.now().strftime("%d_%m_%y_%H_%M")
    run_dir = os.path.join(base_output_dir, ts)
    os.makedirs(run_dir, exist_ok=True)

    # If no logger was provided, create a per-run logger writing directly into logs/
    if logger is None:
        base_log_dir = Path(env.get("LOG_DIR", "logs"))
        os.makedirs(base_log_dir, exist_ok=True)
        log_filename = f"workflow_shot_{ts}.log"
        logger = get_logger("lifia_workflow", log_file=str(base_log_dir / log_filename))

    logger.info(f"Run output directory: {run_dir}")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except FileNotFoundError:
        logger.error(f"Input file {input_file} not found")
        raise

    start_level = int(env.get("INPUT_LEVEL", spec.get("abstraction_level", 1)))

    logger.info(f"Workflow starting: ecosystem={ecosystem} start_level={start_level}")

    current_spec = spec
    max_reached = start_level

    for level in range(start_level, 6):
        next_level = level + 1
        logger.info(f"Attempting conversion {level} -> {next_level}")
        try:
            converter = get_converter(level, next_level)
        except ImportError:
            logger.info(f"No converter available for {level}->{next_level}, stopping conversion chain")
            break

        out_path = os.path.join(run_dir, f"abstraction{next_level}.json")
        try:
            current_spec = converter.convert(current_spec, destination_file=None, ecosystem=ecosystem, logger=logger)
            write_json_file(current_spec, out_path)
            logger.info(f"Wrote intermediate abstraction file: {out_path}")
        except Exception as e:
            logger.exception(f"Conversion {level}->{next_level} failed: {e}")
            break

        if supports(ecosystem, next_level):
            logger.info(f"Ecosystem {ecosystem} supports abstraction level {next_level}")
            max_reached = next_level
        else:
            logger.warning(f"Ecosystem {ecosystem} DOES NOT fully support abstraction level {next_level}")
            # continue trying further conversions but record that ecosystem lacks full support

    summary = {
        "ecosystem": ecosystem,
        "start_level": start_level,
        "max_reached": max_reached,
        "output_base_dir": str(Path(base_output_dir).resolve()),
        "run_dir": str(Path(run_dir).resolve()),
    }

    logger.info(f"Workflow finished. Summary: {summary}")
    return summary


def _ensure_venv(venv_dir: Path, logger: "logging.Logger") -> None:
    if venv_dir.exists():
        logger.info(f"Virtualenv already exists at {venv_dir}")
        return
    logger.info(f"Creating virtualenv at {venv_dir}")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(str(venv_dir))
    logger.info("Virtualenv created")


def _venv_python(venv_dir: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _resolve_requirements_path(req: Path) -> Path:
    """Resolve a requirements file path, supporting both 'requeriments' and 'requirements' directories.

    Returns a Path (may not exist) pointing to the first candidate found.
    """
    # If absolute and exists (or not), return as-is
    if req.is_absolute():
        return req

    # Direct relative candidate
    cand = Path.cwd() / req
    if cand.exists():
        return cand

    # Try common directories (typo'd and correct)
    for d in ("requeriments", "requirements"):
        alt = Path.cwd() / d / req.name
        if alt.exists():
            return alt

    # fallback to the direct relative path (may not exist)
    return cand


def _pip_install(venv_python: Path, requirements: Path, logger: "logging.Logger"):
    logger.info("Upgrading pip in venv")
    subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)

    req_path = _resolve_requirements_path(Path(requirements))
    if req_path.exists():
        logger.info(f"Installing requirements from {req_path}")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(req_path.resolve())], check=True)
    else:
        logger.warning(f"No requirements file found at {req_path}; skipping install")


def _find_suitable_python(min_version=(3, 10)):
    """Return a command list for a python executable with at least min_version or None.

    The returned value is a list suitable for use as the command prefix (e.g.
    ``['py', '-3.10']`` or ``['C:\\\\Python310\\\\python.exe']``).
    """
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [["py", "-3.10"], ["py", "-3.11"], ["python3.10"], ["python3"], ["python"]]
    else:
        candidates = [["python3.10"], ["python3"], ["python"]]

    for parts in candidates:
        # Resolve executable: prefer PATH lookup, otherwise allow absolute paths
        exe = shutil.which(parts[0])
        if not exe and Path(parts[0]).exists():
            exe = str(Path(parts[0]))
        if not exe:
            continue

        # Build command using resolved exe plus remaining args
        cmd = [exe] + parts[1:] + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, universal_newlines=True)
            vals = out.strip().split()
            if len(vals) >= 2:
                maj = int(vals[0]); minor = int(vals[1])
                if maj > min_version[0] or (maj == min_version[0] and minor >= min_version[1]):
                    # Return the command parts (use original parts but with resolved exe)
                    return [exe] + parts[1:]
        except Exception:
            continue

    # If not found via PATH/candidates, on Windows try common installation locations
    if sys.platform.startswith("win"):
        username = os.environ.get("USERNAME") or os.environ.get("USER") or ""
        common_paths = [
            r"C:\\Windows\\py.exe",
            r"C:\\Windows\\System32\\py.exe",
            fr"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python310\\python.exe",
            fr"C:\\Users\\{username}\\AppData\\Local\\Programs\\Python\\Python311\\python.exe",
            r"C:\\Program Files\\Python310\\python.exe",
            r"C:\\Program Files\\Python\\Python310\\python.exe",
            r"C:\\Python310\\python.exe",
        ]
        for p in common_paths:
            try:
                if Path(p).exists():
                    out = subprocess.check_output([p, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"], stderr=subprocess.DEVNULL, universal_newlines=True)
                    vals = out.strip().split()
                    if len(vals) >= 2:
                        maj = int(vals[0]); minor = int(vals[1])
                        if maj > min_version[0] or (maj == min_version[0] and minor >= min_version[1]):
                            return [p]
            except Exception:
                continue

    return None


def _get_python_version(python_exe: Path):
    """Return (major, minor) for the given python executable, or None if it cannot be determined."""
    try:
        out = subprocess.check_output([str(python_exe), "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"], stderr=subprocess.DEVNULL, universal_newlines=True)
        vals = out.strip().split()
        if len(vals) >= 2:
            return int(vals[0]), int(vals[1])
    except Exception:
        return None
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the conversion workflow (optional bootstrap)")
    parser.add_argument("--env", default=".env", help="Env file to load")
    parser.add_argument("--output-dir", default=None, help="Base output directory (overrides .env OUTPUT_DIR)")
    parser.add_argument("--bootstrap", action="store_true", help="Create venv, install requirements and run inside it")
    parser.add_argument("--venv", default=".venv", help="Virtualenv directory to create/use")
    parser.add_argument(
        "--requirements",
        default="requirements/requirements.txt",
        help=(
            "Base requirements file to install into venv. "
            "When bootstrapping, the script will also try to install `requeriments/requirements-<ECOSYSTEM>.txt` "
            "based on the `ECOSYSTEM` value in the env file (supports comma-separated values or 'ALL')."
        ),
    )
    parser.add_argument("--run-ts", default=None, help="(internal) reuse the given run timestamp")
    parser.add_argument(
        "--python-exe",
        default=None,
        help=(
            "Optional python executable (command or path) to create the venv with, "
            "e.g. 'py -3.10' or '/usr/bin/python3.10'. If provided, this will be used to recreate the venv when needed."
        ),
    )
    args = parser.parse_args(argv)

    # Load env first
    env = load_env(args.env)

    # Prepare timestamp and single log file in logs/ (no per-run subdirectories)
    ts = args.run_ts or datetime.now().strftime("%d_%m_%y_%H_%M")
    base_log_dir = Path(env.get("LOG_DIR", "logs"))
    os.makedirs(base_log_dir, exist_ok=True)
    # Use fixed naming for per-run log files as requested: workflow_shot_DD_MM_YY_HH_MM.log
    log_filename = f"workflow_shot_{ts}.log"
    logger = get_logger("lifia_workflow", log_file=str(base_log_dir / log_filename))
    logger.info(f"Log file: {base_log_dir / log_filename}")

    # If bootstrap requested and we're not already running inside the target venv, create venv and re-invoke
    if args.bootstrap:
        venv_dir = Path(args.venv)

        try:
            venv_py = _venv_python(venv_dir)
            if venv_dir.exists() and Path(sys.executable).resolve() == venv_py.resolve():
                logger.info("Already running inside target virtualenv; proceeding to run workflow")
            else:
                # If venv exists, validate or recreate it
                if venv_dir.exists():
                    venv_ver = _get_python_version(venv_py)
                    if venv_ver is not None and (venv_ver[0] > 3 or (venv_ver[0] == 3 and venv_ver[1] >= 10)):
                        logger.info(f"Existing virtualenv at {venv_dir} uses Python {venv_ver[0]}.{venv_ver[1]}")
                    else:
                        logger.warning(f"Existing virtualenv at {venv_dir} uses Python {venv_ver or 'unknown'} which is < 3.10; attempting to recreate with a suitable Python")
                        # choose python command
                        if args.python_exe:
                            py_cmd = shlex.split(args.python_exe)
                        else:
                            py_cmd = _find_suitable_python(min_version=(3, 10))

                        if not py_cmd:
                            raise RuntimeError("No suitable Python 3.10+ available to create virtualenv")

                        logger.info(f"Recreating venv using: {' '.join(py_cmd)}")
                        shutil.rmtree(venv_dir)
                        subprocess.run(py_cmd + ["-m", "venv", str(venv_dir)], check=True)

                else:
                    # venv does not exist; create it using a suitable python
                    if sys.version_info < (3, 10):
                        if args.python_exe:
                            py_cmd = shlex.split(args.python_exe)
                        else:
                            py_cmd = _find_suitable_python(min_version=(3, 10))

                        if not py_cmd:
                            raise RuntimeError("No suitable Python 3.10+ available to create virtualenv")

                        logger.info(f"Creating virtualenv at {venv_dir} using: {' '.join(py_cmd)}")
                        subprocess.run(py_cmd + ["-m", "venv", str(venv_dir)], check=True)
                    else:
                        _ensure_venv(venv_dir, logger)

                venv_py = _venv_python(venv_dir)

                # Install base requirements
                base_requirements = _resolve_requirements_path(Path(args.requirements))
                _pip_install(venv_py, base_requirements, logger)

                # Install ecosystem-specific requirements
                ecosystem = env.get("ECOSYSTEM", "").strip()
                if ecosystem:
                    if ecosystem.upper() == "ALL":
                        agg = _resolve_requirements_path(Path("requeriments/requirements-all-ecosystems.txt"))
                        if agg.exists():
                            _pip_install(venv_py, agg, logger)
                        else:
                            logger.warning(f"No aggregated requirements file found at {agg}; skipping")
                    else:
                        for e in [x.strip() for x in ecosystem.split(",") if x.strip()]:
                            eco_req = _resolve_requirements_path(Path(f"requeriments/requirements-{e.lower()}.txt"))
                            if eco_req.exists():
                                _pip_install(venv_py, eco_req, logger)
                            else:
                                logger.warning(f"No requirements file for ecosystem {e} at {eco_req}; skipping")

                # Re-run this script inside the venv without --bootstrap to avoid recursion
                cmd = [str(venv_py), str(Path(__file__).resolve()), "--env", args.env, "--run-ts", ts]
                if args.output_dir:
                    cmd += ["--output-dir", args.output_dir]
                logger.info(f"Re-invoking inside venv: {' '.join(cmd)}")
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode != 0:
                    logger.error("Re-invoked process failed")
                    logger.error("--- stdout ---\n" + (proc.stdout or ""))
                    logger.error("--- stderr ---\n" + (proc.stderr or ""))
                    raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
                logger.info("Re-invocation succeeded inside venv; exiting bootstrap parent process")
                return
        except RuntimeError as re_err:
            if "No suitable Python 3.10+ available" in str(re_err):
                logger.warning("Could not create a Python 3.10+ virtualenv; proceeding to run in current interpreter (compatibility fallback).")
            else:
                logger.exception("Bootstrap failed")
                raise
        except Exception:
            logger.exception("Bootstrap failed")
            raise

    # Run the workflow in the current interpreter
    output_dir = args.output_dir if args.output_dir is not None else env.get("OUTPUT_DIR", "out")
    run_workflow(env_path=args.env, output_dir=output_dir, run_ts=ts, logger=logger)


if __name__ == "__main__":
    main()
    