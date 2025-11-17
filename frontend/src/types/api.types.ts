/**
 * API Type Definitions
 * Matches the backend FastAPI models
 */

// Health check types
export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  checks: {
    api: boolean;
    imports: boolean;
    examples: boolean;
    api_key_configured: boolean;
  };
  message?: string;
}

// Examples types
export interface ExampleSpec {
  name: string;
  description: string | null;
  type: 'sequential' | 'conditional' | 'parallel' | 'orchestrator' | 'nested';
  content: string;
  filename: string;
}

export interface ExamplesResponse {
  examples: ExampleSpec[];
  count: number;
}

// Generation types
export interface GenerateRequest {
  spec: string;
  provider?: 'claude' | 'aimlapi' | 'gemini';
  model_version?: string;
}

export interface GenerateResponse {
  python_code: string;
  json_output: string;
  workflow_name: string;
  workflow_type: string;
  description: string;
  execution_time: number;
  metadata?: Record<string, any>;
}

// Error types
export interface APIError {
  error: string;
  details?: any;
  suggestion?: string;
  status_code?: number;
}

// Pipeline stage types (for visualization)
export type PipelineStage =
  | 'idle'
  | 'parsing'
  | 'validating'
  | 'generating_json'
  | 'generating_code'
  | 'complete'
  | 'error';

export interface PipelineStatus {
  stage: PipelineStage;
  message: string;
  progress: number; // 0-100
  error?: string;
}