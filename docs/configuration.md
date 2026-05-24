# Configuração — Providers de LLM e Variáveis de Ambiente

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
