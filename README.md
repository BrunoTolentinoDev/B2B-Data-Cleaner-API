# B2B Data Cleaner API

## Visão geral

Dados de leads B2B costumam chegar **sujos ou inconsistentes**: nomes de empresa mal formatados, e-mails inválidos e CNPJ incorreto geram retrabalho em CRMs e quebram automações. Este projeto é uma **API REST assíncrona** que **valida dados estruturais em Python** (formato de e-mail e CNPJ brasileiro) e **enriquece e normaliza o lead a partir do nome** da empresa/contato usando o LLM **DeepSeek** via cliente compatível com OpenAI. As respostas são **contratadas por schema (Pydantic v2)** e expostas via **OpenAPI** para integração previsível.

**Na prática:** payloads de lead mais uniformes para sistemas downstream, com **menos chamadas redundantes ao LLM** para o mesmo nome repetido, graças a um **cache em memória** (TTL + deduplicação single-flight por chave).

---

## Funcionalidades

- **API assíncrona** com **FastAPI** e **Uvicorn** (ASGI).
- **Contratos de entrada/saída** com **Pydantic v2** (`extra` proibido nos schemas de lead).
- **Camada de validação (Python):** regex de e-mail + trim; validação de CNPJ com **pycpfcnpj** e **fallback local** de dígitos verificadores se o caminho da biblioteca falhar.
- **Camada de enriquecimento (LLM):** `AsyncOpenAI` apontando para **DeepSeek** (`base_url` configurável); `temperature=0`, `max_tokens=1024`; extração de JSON da resposta do modelo (inclui blocos *fenced* `json` quando presentes).
- **Pós-processamento:** `perfil_vendas` limitado a **10 palavras**; `sales_hook` rejeitado se tiver mais de **2000** caracteres antes da normalização; `_finalize_sales_hook` normaliza espaços e aplica heurísticas de pontuação / cauda incompleta.
- **Cache em memória** com **TTL** configurável (`CACHE_TTL_SECONDS`, padrão 86400) e comportamento **single-flight** para que requisições concorrentes ao mesmo nome normalizado compartilhem uma única computação.
- **Handlers globais de exceção** para erros de validação, HTTP, JSON inválido da IA e falhas genéricas (`422`, `502`, `500` conforme implementado).
- **Endpoints operacionais:** `GET /` (metadados do serviço + links da doc), `GET /health` (`{"status": "ok"}`).
- **Testes automatizados:** `pytest`, `pytest-asyncio`, `httpx` (testes de integração ASGI com LLM mockada quando aplicável).

---

## Stack tecnológica

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python **3.10+** |
| Framework web | **FastAPI** |
| Servidor | **Uvicorn** (extras `standard` no `requirements`) |
| Validação e config | **Pydantic v2**, **pydantic-settings** (`.env`) |
| Cliente LLM | **openai** (`AsyncOpenAI` → API DeepSeek) |
| CNPJ | **pycpfcnpj** (+ validador de fallback interno) |
| Testes | **pytest**, **pytest-asyncio**, **httpx** (`requirements-dev.txt`) |

---

## Como funciona

1. **Entrada:** o cliente envia `nome`, `email`, `cnpj` em `POST /validate/lead`.
2. **Validação de schema:** o Pydantic aplica limites de tamanho e rejeita campos extras.
3. **Validação estrutural:** e-mail com trim e regex; CNPJ validado; `nome` vazio após `strip` retorna `422`.
4. **Enriquecimento:** `CleaningService.enrich_lead` monta a chave `lead_enrichment:<nome normalizado>`. Em *miss*, chama a API de *chat completion*, faz parse de um objeto JSON com chaves obrigatórias, aplica limites de palavras e finalização de `sales_hook`, e armazena até expirar o TTL.
5. **Saída:** a API devolve os campos enriquecidos, `email` normalizado e `cnpj` como **string de 14 dígitos**.

---

## Arquitetura

```
Cliente
  → FastAPI (rotas: app/api/routes, deps, erros globais)
      → Validadores (e-mail, CNPJ) — Python puro
      → CleaningService + InMemoryCache
          → DeepSeek (chat.completions, AsyncOpenAI)
  → LeadValidateResponse (Pydantic)
```

A configuração está em **`app/core/config.py`** (`Settings`: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `CACHE_TTL_SECONDS`). O serviço de limpeza é registrado em **`app.state`** em `main.py`.

---

## Endpoints da API

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/` | Retorna `service`, `docs` e caminho do `openapi.json`. |
| `GET` | `/health` | Verificação simples: `{"status": "ok"}`. |
| `POST` | `/validate/lead` | Valida e-mail/CNPJ/nome, executa enriquecimento via LLM, retorna `LeadValidateResponse`. |

Documentação interativa: **`/docs`** (Swagger UI). Esquema OpenAPI: **`/openapi.json`**.

**Códigos HTTP usuais:** `200` sucesso; `422` validação ou regra de negócio (e-mail/CNPJ/nome inválidos); `502` resposta da IA não pôde ser interpretada ou não atende ao contrato; `500` erro não tratado (mensagem genérica).

---

## Exemplo de requisição e resposta

**Requisição** (`POST /validate/lead`, `Content-Type: application/json`)

```json
{
  "nome": "magazine luiza sa",
  "email": "contato@exemplo.com",
  "cnpj": "11.444.777/0001-61"
}
```

**Resposta** (`200`) — Os textos de enriquecimento são **gerados pelo modelo**; redação e idioma variam. A forma abaixo segue o schema.

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

Nomes e tipos dos campos seguem **`LeadValidateRequest`** / **`LeadValidateResponse`** em `app/schemas/lead.py`.

---

## Instalação e execução

1. **Clone** o repositório e abra a raiz do projeto.
2. **Ambiente:** copie `.env.example` para `.env` e defina **`DEEPSEEK_API_KEY`** (obrigatório em `Settings`).
3. **Instale dependências de runtime:**

```bash
pip install -r requirements.txt
```

4. **Suba o servidor:**

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

5. Abra **`http://127.0.0.1:8000/docs`** para testar a API.

**Testes:**

```bash
pip install -r requirements-dev.txt
pytest -q
```

**Segurança:** **não** faça commit do `.env`; apenas o `.env.example` deve ir para o controle de versão.

---

## Melhorias futuras

- Substituir o cache em memória por um **armazenamento compartilhado** (ex.: Redis) em implantações com várias instâncias.
- Incluir **persistência** (banco de dados) se for necessário histórico de leads ou auditoria — fora do escopo do código atual.
- Adicionar **autenticação / rate limiting** no *edge* ou em *middleware* ao expor além do ambiente local.
- Ampliar **observabilidade** (*logging* estruturado, métricas, *tracing*) conforme o alvo de deploy.
