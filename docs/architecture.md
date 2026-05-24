# Arquitetura — TestDoc Agent

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
