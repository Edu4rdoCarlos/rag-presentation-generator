import * as vscode from "vscode";
import { TestGenChatProvider } from "./chatProvider";

export function activate(context: vscode.ExtensionContext) {
  const provider = new TestGenChatProvider(context.extensionUri);

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      TestGenChatProvider.viewId,
      provider
    )
  );

  // Ctrl+Shift+P command — opens chat with empty input
  context.subscriptions.push(
    vscode.commands.registerCommand("testgen.analyzeText", () => {
      vscode.commands.executeCommand("testgen.chatView.focus");
    })
  );

  // Right-click on selected text — sends selection directly to chat
  context.subscriptions.push(
    vscode.commands.registerCommand("testgen.analyzeSelection", () => {
      const editor = vscode.window.activeTextEditor;
      const selected = editor?.document.getText(editor.selection).trim();
      if (selected) {
        provider.sendTextToChat(selected);
      } else {
        vscode.commands.executeCommand("testgen.chatView.focus");
      }
    })
  );
}

export function deactivate() {}
