# =============================================================================
# Dockerfile — TestDoc Agent
# Multi-stage build: "builder" compila extensões C (faiss-cpu, tiktoken),
# "runtime" carrega apenas os artefatos necessários → imagem final enxuta.
#
# Build context esperado: raiz do projeto (configurado no docker-compose.yml).
# Todos os COPY são relativos à raiz do projeto.
# =============================================================================


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder
# Responsável por instalar todas as dependências Python, incluindo pacotes
# com extensões C que exigem compiladores (build-essential).
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Impede geração de .pyc e garante output imediato nos logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Desabilita verificação de versão e cache do pip neste estágio
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Instala compilador C necessário para faiss-cpu e tiktoken.
# O cache do apt é removido na mesma camada para não inflar a imagem.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instala em /install (prefixo isolado) para que o stage runtime
# copie apenas os pacotes compilados, sem o toolchain de compilação.
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
# Imagem final: copia os pacotes compilados do builder e o código da aplicação.
# Não inclui build-essential → superfície de ataque e tamanho reduzidos.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # Torna o pacote "app" importável de qualquer working directory
    PYTHONPATH=/app

WORKDIR /app

# Copia os pacotes Python instalados pelo builder
COPY --from=builder /install /usr/local

# ── Usuário não-root ──────────────────────────────────────────────────────
# Boa prática de segurança: a aplicação nunca roda como root.
RUN groupadd --gid 1001 appgroup \
    && useradd \
        --uid 1001 \
        --gid appgroup \
        --shell /bin/bash \
        --no-create-home \
        appuser

# Copia o código-fonte com ownership do usuário da aplicação
COPY --chown=appuser:appgroup . .

USER appuser

EXPOSE 8000

# ── Comando de produção ───────────────────────────────────────────────────
# --workers 2  →  recomendado: (2 × núcleos) + 1; ajuste conforme o host.
# Para desenvolvimento, o docker-compose.yml sobrescreve este CMD.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]
