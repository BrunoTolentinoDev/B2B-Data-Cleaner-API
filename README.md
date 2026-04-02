# B2B Data Cleaner API

## 🚀 Sobre o Projeto

API REST assíncrona que recebe dados básicos de um lead B2B (`nome`, `email`, `cnpj`), valida **e-mail** e **CNPJ** localmente em Python e utiliza a API **DeepSeek** (via cliente OpenAI assíncrono) para enriquecer o lead a partir do **nome**.

**Problema que endereça:** garantir qualidade e padronização dos dados de prospecção antes do uso de IA, evitando dependência de LLM para validações estruturais e reduzindo chamadas desnecessárias através de **cache em memória com TTL**.

---

## ⚙️ Funcionalidades

- Validação de **e-mail** com regex e normalização (`strip`).
- Validação de **CNPJ** com `pycpfcnpj` e fallback algorítmico local em caso de falha da biblioteca.
- **Enriquecimento por IA** a partir do nome:
  - `nome_padronizado`
  - `setor_estimado`
  - `perfil_vendas` (limitado a 10 palavras no pós-processamento)
  - `sales_hook` (texto estruturado com limite definido no schema)
  - `is_garbage`
- **Cache em memória com TTL** para evitar chamadas repetidas à IA.
- Controle de concorrência com padrão **single-flight** para a mesma chave.
- **Tratamento global de erros** (validação Pydantic, HTTPException, falhas de parsing/resposta da IA).
- Documentação automática via **OpenAPI** (Swagger UI em `/docs`).
- Rotas auxiliares: metadados (`/`) e **health check** (`/health`).
- Suíte de **testes** com `pytest` (validadores, cache, serviço com mock da IA e integração HTTP via ASGI).

---

## 🧠 Como Funciona

1. O cliente envia `POST /validate/lead` com `nome`, `email` e `cnpj`.
2. O corpo é validado pelo **Pydantic**; em seguida o sistema valida e-mail e CNPJ com funções locais.
3. Se os dados estiverem válidos, o **`CleaningService`** gera uma chave de cache a partir do nome normalizado.
4. Em caso de cache miss, a API chama a DeepSeek com `temperature=0`, esperando um **JSON estruturado** com os dados de enriquecimento.
5. O campo `sales_hook` passa por pós-processamento para garantir consistência (remoção de espaços extras e ajuste de pontuação).
6. A resposta final agrega os dados enriquecidos com `email` e `cnpj` normalizado (apenas dígitos).

---

## 🛠️ Tecnologias

- **Python 3.10+** (compatível com 3.12)
- **FastAPI**
- **Uvicorn** (servidor ASGI)
- **Pydantic v2** e **pydantic-settings** (configuração e variáveis de ambiente)
- **OpenAI Python SDK** (`openai`) com `AsyncOpenAI` integrado ao endpoint da **DeepSeek**
- **pycpfcnpj** (validação de CNPJ)
- **pytest**, **pytest-asyncio**, **httpx** (testes em `requirements-dev.txt`)

---

## 📦 Como Rodar o Projeto

1. Clone o repositório e entre na pasta do projeto.  
2. Crie o ambiente virtual e ative-o.  
3. Copie `.env.example` para `.env` e defina `DEEPSEEK_API_KEY` (obrigatório para execução).  
4. Instale as dependências:

pip install -r requirements.txt

5. Inicie o servidor:

uvicorn main:app --host 127.0.0.1 --port 8000 --reload

6. Acesse a documentação interativa:  
http://127.0.0.1:8000/docs

**Testes (opcional):**

pip install -r requirements-dev.txt  
pytest -q

---

## 🔌 Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Retorna informações do serviço e links da documentação OpenAPI. |
| `GET` | `/health` | Retorna status `ok` para verificação de saúde da aplicação. |
| `POST` | `/validate/lead` | Valida e-mail e CNPJ e enriquece o lead via IA a partir do `nome`. |

**Códigos HTTP recorrentes:**  
`200` (sucesso), `422` (erro de validação), `502` (falha na resposta da IA), `500` (erro interno).

---

## 📌 Melhorias Futuras

- Evolução para **cache distribuído** conforme aumento de carga.
- Adição de **persistência de dados** (banco de dados).
- Implementação de **observabilidade** (logs estruturados e métricas).
- Suporte a **escalabilidade horizontal**.
