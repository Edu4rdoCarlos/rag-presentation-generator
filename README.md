# TestDoc Agent

Agente inteligente multiagente para geração automática de documentação de estratégias de teste por feature. A partir da descrição de uma funcionalidade, o sistema identifica riscos, recomenda tipos de teste, prioriza cenários e produz um documento técnico estruturado.

---

## Como funciona

O sistema é orquestrado pelo **LangGraph** como um grafo direcionado de três agentes especializados. Cada agente recebe o estado completo da execução, executa sua responsabilidade e retorna uma atualização parcial desse estado.

```
  Entrada (Feature)
        │
        ├─ texto livre? ──→ Agente 0 (Feature Parser)
        │                         │
        ▼                         ▼
┌─────────────────────┐
│   Agente 1          │  Planner + RAG
│   Analista de       │  Consulta base vetorial, injeta Few-shot,
│   Riscos            │  identifica riscos e classifica criticidade.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Agente 2          │  Tool Use
│   Estrategista      │  Aplica a Matriz de Decisão via ferramentas
│   de Testes         │  Python para gerar cenários e tipos de teste.
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Agente 3          │  Reflection
│   Documentador      │  Compila o relatório final e executa auto-revisão.
│   e Crítico         │  Se reprovar, devolve ao Agente 2 (até 3×).
└────────┬────────────┘
         │
    APROVADO? ──── não ──→ Agente 2 (nova iteração)
         │ sim
         ▼
  Documento Final
```

### Os agentes

| # | Nome | Padrão | Responsabilidade |
|---|------|--------|-----------------|
| 0 | Feature Parser | Structured Output | Recebe texto livre e extrai `feature_name`, `description`, `business_rules` e `dependencies` |
| 1 | Analista de Riscos | Planner + RAG | Recupera exemplos similares via banco vetorial, constrói contexto Few-shot, lista riscos e classifica criticidade (Baixa / Média / Alta / Crítica) |
| 2 | Estrategista de Testes | Tool Use | Usa `llm.bind_tools()` para acionar a Matriz de Decisão e produzir tipos de teste (Unitário, Integração, E2E, Segurança…) e cenários priorizados |
| 3 | Documentador e Crítico | Reflection | Formata o documento final e roda auto-revisão; emite `REVER_ESTRATEGIA` para reprocessar ou `APROVADO` para encerrar |

### Estado compartilhado (`TestDocState`)

O estado é um modelo Pydantic que trafega entre os nós. Cada agente enriquece os campos de sua responsabilidade:

```
raw_description                                               ← entrada texto livre
feature_name, description, business_rules, dependencies      ← Agente 0 / entrada direta
retrieved_examples, identified_risks, criticality            ← Agente 1
recommended_test_types, prioritized_scenarios, justification ← Agente 2
final_documentation, reflection_logs, reflection_iteration   ← Agente 3
```

---

## Estrutura do projeto

```
testdoc_agent/
├── app/
│   ├── main.py                       # Entrypoint FastAPI
│   ├── core/
│   │   ├── config.py                 # Configurações via .env (multi-provider)
│   │   ├── llm_provider.py           # Factory de LLM e embeddings (auto-detecção de provider)
│   │   └── state.py                  # TestDocState (Pydantic)
│   ├── agents/
│   │   ├── feature_parser.py         # Agente 0 — parser de texto livre
│   │   ├── risk_analyst.py           # Agente 1 — RAG + análise de riscos
│   │   ├── test_strategist.py        # Agente 2 — tool use + matriz de decisão
│   │   └── documenter_critic.py      # Agente 3 — reflexão e documentação
│   ├── services/
│   │   ├── graph_service.py          # Grafo LangGraph compilado
│   │   └── vector_store.py           # FAISS + embeddings (RAG)
│   ├── data/train/
│   │   └── few_shot_examples.json    # Exemplos anotados para RAG
│   └── api/v1/routes/
│       └── feature.py                # POST /api/v1/feature/analyze (e /analyze/text)
├── run_batch_tests.py                # Bateria de 40 testes automatizados
├── .env.example
└── requirements.txt
```

---

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (para rodar via container)
- Chave de API de **pelo menos um** dos providers suportados (veja a seção abaixo)

