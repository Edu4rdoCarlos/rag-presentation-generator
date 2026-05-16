# TestDoc Agent

Agente inteligente multiagente para geração automática de documentação de estratégias de teste por feature. A partir da descrição de uma funcionalidade, o sistema identifica riscos, recomenda tipos de teste, prioriza cenários e produz um documento técnico estruturado.

---

## Como funciona

O sistema é orquestrado pelo **LangGraph** como um grafo direcionado de três agentes especializados. Cada agente recebe o estado completo da execução, executa sua responsabilidade e retorna uma atualização parcial desse estado.

```
  Entrada (Feature)
        │
        ▼
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

### Os três agentes

| # | Nome | Padrão | Responsabilidade |
|---|------|--------|-----------------|
| 1 | Analista de Riscos | Planner + RAG | Recupera exemplos similares via banco vetorial, constrói contexto Few-shot, lista riscos e classifica criticidade (Baixa / Média / Alta / Crítica) |
| 2 | Estrategista de Testes | Tool Use | Usa `llm.bind_tools()` para acionar a Matriz de Decisão e produzir tipos de teste (Unitário, Integração, E2E, Segurança…) e cenários priorizados |
| 3 | Documentador e Crítico | Reflection | Formata o documento final e roda auto-revisão; emite `REVER_ESTRATEGIA` para reprocessar ou `APROVADO` para encerrar |

### Estado compartilhado (`TestDocState`)

O estado é um modelo Pydantic que trafega entre os nós. Cada agente enriquece os campos de sua responsabilidade:

```
feature_name, description, business_rules, dependencies   ← entrada
retrieved_examples, identified_risks, criticality         ← Agente 1
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
│   │   ├── config.py                 # Configurações via .env
│   │   └── state.py                  # TestDocState (Pydantic)
│   ├── agents/
│   │   ├── risk_analyst.py           # Agente 1 — stub
│   │   ├── test_strategist.py        # Agente 2 — stub + ferramentas
│   │   └── documenter_critic.py      # Agente 3 — stub
│   ├── services/
│   │   └── graph_service.py          # Grafo LangGraph compilado
│   └── api/v1/routes/
│       └── feature.py                # POST /api/v1/feature/analyze
├── deploy/
│   ├── Dockerfile                    # Multi-stage (builder → runtime)
│   ├── docker-compose.yml            # Desenvolvimento com live reload
│   ├── docker-compose.prod.yml       # Overrides de produção
│   └── .dockerignore
├── .env.example
└── requirements.txt
```

---

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (para rodar via container)
- Chave de API OpenAI (ou outro LLM compatível com LangChain)

---

## Como rodar

### Opção 1 — Docker (recomendado)

**1. Configure as variáveis de ambiente**

```bash
cp .env.example .env
# Edite o .env e preencha sua OPENAI_API_KEY
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
# Edite o .env e preencha sua OPENAI_API_KEY
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

Recebe a descrição de uma feature e retorna a documentação de testes gerada pelo pipeline multiagente.

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

**Exemplo de resposta**

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

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `OPENAI_API_KEY` | — | Chave da API OpenAI (obrigatória) |
| `OPENAI_MODEL` | `gpt-4o` | Modelo a ser utilizado pelos agentes |
| `APP_ENV` | `development` | Ambiente da aplicação |
| `APP_DEBUG` | `true` | Ativa modo debug do FastAPI |
| `MAX_REFLECTION_ITERATIONS` | `3` | Limite de ciclos de auto-revisão do Agente 3 |

---

## Implementando os agentes

O projeto foi entregue com os **stubs** dos três agentes prontos para receber a lógica de LLM. Cada arquivo contém comentários `TODO` detalhados indicando exatamente o que implementar:

| Arquivo | O que implementar |
|---------|-------------------|
| [app/agents/risk_analyst.py](app/agents/risk_analyst.py) | `VectorStoreRetriever` + `ChatPromptTemplate` com Few-shot |
| [app/agents/test_strategist.py](app/agents/test_strategist.py) | `llm.bind_tools()` com as funções da Matriz de Decisão |
| [app/agents/documenter_critic.py](app/agents/documenter_critic.py) | Formatação do relatório + prompt de crítica reflexiva |

A orquestração do grafo em [app/services/graph_service.py](app/services/graph_service.py) **não precisa ser alterada** — ela já conecta os nós, define as arestas sequenciais e o laço de reflexão condicional.
