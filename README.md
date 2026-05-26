# TestDoc Agent

Agente inteligente multiagente para geração automática de documentação de estratégias de teste por feature. A partir da descrição de uma funcionalidade, o sistema identifica riscos, recomenda tipos de teste, prioriza cenários e produz um documento técnico estruturado.

---

## ⚙️ Arquitetura e Fluxo dos Agentes

O sistema opera com um pipeline de Agentes de Inteligência Artificial trabalhando em colaboração para gerar o documento final:

1. **Agente 0 (Feature Parser - Opcional):** Se o usuário enviar um texto livre bruto, este agente interpreta o texto e o converte para um formato estruturado (regras de negócio, dependências, etc.).
2. **Agente 1 (Context Gatherer):** Consulta uma base de conhecimento vetorial (RAG) para buscar projetos ou exemplos de testes similares, garantindo que a nova documentação siga os padrões históricos.
3. **Agente 2 (Risk & Strategy Analyzer):** Pega as informações da feature e o contexto histórico para elencar os maiores riscos de negócio, definir o nível de **criticidade** e propor quais tipos de teste (Funcional, Integração, etc.) são primordiais.
4. **Agente 3 (Documenter & Critic):** Recebe o esqueleto estratégico e elabora o documento técnico final detalhado. Possui um mecanismo de **reflection**: ele mesmo critica o documento gerado e, se perceber falta de profundidade (como ausência de tratativa de falhas de segurança em uma feature crítica), devolve para o Agente 2 refazer a estratégia, gerando um loop de melhoria.

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

### 🔑 Configuração da Chave de API (LLM)

O TestDoc Agent delega as análises complexas para grandes modelos de linguagem (LLMs). Toda a integração de agentes roda em cima dessa inteligência. A arquitetura do projeto foi desenhada de forma agnóstica e **suporta múltiplos provedores** (OpenAI, Google Gemini, Anthropic, etc.), conforme as [regras de configuração da aplicação](docs/configuration.md).

**Como configurar:**
1. Crie o arquivo `.env` copiando o modelo: `cp .env.example .env`
2. Obtenha a API Key do provedor de sua preferência.
3. Cole sua chave no arquivo `.env` ativando a variável correspondente:
   ```env
   # Escolha UM dos provedores abaixo:
   
   # Opção 1: Google Gemini (Padrão)
   GOOGLE_API_KEY="AIzaSySuaChaveAqui..."
   
   # Opção 2: OpenAI
   OPENAI_API_KEY="sk-SuaChaveAqui..."
   
   # Opção 3: Anthropic
   ANTHROPIC_API_KEY="sk-ant-SuaChaveAqui..."
   ```
4. A aplicação e o Docker lerão automaticamente esse arquivo, injetando a credencial com segurança no serviço LLM sem expor a chave no código-fonte.

---

## Como rodar

### Opção 1 — Docker (recomendado)

**1. Configure as variáveis de ambiente**

```bash
cp .env.example .env
# Descomente o provider desejado e preencha a chave de API
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
# Descomente o provider desejado e preencha a chave de API
```

**4. Inicie o servidor**

```bash
uvicorn app.main:app --reload
```

---

## 🧪 Pipeline de Testes e Padrão Ouro (Gold Standard)

Para garantir a qualidade contínua das predições do agente (LLM), implementamos uma **Pipeline de Testes** automatizada rodando via Docker. A pipeline se baseia no conceito de **Padrão Ouro** (Gold Standard), que compara as respostas dinâmicas do modelo com saídas e formatos ideais de referência.

### Estrutura de Arquivos

- **`tests/inputs/`**: Contém cenários de teste pré-definidos (JSONs estruturados ou texto livre) que simulam requisições reais da API (ex: Atualização de Perfil, Checkout, etc).
- **`tests/outputs/`**: Contém o respectivo Padrão Ouro de saída. Como o LLM não é determinístico, as asserções validam atributos chave: a precisão do campo **Criticidade** determinada pelo sistema, a **estrutura de chaves obrigatórias** e as sugestões de cenário e testes.
- **`tests/test_pipeline.py`**: Motor dos testes usando `pytest` para ler as entradas e auditar as saídas da aplicação.

### Como executar a Pipeline

A pipeline roda de forma isolada do ambiente de desenvolvimento. Para rodar a bateria inteira contra a API em background:

```bash
docker compose -f deploy/docker-compose.test.yml up --build --abort-on-container-exit --exit-code-from tests
```

---

## Documentação

| Documento | Conteúdo |
|-----------|---------|
| [docs/architecture.md](docs/architecture.md) | Como o sistema funciona, agentes, estado compartilhado e estrutura de pastas |
| [docs/api.md](docs/api.md) | Endpoints da API, exemplos de requisição e resposta |
| [docs/configuration.md](docs/configuration.md) | Providers de LLM e variáveis de ambiente |
| [docs/tests.md](docs/tests.md) | Bateria de testes automatizados |
| [docs/exemplo.md](docs/exemplo.md) | Exemplo prático gerado pela aplicação demonstrando o output real |
| [docs/Especificacao_Tecnica_TestDoc_Agent_LangChain.pdf](docs/Especificacao_Tecnica_TestDoc_Agent_LangChain.pdf) | Especificação técnica oficial do TestDoc Agent abordando detalhes de LangChain |
| [docs/TestDoc_Agent_Documentacao_Com_FewShot.pdf](docs/TestDoc_Agent_Documentacao_Com_FewShot.pdf) | Documentação de referência das técnicas de prompt com FewShot |
| [extension/README.md](extension/README.md) | Extensão VSCode |
