import os
import argparse

from datetime import datetime
from pathlib import Path
from shared.logger import get_logger
from shared.config import load_env

def parse_arguments_and_env(argv=None):
    """
    Parsea los argumentos de línea de comandos, carga el entorno configurado
    y prepara las variables iniciales del sistema (logs, timestamps, etc.).
    """
    parser = argparse.ArgumentParser(description="Run the conversion workflow (optional bootstrap)")
    parser.add_argument("--env", default=".env", help="Env file to load")
    parser.add_argument("--output-dir", default=None, help="Base output directory (overrides .env OUTPUT_DIR)")
    parser.add_argument("--bootstrap", action="store_true", help="Create venv, install requirements and run inside it")
    parser.add_argument("--venv", default=".venv", help="Virtualenv directory to create/use")
    parser.add_argument("--requirements", default="requirements.txt")
    parser.add_argument("--run-ts", default=None, help="(internal) reuse the given run timestamp")
    parser.add_argument("--python-exe", default=None, help="Optional python executable command or path")
    args = parser.parse_args(argv)

    # Carga centralizada de entorno
    env = load_env(args.env)
    logger = get_logger(name="lifia_workflow", env_dict=env)

    return args, env, logger