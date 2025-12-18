'use client';

import { useQuery } from '@tanstack/react-query';
import {
  DollarSign,
  CreditCard,
  PiggyBank,
  Repeat,
  TrendingDown,
  TrendingUp,
  ArrowRight,
} from 'lucide-react';
import Link from 'next/link';
import { getMonthlySpend, getTopMerchants, getRecurringSubscriptions } from '@/utils/api';
import StatsCard from '@/components/dashboard/StatsCard';
import RecentTransactions from '@/components/dashboard/RecentTransactions';
import SubscriptionsList from '@/components/dashboard/SubscriptionsList';

export default function DashboardPage() {
  const { data: monthlyData, isLoading: loadingMonthly } = useQuery({
    queryKey: ['monthlySpend'],
    queryFn: () => getMonthlySpend(12),
  });

  const { data: merchantData, isLoading: loadingMerchants } = useQuery({
    queryKey: ['topMerchants'],
    queryFn: () => getTopMerchants(12, 5),
  });

  const { data: subscriptions, isLoading: loadingSubscriptions } = useQuery({
    queryKey: ['subscriptions'],
    queryFn: getRecurringSubscriptions,
  });

  // Calculate stats
  const totalSpend = monthlyData?.total || 0;
  const avgSpend = monthlyData?.average || 0;
  const monthlyCount = monthlyData?.data?.length || 0;
  const subscriptionTotal = subscriptions?.reduce((sum: number, s: any) => sum + parseFloat(s.amount), 0) || 0;
  const periodChange = monthlyData?.period_change || 0;

  return (
    <div className="space-y-8 fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Dashboard</h1>
          <p className="text-[var(--foreground-secondary)] mt-1">
            Your financial overview at a glance
          </p>
        </div>
        <Link
          href="/analytics"
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          View Detailed Analytics
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Total Spending"
          value={`$${Number(totalSpend).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          change={periodChange !== 0 ? `${periodChange > 0 ? '+' : ''}${periodChange}%` : undefined}
          trend={periodChange > 0 ? 'up' : periodChange < 0 ? 'down' : undefined}
          subtitle={periodChange !== 0 ? "vs last month" : `${monthlyCount} months`}
          icon={DollarSign}
          color="primary"
          loading={loadingMonthly}
        />
        <StatsCard
          title="Monthly Average"
          value={`$${Number(avgSpend).toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={monthlyCount > 0 ? `over ${monthlyCount} months` : undefined}
          icon={CreditCard}
          color="secondary"
          loading={loadingMonthly}
        />
        <StatsCard
          title="Subscriptions"
          value={`$${subscriptionTotal.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          subtitle={subscriptions?.length > 0 ? `${subscriptions.length} active` : "per month"}
          icon={Repeat}
          color="tertiary"
          loading={loadingSubscriptions}
        />
        <StatsCard
          title="Potential Savings"
          value={monthlyData?.potential_savings && monthlyData.potential_savings > 0
            ? `$${Number(monthlyData.potential_savings).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
            : "$0.00"}
          subtitle={monthlyData?.potential_savings > 0 ? "identified" : undefined}
          icon={PiggyBank}
          color="success"
          loading={loadingMonthly}
        />
      </div>

      {/* Quick Spending Summary */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Spending Summary</h2>
          <Link href="/analytics" className="text-sm text-[var(--accent-primary)] hover:underline">
            See full analytics →
          </Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Monthly Trend */}
          <div className="p-4 bg-[var(--glass-bg)] rounded-xl border border-[var(--glass-border)]">
            <div className="flex items-center gap-2 mb-2">
              {periodChange >= 0 ? (
                <TrendingUp className="w-5 h-5 text-red-400" />
              ) : (
                <TrendingDown className="w-5 h-5 text-green-400" />
              )}
              <span className="text-sm text-[var(--foreground-secondary)]">Month Over Month</span>
            </div>
            <p className="text-lg font-bold">
              {periodChange >= 0 ? 'Spending Up' : 'Spending Down'}
            </p>
            <p className="text-sm text-[var(--foreground-secondary)]">
              {Math.abs(periodChange)}% {periodChange >= 0 ? 'increase' : 'decrease'} from last month
            </p>
          </div>

          {/* Top Category */}
          <div className="p-4 bg-[var(--glass-bg)] rounded-xl border border-[var(--glass-border)]">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm text-[var(--foreground-secondary)]">Top Merchant</span>
            </div>
            {loadingMerchants ? (
              <div className="animate-pulse">
                <div className="h-5 w-32 bg-[var(--glass-border)] rounded"></div>
              </div>
            ) : merchantData?.top_merchants?.[0] ? (
              <>
                <p className="text-lg font-bold truncate">
                  {merchantData.top_merchants[0].merchant}
                </p>
                <p className="text-sm text-[var(--foreground-secondary)]">
                  ${merchantData.top_merchants[0].total_amount?.toFixed(2)} ({merchantData.top_merchants[0].transaction_count} transactions)
                </p>
              </>
            ) : (
              <p className="text-sm text-[var(--foreground-secondary)]">No data</p>
            )}
          </div>

          {/* Active Subscriptions */}
          <div className="p-4 bg-[var(--glass-bg)] rounded-xl border border-[var(--glass-border)]">
            <div className="flex items-center gap-2 mb-2">
              <Repeat className="w-5 h-5 text-[var(--accent-tertiary)]" />
              <span className="text-sm text-[var(--foreground-secondary)]">Monthly Recurring</span>
            </div>
            <p className="text-lg font-bold">
              ${subscriptionTotal.toFixed(2)}/mo
            </p>
            <p className="text-sm text-[var(--foreground-secondary)]">
              {subscriptions?.length || 0} active subscriptions
            </p>
          </div>
        </div>
      </div>

      {/* Bottom Row - Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Transactions */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Transactions</h2>
            <Link href="/transactions" className="text-sm text-[var(--accent-primary)] hover:underline">
              View all →
            </Link>
          </div>
          <RecentTransactions />
        </div>

        {/* Subscriptions */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recurring Subscriptions</h2>
          </div>
          <SubscriptionsList data={subscriptions || []} loading={loadingSubscriptions} />
        </div>
      </div>
    </div>
  );
}
