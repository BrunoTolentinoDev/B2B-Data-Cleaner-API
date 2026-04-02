# B2B Data Cleaner API

**Transforme dados brutos de lead em contexto acionável para vendas** — em uma única chamada REST.

API **assíncrona** construída em **FastAPI**, com **validação determinística** (e-mail e CNPJ em Python) e **enriquecimento semântico** via **DeepSeek** (LLM), orquestrado para **custo previsível**: cache em memória com **TTL** e **single-flight** evitam chamadas redundantes à IA quando o mesmo lead se repete.

---

## Por que isso importa

| Para o produto | O que entrega |
|----------------|---------------|
| **Time comercial** | Nome padronizado, **setor estimado**, **perfil de vendas** e um **`sales_hook`** em parágrafo — material pronto para abordagem. |
| **Operação / dados** | **E-mail** e **CNPJ** validados antes de gastar token; **`is_garbage`** sinaliza leads claramente inúteis. |
| **Engenharia** | Contratos **Pydantic v2**, **OpenAPI** nativo, erros HTTP consistentes, testes com **pytest** + mocks da IA. |

---

## Destaques técnicos

- **Async end-to-end** — `async`/`await` na API e na integração com o cliente OpenAI (`AsyncOpenAI`).
- **Separação de responsabilidades** — regras estruturais em **Python puro**; inferência e redação no **LLM** (`temperature: 0` para respostas mais estáveis).
- **Cache inteligente** — chave normalizada por nome; deduplicação concorrente (uma computação por chave sob carga paralela).
- **Observabilidade mínima** — `GET /health` para probes; `GET /` com links úteis.

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Framework | **FastAPI**, **Pydantic v2**, **Uvicorn** |
| IA | **OpenAI SDK** → endpoint **DeepSeek** (`base_url` configurável) |
| Validação CNPJ | **pycpfcnpj** + fallback algorítmico |
| Cache | Memória, **TTL** configurável, **single-flight** por chave |

---

## Fluxo resumido

1. **Entrada:** `nome`, `email`, `cnpj`.
2. **Python:** valida formato de e-mail e dígitos do CNPJ; normaliza saída do CNPJ (somente dígitos).
3. **LLM:** enriquece a partir do nome — padronização, setor, perfil, gancho comercial, flag de lixo.
4. **Cache:** hits repetidos devolvem o mesmo objeto enriquecido até expirar o TTL.

---

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha.

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `DEEPSEEK_API_KEY` | Sim | Chave da API DeepSeek |
| `DEEPSEEK_BASE_URL` | Não | Padrão: `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | Não | Padrão: `deepseek-chat` |
| `CACHE_TTL_SECONDS` | Não | Padrão: `86400` |

---

## Instalação e execução

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**PowerShell (Windows):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

| URL | Uso |
|-----|-----|
| `http://127.0.0.1:8000/` | Metadados + links |
| `http://127.0.0.1:8000/health` | Health check |
| `http://127.0.0.1:8000/docs` | **Swagger UI** (OpenAPI interativo) |

---

## API — `POST /validate/lead`

**Request (JSON)**

| Campo | Tipo | Regras |
|-------|------|--------|
| `nome` | string | 1–200 caracteres |
| `email` | string | 3–320 caracteres; validação por regex |
| `cnpj` | string | 11–18 caracteres; CNPJ válido (dígitos verificadores) |

**Response (JSON)**

| Campo | Descrição |
|-------|-----------|
| `nome_padronizado` | Nome limpo / capitalização |
| `setor_estimado` | Setor inferido (ex.: Varejo, Saúde) |
| `perfil_vendas` | Linha curta de contexto (até 10 palavras após pós-processamento) |
| `sales_hook` | Parágrafo de abordagem (até 2000 caracteres) |
| `is_garbage` | Indica nome claramente inválido / lixo |
| `email` | Eco normalizado |
| `cnpj` | 14 dígitos |

**Exemplo (PowerShell):**

```powershell
curl -Method POST "http://127.0.0.1:8000/validate/lead" `
  -ContentType "application/json" `
  -Body '{"nome":"magazine luiza sa","email":"contato@exemplo.com","cnpj":"11.444.777/0001-61"}'
```

**HTTP:** `200` sucesso · `422` validação · `502` falha na resposta ou no parsing do JSON da IA.

---

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

Cobertura: validadores, cache (incl. concorrência), serviço com **mock** da IA, integração HTTP sobre **ASGI**.

---

## Segurança

Não versionar **`.env`**. Repositório deve conter apenas **`.env.example`**.

---

## Licença

Defina conforme o uso (ex.: MIT, proprietário).
