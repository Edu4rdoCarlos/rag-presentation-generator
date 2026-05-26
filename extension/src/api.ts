import axios from "axios";
import * as vscode from "vscode";

function getApiBase(): string {
  return vscode.workspace
    .getConfiguration("testgen")
    .get<string>("apiUrl", "http://localhost:8000");
}

export interface Question {
  id: string;
  question: string;
}

export interface PreviousQA {
  question: string;
  answer: string;
}

export interface ContextQuestionsResponse {
  is_feature: boolean;
  rejection_message: string;
  ready: boolean;
  questions: Question[];
}

export interface FeatureAnalyzeRequest {
  feature_name: string;
  description: string;
  business_rules: string[];
  dependencies: string[];
}

export interface FeatureAnalyzeResponse {
  feature_name: string;
  criticality: string | null;
  identified_risks: string[];
  recommended_test_types: string[];
  prioritized_scenarios: string[];
  justification: string | null;
  final_documentation: string | null;
  reflection_logs: string[];
  reflection_iteration: number;
}

export async function getContextQuestions(
  rawText: string,
  previousQA: PreviousQA[] = []
): Promise<ContextQuestionsResponse> {
  const response = await axios.post<ContextQuestionsResponse>(
    `${getApiBase()}/api/feature/questions`,
    { raw_text: rawText, previous_qa: previousQA }
  );
  return response.data;
}

export async function analyzeFeatureText(
  rawText: string
): Promise<FeatureAnalyzeResponse> {
  const response = await axios.post<FeatureAnalyzeResponse>(
    `${getApiBase()}/api/feature/analyze/text`,
    { raw_text: rawText }
  );
  return response.data;
}

export async function analyzeFeatureJson(
  payload: FeatureAnalyzeRequest
): Promise<FeatureAnalyzeResponse> {
  const response = await axios.post<FeatureAnalyzeResponse>(
    `${getApiBase()}/api/feature/analyze`,
    payload
  );
  return response.data;
}
