import os


def load_env(path: str = ".env") -> dict:
    """Load key=value entries from a simple .env file and set them in the environment.

    Lines beginning with # are ignored.
    """
    env = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                env[key] = val
                os.environ[key] = val
    except FileNotFoundError:
        # silence missing .env — caller can decide
        pass
    return env
