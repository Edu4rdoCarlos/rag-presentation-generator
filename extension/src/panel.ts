import * as vscode from "vscode";
import { FeatureAnalyzeResponse } from "./api";

export function showResultPanel(
  result: FeatureAnalyzeResponse,
  context: vscode.ExtensionContext
): void {
  const panel = vscode.window.createWebviewPanel(
    "testgenResult",
    `TestGen — ${result.feature_name}`,
    vscode.ViewColumn.Beside,
    {}
  );

  panel.webview.html = buildHtml(result);
}

function buildHtml(r: FeatureAnalyzeResponse): string {
  const risks = r.identified_risks.map((risk) => `<li>${risk}</li>`).join("");
  const testTypes = r.recommended_test_types
    .map((t) => `<span class="tag">${t}</span>`)
    .join(" ");
  const scenarios = r.prioritized_scenarios
    .map((s) => `<li>${s}</li>`)
    .join("");

  return `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <style>
    body { font-family: var(--vscode-font-family); padding: 20px; color: var(--vscode-foreground); }
    h1 { font-size: 1.4em; border-bottom: 1px solid var(--vscode-panel-border); padding-bottom: 8px; }
    h2 { font-size: 1em; margin-top: 20px; color: var(--vscode-descriptionForeground); text-transform: uppercase; letter-spacing: 0.05em; }
    .badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-weight: bold; font-size: 0.85em; }
    .Crítica { background: #c0392b; color: #fff; }
    .Alta    { background: #e67e22; color: #fff; }
    .Média   { background: #f1c40f; color: #000; }
    .Baixa   { background: #27ae60; color: #fff; }
    .tag { background: var(--vscode-badge-background); color: var(--vscode-badge-foreground); padding: 2px 8px; border-radius: 4px; font-size: 0.85em; margin-right: 4px; }
    ul { padding-left: 20px; }
    li { margin: 4px 0; }
    .justification { background: var(--vscode-textBlockQuote-background); border-left: 3px solid var(--vscode-textBlockQuote-border); padding: 10px 14px; border-radius: 4px; }
  </style>
</head>
<body>
  <h1>${r.feature_name}</h1>
  <p>Criticidade: <span class="badge ${r.criticality}">${r.criticality ?? "—"}</span></p>

  <h2>Riscos identificados</h2>
  <ul>${risks || "<li>Nenhum risco identificado.</li>"}</ul>

  <h2>Tipos de teste recomendados</h2>
  <p>${testTypes || "—"}</p>

  <h2>Cenários prioritários</h2>
  <ul>${scenarios || "<li>Nenhum cenário gerado.</li>"}</ul>

  <h2>Justificativa</h2>
  <p class="justification">${r.justification ?? "—"}</p>
</body>
</html>`;
}
