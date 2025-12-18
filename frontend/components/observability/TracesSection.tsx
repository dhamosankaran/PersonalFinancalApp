'use client';

import { useEffect, useState } from 'react';
import {
    Activity,
    Clock,
    DollarSign,
    Hash,
    RefreshCw,
    Search,
    Filter,
    ChevronDown,
    Layers,
    Cpu,
} from 'lucide-react';

interface TraceData {
    id: string;
    name: string;
    user_id: string | null;
    start_time: string;
    duration_ms: number | null;
    status: string;
    input_summary: string | null;
    output_summary: string | null;
    span_count: number;
    llm_spans?: number;
    total_tokens?: number;
    total_cost?: number;
}

interface TracingStats {
    total_traces: number;
    total_llm_calls: number;
    total_tokens: number;
    total_cost_usd: number;
    recent_trace_count: number;
}

interface LLMCallsSummary {
    total_calls: number;
    by_provider: Record<string, {
        call_count: number;
        total_tokens: number;
        total_cost: number;
        avg_duration_ms: number;
    }>;
}

export function TracesSection() {
    const [traces, setTraces] = useState<TraceData[]>([]);
    const [stats, setStats] = useState<TracingStats | null>(null);
    const [llmSummary, setLLMSummary] = useState<LLMCallsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [selectedTrace, setSelectedTrace] = useState<string | null>(null);

    const fetchData = async () => {
        try {
            const [tracesRes, statsRes, llmRes] = await Promise.all([
                fetch('http://localhost:8000/api/traces/recent?limit=30'),
                fetch('http://localhost:8000/api/traces/stats'),
                fetch('http://localhost:8000/api/traces/llm-calls'),
            ]);

            const tracesData = await tracesRes.json();
            const statsData = await statsRes.json();
            const llmData = await llmRes.json();

            setTraces(tracesData.traces || []);
            setStats(statsData);
            setLLMSummary(llmData);
        } catch (err) {
            console.error('Failed to fetch traces:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const formatDuration = (ms: number | null) => {
        if (ms === null) return '-';
        if (ms < 1000) return `${Math.round(ms)}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    const formatCost = (cost: number | null | undefined) => {
        if (!cost) return '$0.00';
        if (cost < 0.01) return `$${cost.toFixed(6)}`;
        return `$${cost.toFixed(4)}`;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-32">
                <RefreshCw className="w-6 h-6 animate-spin text-[var(--accent-primary)]" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-blue-500/20">
                            <Layers className="w-5 h-5 text-blue-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Total Traces</p>
                            <p className="text-xl font-bold">{stats?.total_traces || 0}</p>
                        </div>
                    </div>
                </div>

                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-purple-500/20">
                            <Cpu className="w-5 h-5 text-purple-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">LLM Calls</p>
                            <p className="text-xl font-bold">{stats?.total_llm_calls || 0}</p>
                        </div>
                    </div>
                </div>

                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-green-500/20">
                            <Hash className="w-5 h-5 text-green-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Total Tokens</p>
                            <p className="text-xl font-bold">{(stats?.total_tokens || 0).toLocaleString()}</p>
                        </div>
                    </div>
                </div>

                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-yellow-500/20">
                            <DollarSign className="w-5 h-5 text-yellow-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Est. Cost</p>
                            <p className="text-xl font-bold">{formatCost(stats?.total_cost_usd)}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* LLM Calls by Provider */}
            {llmSummary && Object.keys(llmSummary.by_provider).length > 0 && (
                <div className="glass-card p-4">
                    <h3 className="font-semibold mb-3">LLM Usage by Provider</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {Object.entries(llmSummary.by_provider).map(([provider, data]) => (
                            <div key={provider} className="bg-[var(--background-tertiary)] rounded-xl p-4">
                                <div className="flex items-center justify-between mb-2">
                                    <span className="font-medium capitalize">{provider}</span>
                                    <span className="text-sm text-[var(--foreground-secondary)]">
                                        {data.call_count} calls
                                    </span>
                                </div>
                                <div className="grid grid-cols-3 gap-2 text-sm">
                                    <div>
                                        <p className="text-[var(--foreground-secondary)]">Tokens</p>
                                        <p className="font-mono">{data.total_tokens.toLocaleString()}</p>
                                    </div>
                                    <div>
                                        <p className="text-[var(--foreground-secondary)]">Cost</p>
                                        <p className="font-mono">{formatCost(data.total_cost)}</p>
                                    </div>
                                    <div>
                                        <p className="text-[var(--foreground-secondary)]">Avg Time</p>
                                        <p className="font-mono">{formatDuration(data.avg_duration_ms)}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recent Traces */}
            <div className="glass-card p-4">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold">Recent Traces</h3>
                    <button
                        onClick={fetchData}
                        className="btn-secondary flex items-center gap-2 text-sm"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Refresh
                    </button>
                </div>

                {traces.length === 0 ? (
                    <div className="text-center py-8 text-[var(--foreground-secondary)]">
                        <Layers className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>No traces yet. Make a chat query to see traces.</p>
                    </div>
                ) : (
                    <div className="space-y-2">
                        {traces.map((trace) => (
                            <div
                                key={trace.id}
                                className="bg-[var(--background-tertiary)] rounded-xl p-3 hover:bg-[var(--background-secondary)] transition-colors cursor-pointer"
                                onClick={() => setSelectedTrace(selectedTrace === trace.id ? null : trace.id)}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-2 h-2 rounded-full ${trace.status === 'success' ? 'bg-green-400' :
                                                trace.status === 'error' ? 'bg-red-400' : 'bg-yellow-400'
                                            }`} />
                                        <span className="font-medium">{trace.name}</span>
                                        <span className="text-sm text-[var(--foreground-secondary)]">
                                            {trace.span_count} spans
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-4 text-sm">
                                        {trace.total_tokens && (
                                            <span className="text-[var(--foreground-secondary)]">
                                                {trace.total_tokens.toLocaleString()} tokens
                                            </span>
                                        )}
                                        <span className="font-mono text-green-400">
                                            {formatDuration(trace.duration_ms)}
                                        </span>
                                        <span className="text-[var(--foreground-secondary)]">
                                            {new Date(trace.start_time).toLocaleTimeString()}
                                        </span>
                                    </div>
                                </div>

                                {selectedTrace === trace.id && (
                                    <div className="mt-3 pt-3 border-t border-[var(--glass-border)] text-sm">
                                        {trace.input_summary && (
                                            <div className="mb-2">
                                                <span className="text-[var(--foreground-secondary)]">Input: </span>
                                                <span>{trace.input_summary}</span>
                                            </div>
                                        )}
                                        {trace.output_summary && (
                                            <div>
                                                <span className="text-[var(--foreground-secondary)]">Output: </span>
                                                <span>{trace.output_summary}</span>
                                            </div>
                                        )}
                                        <div className="mt-2 text-xs text-[var(--foreground-secondary)]">
                                            Trace ID: {trace.id}
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
