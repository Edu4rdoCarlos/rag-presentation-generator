import * as vscode from "vscode";
import { analyzeFeatureText, getContextQuestions, PreviousQA } from "./api";

export class TestGenChatProvider implements vscode.WebviewViewProvider {
  public static readonly viewId = "testgen.chatView";
  private _view?: vscode.WebviewView;

  private _rawText = "";
  private _accumulatedQA: PreviousQA[] = [];

  constructor(_extensionUri: vscode.Uri) {}

  resolveWebviewView(webviewView: vscode.WebviewView) {
    this._view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this._getHtml();

    webviewView.webview.onDidReceiveMessage(async (message: Record<string, any>) => {
      if (message.type === "start") {
        await this._handleStart(message.text);
      } else if (message.type === "submit_answers") {
        await this._handleSubmitAnswers(message.answers);
      }
    });
  }

  public sendTextToChat(text: string) {
    if (this._view) {
      this._view.show(true);
      this._view.webview.postMessage({ type: "prefill", text });
    }
  }

  private async _handleStart(rawText: string) {
    this._rawText = rawText;
    this._accumulatedQA = [];
    await this._nextQuestionRound();
  }

  private async _nextQuestionRound() {
    this._post({ type: "loading_questions" });
    try {
      const result = await getContextQuestions(this._rawText, this._accumulatedQA);
      if (result.ready) {
        await this._runAnalysis();
      } else {
        this._post({ type: "questions", questions: result.questions });
      }
    } catch {
      // Questions endpoint unavailable — fall back to direct analysis
      await this._runAnalysis();
    }
  }

  private async _handleSubmitAnswers(
    answers: Array<{ id: string; question: string; answer: string }>
  ) {
    const answered = answers.filter((a) => a.answer.trim());
    answered.forEach((a) => {
      this._accumulatedQA.push({ question: a.question, answer: a.answer });
    });
    await this._nextQuestionRound();
  }

  private async _runAnalysis() {
    this._post({ type: "loading" });
    let enriched = this._rawText;
    if (this._accumulatedQA.length) {
      enriched += "\n\n## Contexto adicional fornecido pelo desenvolvedor";
      this._accumulatedQA.forEach((qa) => {
        enriched += `\n\n**${qa.question}**\n${qa.answer}`;
      });
    }
    try {
      const result = await analyzeFeatureText(enriched);
      this._post({ type: "result", data: result });
    } catch (err: any) {
      this._post({ type: "error", message: err.message });
    }
  }

  private _post(message: object) {
    this._view?.webview.postMessage(message);
  }