---

## Providers de LLM

O sistema detecta automaticamente qual provider usar com base nas chaves de API presentes no `.env`. Não é necessário alterar nenhum código — basta configurar as variáveis de ambiente.

### Providers suportados

| Provider | Variável de ambiente | Modelo padrão |
|----------|---------------------|---------------|
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.5-flash` |
| OpenAI | `OPENAI_API_KEY` | `gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |
| NVIDIA NIM | `NVIDIA_API_KEY` | `meta/llama-3.1-70b-instruct` |

### Como configurar

Copie o arquivo de exemplo e preencha **apenas** a chave do provider desejado:

```bash
cp .env.example .env
```

Exemplos de configuração mínima:

```env
# Google Gemini
GOOGLE_API_KEY=AIza...

# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# NVIDIA NIM
NVIDIA_API_KEY=nvapi-...
```

### Ordem de auto-detecção

Quando `LLM_PROVIDER` não está definido, o sistema usa a **primeira** chave encontrada nesta ordem:

```
OPENAI_API_KEY → ANTHROPIC_API_KEY → NVIDIA_API_KEY → GOOGLE_API_KEY
```

### Forçar um provider ou trocar o modelo

```env
# Forçar provider específico
LLM_PROVIDER=openai

# Substituir o modelo padrão do provider ativo
LLM_MODEL=gpt-4o
```

### Nota sobre Anthropic e embeddings

A API da Anthropic **não oferece endpoint de embeddings**. O vector store (RAG do Agente 1) precisa de um modelo de embeddings. Ao usar `ANTHROPIC_API_KEY`, defina também `GOOGLE_API_KEY` ou `OPENAI_API_KEY` — o sistema usará automaticamente como fallback apenas para os embeddings:

```env
ANTHROPIC_API_KEY=sk-ant-...   # LLM principal
GOOGLE_API_KEY=AIza...         # fallback para embeddings
```

---

## Como rodar

### Opção 1 — Docker (recomendado)

**1. Configure as variáveis de ambiente**

```bash
cp .env.example .env
# Edite o .env e preencha a chave do provider desejado
```

**2. Suba o container em modo desenvolvimento** (com live reload)

```bash
docker compose -f deploy/docker-compose.yml up --build
```

Alterações em `app/` são refletidas instantaneamente sem rebuild.

**3. Verifique se subiu**

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

**Outros comandos úteis**

```bash
# Rodar em background
docker compose -f deploy/docker-compose.yml up -d

# Acompanhar logs
docker compose -f deploy/docker-compose.yml logs -f api

# Abrir shell no container
docker compose -f deploy/docker-compose.yml exec api bash

# Parar
docker compose -f deploy/docker-compose.yml down
```

**Modo produção**

```bash
docker compose \
  -f deploy/docker-compose.yml \
  -f deploy/docker-compose.prod.yml \
  up -d --build
```

---

### Opção 2 — Local (sem Docker)

**1. Crie e ative um ambiente virtual**

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
```

**2. Instale as dependências**

```bash
pip install -r requirements.txt
```

**3. Configure as variáveis de ambiente**

```bash
cp .env.example .env
# Edite o .env e preencha a chave do provider desejado
```

**4. Inicie o servidor**

```bash
uvicorn app.main:app --reload
```

---

## API

Com o servidor rodando, a documentação interativa está disponível em:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### `POST /api/v1/feature/analyze`

Recebe a feature já estruturada e retorna a documentação gerada pelo pipeline.

**Exemplo de requisição**

```bash
curl -X POST http://localhost:8000/api/v1/feature/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "feature_name": "Checkout com cupom",
    "description": "Aplica cupons de desconto durante o processo de checkout.",
    "business_rules": [
      "Cupom pode estar ativo, expirado ou esgotado.",
      "Cupom não pode ser usado duas vezes pelo mesmo usuário.",
      "Valor final não pode ficar negativo.",
      "Pagamento só deve ser criado se o pedido for válido."
    ],
    "dependencies": ["PaymentService", "CouponService", "OrderService"]
  }'
