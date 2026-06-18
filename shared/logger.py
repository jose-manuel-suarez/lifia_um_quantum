import os
import logging

class ColorFormatter(logging.Formatter):
    """Formatter que inyecta secuencias de escape ANSI para dar color en consola."""
    RESET = "\033[0m"
    GREEN = "\033[32m"      # INFO exitoso
    YELLOW = "\033[33m"     # WARNING
    RED = "\033[31m"        # ERROR / CRITICAL
    CYAN = "\033[36m"       # Metadatos (Tiempo)

    def format(self, record):
        # Guardamos el formato original por seguridad
        orig_fmt = self._style._fmt

        # Aplicamos colores condicionales según la severidad del log
        if record.levelno == logging.INFO:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} {self.GREEN}%(levelname)s: %(message)s{self.RESET}"
        elif record.levelno == logging.WARNING:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} {self.YELLOW}%(levelname)s: %(message)s{self.RESET}"
        elif record.levelno >= logging.ERROR:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} {self.RED}%(levelname)s: %(message)s{self.RESET}"
        else:
            self._style._fmt = f"{self.CYAN}%(asctime)s{self.RESET} %(levelname)s: %(message)s"

        result = super().format(record)
        self._style._fmt = orig_fmt  # Restauramos el formato estándar
        return result


def get_logger(name: str = "lifia", log_file: str = None, level=logging.INFO) -> logging.Logger:
    """
    Inicializa y configura un logger unificado con salida de colores en consola 
    y persistencia plana en archivo de texto.
    """
    # Forzar a Windows a interpretar secuencias ANSI si se ejecuta localmente
    if os.name == 'nt':
        os.system('')

    logger = logging.getLogger(name)
    
    # Evitar duplicación de handlers si el logger ya fue inicializado previamente
    if logger.handlers:
        return logger
        
    logger.setLevel(level)

    # Estructura del string de formato base
    fmt_str = "%(asctime)s %(levelname)s %(message)s"
    plain_formatter = logging.Formatter(fmt_str)

    # 1. Configuración de Salida por Consola (Con color verde/amarillo/rojo)
    sh = logging.StreamHandler()
    color_formatter = ColorFormatter(fmt_str)  # Se pasa el string de formato
    sh.setFormatter(color_formatter)
    logger.addHandler(sh)

    # 2. Configuración de Salida a Archivo (Texto plano limpio de caracteres ANSI)
    if not log_file:
        log_file = os.environ.get("LOG_FILE", "workflow.log")

    # Asegura que el directorio del archivo de logs exista antes de crearlo
    log_path = os.path.dirname(log_file)
    if log_path:
        os.makedirs(log_path, exist_ok=True)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(plain_formatter)
    logger.addHandler(fh)

    return logger