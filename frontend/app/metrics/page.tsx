'use client';

import { useEffect, useState } from 'react';
import {
    Activity,
    Clock,
    Database,
    FileText,
    MessageSquare,
    Search,
    AlertCircle,
    CheckCircle,
    RefreshCw,
    Play,
    Zap,
    TrendingUp,
    Server,
} from 'lucide-react';

interface FlowMetrics {
    total_requests: number;
    total_errors: number;
    error_rate: number;
    avg_latency_ms?: number;
    p50_latency_ms?: number;
    p95_latency_ms?: number;
    p99_latency_ms?: number;
    counters: Record<string, number>;
    gauges: Record<string, number>;
    histograms: Record<string, { avg: number; min: number; max: number; count: number }>;
}

interface MetricsSummary {
    summary: {
        uptime_seconds: number;
        start_time: string;
        total_requests: number;
        total_errors: number;
        error_rate: number;
    };
    flows: Record<string, FlowMetrics>;
}

interface BenchmarkResult {
    status: string;
    query?: string;
    elapsed_ms?: number;
    metrics?: Record<string, number>;
    error?: string;
    message?: string;
}

const flowIcons: Record<string, React.ComponentType<{ className?: string }>> = {
    document_processing: FileText,
    embedding: Zap,
    vector_store: Database,
    rag: MessageSquare,
    analytics: TrendingUp,
    api: Server,
};

const flowLabels: Record<string, string> = {
    document_processing: 'Document Processing',
    embedding: 'Embeddings',
    vector_store: 'Vector Store',
    rag: 'RAG Pipeline',
    analytics: 'Analytics',
    api: 'API',
};

