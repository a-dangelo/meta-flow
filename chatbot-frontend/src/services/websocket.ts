/**
 * WebSocket client for real-time updates
 */

import { io, Socket } from 'socket.io-client';
import {
  WSMessage,
  WSLogMessage,
  WSStatusMessage,
  WSResultMessage,
  WSErrorMessage
} from './types';

export interface WebSocketHandlers {
  onLog?: (message: WSLogMessage) => void;
  onStatus?: (message: WSStatusMessage) => void;
  onResult?: (message: WSResultMessage) => void;
  onError?: (message: WSErrorMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

class WebSocketClient {
  private socket: Socket | null = null;
  private handlers: WebSocketHandlers = {};
  private sessionId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  constructor(private baseURL: string = 'ws://localhost:8000') {}

  connect(sessionId: string, handlers: WebSocketHandlers = {}): void {
    if (this.socket?.connected) {
      console.log('[WS] Already connected');
      return;
    }

    this.sessionId = sessionId;
    this.handlers = handlers;

    // WebSocket URL for chatbot API
    const wsUrl = `${this.baseURL}/ws/chat/${sessionId}`;

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
    (this as any).ws = ws;
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
    const ws = (this as any).ws as WebSocket | undefined;
    if (ws) {
      console.log('[WS] Disconnecting...');
      ws.close();
      (this as any).ws = null;
    }
    this.sessionId = null;
    this.handlers = {};
    this.reconnectAttempts = 0;
  }

  send(message: WSMessage): void {
    const ws = (this as any).ws as WebSocket | undefined;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    } else {
      console.warn('[WS] Cannot send message - not connected');
    }
  }

  isConnected(): boolean {
    const ws = (this as any).ws as WebSocket | undefined;
    return ws?.readyState === WebSocket.OPEN || false;
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