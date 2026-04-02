# B2B Data Cleaner API

API REST **assíncrona** em **FastAPI** que valida **e-mail** e **CNPJ** em Python e enriquece o lead via **DeepSeek** usando o **nome** como entrada principal. Inclui **cache em memória** (TTL configurável) e **single-flight** para não repetir chamadas à LLM para o mesmo nome normalizado.

---

## Stack (o que o projeto usa)

| Área | Tecnologia |
|------|------------|
| Runtime | Python **3.10+** |
| API / validação | **FastAPI**, **Pydantic v2**, **Uvicorn** (ASGI) |
| Config | **pydantic-settings** (`.env`) |
| Integração LLM | **openai** (`AsyncOpenAI`, `base_url` da DeepSeek) |
| CNPJ | **pycpfcnpj** + validação alternativa no código |
| Testes | **pytest**, **pytest-asyncio**, **httpx** (`requirements-dev.txt`) |

---

## Funcionalidades (reais)

- `POST /validate/lead`: body `nome`, `email`, `cnpj` (Pydantic; `extra` proibido).
- Validação de e-mail (regex + trim) e de CNPJ antes da IA.
- Resposta com: `nome_padronizado`, `setor_estimado`, `perfil_vendas` (truncado a **10 palavras** no pós-processamento), `sales_hook` (parágrafo; rejeita string **> 2000** caracteres antes do pós-processamento; schema limita a 2000), `is_garbage`, além de `email` e `cnpj` só com dígitos.
- Chamada ao modelo: `temperature=0`, `max_tokens=1024`, parsing de JSON retornado (remove cercas tipo *code fence* `json` quando presentes).
- Pós-processamento de `sales_hook`: normalização de espaços, heurística para cauda truncada e garantia de pontuação final quando aplicável (`_finalize_sales_hook`).
- Tratamento global de erros (`RequestValidationError`, `HTTPException`, `AIResponseError`, etc.).
- `GET /` — metadados e links para `/docs` e OpenAPI; `GET /health` — `{ "status": "ok" }`.

---

## Fluxo lógico

1. Valida corpo e regras de e-mail/CNPJ/nome não vazio.
2. Monta chave de cache `lead_enrichment:<nome normalizado>`.
3. Em miss: `chat.completions.create` na DeepSeek; extrai objeto JSON; valida campos obrigatórios; aplica limites e `_finalize_sales_hook`.
4. Retorna `LeadValidateResponse`.

---

## Como rodar

```bash
# Copie .env.example para .env e defina DEEPSEEK_API_KEY
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Documentação interativa: `http://127.0.0.1:8000/docs`

**Testes:**

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Serviço, `docs`, `openapi.json` |
| `GET` | `/health` | Health check |
| `POST` | `/validate/lead` | Valida lead e enriquece via IA |

HTTP usuais: `200`, `422`, `502` (falha de parsing/resposta da IA), `500`.

---

## Segurança

Não versionar `.env` (chaves). Usar `.env.example` como referência.