export default function MetricsPage() {
    const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResult | null>(null);
    const [benchmarking, setBenchmarking] = useState(false);
    const [autoRefresh, setAutoRefresh] = useState(false);

    const fetchMetrics = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/metrics/summary');
            if (!response.ok) throw new Error('Failed to fetch metrics');
            const data = await response.json();
            setMetrics(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load metrics');
        } finally {
            setLoading(false);
        }
    };

    const runBenchmark = async () => {
        setBenchmarking(true);
        try {
            const response = await fetch('http://localhost:8000/api/metrics/benchmark/run', {
                method: 'POST',
            });
            const data = await response.json();
            setBenchmarkResult(data);
        } catch (err) {
            setBenchmarkResult({
                status: 'error',
                error: err instanceof Error ? err.message : 'Benchmark failed',
            });
        } finally {
            setBenchmarking(false);
        }
    };

    useEffect(() => {
        fetchMetrics();
    }, []);

    useEffect(() => {
        if (autoRefresh) {
            const interval = setInterval(fetchMetrics, 5000);
            return () => clearInterval(interval);
        }
    }, [autoRefresh]);

    const formatUptime = (seconds: number) => {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        return `${hours}h ${minutes}m ${secs}s`;
    };

    const formatLatency = (ms?: number) => {
        if (ms === undefined) return '-';
        if (ms < 1) return '<1ms';
        if (ms < 1000) return `${Math.round(ms)}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <RefreshCw className="w-8 h-8 animate-spin text-[var(--accent-primary)]" />
            </div>
        );
    }

    if (error) {
        return (
            <div className="glass-card p-6">
                <div className="flex items-center gap-3 text-red-400">
                    <AlertCircle className="w-6 h-6" />
                    <p>{error}</p>
                </div>
                <button
                    onClick={fetchMetrics}
                    className="mt-4 btn-primary"
                >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">System Metrics</h1>
                    <p className="text-[var(--foreground-secondary)] mt-1">
                        Monitor performance and observability across all flows
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoRefresh}
                            onChange={(e) => setAutoRefresh(e.target.checked)}
                            className="w-4 h-4 rounded"
                        />
                        <span className="text-sm">Auto-refresh (5s)</span>
                    </label>
                    <button
                        onClick={fetchMetrics}
                        className="btn-secondary flex items-center gap-2"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-blue-500/20 to-blue-600/20">
                            <Clock className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Uptime</p>
                            <p className="text-xl font-bold">
                                {formatUptime(metrics?.summary.uptime_seconds || 0)}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-green-500/20 to-green-600/20">
                            <Activity className="w-6 h-6 text-green-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Total Requests</p>
                            <p className="text-xl font-bold">
                                {metrics?.summary.total_requests.toLocaleString() || 0}
                            </p>
                        </div>
                    </div>
                </div>

                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-red-500/20 to-red-600/20">
                            <AlertCircle className="w-6 h-6 text-red-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Error Rate</p>
                            <p className="text-xl font-bold">
                                {((metrics?.summary.error_rate || 0) * 100).toFixed(2)}%
                            </p>
                        </div>
                    </div>
                </div>

                <div className="glass-card p-4">
                    <div className="flex items-center gap-3">
                        <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-purple-600/20">
                            <CheckCircle className="w-6 h-6 text-purple-400" />
                        </div>
                        <div>
                            <p className="text-sm text-[var(--foreground-secondary)]">Status</p>
                            <p className="text-xl font-bold text-green-400">Healthy</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Flow Metrics */}
            <div className="glass-card p-6">
                <h2 className="text-xl font-bold mb-4">Flow Performance</h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {metrics?.flows &&
                        Object.entries(metrics.flows)
                            .filter(([_, data]) => data.total_requests > 0)
                            .map(([flowName, flowData]) => {
                                const Icon = flowIcons[flowName] || Activity;
                                const label = flowLabels[flowName] || flowName;

                                return (
                                    <div key={flowName} className="bg-[var(--background-tertiary)] rounded-xl p-4">
                                        <div className="flex items-center gap-3 mb-4">
                                            <div className="p-2 rounded-lg bg-[var(--accent-primary)]/20">
                                                <Icon className="w-5 h-5 text-[var(--accent-primary)]" />
                                            </div>
                                            <div>
                                                <h3 className="font-semibold">{label}</h3>
                                                <p className="text-sm text-[var(--foreground-secondary)]">
                                                    {flowData.total_requests} requests
                                                </p>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-3 gap-2 text-sm">
                                            <div>
                                                <p className="text-[var(--foreground-secondary)]">Avg</p>
                                                <p className="font-mono font-bold text-green-400">
                                                    {formatLatency(flowData.avg_latency_ms)}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-[var(--foreground-secondary)]">P95</p>
                                                <p className="font-mono font-bold text-yellow-400">
                                                    {formatLatency(flowData.p95_latency_ms)}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-[var(--foreground-secondary)]">P99</p>
                                                <p className="font-mono font-bold text-orange-400">
                                                    {formatLatency(flowData.p99_latency_ms)}
                                                </p>
                                            </div>
                                        </div>

                                        {flowData.error_rate > 0 && (
                                            <div className="mt-2 text-sm text-red-400">
                                                Error rate: {(flowData.error_rate * 100).toFixed(2)}%
                                            </div>
                                        )}

                                        {/* Counters */}
                                        {Object.keys(flowData.counters).length > 0 && (
                                            <div className="mt-3 pt-3 border-t border-[var(--glass-border)]">
                                                <div className="grid grid-cols-2 gap-2 text-xs">
                                                    {Object.entries(flowData.counters).slice(0, 4).map(([key, value]) => (
                                                        <div key={key} className="flex justify-between">
                                                            <span className="text-[var(--foreground-secondary)]">
                                                                {key.replace(/_/g, ' ')}
                                                            </span>
                                                            <span className="font-mono">{value}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                );
                            })}

                    {(!metrics?.flows ||
                        Object.values(metrics.flows).every((f) => f.total_requests === 0)) && (
                            <div className="col-span-2 text-center py-8 text-[var(--foreground-secondary)]">
                                <Activity className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                <p>No metrics collected yet. Start using the application to see data.</p>
                            </div>
                        )}
                </div>
            </div>

            {/* Benchmark Section */}
            <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold">Run Benchmark</h2>
                    <button
                        onClick={runBenchmark}
                        disabled={benchmarking}
                        className="btn-primary flex items-center gap-2"
                    >
                        {benchmarking ? (
                            <>
                                <RefreshCw className="w-4 h-4 animate-spin" />
                                Running...
                            </>
                        ) : (
                            <>
                                <Play className="w-4 h-4" />
                                Run Benchmark
                            </>
                        )}
                    </button>
                </div>

                <p className="text-sm text-[var(--foreground-secondary)] mb-4">
                    Run a sample RAG query to measure current performance.
                </p>

                {benchmarkResult && (
                    <div
                        className={`rounded-xl p-4 ${benchmarkResult.status === 'success'
                            ? 'bg-green-500/10 border border-green-500/30'
                            : 'bg-red-500/10 border border-red-500/30'
                            }`}
                    >
                        {benchmarkResult.status === 'success' ? (
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-green-400">
                                    <CheckCircle className="w-5 h-5" />
                                    <span className="font-semibold">{benchmarkResult.message}</span>
                                </div>
                                {benchmarkResult.metrics && (
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
                                        <div>
                                            <p className="text-[var(--foreground-secondary)]">Total Time</p>
                                            <p className="font-mono font-bold">
                                                {benchmarkResult.metrics.total_time_ms?.toFixed(2)}ms
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[var(--foreground-secondary)]">Retrieval</p>
                                            <p className="font-mono font-bold">
                                                {benchmarkResult.metrics.retrieval_ms?.toFixed(2)}ms
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[var(--foreground-secondary)]">LLM Generation</p>
                                            <p className="font-mono font-bold">
                                                {benchmarkResult.metrics.llm_generation_ms?.toFixed(2)}ms
                                            </p>
                                        </div>
                                        <div>
                                            <p className="text-[var(--foreground-secondary)]">Sources</p>
                                            <p className="font-mono font-bold">
                                                {benchmarkResult.metrics.source_count}
                                            </p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="flex items-center gap-2 text-red-400">
                                <AlertCircle className="w-5 h-5" />
                                <span>{benchmarkResult.error}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* RAGAS Quality Evaluation Section */}
            <RAGASEvaluationSection />
        </div>
    );
}

// RAGAS Evaluation Component
function RAGASEvaluationSection() {
    const [question, setQuestion] = useState('');
    const [evaluating, setEvaluating] = useState(false);
    const [result, setResult] = useState<{
        question: string;
        answer: string;
        sources_count: number;
        rag_metrics?: Record<string, number>;
        ragas_evaluation?: {
            faithfulness?: number;
            calculation_accuracy?: number;
            answer_relevancy?: number;
            context_precision?: number;
            context_recall?: number;
            overall_score?: number;
        };
        ragas_available: boolean;
    } | null>(null);
    const [aggregateScores, setAggregateScores] = useState<{
        sample_count: number;
        avg_faithfulness?: number;
        avg_calculation_accuracy?: number;
        avg_answer_relevancy?: number;
        avg_context_precision?: number;
        avg_overall_score?: number;
    } | null>(null);

    useEffect(() => {
        fetchAggregateScores();
    }, []);

    const fetchAggregateScores = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/evaluation/aggregate');
            const data = await response.json();
            setAggregateScores(data);
        } catch (err) {
            console.error('Failed to fetch aggregate scores:', err);
        }
    };

    const runEvaluation = async () => {
        if (!question.trim()) return;
        setEvaluating(true);
        setResult(null); // Clear previous result

        // Create abort controller for timeout (2 min for RAGAS)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);

        try {
            const response = await fetch('http://localhost:8000/api/evaluation/live-query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question }),
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            setResult(data);
            fetchAggregateScores(); // Refresh aggregate after new evaluation
        } catch (err) {
            console.error('Evaluation failed:', err);
            if (err instanceof Error && err.name === 'AbortError') {
                alert('Evaluation timed out after 2 minutes. RAGAS evaluation requires multiple LLM API calls.');
            } else {
                alert(`Evaluation failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
            }
        } finally {
            setEvaluating(false);
        }
    };

    const getScoreColor = (score?: number) => {
        if (score === undefined || score === null) return 'text-gray-400';
        if (score >= 0.9) return 'text-green-400';
        if (score >= 0.7) return 'text-yellow-400';
        if (score >= 0.5) return 'text-orange-400';
        return 'text-red-400';
    };

    const formatScore = (score?: number) => {
        if (score === undefined || score === null) return '-';
        return (score * 100).toFixed(1) + '%';
    };

    return (
        <div className="glass-card p-6">
            <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-teal-500/20">
                    <Search className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                    <h2 className="text-xl font-bold">RAGAS Quality Evaluation</h2>
                    <p className="text-sm text-[var(--foreground-secondary)]">
                        Evaluate RAG answer quality with Faithfulness, Relevancy, and Precision
                    </p>
                </div>
            </div>

            {/* Aggregate Scores */}
            {aggregateScores && aggregateScores.sample_count > 0 && (
                <div className="bg-[var(--background-tertiary)] rounded-xl p-4 mb-4">
                    <p className="text-sm text-[var(--foreground-secondary)] mb-3">
                        Aggregate scores ({aggregateScores.sample_count} samples)
                    </p>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Faithfulness</p>
                            <p className={`text-xl font-bold ${getScoreColor(aggregateScores.avg_faithfulness)}`}>
                                {formatScore(aggregateScores.avg_faithfulness)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Calc Accuracy</p>
                            <p className={`text-xl font-bold ${getScoreColor(aggregateScores.avg_calculation_accuracy)}`}>
                                {formatScore(aggregateScores.avg_calculation_accuracy)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Relevancy</p>
                            <p className={`text-xl font-bold ${getScoreColor(aggregateScores.avg_answer_relevancy)}`}>
                                {formatScore(aggregateScores.avg_answer_relevancy)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Precision</p>
                            <p className={`text-xl font-bold ${getScoreColor(aggregateScores.avg_context_precision)}`}>
                                {formatScore(aggregateScores.avg_context_precision)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Overall</p>
                            <p className={`text-xl font-bold ${getScoreColor(aggregateScores.avg_overall_score)}`}>
                                {formatScore(aggregateScores.avg_overall_score)}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Question Input */}
            <div className="flex gap-2 mb-4">
                <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Enter a question to evaluate..."
                    className="flex-1 bg-[var(--background-tertiary)] border border-[var(--glass-border)] rounded-xl px-4 py-2 focus:outline-none focus:border-[var(--accent-primary)]"
                    onKeyDown={(e) => e.key === 'Enter' && runEvaluation()}
                />
                <button
                    onClick={runEvaluation}
                    disabled={evaluating || !question.trim()}
                    className="btn-primary flex items-center gap-2"
                >
                    {evaluating ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                        <Play className="w-4 h-4" />
                    )}
                    Evaluate
                </button>
            </div>

            {/* Results */}
            {result && (
                <div className="space-y-4">
                    {/* Answer */}
                    <div className="bg-[var(--background-tertiary)] rounded-xl p-4">
                        <p className="text-sm text-[var(--foreground-secondary)] mb-2">Answer</p>
                        <p className="text-sm">{result.answer}</p>
                        <p className="text-xs text-[var(--foreground-secondary)] mt-2">
                            {result.sources_count} sources retrieved
                        </p>
                    </div>

                    {/* RAGAS Scores */}
                    {result.ragas_evaluation ? (
                        <div className="bg-gradient-to-r from-cyan-500/10 to-teal-500/10 border border-cyan-500/30 rounded-xl p-4">
                            <p className="font-semibold mb-3 text-cyan-400">RAGAS Quality Scores</p>
                            <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                                <div>
                                    <p className="text-xs text-[var(--foreground-secondary)]">Faithfulness</p>
                                    <p className={`text-lg font-bold ${getScoreColor(result.ragas_evaluation.faithfulness)}`}>
                                        {formatScore(result.ragas_evaluation.faithfulness)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-[var(--foreground-secondary)]">Calc Accuracy</p>
                                    <p className={`text-lg font-bold ${getScoreColor(result.ragas_evaluation.calculation_accuracy)}`}>
                                        {formatScore(result.ragas_evaluation.calculation_accuracy)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-[var(--foreground-secondary)]">Relevancy</p>
                                    <p className={`text-lg font-bold ${getScoreColor(result.ragas_evaluation.answer_relevancy)}`}>
                                        {formatScore(result.ragas_evaluation.answer_relevancy)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-[var(--foreground-secondary)]">Precision</p>
                                    <p className={`text-lg font-bold ${getScoreColor(result.ragas_evaluation.context_precision)}`}>
                                        {formatScore(result.ragas_evaluation.context_precision)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-[var(--foreground-secondary)]">Recall</p>
                                    <p className={`text-lg font-bold ${getScoreColor(result.ragas_evaluation.context_recall)}`}>
                                        {formatScore(result.ragas_evaluation.context_recall)}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-[var(--foreground-secondary)]">Overall</p>
                                    <p className={`text-lg font-bold ${getScoreColor(result.ragas_evaluation.overall_score)}`}>
                                        {formatScore(result.ragas_evaluation.overall_score)}
                                    </p>
                                </div>
                            </div>
                        </div>
                    ) : (
                        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
                            <div className="flex items-center gap-2 text-yellow-400">
                                <AlertCircle className="w-5 h-5" />
                                <span>
                                    RAGAS not available. Install with: <code className="bg-[var(--background-tertiary)] px-2 py-1 rounded">pip install ragas datasets</code>
                                </span>
                            </div>
                        </div>
                    )}

                    {/* Performance Metrics */}
                    {result.rag_metrics && (
                        <div className="bg-[var(--background-tertiary)] rounded-xl p-4">
                            <p className="text-sm text-[var(--foreground-secondary)] mb-2">Performance</p>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                                <div>
                                    <span className="text-[var(--foreground-secondary)]">Total: </span>
                                    <span className="font-mono font-bold">{result.rag_metrics.total_time_ms?.toFixed(0)}ms</span>
                                </div>
                                <div>
                                    <span className="text-[var(--foreground-secondary)]">Retrieval: </span>
                                    <span className="font-mono font-bold">{result.rag_metrics.retrieval_ms?.toFixed(0)}ms</span>
                                </div>
                                <div>
                                    <span className="text-[var(--foreground-secondary)]">LLM: </span>
                                    <span className="font-mono font-bold">{result.rag_metrics.llm_generation_ms?.toFixed(0)}ms</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
