'use client';

import { Repeat, AlertCircle } from 'lucide-react';

interface SubscriptionsListProps {
    data: Array<{
        merchant: string;
        amount: number | string;
        frequency: string;
        last_charge: string;
        total_paid: number | string;
    }>;
    loading?: boolean;
}

export default function SubscriptionsList({ data, loading }: SubscriptionsListProps) {
    if (loading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="flex items-center gap-3 animate-pulse">
                        <div className="w-10 h-10 bg-[var(--glass-bg)] rounded-lg" />
                        <div className="flex-1 space-y-2">
                            <div className="h-4 w-24 bg-[var(--glass-bg)] rounded" />
                            <div className="h-3 w-16 bg-[var(--glass-bg)] rounded" />
                        </div>
                        <div className="h-5 w-16 bg-[var(--glass-bg)] rounded" />
                    </div>
                ))}
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="h-[200px] flex flex-col items-center justify-center text-[var(--foreground-secondary)] text-center">
                <Repeat className="w-12 h-12 mb-3 opacity-50" />
                <p>No recurring subscriptions detected</p>
                <p className="text-xs mt-1">Upload more statements to detect patterns</p>
            </div>
        );
    }

    const totalMonthly = data.reduce((sum, s) => sum + parseFloat(String(s.amount)), 0);

    return (
        <div className="space-y-3">
            {data.slice(0, 4).map((subscription, index) => {
                const amount = parseFloat(String(subscription.amount));

                return (
                    <div
                        key={`${subscription.merchant}-${index}`}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--glass-bg)] transition-all cursor-pointer group"
                    >
                        <div className="w-10 h-10 rounded-lg bg-[var(--accent-tertiary)] bg-opacity-20 flex items-center justify-center">
                            <Repeat className="w-5 h-5 text-[var(--accent-tertiary)]" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-medium truncate group-hover:text-[var(--accent-primary)] transition-colors">
                                {subscription.merchant}
                            </p>
                            <p className="text-xs text-[var(--foreground-secondary)]">
                                {subscription.frequency}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="font-bold text-[var(--accent-tertiary)]">
                                ${amount.toFixed(2)}
                            </p>
                        </div>
                    </div>
                );
            })}

            {/* Total */}
            <div className="mt-4 pt-4 border-t border-[var(--glass-border)]">
                <div className="flex items-center justify-between">
                    <span className="text-sm text-[var(--foreground-secondary)]">Est. Monthly Total</span>
                    <span className="font-bold text-lg">
                        ${totalMonthly.toFixed(2)}
                    </span>
                </div>
            </div>

            {/* Warning */}
            {data.length > 3 && (
                <div className="mt-3 p-3 rounded-lg bg-[var(--accent-tertiary)] bg-opacity-10 border border-[var(--accent-tertiary)] border-opacity-30">
                    <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-[var(--accent-tertiary)]" />
                        <span className="text-sm text-[var(--accent-tertiary)]">
                            {data.length} subscriptions detected
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
}
