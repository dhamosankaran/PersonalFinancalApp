'use client';

import { LucideIcon } from 'lucide-react';

interface StatsCardProps {
    title: string;
    value: string;
    change?: string;
    trend?: 'up' | 'down';
    subtitle?: string;
    icon: LucideIcon;
    color: 'primary' | 'secondary' | 'tertiary' | 'success';
    loading?: boolean;
}

const colorClasses = {
    primary: {
        bg: 'from-[#6366f1] to-[#8b5cf6]',
        icon: 'bg-[rgba(99,102,241,0.2)]',
        iconColor: 'text-[#818cf8]',
    },
    secondary: {
        bg: 'from-[#3b82f6] to-[#06b6d4]',
        icon: 'bg-[rgba(59,130,246,0.2)]',
        iconColor: 'text-[#60a5fa]',
    },
    tertiary: {
        bg: 'from-[#f59e0b] to-[#ef4444]',
        icon: 'bg-[rgba(245,158,11,0.2)]',
        iconColor: 'text-[#fbbf24]',
    },
    success: {
        bg: 'from-[#10b981] to-[#059669]',
        icon: 'bg-[rgba(16,185,129,0.2)]',
        iconColor: 'text-[#34d399]',
    },
};

export default function StatsCard({
    title,
    value,
    change,
    trend,
    subtitle,
    icon: Icon,
    color,
    loading,
}: StatsCardProps) {
    const colors = colorClasses[color];

    if (loading) {
        return (
            <div className="glass-card p-6 animate-pulse">
                <div className="flex items-start justify-between">
                    <div className="space-y-3">
                        <div className="h-4 w-24 bg-[var(--glass-bg)] rounded" />
                        <div className="h-8 w-32 bg-[var(--glass-bg)] rounded" />
                        <div className="h-3 w-16 bg-[var(--glass-bg)] rounded" />
                    </div>
                    <div className="w-12 h-12 bg-[var(--glass-bg)] rounded-xl" />
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card p-6 hover-glow cursor-pointer group">
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-[var(--foreground-secondary)] text-sm font-medium">{title}</p>
                    <p className="text-2xl font-bold mt-2 group-hover:scale-105 transition-transform">{value}</p>
                    {change && (
                        <div className="flex items-center gap-1 mt-2">
                            <span
                                className={`text-sm font-medium ${trend === 'up' ? 'text-[var(--accent-danger)]' : 'text-[var(--accent-secondary)]'
                                    }`}
                            >
                                {change}
                            </span>
                            <span className="text-xs text-[var(--foreground-secondary)]">vs last period</span>
                        </div>
                    )}
                    {subtitle && (
                        <p className="text-sm text-[var(--foreground-secondary)] mt-2">{subtitle}</p>
                    )}
                </div>
                <div className={`w-12 h-12 rounded-xl ${colors.icon} flex items-center justify-center`}>
                    <Icon className={`w-6 h-6 ${colors.iconColor}`} />
                </div>
            </div>
            {/* Gradient line at bottom */}
            <div className={`h-1 rounded-full bg-gradient-to-r ${colors.bg} mt-4 opacity-60`} />
        </div>
    );
}
