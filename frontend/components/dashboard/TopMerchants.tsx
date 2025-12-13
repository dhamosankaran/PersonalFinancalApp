'use client';

import { Store, TrendingUp } from 'lucide-react';

interface TopMerchantsProps {
    data: Array<{
        merchant: string;
        total_amount: number;
        transaction_count: number;
        average_amount: number;
    }>;
    loading?: boolean;
}

export default function TopMerchants({ data, loading }: TopMerchantsProps) {
    if (loading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
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
            <div className="h-[200px] flex items-center justify-center text-[var(--foreground-secondary)] text-center">
                <p>No merchant data available</p>
            </div>
        );
    }

    const maxAmount = Math.max(...data.map((m) => m.total_amount));

    return (
        <div className="space-y-3">
            {data.map((merchant, index) => {
                const percentage = (merchant.total_amount / maxAmount) * 100;

                return (
                    <div
                        key={merchant.merchant}
                        className="group p-3 rounded-lg hover:bg-[var(--glass-bg)] transition-all cursor-pointer"
                    >
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center text-white font-bold">
                                {index + 1}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="font-medium truncate group-hover:text-[var(--accent-primary)] transition-colors">
                                    {merchant.merchant}
                                </p>
                                <p className="text-xs text-[var(--foreground-secondary)]">
                                    {merchant.transaction_count} transactions
                                </p>
                            </div>
                            <div className="text-right">
                                <p className="font-bold text-[var(--accent-primary)]">
                                    ${merchant.total_amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                </p>
                            </div>
                        </div>
                        {/* Progress bar */}
                        <div className="mt-2 h-1 bg-[var(--glass-bg)] rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-primary-hover)] transition-all duration-500"
                                style={{ width: `${percentage}%` }}
                            />
                        </div>
                    </div>
                );
            })}
        </div>
    );
}
