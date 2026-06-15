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

    # If no logger was provided, create a per-run logger in logs/<ts>/
    if logger is None:
        base_log_dir = Path(env.get("LOG_DIR", "logs"))
        run_log_dir = base_log_dir / ts
        os.makedirs(run_log_dir, exist_ok=True)
        log_filename = Path(env.get("LOG_FILE", "workflow.log")).name
        logger = get_logger("lifia_workflow", log_file=str(run_log_dir / log_filename))

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
    """Return a command list for a python executable with at least min_version or None."""
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [["py", "-3.10"], ["py", "-3.11"], ["python3.10"], ["python3"], ["python"]]
    else:
        candidates = [["python3.10"], ["python3"], ["python"]]

    for parts in candidates:
        exe = shutil.which(parts[0])
        if not exe:
            continue
        cmd = parts + ["-c", "import sys; print(sys.version_info[0], sys.version_info[1])"]
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, universal_newlines=True)
            vals = out.strip().split()
            if len(vals) >= 2:
                maj = int(vals[0]); minor = int(vals[1])
                if maj > min_version[0] or (maj == min_version[0] and minor >= min_version[1]):
                    return parts
        except Exception:
            continue
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
    args = parser.parse_args(argv)

    # Load env first
    env = load_env(args.env)

    # Prepare timestamp and per-run log directory so bootstrap and child process share it
    ts = args.run_ts or datetime.now().strftime("%d_%m_%y_%H_%M")
    base_log_dir = Path(env.get("LOG_DIR", "logs"))
    run_log_dir = base_log_dir / ts
    os.makedirs(run_log_dir, exist_ok=True)
    log_filename = Path(env.get("LOG_FILE", "workflow.log")).name
    logger = get_logger("lifia_workflow", log_file=str(run_log_dir / log_filename))
    logger.info(f"Log file: {run_log_dir / log_filename}")

    # If bootstrap requested and we're not already running inside the target venv, create venv and re-invoke
    if args.bootstrap:
        venv_dir = Path(args.venv)
        venv_py = _venv_python(venv_dir)

        # If current interpreter is already the venv python, just run workflow normally
        try:
            if venv_dir.exists() and Path(sys.executable).resolve() == venv_py.resolve():
                logger.info("Already running inside target virtualenv; proceeding to run workflow")
            else:
                # Create the venv. If current Python is older than 3.10, try to find a suitable python on PATH
                if not venv_dir.exists():
                    if sys.version_info < (3, 10):
                        logger.info("Current interpreter < 3.10; attempting to find Python 3.10+ on PATH to create venv")
                        py_cmd = _find_suitable_python(min_version=(3, 10))
                        if py_cmd:
                            logger.info(f"Creating virtualenv at {venv_dir} using: {' '.join(py_cmd)}")
                            subprocess.run(py_cmd + ["-m", "venv", str(venv_dir)], check=True)
                        else:
                            logger.info("No suitable external Python found; creating venv with current interpreter")
                            _ensure_venv(venv_dir, logger)
                    else:
                        _ensure_venv(venv_dir, logger)
                else:
                    logger.info(f"Virtualenv already exists at {venv_dir}")

                venv_py = _venv_python(venv_dir)

                # Always install the provided base requirements file first (if present)
                base_requirements = _resolve_requirements_path(Path(args.requirements))
                _pip_install(venv_py, base_requirements, logger)

                # Also attempt to install ecosystem-specific requirements based on .env ECOSYSTEM
                ecosystem = env.get("ECOSYSTEM", "").strip()
                if ecosystem:
                    # Support 'ALL' to install the aggregated file, or comma-separated list
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
        except Exception:
            logger.exception("Bootstrap failed")
            raise

    # Run the workflow in the current interpreter
    output_dir = args.output_dir if args.output_dir is not None else env.get("OUTPUT_DIR", "out")
    run_workflow(env_path=args.env, output_dir=output_dir, run_ts=ts, logger=logger)


if __name__ == "__main__":
    main()
