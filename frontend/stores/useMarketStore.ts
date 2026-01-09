import { create } from 'zustand';
import { MarketQuote, OHLC, TechnicalIndicators } from '@/types';

interface MarketState {
  // Market Data
  quotes: Map<string, MarketQuote>;
  ohlcData: Map<string, OHLC[]>;
  indicators: Map<string, TechnicalIndicators>;

  // Watchlist
  watchlist: string[];

  // Actions
  updateQuote: (symbol: string, quote: MarketQuote) => void;
  updateOHLC: (symbol: string, ohlc: OHLC[]) => void;
  updateIndicators: (symbol: string, indicators: TechnicalIndicators) => void;
  addToWatchlist: (symbol: string) => void;
  removeFromWatchlist: (symbol: string) => void;
  reset: () => void;
}

export const useMarketStore = create<MarketState>((set) => ({
  quotes: new Map(),
  ohlcData: new Map(),
  indicators: new Map(),
  watchlist: ['NIFTY', 'BANKNIFTY', 'FINNIFTY'],

  updateQuote: (symbol, quote) =>
    set((state) => {
      const newQuotes = new Map(state.quotes);
      newQuotes.set(symbol, quote);
      return { quotes: newQuotes };
    }),

  updateOHLC: (symbol, ohlc) =>
    set((state) => {
      const newOHLC = new Map(state.ohlcData);
      newOHLC.set(symbol, ohlc);
      return { ohlcData: newOHLC };
    }),

  updateIndicators: (symbol, indicators) =>
    set((state) => {
      const newIndicators = new Map(state.indicators);
      newIndicators.set(symbol, indicators);
      return { indicators: newIndicators };
    }),

  addToWatchlist: (symbol) =>
    set((state) => ({
      watchlist: state.watchlist.includes(symbol)
        ? state.watchlist
        : [...state.watchlist, symbol],
    })),

  removeFromWatchlist: (symbol) =>
    set((state) => ({
      watchlist: state.watchlist.filter((s) => s !== symbol),
    })),

  reset: () =>
    set({
      quotes: new Map(),
      ohlcData: new Map(),
      indicators: new Map(),
    }),
}));
