# B2B Data Cleaner API

**API de higienização e enriquecimento de leads B2B:** valida e-mail e CNPJ com regras determinísticas, padroniza o nome e devolve contexto comercial acionável — com **menos custo de LLM** em leads repetidos graças a cache com TTL.

---

## Sobre o projeto

Serviço pensado para **integração em pipelines de dados** e **ferramentas de CRM/automação**: times de **vendas**, **operações** e **dados** precisam de **leads consistentes** antes de segmentar, pontuar ou disparar campanhas. Esta API atua como **camada de qualidade na entrada**: recusa ruído estrutural cedo (e-mail/CNPJ inválidos) e enriquece o que passou pelo filtro — **nome padronizado**, **setor estimado**, **perfil para vendas**, **gancho de abordagem** e sinal de **nome lixo** — para decisões e cadastros mais **confiáveis**.

---

## O problema de negócio (e o impacto)

| Dor | Efeito no mundo real |
|-----|----------------------|
| **Dados inconsistentes** | CRM “sujo”, duplicidade semântica, relatórios mentirosos. |
| **Leads despadronizados** | Segmentação fraca, cadência genérica, baixa relevância na abordagem. |
| **Erros silenciosos** (e-mail/CNPJ) | Automações quebrando downstream, filas de *retry*, suporte operacional. |

**O que muda com uma API assim:** **padronização** e **consistência** na origem → melhor **qualidade de dados** para **tomada de decisão**, cadastros mais **confiáveis** e base para **automação** que não depende só de regra frágil — sem prometer métricas que o código não mede.

---

## Exemplo de uso (contrato real da API)

> **Nota:** o contrato implementado é `nome`, `email`, `cnpj` — não há campos `company` ou `phone` neste repositório.

**`POST /validate/lead`** — entrada típica (lead “sujo” / informal):

```json
{
  "nome": "magazine luiza sa",
  "email": "  contato@exemplo.com  ",
  "cnpj": "11.444.777/0001-61"
}
```

**Resposta `200`** (trechos de enriquecimento **variam** conforme o modelo; formato fixo):

```json
{
  "nome_padronizado": "Magazine Luiza",
  "setor_estimado": "Varejo",
  "perfil_vendas": "Grande varejista nacional com forte atuação digital",
  "sales_hook": "Podemos conversar sobre como a Magazine Luiza se encaixa na sua estratégia de prospecção.",
  "is_garbage": false,
  "email": "contato@exemplo.com",
  "cnpj": "11444777000161"
}
```

Schemas: `app/schemas/lead.py` (`LeadValidateRequest` / `LeadValidateResponse`).

---

## Funcionalidades

**Qualidade e padronização**
- Validação **determinística** de **e-mail** (regex + trim) e **CNPJ** (**pycpfcnpj** + fallback de dígitos verificadores).
- **CNPJ** na resposta só com **14 dígitos** — formato único para CRM e integrações.
- **Nome** passa por enriquecimento com **LLM** (padronização + contexto comercial).

**Enriquecimento comercial (LLM DeepSeek)**
- `nome_padronizado`, `setor_estimado`, `perfil_vendas` (até **10 palavras** após pós-processamento), `sales_hook` (parágrafo; limite **2000** caracteres no pipeline + schema), `is_garbage`.
- Cliente **openai** (`AsyncOpenAI`), `temperature=0`, `max_tokens=1024`, parse robusto de JSON (inclui *fences* `json` quando o modelo manda).

**Performance e consistência operacional**
- **Cache em memória** + **TTL** (`CACHE_TTL_SECONDS`, padrão 86400) + **single-flight** — mesma chave de nome normalizado não dispara N chamadas concorrentes à IA.

**Engenharia de API**
- **FastAPI** + **Pydantic v2** (`extra` proibido), **OpenAPI** em `/docs` e `/openapi.json`.
- **Handlers globais** (`422`, `502`, `500` conforme implementação).
- **`GET /`**, **`GET /health`**, testes com **pytest** / **httpx** (integração ASGI).

---

## Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python **3.10+** |
| API | **FastAPI**, **Uvicorn** (ASGI, extras `standard`) |
| Contratos & config | **Pydantic v2**, **pydantic-settings** (`.env`) |
| LLM | **openai** (`AsyncOpenAI` → **DeepSeek**) |
| CNPJ | **pycpfcnpj** + validador interno |
| Testes | **pytest**, **pytest-asyncio**, **httpx** (`requirements-dev.txt`) |

---

## Como funciona (pipeline)

1. Cliente envia `nome`, `email`, `cnpj` → `POST /validate/lead`.
2. **Pydantic** valida limites e bloqueia campos extras.
3. **Validação estrutural:** e-mail + CNPJ + nome não vazio → senão `422`.
4. **`CleaningService.enrich_lead`:** chave `lead_enrichment:<nome normalizado>`; em *miss*, *chat completion* DeepSeek → JSON obrigatório → pós-processamento (`perfil_vendas`, `_finalize_sales_hook`).
5. Resposta **enriquecida** + `email` + `cnpj` dígitos.

**Arquitetura**

```
Cliente → FastAPI (routes, deps, erros)
       → Validadores (e-mail, CNPJ)
       → CleaningService + InMemoryCache → DeepSeek (AsyncOpenAI)
       → LeadValidateResponse
```

Config: `app/core/config.py` (`DEEPSEEK_*`, `CACHE_TTL_SECONDS`); serviço em `app.state` (`main.py`).

**Endpoints**

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/` | `service`, `docs`, `openapi.json` |
| `GET` | `/health` | `{"status": "ok"}` |
| `POST` | `/validate/lead` | Valida + enriquece |

**HTTP:** `200` · `422` · `502` (IA) · `500`.

---

## Como rodar

```bash
# .env a partir de .env.example — obrigatório: DEEPSEEK_API_KEY
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Docs: `http://127.0.0.1:8000/docs`

```bash
pip install -r requirements-dev.txt && pytest -q
```

**Segurança:** não commitar `.env`.

---

## Diferenciais (backend + negócio)

- **Não é CRUD genérico:** há **camada de validação** (regras de negócio brasileiras — CNPJ) separada da **camada semântica** (LLM).
- **Pensamento de custo e escala:** cache + single-flight = **menos chamadas à IA** em leads repetidos — decisão típica de **produto** em pipeline de dados.
- **Contratos explícitos:** Pydantic + OpenAPI = integração previsível com **CRM**, **ETL** ou **orquestradores**.
- **Tratamento de falha:** erros de validação vs. falha de parsing da IA mapeados para HTTP — operação sabe **o que** quebrou.

---

## Melhorias futuras

- Cache **distribuído** (ex.: Redis) para múltiplas instâncias.
- **Persistência** / auditoria de leads se o produto evoluir.
- **Auth** / **rate limiting** na borda para exposição pública.
- **Observabilidade** (logs estruturados, métricas, tracing) alinhada ao deploy.
