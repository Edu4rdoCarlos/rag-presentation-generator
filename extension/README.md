# TestGen — Extensão VSCode

Extensão VSCode que conecta o editor ao TestDoc Agent. Você descreve uma feature em linguagem natural e a extensão retorna riscos, criticidade, tipos de teste e cenários priorizados diretamente no painel lateral.

---

## Pré-requisitos

- [Node.js 18+](https://nodejs.org/) e npm
- [VSCode 1.90+](https://code.visualstudio.com/)
- Backend TestDoc Agent rodando em `http://localhost:8000`

---

## Rodar em modo desenvolvimento (F5)

Este é o fluxo recomendado para desenvolver ou testar a extensão localmente.

**1. Instale as dependências**

```bash
cd extension
npm install
```

**2. Abra a pasta `extension/` no VSCode**

```bash
code extension/
```

**3. Pressione F5**

O VSCode compila o TypeScript automaticamente (via `preLaunchTask`) e abre uma nova janela **[Extension Development Host]** com a extensão carregada.

Na janela de desenvolvimento:
- Clique no ícone de béquer na barra lateral para abrir o painel **TestGen**
- Ou use `Ctrl+Shift+P` → `TestGen: Analyze Feature`
- Ou selecione um texto no editor, clique com o botão direito → `TestGen: Analyze Selected Text`

---

## Gerar e instalar o `.vsix` (distribuição)

Use este fluxo para instalar a extensão de forma permanente no VSCode, sem precisar manter a janela de debug aberta.

**1. Instale as dependências (se ainda não instalou)**

```bash
cd extension
npm install
```

**2. Gere o pacote `.vsix`**

```bash
npm run package
```

O arquivo `testgen-extension-0.2.0.vsix` será gerado na pasta `extension/`.

**3. Instale no VSCode**

```
Ctrl+Shift+P → "Extensions: Install from VSIX..." → selecione o .vsix gerado
```

---

## Configuração

Por padrão a extensão aponta para `http://localhost:8000`. Para alterar:

```
Ctrl+Shift+P → "Preferences: Open Settings (UI)" → pesquise "TestGen"
```

| Setting | Padrão | Descrição |
|---------|--------|-----------|
| `testgen.apiUrl` | `http://localhost:8000` | URL base do TestDoc Agent API |

---

## Estrutura do código

```
extension/
├── src/
│   ├── extension.ts     # Entry point — registra comandos e o WebviewViewProvider
│   ├── chatProvider.ts  # UI do chat + lógica do fluxo de perguntas/análise
│   ├── api.ts           # Funções HTTP para os endpoints da API
│   └── panel.ts         # (reservado) painel de resultado em aba separada
├── .vscode/
│   ├── launch.json      # Configuração F5
│   └── tasks.json       # Task de compilação TypeScript
├── package.json
└── tsconfig.json
```

---

## Scripts disponíveis

| Comando | O que faz |
|---------|-----------|
| `npm run compile` | Compila TypeScript → `out/` |
| `npm run watch` | Compila em modo watch (recompila ao salvar) |
| `npm run package` | Gera o `.vsix` para distribuição |
