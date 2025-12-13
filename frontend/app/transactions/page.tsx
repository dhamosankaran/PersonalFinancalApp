'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Search,
    Filter,
    Download,
    ChevronLeft,
    ChevronRight,
    Edit2,
    Trash2,
    X,
} from 'lucide-react';
import { getTransactions, deleteTransaction, updateTransaction } from '@/utils/api';
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

const categories = Object.keys(categoryColors);

export default function TransactionsPage() {
    const [search, setSearch] = useState('');
    const [categoryFilter, setCategoryFilter] = useState('');
    const [page, setPage] = useState(0);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editCategory, setEditCategory] = useState('');
    const limit = 20;
    const queryClient = useQueryClient();

    const { data: transactions, isLoading } = useQuery({
        queryKey: ['transactions', { category: categoryFilter, offset: page * limit }],
        queryFn: () =>
            getTransactions({
                category: categoryFilter || undefined,
                limit,
                offset: page * limit,
            }),
    });

    const deleteMutation = useMutation({
        mutationFn: deleteTransaction,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['transactions'] });
        },
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, data }: { id: string; data: any }) => updateTransaction(id, data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['transactions'] });
            setEditingId(null);
        },
    });

    const filteredTransactions = transactions?.filter((t: any) =>
        t.merchant?.toLowerCase().includes(search.toLowerCase())
    );

    const handleCategoryUpdate = (id: string) => {
        if (editCategory) {
            updateMutation.mutate({ id, data: { category: editCategory } });
        }
    };

    return (
        <div className="space-y-6 fade-in">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Transactions</h1>
                    <p className="text-[var(--foreground-secondary)] mt-1">
                        View and manage all your transactions
                    </p>
                </div>
                <button className="btn-secondary inline-flex items-center gap-2">
                    <Download className="w-4 h-4" />
                    Export CSV
                </button>
            </div>

            {/* Filters */}
            <div className="glass-card p-4">
                <div className="flex flex-wrap items-center gap-4">
                    {/* Search */}
                    <div className="relative flex-1 min-w-[200px]">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--foreground-secondary)]" />
                        <input
                            type="text"
                            placeholder="Search merchants..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="input-field pl-10"
                        />
                    </div>

                    {/* Category Filter */}
                    <div className="relative">
                        <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--foreground-secondary)]" />
                        <select
                            value={categoryFilter}
                            onChange={(e) => {
                                setCategoryFilter(e.target.value);
                                setPage(0);
                            }}
                            className="input-field pl-10 pr-8 appearance-none cursor-pointer"
                        >
                            <option value="">All Categories</option>
                            {categories.map((cat) => (
                                <option key={cat} value={cat}>
                                    {cat}
                                </option>
                            ))}
                        </select>
                    </div>

                    {categoryFilter && (
                        <button
                            onClick={() => setCategoryFilter('')}
                            className="btn-secondary text-sm py-2"
                        >
                            Clear Filters
                        </button>
                    )}
                </div>
            </div>

            {/* Transactions Table */}
            <div className="glass-card overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="spinner" />
                    </div>
                ) : !filteredTransactions || filteredTransactions.length === 0 ? (
                    <div className="text-center py-20 text-[var(--foreground-secondary)]">
                        <p className="text-lg">No transactions found</p>
                        <p className="text-sm mt-1">
                            {categoryFilter ? 'Try a different filter' : 'Upload your statements to get started'}
                        </p>
                    </div>
                ) : (
                    <>
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-[var(--background-tertiary)]">
                                    <tr>
                                        <th className="text-left px-6 py-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                            Date
                                        </th>
                                        <th className="text-left px-6 py-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                            Merchant
                                        </th>
                                        <th className="text-left px-6 py-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                            Category
                                        </th>
                                        <th className="text-right px-6 py-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                            Amount
                                        </th>
                                        <th className="text-right px-6 py-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                            Actions
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-[var(--glass-border)]">
                                    {filteredTransactions.map((transaction: any) => {
                                        const categoryColor = categoryColors[transaction.category] || categoryColors['Uncategorized'];
                                        const isEditing = editingId === transaction.id;

                                        return (
                                            <tr
                                                key={transaction.id}
                                                className="hover:bg-[var(--glass-bg)] transition-colors"
                                            >
                                                <td className="px-6 py-4">
                                                    <span className="text-sm">
                                                        {format(new Date(transaction.transaction_date), 'MMM d, yyyy')}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <p className="font-medium">{transaction.merchant || 'Unknown'}</p>
                                                    {transaction.description && (
                                                        <p className="text-xs text-[var(--foreground-secondary)] truncate max-w-[200px]">
                                                            {transaction.description}
                                                        </p>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    {isEditing ? (
                                                        <div className="flex items-center gap-2">
                                                            <select
                                                                value={editCategory || transaction.category}
                                                                onChange={(e) => setEditCategory(e.target.value)}
                                                                className="input-field py-1 text-sm w-32"
                                                            >
                                                                {categories.map((cat) => (
                                                                    <option key={cat} value={cat}>
                                                                        {cat}
                                                                    </option>
                                                                ))}
                                                            </select>
                                                            <button
                                                                onClick={() => handleCategoryUpdate(transaction.id)}
                                                                className="text-[var(--accent-secondary)] hover:text-white"
                                                            >
                                                                ✓
                                                            </button>
                                                            <button
                                                                onClick={() => setEditingId(null)}
                                                                className="text-[var(--accent-danger)] hover:text-white"
                                                            >
                                                                <X className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    ) : (
                                                        <span
                                                            className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium text-white ${categoryColor}`}
                                                        >
                                                            {transaction.category || 'Uncategorized'}
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <span className="font-bold text-[var(--accent-danger)]">
                                                        -${parseFloat(transaction.amount).toFixed(2)}
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    <div className="flex items-center justify-end gap-2">
                                                        <button
                                                            onClick={() => {
                                                                setEditingId(transaction.id);
                                                                setEditCategory(transaction.category);
                                                            }}
                                                            className="p-2 rounded-lg hover:bg-[var(--glass-bg)] text-[var(--foreground-secondary)] hover:text-[var(--accent-primary)] transition-colors"
                                                        >
                                                            <Edit2 className="w-4 h-4" />
                                                        </button>
                                                        <button
                                                            onClick={() => {
                                                                if (confirm('Delete this transaction?')) {
                                                                    deleteMutation.mutate(transaction.id);
                                                                }
                                                            }}
                                                            className="p-2 rounded-lg hover:bg-[var(--glass-bg)] text-[var(--foreground-secondary)] hover:text-[var(--accent-danger)] transition-colors"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        <div className="flex items-center justify-between px-6 py-4 border-t border-[var(--glass-border)]">
                            <p className="text-sm text-[var(--foreground-secondary)]">
                                Showing {page * limit + 1} to {page * limit + filteredTransactions.length} transactions
                            </p>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                                    disabled={page === 0}
                                    className="btn-secondary p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <ChevronLeft className="w-5 h-5" />
                                </button>
                                <span className="px-4 py-2 text-sm">Page {page + 1}</span>
                                <button
                                    onClick={() => setPage((p) => p + 1)}
                                    disabled={filteredTransactions.length < limit}
                                    className="btn-secondary p-2 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <ChevronRight className="w-5 h-5" />
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
