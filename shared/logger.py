import os
import logging
from datetime import datetime
from typing import Optional

from click import Path

class ColorFormatter(logging.Formatter):
    """Formatter condicional que inyecta colores ANSI si se solicita."""
    RESET = "\033[0m"
    GREEN = "\033[32m"      # INFO exitoso
    YELLOW = "\033[33m"     # WARNING
    RED = "\033[31m"        # ERROR / CRITICAL
    CYAN = "\033[36m"       # Metadatos (Tiempo)

    def __init__(self, fmt: str, use_color: bool = True):
        super().__init__(fmt)
        self.use_color = use_color

    def format(self, record):
        if not self.use_color:
            return super().format(record)

        orig_fmt = self._style._fmt

        if record.levelno == logging.INFO:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} {self.GREEN}%(levelname)s: %(message)s{self.RESET}"
        elif record.levelno == logging.WARNING:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} {self.YELLOW}%(levelname)s: %(message)s{self.RESET}"
        elif record.levelno >= logging.ERROR:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} {self.RED}%(levelname)s: %(message)s{self.RESET}"
        else:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} %(levelname)s: %(message)s"

        result = super().format(record)
        self._style._fmt = orig_fmt
        return result


def get_logger(name: str = "lifia", env_dict: Optional[dict] = None) -> logging.Logger:
    """
    Inicializa y configura un logger dinámicamente parametrizado.
    Genera el nombre del archivo basado en el ecosistema y la estampa de tiempo actual.
    """
    cfg = env_dict if env_dict is not None else os.environ

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    if not cfg.get("LOG_ALLOWED", "True").lower() in ("true", "1", "yes", "y"):
        return

    # 2. Configuración de severidad y formato
    log_level_str = cfg.get("LOG_LEVEL", "INFO").upper()
    use_color = cfg.get("LOG_COLOR", "True").lower() in ("true", "1", "yes")
    disable_file = cfg.get("LOG_DISABLE_FILE", "False").lower() in ("true", "1", "yes")
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    logger.setLevel(level_map.get(log_level_str, logging.INFO))
    fmt_str = "%(asctime)s %(levelname)s %(message)s"

    # 3. Handler de Consola
    if os.name == 'nt' and use_color:
        os.system('')
    sh = logging.StreamHandler()
    sh.setFormatter(ColorFormatter(fmt_str, use_color=use_color))
    logger.addHandler(sh)

    # 4. Handler de Archivo Físico Automatizado
    if not disable_file:
        
        from shared.io_utils import get_project_root
        
        log_filename = f"run_shot_{cfg.get("ECOSYSTEM", "DEFAULT").upper()}_{datetime.now().strftime("%d_%m_%y__%H_%M")}.log"
        full_log_path = os.path.join(get_project_root(), cfg['LOG_DIR'], log_filename)

        # Asegurar que la estructura de directorios exista
        os.makedirs(log_filename, exist_ok=True)

        fh = logging.FileHandler(full_log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter(fmt_str))
        logger.addHandler(fh)

    return logger