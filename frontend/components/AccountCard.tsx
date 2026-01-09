'use client';

import { useTradingStore } from '@/stores/useTradingStore';
import { TrendingUp, TrendingDown, Wallet, DollarSign } from 'lucide-react';

export default function AccountCard() {
  const balance = useTradingStore((state) => state.balance);
  const isPaperTrading = useTradingStore((state) => state.isPaperTrading);

  const metrics = [
    {
      label: 'Total Balance',
      value: balance.totalBalance,
      icon: Wallet,
      color: 'text-blue-500',
    },
    {
      label: 'Available',
      value: balance.availableBalance,
      icon: DollarSign,
      color: 'text-green-500',
    },
    {
      label: 'Used Margin',
      value: balance.usedMargin,
      icon: TrendingDown,
      color: 'text-orange-500',
    },
    {
      label: 'Unrealized P&L',
      value: balance.unrealizedPnL,
      icon: balance.unrealizedPnL >= 0 ? TrendingUp : TrendingDown,
      color: balance.unrealizedPnL >= 0 ? 'text-green-500' : 'text-red-500',
    },
  ];

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Account Balance</h3>
        {isPaperTrading && (
          <span className="px-3 py-1 bg-yellow-900/30 text-yellow-400 text-xs font-medium rounded-full">
            Paper Trading
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div
              key={metric.label}
              className="bg-gray-900/50 rounded-lg p-4 border border-gray-700"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-400">{metric.label}</span>
                <Icon className={`w-4 h-4 ${metric.color}`} />
              </div>
              <div className={`text-2xl font-bold ${metric.color}`}>
                ₹{metric.value.toLocaleString('en-IN', {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-700">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-400">Today's P&L</span>
          <span
            className={`text-lg font-bold ${
              balance.realizedPnL >= 0 ? 'text-green-500' : 'text-red-500'
            }`}
          >
            {balance.realizedPnL >= 0 ? '+' : ''}₹
            {balance.realizedPnL.toLocaleString('en-IN', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
