# TestDoc Agent

Agente inteligente multiagente para geração automática de documentação de estratégias de teste por feature. A partir da descrição de uma funcionalidade, o sistema identifica riscos, recomenda tipos de teste, prioriza cenários e produz um documento técnico estruturado.

---

## Extensão VSCode

A pasta [`extension/`](extension/) contém uma extensão VSCode que conecta o editor ao TestDoc Agent. Com ela é possível descrever uma feature diretamente no painel lateral do VSCode e visualizar o resultado sem sair do editor.

Para instalar e rodar a extensão, consulte o [extension/README.md](extension/README.md).

---

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (para rodar via container)
- Chave de API de **pelo menos um** dos providers suportados ([ver configuração de providers](docs/configuration.md))

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

## Documentação

| Documento | Conteúdo |
|-----------|---------|
| [docs/architecture.md](docs/architecture.md) | Como o sistema funciona, agentes, estado compartilhado e estrutura de pastas |
| [docs/api.md](docs/api.md) | Endpoints da API, exemplos de requisição e resposta |
| [docs/configuration.md](docs/configuration.md) | Providers de LLM e variáveis de ambiente |
| [docs/tests.md](docs/tests.md) | Bateria de testes automatizados |
| [extension/README.md](extension/README.md) | Extensão VSCode |
