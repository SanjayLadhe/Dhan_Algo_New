'use client';

import { useTradingStore } from '@/stores/useTradingStore';
import { formatDistanceToNow } from 'date-fns';

export default function PositionsTable() {
  const positions = useTradingStore((state) => state.positions);

  if (positions.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 text-center">
        <p className="text-gray-400">No open positions</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold">Open Positions</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">
                Symbol
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">
                Type
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">
                Qty
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">
                Entry Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">
                Current Price
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">
                P&L
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">
                P&L %
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">
                Time
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {positions.map((position) => (
              <tr key={position.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3 text-sm font-medium">
                  {position.symbol}
                </td>
                <td className="px-4 py-3 text-sm">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      position.type === 'CE'
                        ? 'bg-green-900/30 text-green-400'
                        : 'bg-red-900/30 text-red-400'
                    }`}
                  >
                    {position.type}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  {position.quantity}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  ₹{position.entryPrice.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  ₹{position.currentPrice.toFixed(2)}
                </td>
                <td
                  className={`px-4 py-3 text-sm text-right font-medium ${
                    position.pnl >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}
                >
                  ₹{position.pnl.toFixed(2)}
                </td>
                <td
                  className={`px-4 py-3 text-sm text-right font-medium ${
                    position.pnlPercentage >= 0
                      ? 'text-green-500'
                      : 'text-red-500'
                  }`}
                >
                  {position.pnlPercentage > 0 ? '+' : ''}
                  {position.pnlPercentage.toFixed(2)}%
                </td>
                <td className="px-4 py-3 text-sm text-gray-400">
                  {formatDistanceToNow(new Date(position.entryTime), {
                    addSuffix: true,
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
