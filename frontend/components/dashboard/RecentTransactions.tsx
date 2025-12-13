'use client';

import { useQuery } from '@tanstack/react-query';
import { getTransactions } from '@/utils/api';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { format } from 'date-fns';

const categoryColors: Record<string, string> = {
    'Food & Dining': 'bg-[#ff6b6b]',
    'Groceries': 'bg-[#4ecdc4]',
    'Transportation': 'bg-[#45b7d1]',
    'Shopping': 'bg-[#ffa07a]',
    'Entertainment': 'bg-[#98d8c8]',
    'Utilities': 'bg-[#6c5ce7]',
    'Healthcare': 'bg-[#a8e6cf]',
    'Travel': 'bg-[#ffd93d]',
    'Subscriptions': 'bg-[#bc85a3]',
    'Uncategorized': 'bg-[#95a5a6]',
};

export default function RecentTransactions() {
    const { data, isLoading } = useQuery({
        queryKey: ['recentTransactions'],
        queryFn: () => getTransactions({ limit: 5 }),
    });

    if (isLoading) {
        return (
            <div className="space-y-3">
                {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex items-center gap-3 animate-pulse">
                        <div className="w-10 h-10 bg-[var(--glass-bg)] rounded-lg" />
                        <div className="flex-1 space-y-2">
                            <div className="h-4 w-32 bg-[var(--glass-bg)] rounded" />
                            <div className="h-3 w-20 bg-[var(--glass-bg)] rounded" />
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
                <p>No transactions yet. Upload your statements to get started.</p>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {data.slice(0, 5).map((transaction: any) => {
                const categoryColor = categoryColors[transaction.category] || categoryColors['Uncategorized'];
                const date = new Date(transaction.transaction_date);

                return (
                    <div
                        key={transaction.id}
                        className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--glass-bg)] transition-all cursor-pointer group"
                    >
                        <div className={`w-10 h-10 rounded-lg ${categoryColor} flex items-center justify-center`}>
                            <span className="text-white text-xs font-bold">
                                {transaction.category?.charAt(0) || '?'}
                            </span>
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-medium truncate group-hover:text-[var(--accent-primary)] transition-colors">
                                {transaction.merchant || 'Unknown'}
                            </p>
                            <p className="text-xs text-[var(--foreground-secondary)]">
                                {format(date, 'MMM d, yyyy')} • {transaction.category || 'Uncategorized'}
                            </p>
                        </div>
                        <div className="text-right">
                            <p className="font-bold text-[var(--accent-danger)]">
                                -${parseFloat(transaction.amount).toFixed(2)}
                            </p>
                        </div>
                    </div>
                );
            })}

            <a
                href="/transactions"
                className="block text-center text-sm text-[var(--accent-primary)] hover:underline mt-4"
            >
                View all transactions →
            </a>
        </div>
    );
}
