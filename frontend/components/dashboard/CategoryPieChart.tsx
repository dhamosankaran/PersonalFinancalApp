'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';

interface CategoryPieChartProps {
    data: Array<{
        category: string;
        amount: number;
        percentage: number;
    }>;
    loading?: boolean;
}

const COLORS = [
    '#6366f1', // Indigo
    '#10b981', // Emerald
    '#f59e0b', // Amber
    '#ef4444', // Red
    '#8b5cf6', // Violet
    '#06b6d4', // Cyan
    '#ec4899', // Pink
    '#84cc16', // Lime
    '#f97316', // Orange
    '#64748b', // Slate
];

export default function CategoryPieChart({ data, loading }: CategoryPieChartProps) {
    if (loading) {
        return (
            <div className="h-[300px] flex items-center justify-center">
                <div className="spinner" />
            </div>
        );
    }

    if (!data || data.length === 0) {
        return (
            <div className="h-[300px] flex items-center justify-center text-[var(--foreground-secondary)] text-center">
                <p>No category data available</p>
            </div>
        );
    }

    const chartData = data.slice(0, 8).map((item, index) => ({
        name: item.category,
        value: item.amount,
        percentage: item.percentage,
        fill: COLORS[index % COLORS.length],
    }));

    const CustomTooltip = ({ active, payload }: any) => {
        if (active && payload && payload.length) {
            const data = payload[0].payload;
            return (
                <div className="glass-card p-3 border border-[var(--accent-primary)]">
                    <p className="text-sm font-medium">{data.name}</p>
                    <p className="text-lg font-bold" style={{ color: data.fill }}>
                        ${data.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </p>
                    <p className="text-xs text-[var(--foreground-secondary)]">
                        {data.percentage.toFixed(1)}% of total
                    </p>
                </div>
            );
        }
        return null;
    };

    const renderLegend = (props: any) => {
        const { payload } = props;
        return (
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
                {payload.slice(0, 5).map((entry: any, index: number) => (
                    <div key={`legend-${index}`} className="flex items-center gap-1">
                        <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: entry.color }}
                        />
                        <span className="text-xs text-[var(--foreground-secondary)]">
                            {entry.value.length > 10 ? entry.value.substring(0, 10) + '...' : entry.value}
                        </span>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <ResponsiveContainer width="100%" height={300}>
            <PieChart>
                <Pie
                    data={chartData}
                    cx="50%"
                    cy="45%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                >
                    {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend content={renderLegend} />
            </PieChart>
        </ResponsiveContainer>
    );
}
