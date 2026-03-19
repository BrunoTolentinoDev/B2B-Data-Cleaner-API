# B2B Data Cleaner API

API REST assíncrona (FastAPI) para validação estrutural de leads e enriquecimento via **DeepSeek** a partir do nome da empresa/contato.

## Stack

| Camada | Tecnologia |
|--------|------------|
| Framework | FastAPI, Pydantic v2, Uvicorn |
| IA | OpenAI SDK (`AsyncOpenAI`) → endpoint DeepSeek |
| Validação CNPJ | `pycpfcnpj` + fallback algorítmico |
| Cache | Memória (TTL configurável), single-flight por chave |

## Comportamento

- **Python:** normalização leve de e-mail, validação de e-mail (regex), validação de CNPJ, normalização do CNPJ (somente dígitos na resposta).
- **IA:** inferência a partir do **nome** — padronização, setor, perfil curto, parágrafo de abordagem (`sales_hook`) e classificação `is_garbage`.
- **Cache:** mesma chave de nome (normalizada) reutiliza o objeto enriquecido sem nova chamada à API de IA até expirar o TTL.

## Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste.

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DEEPSEEK_API_KEY` | Sim | Chave da API DeepSeek |
| `DEEPSEEK_BASE_URL` | Não | Padrão: `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | Não | Padrão: `deepseek-chat` |
| `CACHE_TTL_SECONDS` | Não | Padrão: `86400` |

## Instalação e execução

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

URLs úteis (ajuste host/porta se necessário):

| URL | Uso |
|-----|-----|
| `http://127.0.0.1:8000/` | Metadados + links |
| `http://127.0.0.1:8000/health` | Health check |
| `http://127.0.0.1:8000/docs` | OpenAPI (Swagger UI) |

## API

### `POST /validate/lead`

**Request (JSON)**

| Campo | Tipo | Regras |
|-------|------|--------|
| `nome` | string | 1–200 caracteres |
| `email` | string | 3–320 caracteres; validado por regex |
| `cnpj` | string | 11–18 caracteres; dígitos verificadores válidos |

**Response (JSON)**

| Campo | Tipo |
|-------|------|
| `nome_padronizado` | string |
| `setor_estimado` | string |
| `perfil_vendas` | string (até 10 palavras após pós-processamento) |
| `sales_hook` | string (parágrafo; máx. 2000 caracteres) |
| `is_garbage` | boolean |
| `email` | string |
| `cnpj` | string (14 dígitos) |

Exemplo `curl` (Windows, PowerShell):

```powershell
curl -Method POST "http://127.0.0.1:8000/validate/lead" `
  -ContentType "application/json" `
  -Body '{"nome":"magazine luiza sa","email":"contato@exemplo.com","cnpj":"11.444.777/0001-61"}'
```

Códigos HTTP usuais: `200` sucesso; `422` validação (corpo, e-mail ou CNPJ); `502` falha de resposta/parsing da IA.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Segurança

Não commite `.env`. Use apenas `.env.example` no repositório.

## Licença

Defina conforme o uso do projeto (ex.: MIT, proprietário).
