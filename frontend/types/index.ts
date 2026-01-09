// Trading Types
export interface Position {
  id: string;
  symbol: string;
  type: 'CE' | 'PE';
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercentage: number;
  stopLoss: number;
  target: number;
  status: 'OPEN' | 'CLOSED';
  entryTime: string;
  exitTime?: string;
}

export interface Order {
  id: string;
  symbol: string;
  type: 'BUY' | 'SELL';
  orderType: 'MARKET' | 'LIMIT';
  quantity: number;
  price?: number;
  status: 'PENDING' | 'EXECUTED' | 'CANCELLED' | 'REJECTED';
  timestamp: string;
}

export interface AccountBalance {
  totalBalance: number;
  availableBalance: number;
  usedMargin: number;
  unrealizedPnL: number;
  realizedPnL: number;
}

// Market Data Types
export interface MarketQuote {
  symbol: string;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  change: number;
  changePercent: number;
  timestamp: string;
}

export interface OHLC {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// Technical Indicators
export interface TechnicalIndicators {
  symbol: string;
  rsi: number;
  atr: number;
  vwap: number;
  fractalHigh?: number;
  fractalLow?: number;
  adx?: number;
}

// Strategy Types
export interface StrategyConfig {
  name: string;
  enabled: boolean;
  riskPerTrade: number;
  maxPositions: number;
  stopLossMultiplier: number;
  targetMultiplier: number;
}

// WebSocket Message Types
export interface WSMessage {
  type: 'quote' | 'order' | 'position' | 'trade' | 'indicator';
  data: any;
  timestamp: string;
}

// Trade Signal
export interface TradeSignal {
  symbol: string;
  type: 'CE' | 'PE';
  action: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  stopLoss: number;
  target: number;
  confidence: number;
  indicators: TechnicalIndicators;
  timestamp: string;
}

// Paper Trading
export interface PaperTradingConfig {
  enabled: boolean;
  initialBalance: number;
  slippagePercent: number;
}
