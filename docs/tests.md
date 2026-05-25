# Testes — TestDoc Agent

## Bateria de 40 testes (`run_batch_tests.py`)

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

---

## Teste manual via Swagger

Com o servidor rodando, acesse `http://localhost:8000/docs` para testar interativamente os endpoints pelo Swagger UI sem precisar usar `curl`.
