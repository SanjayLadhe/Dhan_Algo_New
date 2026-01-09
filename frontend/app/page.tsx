'use client';

import { useEffect, useState } from 'react';
import AccountCard from '@/components/AccountCard';
import PositionsTable from '@/components/PositionsTable';
import MarketWatchlist from '@/components/MarketWatchlist';
import TradingChart from '@/components/TradingChart';
import { useMarketStore } from '@/stores/useMarketStore';
import { Activity, BarChart3, TrendingUp } from 'lucide-react';

export default function Home() {
  const [selectedSymbol, setSelectedSymbol] = useState('NIFTY');
  const ohlcData = useMarketStore((state) => state.ohlcData);
  const chartData = ohlcData.get(selectedSymbol) || [];

  // Sample data for demo
  useEffect(() => {
    // In production, this would come from WebSocket
    const sampleOHLC = Array.from({ length: 100 }, (_, i) => {
      const base = 22000 + Math.random() * 1000;
      return {
        time: Date.now() / 1000 - (100 - i) * 300,
        open: base,
        high: base + Math.random() * 50,
        low: base - Math.random() * 50,
        close: base + (Math.random() - 0.5) * 40,
        volume: Math.floor(Math.random() * 1000000),
      };
    });

    useMarketStore.getState().updateOHLC('NIFTY', sampleOHLC);
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 p-4">
      {/* Header */}
      <header className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Activity className="text-blue-500" />
              Dhan Algo Trading
            </h1>
            <p className="text-gray-400 mt-1">
              Advanced Algorithmic Trading Platform
            </p>
          </div>

          <div className="flex gap-2">
            <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Start Trading
            </button>
            <button className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-medium transition-colors flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Analytics
            </button>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Left Column - Account & Watchlist */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <AccountCard />
          <MarketWatchlist />
        </div>

        {/* Center Column - Chart & Positions */}
        <div className="col-span-12 lg:col-span-9 space-y-4">
          {/* Trading Chart */}
          <TradingChart symbol={selectedSymbol} data={chartData} />

          {/* Positions Table */}
          <PositionsTable />

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Win Rate</div>
              <div className="text-2xl font-bold text-green-500">67.5%</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Total Trades</div>
              <div className="text-2xl font-bold">142</div>
            </div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="text-sm text-gray-400 mb-1">Avg Profit</div>
              <div className="text-2xl font-bold text-green-500">₹2,350</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
