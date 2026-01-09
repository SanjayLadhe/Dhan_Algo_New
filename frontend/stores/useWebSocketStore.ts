import { create } from 'zustand';

interface WebSocketState {
  isConnected: boolean;
  reconnectAttempts: number;
  lastMessage: any;
  error: string | null;

  // Actions
  setConnected: (connected: boolean) => void;
  setReconnectAttempts: (attempts: number) => void;
  setLastMessage: (message: any) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useWebSocketStore = create<WebSocketState>((set) => ({
  isConnected: false,
  reconnectAttempts: 0,
  lastMessage: null,
  error: null,

  setConnected: (connected) => set({ isConnected: connected }),
  setReconnectAttempts: (attempts) => set({ reconnectAttempts: attempts }),
  setLastMessage: (message) => set({ lastMessage: message }),
  setError: (error) => set({ error }),

  reset: () =>
    set({
      isConnected: false,
      reconnectAttempts: 0,
      lastMessage: null,
      error: null,
    }),
}));
