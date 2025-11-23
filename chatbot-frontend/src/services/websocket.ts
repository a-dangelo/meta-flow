/**
 * WebSocket client for real-time updates
 */

import type {
  WSMessage,
  WSLogMessage,
  WSStatusMessage,
  WSResultMessage,
  WSErrorMessage
} from './types';

// Determine WebSocket protocol based on current page protocol
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const DEFAULT_WS_BASE =
  import.meta.env.VITE_CHATBOT_WS_URL || `${wsProtocol}//${window.location.host}/ws`;

export interface WebSocketHandlers {
  onLog?: (message: WSLogMessage) => void;
  onStatus?: (message: WSStatusMessage) => void;
  onResult?: (message: WSResultMessage) => void;
  onError?: (message: WSErrorMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

class WebSocketClient {
  private socket: WebSocket | null = null;
  private handlers: WebSocketHandlers = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private baseURL: string;

  constructor(baseURL: string = DEFAULT_WS_BASE) {
    this.baseURL = baseURL;
  }

  connect(sessionId: string, handlers: WebSocketHandlers = {}): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }

    this.handlers = handlers;

    // WebSocket URL for chatbot API
    const wsUrl = `${this.baseURL}/chat/${sessionId}`;

    console.log(`[WS] Connecting to ${wsUrl}`);

    // Create native WebSocket connection
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('[WS] Connected');
      this.reconnectAttempts = 0;
      handlers.onConnect?.();

      // Send initial ping
      this.sendPing(ws);
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('[WS] Failed to parse message:', error);
      }
    };

    ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      handlers.onError?.({
        type: 'error',
        data: {
          error: 'WebSocket connection error',
          details: error
        }
      });
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      handlers.onDisconnect?.();

      // Attempt reconnection
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        console.log(`[WS] Reconnecting... (attempt ${this.reconnectAttempts})`);
        setTimeout(() => {
          this.connect(sessionId, handlers);
        }, 2000 * this.reconnectAttempts);
      }
    };

    // Store WebSocket reference
    this.socket = ws;
  }

  private sendPing(ws: WebSocket): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'ping' }));

      // Schedule next ping
      setTimeout(() => this.sendPing(ws), 30000);
    }
  }

  private handleMessage(message: WSMessage): void {
    console.log(`[WS] Received:`, message.type, message.data);

    switch (message.type) {
      case 'connected':
        // Welcome message, no action needed
        console.log('[WS] Welcome message received');
        break;
      case 'log':
        this.handlers.onLog?.(message as WSLogMessage);
        break;
      case 'status':
        this.handlers.onStatus?.(message as WSStatusMessage);
        break;
      case 'result':
        this.handlers.onResult?.(message as WSResultMessage);
        break;
      case 'error':
        this.handlers.onError?.(message as WSErrorMessage);
        break;
      case 'pong':
        // Heartbeat response, no action needed
        break;
      default:
        console.warn('[WS] Unknown message type:', message.type);
    }
  }

  disconnect(): void {
    if (this.socket) {
      console.log('[WS] Disconnecting...');
      this.socket.close();
      this.socket = null;
    }
    this.handlers = {};
    this.reconnectAttempts = 0;
  }

  send(message: WSMessage): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('[WS] Cannot send message - not connected');
    }
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN || false;
  }
}

// Singleton instance
let wsInstance: WebSocketClient | null = null;

export const getWebSocket = (baseURL?: string): WebSocketClient => {
  if (!wsInstance) {
    wsInstance = new WebSocketClient(baseURL);
  }
  return wsInstance;
};

export default WebSocketClient;