  private _getHtml(): string {
    return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: var(--vscode-font-family);
  font-size: var(--vscode-font-size);
  color: var(--vscode-foreground);
  background: var(--vscode-sideBar-background);
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}
#messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.msg-user {
  background: var(--vscode-input-background);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 0.9em;
  color: var(--vscode-foreground);
  align-self: flex-end;
  max-width: 90%;
  word-break: break-word;
}
.msg-assistant {
  background: var(--vscode-editor-inactiveSelectionBackground);
  border-left: 3px solid var(--vscode-focusBorder);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 0.88em;
}
.msg-assistant h3 {
  font-size: 0.78em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--vscode-descriptionForeground);
  margin-bottom: 5px;
  margin-top: 10px;
}
.msg-assistant h3:first-child { margin-top: 0; }
.badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.82em;
}
.Crítica { background: #c0392b; color: #fff; }
.Alta    { background: #e67e22; color: #fff; }
.Média   { background: #f1c40f; color: #000; }
.Baixa   { background: #27ae60; color: #fff; }
.tag {
  display: inline-block;
  background: var(--vscode-badge-background);
  color: var(--vscode-badge-foreground);
  padding: 1px 7px;
  border-radius: 4px;
  font-size: 0.82em;
  margin: 2px 2px 2px 0;
}
ul { padding-left: 16px; }
li { margin: 3px 0; }
.loading {
  color: var(--vscode-descriptionForeground);
  font-style: italic;
  font-size: 0.88em;
}
.error { color: var(--vscode-errorForeground); font-size: 0.88em; }
.welcome {
  color: var(--vscode-descriptionForeground);
  font-size: 0.88em;
  text-align: center;
  margin-top: 20px;
  line-height: 1.6;
}
#input-area {
  display: flex;
  gap: 6px;
  padding: 10px;
  border-top: 1px solid var(--vscode-panel-border);
  background: var(--vscode-sideBar-background);
  flex-shrink: 0;
}
#input {
  flex: 1;
  resize: none;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, transparent);
  border-radius: 6px;
  padding: 8px;
  font-family: inherit;
  font-size: 0.9em;
  min-height: 60px;
  max-height: 120px;
}
#input:focus { outline: 1px solid var(--vscode-focusBorder); }
#send {
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 6px;
  padding: 0 12px;
  cursor: pointer;
  font-size: 1.1em;
  align-self: flex-end;
  height: 36px;
}
#send:hover { background: var(--vscode-button-hoverBackground); }
#question-panel {
  display: none;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  border-top: 1px solid var(--vscode-panel-border);
  background: var(--vscode-sideBar-background);
  flex-shrink: 0;
  max-height: 60vh;
  overflow-y: auto;
}
.q-header {
  font-size: 0.78em;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--vscode-descriptionForeground);
  padding-bottom: 6px;
  border-bottom: 1px solid var(--vscode-panel-border);
}
.q-item { display: flex; flex-direction: column; gap: 5px; }
.q-label { font-size: 0.85em; line-height: 1.4; }
.q-num { font-weight: bold; color: var(--vscode-descriptionForeground); margin-right: 3px; }
.q-input {
  resize: none;
  background: var(--vscode-input-background);
  color: var(--vscode-input-foreground);
  border: 1px solid var(--vscode-input-border, transparent);
  border-radius: 4px;
  padding: 6px 8px;
  font-family: inherit;
  font-size: 0.85em;
  min-height: 44px;
  max-height: 80px;
}
.q-input:focus { outline: 1px solid var(--vscode-focusBorder); }
.q-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 6px;
  border-top: 1px solid var(--vscode-panel-border);
}
.btn-skip {
  background: none;
  border: none;
  color: var(--vscode-descriptionForeground);
  cursor: pointer;
  font-size: 0.82em;
  font-family: inherit;
  text-decoration: underline;
}
.btn-skip:hover { color: var(--vscode-foreground); }
.btn-analyze {
  background: var(--vscode-button-background);
  color: var(--vscode-button-foreground);
  border: none;
  border-radius: 6px;
  padding: 6px 14px;
  cursor: pointer;
  font-size: 0.88em;
  font-family: inherit;
}
.btn-analyze:hover { background: var(--vscode-button-hoverBackground); }
</style>
</head>
<body>

<div id="messages">
  <div class="welcome">
    Descreva uma feature em linguagem natural<br>e o TestGen vai identificar riscos,<br>criticidade e tipos de teste.
  </div>
</div>

<div id="input-area">
  <textarea id="input" placeholder="Ex: Tela de login com autenticação em dois fatores..."></textarea>
  <button id="send" title="Enviar (Enter)">&#9654;</button>
</div>

<div id="question-panel"></div>

<script>
const vscode        = acquireVsCodeApi();
const messagesEl    = document.getElementById('messages');
const inputEl       = document.getElementById('input');
const sendBtn       = document.getElementById('send');
const inputArea     = document.getElementById('input-area');
const questionPanel = document.getElementById('question-panel');

let capturedText     = '';
let currentQuestions = [];

function scrollBottom() { messagesEl.scrollTop = messagesEl.scrollHeight; }

function addLoading(id, text) {
  const div = document.createElement('div');
  div.className = 'loading';
  if (id) div.id = id;
  div.textContent = text;
  messagesEl.appendChild(div);
  scrollBottom();
}

