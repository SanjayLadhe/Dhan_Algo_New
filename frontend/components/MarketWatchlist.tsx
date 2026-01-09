'use client';

import { useMarketStore } from '@/stores/useMarketStore';
import { TrendingUp, TrendingDown } from 'lucide-react';

export default function MarketWatchlist() {
  const watchlist = useMarketStore((state) => state.watchlist);
  const quotes = useMarketStore((state) => state.quotes);

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold">Market Watchlist</h3>
      </div>

      <div className="divide-y divide-gray-700">
        {watchlist.map((symbol) => {
          const quote = quotes.get(symbol);
          const isPositive = quote ? quote.change >= 0 : false;

          return (
            <div
              key={symbol}
              className="p-4 hover:bg-gray-700/50 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-semibold">{symbol}</div>
                  {quote && (
                    <div className="text-xs text-gray-400 mt-1">
                      Vol: {(quote.volume / 1000000).toFixed(2)}M
                    </div>
                  )}
                </div>

                <div className="text-right">
                  <div className="text-lg font-bold">
                    {quote ? `₹${quote.ltp.toFixed(2)}` : '---'}
                  </div>
                  {quote && (
                    <div
                      className={`flex items-center gap-1 text-sm font-medium ${
                        isPositive ? 'text-green-500' : 'text-red-500'
                      }`}
                    >
                      {isPositive ? (
                        <TrendingUp className="w-3 h-3" />
                      ) : (
                        <TrendingDown className="w-3 h-3" />
                      )}
                      <span>
                        {isPositive ? '+' : ''}
                        {quote.changePercent.toFixed(2)}%
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {quote && (
                <div className="grid grid-cols-4 gap-2 mt-3 text-xs">
                  <div>
                    <div className="text-gray-400">Open</div>
                    <div className="font-medium">{quote.open.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-gray-400">High</div>
                    <div className="font-medium text-green-500">
                      {quote.high.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Low</div>
                    <div className="font-medium text-red-500">
                      {quote.low.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-400">Close</div>
                    <div className="font-medium">{quote.close.toFixed(2)}</div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
