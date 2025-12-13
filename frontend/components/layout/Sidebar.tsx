'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    Upload,
    Receipt,
    MessageSquare,
    BarChart3,
    Settings,
    Wallet,
    TrendingUp,
    Activity,
} from 'lucide-react';

const navItems = [
    { href: '/', label: 'Dashboard', icon: LayoutDashboard },
    { href: '/upload', label: 'Upload', icon: Upload },
    { href: '/transactions', label: 'Transactions', icon: Receipt },
    { href: '/chat', label: 'AI Chat', icon: MessageSquare },
    { href: '/analytics', label: 'Analytics', icon: BarChart3 },
    { href: '/metrics', label: 'Metrics', icon: Activity },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="fixed left-0 top-0 h-screen w-64 bg-[var(--background-secondary)] border-r border-[var(--glass-border)] flex flex-col z-50">
            {/* Logo */}
            <div className="p-6 border-b border-[var(--glass-border)]">
                <Link href="/" className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center">
                        <Wallet className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h1 className="font-bold text-lg gradient-text">FinanceAI</h1>
                        <p className="text-xs text-[var(--foreground-secondary)]">Personal Planner</p>
                    </div>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 p-4 space-y-1">
                {navItems.map((item) => {
                    const isActive = pathname === item.href;
                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${isActive
                                ? 'bg-gradient-to-r from-[var(--accent-primary)] to-[var(--accent-primary-hover)] text-white shadow-lg'
                                : 'text-[var(--foreground-secondary)] hover:bg-[var(--glass-bg)] hover:text-[var(--foreground)]'
                                }`}
                        >
                            <Icon className="w-5 h-5" />
                            <span className="font-medium">{item.label}</span>
                            {isActive && (
                                <div className="ml-auto w-2 h-2 rounded-full bg-white animate-pulse" />
                            )}
                        </Link>
                    );
                })}
            </nav>

            {/* Stats Card */}
            <div className="p-4">
                <div className="glass-card p-4">
                    <div className="flex items-center gap-2 mb-2">
                        <TrendingUp className="w-4 h-4 text-[var(--accent-secondary)]" />
                        <span className="text-sm font-medium">Privacy Mode</span>
                    </div>
                    <p className="text-xs text-[var(--foreground-secondary)]">
                        All data stored locally. Only AI queries sent to LLM.
                    </p>
                    <div className="mt-3 flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-[var(--accent-secondary)] animate-pulse" />
                        <span className="text-xs text-[var(--accent-secondary)]">Secure & Private</span>
                    </div>
                </div>
            </div>

            {/* Settings */}
            <div className="p-4 border-t border-[var(--glass-border)]">
                <Link
                    href="/settings"
                    className="flex items-center gap-3 px-4 py-3 rounded-xl text-[var(--foreground-secondary)] hover:bg-[var(--glass-bg)] hover:text-[var(--foreground)] transition-all"
                >
                    <Settings className="w-5 h-5" />
                    <span className="font-medium">Settings</span>
                </Link>
            </div>
        </aside>
    );
}
