import os
import json
from pathlib import Path

def _config_path():
    appdata = os.environ.get("APPDATA") or Path.home()
    pasta = Path(appdata) / "SIA"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta / "config.json"

def carregar_config():
    try:
        path = _config_path()
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def salvar_config(config):
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise RuntimeError(f"Nao foi possivel salvar a configuracao: {e}")

def obter_chaves():
    config = carregar_config()
    chaves_str = config.get("gemini_keys", "")
    if not chaves_str:
        return []
    return [k.strip() for k in chaves_str.split(",") if k.strip()]

def chaves_configuradas():
    return len(obter_chaves()) > 0

def config_path_str():
    return str(_config_path())
