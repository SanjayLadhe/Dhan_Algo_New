import { create } from 'zustand';
import { Position, Order, AccountBalance, TradeSignal } from '@/types';

interface TradingState {
  // Account
  balance: AccountBalance;

  // Positions & Orders
  positions: Position[];
  orders: Order[];
  signals: TradeSignal[];

  // Trading Status
  isTradingActive: boolean;
  isPaperTrading: boolean;

  // Actions
  setBalance: (balance: AccountBalance) => void;
  addPosition: (position: Position) => void;
  updatePosition: (id: string, updates: Partial<Position>) => void;
  removePosition: (id: string) => void;
  addOrder: (order: Order) => void;
  updateOrder: (id: string, updates: Partial<Order>) => void;
  addSignal: (signal: TradeSignal) => void;
  setTradingActive: (active: boolean) => void;
  setPaperTrading: (enabled: boolean) => void;
  reset: () => void;
}

const initialBalance: AccountBalance = {
  totalBalance: 1005000,
  availableBalance: 1005000,
  usedMargin: 0,
  unrealizedPnL: 0,
  realizedPnL: 0,
};

export const useTradingStore = create<TradingState>((set) => ({
  balance: initialBalance,
  positions: [],
  orders: [],
  signals: [],
  isTradingActive: false,
  isPaperTrading: true,

  setBalance: (balance) => set({ balance }),

  addPosition: (position) =>
    set((state) => ({ positions: [...state.positions, position] })),

  updatePosition: (id, updates) =>
    set((state) => ({
      positions: state.positions.map((p) =>
        p.id === id ? { ...p, ...updates } : p
      ),
    })),

  removePosition: (id) =>
    set((state) => ({
      positions: state.positions.filter((p) => p.id !== id),
    })),

  addOrder: (order) =>
    set((state) => ({ orders: [order, ...state.orders].slice(0, 100) })),

  updateOrder: (id, updates) =>
    set((state) => ({
      orders: state.orders.map((o) => (o.id === id ? { ...o, ...updates } : o)),
    })),

  addSignal: (signal) =>
    set((state) => ({ signals: [signal, ...state.signals].slice(0, 50) })),

  setTradingActive: (active) => set({ isTradingActive: active }),

  setPaperTrading: (enabled) => set({ isPaperTrading: enabled }),

  reset: () =>
    set({
      balance: initialBalance,
      positions: [],
      orders: [],
      signals: [],
      isTradingActive: false,
    }),
}));