function removeById(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function addResult(data) {
  removeById('loading-msg');
  const risks     = (data.identified_risks || []).map(r => '<li>' + r + '</li>').join('');
  const tags      = (data.recommended_test_types || []).map(t => '<span class="tag">' + t + '</span>').join('');
  const scenarios = (data.prioritized_scenarios || []).map(s => '<li>' + s + '</li>').join('');

  let html = '<h3>Feature</h3>'
    + '<strong>' + data.feature_name + '</strong> '
    + '<span class="badge ' + (data.criticality || '') + '">' + (data.criticality || '—') + '</span>';
  if (risks)                html += '<h3>Riscos identificados</h3><ul>' + risks + '</ul>';
  if (tags)                 html += '<h3>Tipos de teste</h3><p>' + tags + '</p>';
  if (scenarios)            html += '<h3>Cenários prioritários</h3><ul>' + scenarios + '</ul>';
  if (data.justification)   html += '<h3>Justificativa</h3><p>' + data.justification + '</p>';
  if (data.final_documentation) html += '<h3>Documentação final</h3><pre style="white-space:pre-wrap;font-size:0.85em">' + data.final_documentation + '</pre>';

  const div = document.createElement('div');
  div.className = 'msg-assistant';
  div.innerHTML = html;
  messagesEl.appendChild(div);
  scrollBottom();
  inputArea.style.display = 'flex';
}

function addError(msg) {
  removeById('loading-msg');
  const div = document.createElement('div');
  div.className = 'error';
  div.textContent = 'Erro: ' + msg;
  messagesEl.appendChild(div);
  scrollBottom();
  inputArea.style.display = 'flex';
}

// ── Question panel ────────────────────────────────────────────
function showQuestions(questions) {
  removeById('loading-q-msg');
  currentQuestions = questions;
  questionPanel.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'q-header';
  header.textContent = 'Para uma análise sem suposições';
  questionPanel.appendChild(header);

  questions.forEach(function(q, i) {
    const item = document.createElement('div');
    item.className = 'q-item';

    const label = document.createElement('div');
    label.className = 'q-label';
    label.innerHTML = '<span class="q-num">' + (i + 1) + '.</span>' + q.question;

    const textarea = document.createElement('textarea');
    textarea.className = 'q-input';
    textarea.dataset.idx = String(i);
    textarea.placeholder = 'Resposta opcional (Tab para próxima, Enter para analisar)';
    textarea.rows = 2;
    textarea.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doAnalyze(false); }
    });

    item.appendChild(label);
    item.appendChild(textarea);
    questionPanel.appendChild(item);
  });

  const actions = document.createElement('div');
  actions.className = 'q-actions';

  const skipBtn = document.createElement('button');
  skipBtn.className = 'btn-skip';
  skipBtn.textContent = 'Pular tudo';
  skipBtn.addEventListener('click', function() { doAnalyze(true); });

  const analyzeBtn = document.createElement('button');
  analyzeBtn.className = 'btn-analyze';
  analyzeBtn.textContent = 'Analisar com contexto →';
  analyzeBtn.addEventListener('click', function() { doAnalyze(false); });

  actions.appendChild(skipBtn);
  actions.appendChild(analyzeBtn);
  questionPanel.appendChild(actions);

  questionPanel.style.display = 'flex';
  const first = questionPanel.querySelector('.q-input');
  if (first) first.focus();
}

function doAnalyze(skipAll) {
  const answers = [];
  if (!skipAll) {
    questionPanel.querySelectorAll('.q-input').forEach(function(ta) {
      const idx = parseInt(ta.dataset.idx, 10);
      answers.push({
        id:       currentQuestions[idx].id,
        question: currentQuestions[idx].question,
        answer:   ta.value.trim()
      });
    });
  }
  questionPanel.style.display = 'none';
  questionPanel.innerHTML = '';
  vscode.postMessage({ type: 'submit_answers', answers: answers });
}

// ── Main send ─────────────────────────────────────────────────
function send() {
  const text = inputEl.value.trim();
  if (!text) return;
  inputEl.value = '';
  capturedText = text;

  const div = document.createElement('div');
  div.className = 'msg-user';
  div.textContent = text;
  messagesEl.appendChild(div);
  scrollBottom();

  inputArea.style.display = 'none';
  vscode.postMessage({ type: 'start', text: text });
}

sendBtn.addEventListener('click', send);
inputEl.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

window.addEventListener('message', function(event) {
  const msg = event.data;
  if      (msg.type === 'loading_questions') addLoading('loading-q-msg', 'Identificando lacunas de contexto...');
  else if (msg.type === 'questions')         showQuestions(msg.questions);
  else if (msg.type === 'loading')           addLoading('loading-msg', 'Analisando feature...');
  else if (msg.type === 'result')            addResult(msg.data);
  else if (msg.type === 'error')             addError(msg.message);
  else if (msg.type === 'prefill')           { inputEl.value = msg.text; inputArea.style.display = 'flex'; inputEl.focus(); }
});
</script>
</body>
</html>`;
  }
}
