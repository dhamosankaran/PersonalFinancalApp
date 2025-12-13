'use client';

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';

interface SpendingChartProps {
    data: Array<{
        month: string;
        amount: number;
    }>;
    loading?: boolean;
}

export default function SpendingChart({ data, loading }: SpendingChartProps) {
    if (loading) {
        return (
            <div className="h-[300px] flex items-center justify-center">
                <div className="spinner" />
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="h-[300px] flex items-center justify-center text-[var(--foreground-secondary)]">
                <p>No spending data available. Upload your statements to get started.</p>
            </div>
        );
    }

    // Format data for chart
    const chartData = [...data].reverse().map((item) => ({
        name: item.month,
        amount: item.amount,
    }));

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="glass-card p-3 border border-[var(--accent-primary)]">
                    <p className="text-sm font-medium">{label}</p>
                    <p className="text-lg font-bold text-[var(--accent-primary)]">
                        ${payload[0].value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                    <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
                <XAxis
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: 'var(--foreground-secondary)', fontSize: 12 }}
                />
                <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: 'var(--foreground-secondary)', fontSize: 12 }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip content={<CustomTooltip />} />
                <Area
                    type="monotone"
                    dataKey="amount"
                    stroke="var(--accent-primary)"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorSpend)"
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}
