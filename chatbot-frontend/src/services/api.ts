/**
 * API client for chatbot backend
 */

import axios from 'axios';
import type { AxiosInstance } from 'axios';
import type {
  ChatMessageRequest,
  ChatMessageResponse,
  SessionStateResponse,
  WorkflowListResponse,
  Workflow
} from './types';

class ChatbotAPI {
  private client: AxiosInstance;

  constructor(baseURL: string = 'http://localhost:8000') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for debugging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('[API] Request error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`[API] Response:`, response.status);
        return response;
      },
      (error) => {
        console.error('[API] Response error:', error.response?.data || error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async checkHealth(): Promise<boolean> {
    try {
      const response = await this.client.get('/health');
      return response.data.status === 'healthy';
    } catch {
      return false;
    }
  }

  // Chat endpoints
  async sendMessage(request: ChatMessageRequest): Promise<ChatMessageResponse> {
    const response = await this.client.post<ChatMessageResponse>(
      '/chat/message',
      request
    );
    return response.data;
  }

  async getSession(sessionId: string): Promise<SessionStateResponse> {
    const response = await this.client.get<SessionStateResponse>(
      `/chat/session/${sessionId}`
    );
    return response.data;
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.client.delete(`/chat/session/${sessionId}`);
  }

  // Workflow endpoints
  async listWorkflows(
    accessLevel: string = 'employee',
    category?: string
  ): Promise<WorkflowListResponse> {
    const params: any = { access_level: accessLevel };
    if (category) params.category = category;

    const response = await this.client.get<WorkflowListResponse>(
      '/workflows/list',
      { params }
    );
    return response.data;
  }

  async getWorkflow(
    workflowName: string,
    accessLevel: string = 'employee'
  ): Promise<Workflow> {
    const response = await this.client.get<Workflow>(
      `/workflows/${workflowName}`,
      { params: { access_level: accessLevel } }
    );
    return response.data;
  }
}

// Singleton instance
let apiInstance: ChatbotAPI | null = null;

export const getAPI = (baseURL?: string): ChatbotAPI => {
  if (!apiInstance) {
    apiInstance = new ChatbotAPI(baseURL);
  }
  return apiInstance;
};

export default ChatbotAPI;