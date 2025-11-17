/**
 * API Service Layer
 * Handles all communication with the backend FastAPI server
 * Includes comprehensive error handling and retry logic
 */

import axios, { AxiosError } from 'axios';
import type { AxiosInstance, AxiosRequestConfig } from 'axios';
import { API_URL, ENABLE_DEBUG } from '@/config/env';
import type {
  HealthResponse,
  ExamplesResponse,
  GenerateRequest,
  GenerateResponse,
  APIError,
} from '@/types';

/**
 * Custom error class for API errors
 */
export class APIServiceError extends Error {
  public statusCode?: number;
  public details?: any;
  public suggestion?: string;

  constructor(message: string, statusCode?: number, details?: any, suggestion?: string) {
    super(message);
    this.name = 'APIServiceError';
    this.statusCode = statusCode;
    this.details = details;
    this.suggestion = suggestion;
  }
}

/**
 * API Service configuration
 */
class APIService {
  private client: AxiosInstance;
  private abortController: AbortController | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000, // 30 seconds timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for debugging
    if (ENABLE_DEBUG) {
      this.client.interceptors.request.use(
        (config) => {
          console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data);
          return config;
        },
        (error) => {
          console.error('[API] Request error:', error);
          return Promise.reject(error);
        }
      );
    }

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        if (ENABLE_DEBUG) {
          console.log(`[API] Response:`, response.data);
        }
        return response;
      },
      (error: AxiosError<APIError>) => {
        return Promise.reject(this.handleAxiosError(error));
      }
    );
  }

  /**
   * Handle Axios errors and convert to APIServiceError
   */
  private handleAxiosError(error: AxiosError<APIError>): APIServiceError {
    if (error.response) {
      // Server responded with error status
      const { data, status } = error.response;
      const message = data?.error || `Request failed with status ${status}`;
      const suggestion = data?.suggestion || this.getSuggestionForStatus(status);

      return new APIServiceError(message, status, data?.details, suggestion);
    } else if (error.request) {
      // Request made but no response received
      const message = 'No response from server';
      const suggestion = 'Please check if the backend server is running on ' + API_URL;

      return new APIServiceError(message, undefined, error.request, suggestion);
    } else {
      // Error in request setup
      return new APIServiceError(
        error.message || 'Request failed',
        undefined,
        undefined,
        'Please check your network connection'
      );
    }
  }

  /**
   * Get helpful suggestion based on HTTP status code
   */
  private getSuggestionForStatus(status: number): string {
    switch (status) {
      case 400:
        return 'Please check your input and try again';
      case 401:
        return 'Authentication required. Please check your API key configuration';
      case 403:
        return 'Access forbidden. Please check your permissions';
      case 404:
        return 'Resource not found. Please check the URL';
      case 422:
        return 'Invalid input format. Please check the specification syntax';
      case 500:
        return 'Server error. Please try again later or contact support';
      case 502:
      case 503:
      case 504:
        return 'Server temporarily unavailable. Please try again in a few moments';
      default:
        return 'An error occurred. Please try again';
    }
  }

  /**
   * Cancel any pending requests
   */
  public cancelRequest(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }

  /**
   * Health check endpoint
   */
  public async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await this.client.get<HealthResponse>('/api/health');
      return response.data;
    } catch (error) {
      if (error instanceof APIServiceError) {
        throw error;
      }
      throw new APIServiceError('Health check failed', undefined, error);
    }
  }

  /**
   * Get available workflow examples
   */
  public async getExamples(): Promise<ExamplesResponse> {
    try {
      const response = await this.client.get<ExamplesResponse>('/api/examples');
      return response.data;
    } catch (error) {
      if (error instanceof APIServiceError) {
        throw error;
      }
      throw new APIServiceError('Failed to load examples', undefined, error);
    }
  }

  /**
   * Generate agent from specification
   * Supports cancellation via AbortController
   */
  public async generateAgent(
    request: GenerateRequest,
    onProgress?: (stage: string, progress: number) => void
  ): Promise<GenerateResponse> {
    // Cancel any existing request
    this.cancelRequest();

    // Create new abort controller
    this.abortController = new AbortController();

    const config: AxiosRequestConfig = {
      signal: this.abortController.signal,
      // Extended timeout for generation
      timeout: 60000, // 60 seconds for generation
      onDownloadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress('generating', progress);
        }
      },
    };

    try {
      // Notify progress: starting
      onProgress?.('parsing', 10);

      const response = await this.client.post<GenerateResponse>(
        '/api/generate',
        request,
        config
      );

      // Notify progress: complete
      onProgress?.('complete', 100);

      return response.data;
    } catch (error) {
      // Check if request was cancelled
      if (axios.isCancel(error)) {
        throw new APIServiceError('Request cancelled by user');
      }

      if (error instanceof APIServiceError) {
        throw error;
      }

      throw new APIServiceError(
        'Agent generation failed',
        undefined,
        error,
        'Please check your specification format and try again'
      );
    } finally {
      this.abortController = null;
    }
  }

  /**
   * Retry wrapper for requests
   */
  public async withRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;

        // Don't retry on client errors (4xx)
        if (
          error instanceof APIServiceError &&
          error.statusCode &&
          error.statusCode >= 400 &&
          error.statusCode < 500
        ) {
          throw error;
        }

        // Don't retry on last attempt
        if (attempt === maxRetries) {
          break;
        }

        // Wait before retrying (exponential backoff)
        const waitTime = delay * Math.pow(2, attempt - 1);
        if (ENABLE_DEBUG) {
          console.log(`[API] Retrying in ${waitTime}ms (attempt ${attempt}/${maxRetries})`);
        }
        await new Promise((resolve) => setTimeout(resolve, waitTime));
      }
    }

    throw lastError || new APIServiceError('Operation failed after retries');
  }
}

// Export singleton instance
const apiService = new APIService();

export default apiService;

// Export convenience methods
export const checkHealth = () => apiService.checkHealth();
export const getExamples = () => apiService.getExamples();
export const generateAgent = (
  request: GenerateRequest,
  onProgress?: (stage: string, progress: number) => void
) => apiService.generateAgent(request, onProgress);
export const cancelRequest = () => apiService.cancelRequest();