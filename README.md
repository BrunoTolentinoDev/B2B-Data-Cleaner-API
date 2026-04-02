# B2B Data Cleaner API

## 🚀 Sobre o Projeto

API REST assíncrona que recebe dados básicos de um lead B2B (`nome`, `email`, `cnpj`), valida **e-mail** e **CNPJ** em Python e usa a API **DeepSeek** (via cliente OpenAI assíncrono) para enriquecer o lead a partir do **nome**.

**Problema que endereça:** padronizar e enriquecer informações de prospecção sem depender da IA para validações estruturais (formato de e-mail e CNPJ), reduzindo chamadas desnecessárias à LLM quando o mesmo nome já foi processado (cache em memória com TTL).

---

## ⚙️ Funcionalidades

- Validação de **e-mail** com regex e normalização (`strip`).
- Validação de **CNPJ** com `pycpfcnpj` e fallback algorítmico local se a lib falhar.
- **Enriquecimento por IA** a partir do nome: `nome_padronizado`, `setor_estimado`, `perfil_vendas` (limitado a 10 palavras no pós-processamento), `sales_hook` (parágrafo, até 2000 caracteres no schema), `is_garbage`.
- **Cache em memória** com TTL configurável e padrão single-flight para evitar computações duplicadas concorrentes para a mesma chave.
- **Tratamento global de erros** (validação Pydantic, HTTPException, falhas de parsing/resposta da IA).
- Documentação automática **OpenAPI** (Swagger UI em `/docs`).
- Rotas auxiliares: metadados na raiz (`/`) e **health check** (`/health`).
- Suíte de **testes** com `pytest` (validadores, cache, serviço com mock da IA, integração HTTP via ASGI).

---

## 🧠 Como Funciona

1. O cliente envia `POST /validate/lead` com `nome`, `email` e `cnpj`.
2. O corpo é validado pelo **Pydantic**; em seguida o fluxo valida e-mail e CNPJ com funções em `app/services/validators.py`.
3. Se tudo estiver válido, o **`CleaningService`** monta a chave de cache a partir do nome normalizado e, em caso de miss, chama a DeepSeek com `temperature=0`, esperando um **JSON** com os campos de enriquecimento.
4. O texto de `sales_hook` passa por pós-processamento (normalização de espaços, regras para evitar frases claramente truncadas e garantir fechamento com pontuação quando aplicável).
5. A resposta agrega os campos enriquecidos com `email` e `cnpj` (este último somente dígitos).

---

## 🛠️ Tecnologias

- **Python 3.10+** (recomendado; ambiente de desenvolvimento com 3.12 é compatível com o projeto)
- **FastAPI**
- **Uvicorn** (servidor ASGI)
- **Pydantic v2** e **pydantic-settings** (configuração e variáveis de ambiente, inclusive `.env`)
- **OpenAI Python SDK** (`openai`), com `AsyncOpenAI` apontando para o endpoint da **DeepSeek**
- **pycpfcnpj** (validação de CNPJ)
- **pytest**, **pytest-asyncio**, **httpx** (dependências de teste em `requirements-dev.txt`)

---

## 📦 Como Rodar o Projeto

1. Clone o repositório e entre na pasta do projeto.
2. Crie o ambiente virtual e ative-o.
3. Copie `.env.example` para `.env` e defina `DEEPSEEK_API_KEY` (obrigatório para subir a aplicação com as configurações atuais).
4. Instale dependências:

```bash
pip install -r requirements.txt
```

5. Inicie o servidor:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

6. Acesse a documentação interativa: `http://127.0.0.1:8000/docs`

**Testes (opcional):**

```bash
pip install -r requirements-dev.txt
pytest -q
```

---

## 🔌 Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Retorna nome do serviço e caminhos para documentação OpenAPI (`docs`, `openapi.json`). |
| `GET` | `/health` | Retorna status `ok` para verificação de saúde do processo. |
| `POST` | `/validate/lead` | Valida e-mail e CNPJ; enriquece o lead via IA a partir do `nome`; resposta conforme schema `LeadValidateResponse`. |

**Códigos HTTP recorrentes:** `200` (sucesso), `422` (validação de entrada ou regras de negócio), `502` (falha ao interpretar/responder conforme esperado da IA), `500` (erro interno não tratado).

---

## 📌 Melhorias Futuras

- Evoluir persistência e observabilidade conforme necessidade de produção (o projeto atual não inclui banco de dados nem métricas agregadas).
- Avaliar cache distribuído ou filas se o volume de requisições exigir escala horizontal além do processo único em memória.
