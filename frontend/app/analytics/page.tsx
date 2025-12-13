'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    TrendingUp,
    TrendingDown,
    PieChart,
    BarChart3,
    Calendar,
    DollarSign,
    Target,
    Lightbulb,
    RefreshCw,
} from 'lucide-react';
import {
    getMonthlySpend,
    getCategoryBreakdown,
    getTopMerchants,
    getRecurringSubscriptions,
    getInsights,
    refreshInsights,
} from '@/utils/api';
import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart as RechartsPie,
    Pie,
    Cell,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import { format } from 'date-fns';

const COLORS = [
    '#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#64748b',
];

export default function AnalyticsPage() {
    const [timeRange, setTimeRange] = useState(12);
    const queryClient = useQueryClient();

    const { data: monthlyData, isLoading: loadingMonthly } = useQuery({
        queryKey: ['monthlySpend', timeRange],
        queryFn: () => getMonthlySpend(timeRange),
    });

    const { data: categoryData, isLoading: loadingCategory } = useQuery({
        queryKey: ['categoryBreakdown', timeRange],
        queryFn: () => getCategoryBreakdown(timeRange),
    });

    const { data: merchantData, isLoading: loadingMerchants } = useQuery({
        queryKey: ['topMerchants', timeRange],
        queryFn: () => getTopMerchants(timeRange, 10),
    });

    const { data: subscriptions, isLoading: loadingSubscriptions } = useQuery({
        queryKey: ['subscriptions'],
        queryFn: getRecurringSubscriptions,
    });

    const { data: insightsData, isLoading: loadingInsights } = useQuery({
        queryKey: ['insights'],
        queryFn: () => getInsights(false),
        staleTime: 1000 * 60 * 60, // 1 hour - insights don't auto-refresh
    });

    // Mutation for refreshing insights (makes LLM API call)
    const refreshInsightsMutation = useMutation({
        mutationFn: refreshInsights,
        onSuccess: (data) => {
            queryClient.setQueryData(['insights'], data);
        },
    });

    // Prepare chart data
    const monthlyChartData = [...(monthlyData?.data || [])].reverse().map((item: any) => ({
        month: item.month,
        amount: item.amount,
        count: item.count,
    }));

    const categoryChartData = (categoryData?.data || []).slice(0, 8).map((item: any, index: number) => ({
        name: item.category,
        value: item.amount,
        percentage: item.percentage,
        fill: COLORS[index % COLORS.length],
    }));

    const merchantChartData = (merchantData?.top_merchants || []).map((item: any) => ({
        name: item.merchant.length > 15 ? item.merchant.substring(0, 15) + '...' : item.merchant,
        amount: item.total_amount,
        count: item.transaction_count,
    }));

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="glass-card p-3 border border-[var(--accent-primary)]">
                    <p className="text-sm font-medium">{label}</p>
                    {payload.map((entry: any, index: number) => (
                        <p key={index} className="text-sm" style={{ color: entry.color }}>
                            {entry.name}: ${entry.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    // Format AI insights for better readability
    const InsightCard = ({ question, answer }: { question: string; answer: string }) => {
        // Parse the answer to extract structured content
        const formatAnswer = (text: string) => {
            if (!text) return null;

            // Split by numbered items (1. 2. 3. etc.) or bullet points
            const lines = text.split(/\n+/);
            const formattedContent: JSX.Element[] = [];
            let currentSection: string[] = [];

            lines.forEach((line, idx) => {
                const trimmedLine = line.trim();
                if (!trimmedLine) return;

                // Check if it's a numbered item
                const numberedMatch = trimmedLine.match(/^(\d+)\.\s*\*\*(.+?)\*\*:?\s*(.*)$/);
                const bulletMatch = trimmedLine.match(/^[-•]\s*\*\*(.+?)\*\*:?\s*(.*)$/);
                const boldMatch = trimmedLine.match(/\*\*(.+?)\*\*/g);

                if (numberedMatch) {
                    // Numbered list item with bold heading
                    formattedContent.push(
                        <div key={idx} className="mb-3 pl-4 border-l-2 border-[var(--accent-primary)]">
                            <p className="font-semibold text-[var(--foreground)]">
                                {numberedMatch[1]}. {numberedMatch[2]}
                            </p>
                            {numberedMatch[3] && (
                                <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                    {numberedMatch[3].replace(/\*\*/g, '')}
                                </p>
                            )}
                        </div>
                    );
                } else if (bulletMatch) {
                    // Bullet point with bold heading
                    formattedContent.push(
                        <div key={idx} className="mb-2 pl-4 flex gap-2">
                            <span className="text-[var(--accent-primary)]">•</span>
                            <div>
                                <span className="font-medium">{bulletMatch[1]}</span>
                                {bulletMatch[2] && <span className="text-[var(--foreground-secondary)]"> {bulletMatch[2]}</span>}
                            </div>
                        </div>
                    );
                } else if (boldMatch) {
                    // Line with some bold text
                    const formattedText = trimmedLine
                        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\$(\d+(?:,\d{3})*(?:\.\d{2})?)/g, '<span class="text-[var(--accent-primary)] font-medium">$$$1</span>');
                    formattedContent.push(
                        <p
                            key={idx}
                            className="text-sm text-[var(--foreground)] mb-2"
                            dangerouslySetInnerHTML={{ __html: formattedText }}
                        />
                    );
                } else {
                    // Regular paragraph
                    formattedContent.push(
                        <p key={idx} className="text-sm text-[var(--foreground-secondary)] mb-2">
                            {trimmedLine}
                        </p>
                    );
                }
            });

            return formattedContent;
        };

        // Map question to icon and color
        const getQuestionStyle = (q: string) => {
            if (q.includes('spending categories')) return { icon: '📊', color: 'var(--accent-primary)' };
            if (q.includes('save money')) return { icon: '💰', color: '#10b981' };
            if (q.includes('unusual')) return { icon: '⚠️', color: '#f59e0b' };
            if (q.includes('merchants')) return { icon: '🏪', color: '#8b5cf6' };
            return { icon: '💡', color: 'var(--accent-secondary)' };
        };

        const style = getQuestionStyle(question);

        return (
            <div className="p-5 rounded-xl bg-[var(--background)] border border-[var(--glass-border)] hover:border-[var(--accent-primary)] transition-colors">
                <div className="flex items-start gap-3 mb-4">
                    <span className="text-2xl">{style.icon}</span>
                    <h3 className="font-semibold text-[var(--foreground)]" style={{ color: style.color }}>
                        {question}
                    </h3>
                </div>
                <div className="space-y-1">
                    {formatAnswer(answer)}
                </div>
            </div>
        );
    };

    return (
        <div className="space-y-8 fade-in">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Analytics</h1>
                    <p className="text-[var(--foreground-secondary)] mt-1">
                        Deep dive into your financial data
                    </p>
                </div>
                <select
                    value={timeRange}
                    onChange={(e) => setTimeRange(Number(e.target.value))}
                    className="input-field py-2 px-4 w-auto"
                >
                    <option value={3}>Last 3 months</option>
                    <option value={6}>Last 6 months</option>
                    <option value={12}>Last 12 months</option>
                    <option value={24}>Last 24 months</option>
                </select>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <DollarSign className="w-5 h-5 text-[var(--accent-primary)]" />
                        <span className="text-sm text-[var(--foreground-secondary)]">Total Spent</span>
                    </div>
                    <p className="text-2xl font-bold">
                        ${(monthlyData?.total || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                </div>
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <Calendar className="w-5 h-5 text-[var(--accent-secondary)]" />
                        <span className="text-sm text-[var(--foreground-secondary)]">Monthly Avg</span>
                    </div>
                    <p className="text-2xl font-bold">
                        ${(monthlyData?.average || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                </div>
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <Target className="w-5 h-5 text-[var(--accent-tertiary)]" />
                        <span className="text-sm text-[var(--foreground-secondary)]">Categories</span>
                    </div>
                    <p className="text-2xl font-bold">{categoryData?.data?.length || 0}</p>
                </div>
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-2">
                        <BarChart3 className="w-5 h-5 text-[#ec4899]" />
                        <span className="text-sm text-[var(--foreground-secondary)]">Merchants</span>
                    </div>
                    <p className="text-2xl font-bold">{merchantData?.total_merchants || 0}</p>
                </div>
            </div>

            {/* Spending Trend */}
            <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <TrendingUp className="w-6 h-6 text-[var(--accent-primary)]" />
                        <h2 className="text-xl font-semibold">Spending Trend</h2>
                    </div>
                </div>
                {loadingMonthly ? (
                    <div className="h-[350px] flex items-center justify-center">
                        <div className="spinner" />
                    </div>
                ) : monthlyChartData.length === 0 ? (
                    <div className="h-[350px] flex items-center justify-center text-[var(--foreground-secondary)]">
                        No data available
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height={350}>
                        <AreaChart data={monthlyChartData}>
                            <defs>
                                <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
                            <XAxis dataKey="month" tick={{ fill: '#a0a0a0', fontSize: 12 }} />
                            <YAxis
                                tick={{ fill: '#a0a0a0', fontSize: 12 }}
                                tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Area
                                type="monotone"
                                dataKey="amount"
                                stroke="#6366f1"
                                strokeWidth={3}
                                fill="url(#colorAmount)"
                                name="Spending"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                )}
            </div>

            {/* Category & Merchant Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Category Pie Chart */}
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <PieChart className="w-6 h-6 text-[var(--accent-secondary)]" />
                        <h2 className="text-xl font-semibold">Category Distribution</h2>
                    </div>
                    {loadingCategory ? (
                        <div className="h-[350px] flex items-center justify-center">
                            <div className="spinner" />
                        </div>
                    ) : categoryChartData.length === 0 ? (
                        <div className="h-[350px] flex items-center justify-center text-[var(--foreground-secondary)]">
                            No data available
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={350}>
                            <RechartsPie>
                                <Pie
                                    data={categoryChartData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={120}
                                    paddingAngle={2}
                                    dataKey="value"
                                    label={({ name, percentage }) => `${name} (${percentage?.toFixed(0)}%)`}
                                    labelLine={{ stroke: '#a0a0a0' }}
                                >
                                    {categoryChartData.map((entry: any, index: number) => (
                                        <Cell key={`cell-${index}`} fill={entry.fill} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value: number) => [`$${value.toFixed(2)}`, 'Amount']}
                                    contentStyle={{
                                        background: '#1a1a2e',
                                        border: '1px solid rgba(255,255,255,0.1)',
                                        borderRadius: '8px',
                                    }}
                                />
                            </RechartsPie>
                        </ResponsiveContainer>
                    )}
                </div>

                {/* Top Merchants Bar Chart */}
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <BarChart3 className="w-6 h-6 text-[var(--accent-tertiary)]" />
                        <h2 className="text-xl font-semibold">Top Merchants</h2>
                    </div>
                    {loadingMerchants ? (
                        <div className="h-[350px] flex items-center justify-center">
                            <div className="spinner" />
                        </div>
                    ) : merchantChartData.length === 0 ? (
                        <div className="h-[350px] flex items-center justify-center text-[var(--foreground-secondary)]">
                            No data available
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height={350}>
                            <BarChart data={merchantChartData} layout="vertical">
                                <CartesianGrid strokeDasharray="3 3" stroke="#2a2a4a" />
                                <XAxis
                                    type="number"
                                    tick={{ fill: '#a0a0a0', fontSize: 12 }}
                                    tickFormatter={(v) => `$${v}`}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    tick={{ fill: '#a0a0a0', fontSize: 11 }}
                                    width={120}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Bar dataKey="amount" fill="#f59e0b" radius={[0, 4, 4, 0]} name="Amount" />
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </div>

            {/* Category Breakdown Table */}
            <div className="glass-card p-6">
                <div className="flex items-center gap-3 mb-6">
                    <Target className="w-6 h-6 text-[var(--accent-primary)]" />
                    <h2 className="text-xl font-semibold">Category Breakdown</h2>
                </div>
                {loadingCategory ? (
                    <div className="h-[200px] flex items-center justify-center">
                        <div className="spinner" />
                    </div>
                ) : (categoryData?.data || []).length === 0 ? (
                    <div className="text-center py-12 text-[var(--foreground-secondary)]">
                        No category data available
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="border-b border-[var(--glass-border)]">
                                <tr>
                                    <th className="text-left py-3 px-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                        Category
                                    </th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                        Amount
                                    </th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                        Transactions
                                    </th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                        Avg/Transaction
                                    </th>
                                    <th className="text-right py-3 px-4 text-sm font-medium text-[var(--foreground-secondary)]">
                                        % of Total
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-[var(--glass-border)]">
                                {(categoryData?.data || []).map((cat: any, index: number) => (
                                    <tr key={cat.category} className="hover:bg-[var(--glass-bg)]">
                                        <td className="py-4 px-4">
                                            <div className="flex items-center gap-3">
                                                <div
                                                    className="w-3 h-3 rounded-full"
                                                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                                                />
                                                <span className="font-medium">{cat.category}</span>
                                            </div>
                                        </td>
                                        <td className="text-right py-4 px-4 font-bold">
                                            ${cat.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                                        </td>
                                        <td className="text-right py-4 px-4 text-[var(--foreground-secondary)]">
                                            {cat.count}
                                        </td>
                                        <td className="text-right py-4 px-4 text-[var(--foreground-secondary)]">
                                            ${cat.average?.toFixed(2) || '0.00'}
                                        </td>
                                        <td className="text-right py-4 px-4">
                                            <div className="flex items-center justify-end gap-2">
                                                <div className="w-20 h-2 bg-[var(--glass-bg)] rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full rounded-full"
                                                        style={{
                                                            width: `${cat.percentage}%`,
                                                            backgroundColor: COLORS[index % COLORS.length],
                                                        }}
                                                    />
                                                </div>
                                                <span className="text-sm">{cat.percentage?.toFixed(1)}%</span>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* AI Insights */}
            <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <Lightbulb className="w-6 h-6 text-[#fbbf24]" />
                        <h2 className="text-xl font-semibold">AI Insights</h2>
                        {insightsData?.cached && (
                            <span className="text-xs px-2 py-1 rounded-full bg-[var(--glass-bg)] text-[var(--foreground-secondary)]">
                                Cached
                            </span>
                        )}
                        {insightsData?.last_updated && (
                            <span className="text-xs text-[var(--foreground-secondary)]">
                                Updated: {new Date(insightsData.last_updated).toLocaleDateString()}
                            </span>
                        )}
                    </div>
                    <button
                        onClick={() => refreshInsightsMutation.mutate()}
                        disabled={refreshInsightsMutation.isPending || loadingInsights}
                        className="btn-secondary flex items-center gap-2 text-sm py-2 px-4"
                        title="Refresh insights using AI (makes LLM API call)"
                    >
                        <RefreshCw className={`w-4 h-4 ${refreshInsightsMutation.isPending ? 'animate-spin' : ''}`} />
                        {refreshInsightsMutation.isPending ? 'Generating...' : 'Refresh with AI'}
                    </button>
                </div>
                {loadingInsights || refreshInsightsMutation.isPending ? (
                    <div className="h-[150px] flex flex-col items-center justify-center gap-3">
                        <div className="spinner" />
                        <p className="text-sm text-[var(--foreground-secondary)]">
                            {refreshInsightsMutation.isPending ? 'Generating fresh insights with AI...' : 'Loading insights...'}
                        </p>
                    </div>
                ) : !insightsData?.insights || Object.keys(insightsData.insights).length === 0 ? (
                    <div className="text-center py-8 text-[var(--foreground-secondary)]">
                        <p>No insights available yet</p>
                        <p className="text-sm mt-1">Click "Refresh with AI" to generate insights from your transaction data</p>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {Object.entries(insightsData.insights).map(([question, answer]: [string, any]) => (
                            <InsightCard key={question} question={question} answer={answer} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
