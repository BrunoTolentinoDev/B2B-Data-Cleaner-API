import os
import sys
from pathlib import Path


# Garante variáveis mínimas para instanciar `Settings()` sem depender do `.env` local.
os.environ.setdefault("DEEPSEEK_API_KEY", "test-key")
os.environ.setdefault("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")

# Permite importar `main` e `app` quando o pytest rodar a partir da raiz.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