```

### `POST /api/v1/feature/analyze/text`

Recebe uma **descrição em texto livre** e passa pelo Agente 0 antes de entrar no pipeline principal.

**Exemplo de requisição**

```bash
curl -X POST http://localhost:8000/api/v1/feature/analyze/text \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Checkout com cupom de desconto. O usuário aplica um código durante a compra. Cupons expirados ou já usados devem ser rejeitados. O valor final não pode ficar negativo. Depende do PaymentService e CouponService."
  }'
```

**Exemplo de resposta (ambos os endpoints)**

```json
{
  "feature_name": "Checkout com cupom",
  "criticality": "Crítica",
  "identified_risks": [
    "Aceitar cupom expirado.",
    "Aceitar cupom esgotado.",
    "Permitir reuso de cupom pelo mesmo usuário.",
    "Gerar valor final negativo.",
    "Criar pagamento para pedido inválido."
  ],
  "recommended_test_types": ["unitário", "integração", "E2E", "segurança"],
  "prioritized_scenarios": [
    "Validar cálculo de desconto para cupom ativo.",
    "Rejeitar cupom expirado.",
    "Impedir reutilização do cupom.",
    "Impedir valor final negativo.",
    "Criar pagamento apenas para pedido válido."
  ],
  "justification": "...",
  "final_documentation": "...",
  "reflection_logs": ["APROVADO"],
  "reflection_iteration": 1
}
```

---

## Testes

### Bateria de 40 testes (`run_batch_tests.py`)

O arquivo `run_batch_tests.py` executa uma bateria de **40 casos de teste** cobrindo domínios variados (e-commerce, fintech, saúde, educação, redes sociais, logística, imóveis) e gera dois relatórios de saída.

**Pré-requisito:** servidor rodando em `http://localhost:8000`.

**Como executar:**

```bash
python run_batch_tests.py
```

**O que acontece:**

1. Cada caso é enviado para `POST /api/v1/feature/analyze/text` com timeout de 90 segundos
2. As requisições são feitas sequencialmente (1 conexão) com 3 segundos de intervalo para evitar rate limit
3. Em caso de HTTP 429 (rate limit), aguarda 15 segundos e retenta automaticamente

**Saída gerada:**

| Arquivo | Formato | Conteúdo |
|---------|---------|----------|
| `batch_results.json` | JSON | Resultado bruto completo de todos os casos, com tempo de execução por feature |
| `batch_results.md` | Markdown | Relatório formatado com riscos, cenários, tipos de teste e justificativa de cada feature |

**Exemplo de saída do terminal:**

```
=====================================================
  Iniciando bateria com 40 testes no TestDoc Agent
=====================================================
[01/40] Analisando feature...
[01/40] ✅ Sucesso!
[02/40] Analisando feature...
[02/40] ✅ Sucesso!
...
=====================================================
✅ Concluído! Resultados salvos em:
   - batch_results.json (Bruto)
   - batch_results.md (Formatado para leitura)
=====================================================
```

### Teste manual via Swagger

Com o servidor rodando, acesse `http://localhost:8000/docs` para testar interativamente os endpoints pelo Swagger UI sem precisar usar `curl`.

---

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `LLM_PROVIDER` | _(auto)_ | Força o provider: `openai`, `anthropic`, `google` ou `nvidia` |
| `LLM_MODEL` | _(padrão do provider)_ | Substitui o modelo padrão do provider ativo |
| `GOOGLE_API_KEY` | — | Chave da API Google Gemini |
| `GOOGLE_MODEL` | `gemini-2.5-flash` | Modelo Gemini padrão |
| `OPENAI_API_KEY` | — | Chave da API OpenAI |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo OpenAI padrão |
| `ANTHROPIC_API_KEY` | — | Chave da API Anthropic |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Modelo Anthropic padrão |
| `NVIDIA_API_KEY` | — | Chave da API NVIDIA NIM |
| `NVIDIA_MODEL` | `meta/llama-3.1-70b-instruct` | Modelo NVIDIA padrão |
| `APP_ENV` | `development` | Ambiente da aplicação |
| `APP_DEBUG` | `true` | Ativa modo debug do FastAPI |
| `MAX_REFLECTION_ITERATIONS` | `3` | Limite de ciclos de auto-revisão do Agente 3 |
