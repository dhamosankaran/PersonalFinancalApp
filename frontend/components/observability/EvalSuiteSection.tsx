'use client';

import { useEffect, useState } from 'react';
import {
    CheckCircle,
    XCircle,
    Play,
    RefreshCw,
    ClipboardList,
    AlertCircle,
} from 'lucide-react';

interface TestCase {
    id: string;
    question: string;
    category: string;
    description: string;
    min_faithfulness: number;
    min_relevancy: number;
    min_precision: number;
}

interface TestResult {
    test_case_id: string;
    question: string;
    answer: string;
    sources_count: number;
    faithfulness: number | null;
    calculation_accuracy: number | null;
    answer_relevancy: number | null;
    context_precision: number | null;
    overall_score: number | null;
    passed: boolean;
    failure_reason: string | null;
    latency_ms: number;
}

interface SuiteResult {
    run_id: string;
    start_time: string;
    end_time: string;
    duration_seconds: number;
    total_cases: number;
    passed_cases: number;
    failed_cases: number;
    pass_rate: number;
    avg_faithfulness: number | null;
    avg_relevancy: number | null;
    avg_precision: number | null;
    avg_overall: number | null;
    avg_latency_ms: number | null;
    results: TestResult[];
}

export function EvalSuiteSection() {
    const [testCases, setTestCases] = useState<TestCase[]>([]);
    const [loading, setLoading] = useState(true);
    const [running, setRunning] = useState(false);
    const [result, setResult] = useState<SuiteResult | null>(null);
    const [selectedCases, setSelectedCases] = useState<Set<string>>(new Set());

    useEffect(() => {
        fetchTestCases();
    }, []);

    const fetchTestCases = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/evaluation/test-suite');
            const data = await response.json();
            setTestCases(data.test_cases || []);
        } catch (err) {
            console.error('Failed to fetch test cases:', err);
        } finally {
            setLoading(false);
        }
    };

    const runSuite = async () => {
        setRunning(true);
        setResult(null);

        try {
            const body = selectedCases.size > 0
                ? JSON.stringify({ test_case_ids: Array.from(selectedCases) })
                : null;

            const response = await fetch('http://localhost:8000/api/evaluation/test-suite/run', {
                method: 'POST',
                headers: body ? { 'Content-Type': 'application/json' } : undefined,
                body,
            });

            const data = await response.json();
            setResult(data);
        } catch (err) {
            console.error('Failed to run test suite:', err);
        } finally {
            setRunning(false);
        }
    };

    const toggleCase = (id: string) => {
        const newSelected = new Set(selectedCases);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedCases(newSelected);
    };

    const selectAll = () => {
        if (selectedCases.size === testCases.length) {
            setSelectedCases(new Set());
        } else {
            setSelectedCases(new Set(testCases.map(tc => tc.id)));
        }
    };

    const getScoreColor = (score: number | null) => {
        if (score === null) return 'text-gray-400';
        if (score >= 0.9) return 'text-green-400';
        if (score >= 0.7) return 'text-yellow-400';
        if (score >= 0.5) return 'text-orange-400';
        return 'text-red-400';
    };

    const formatScore = (score: number | null) => {
        if (score === null) return '-';
        return (score * 100).toFixed(0) + '%';
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
            {/* Test Cases */}
            <div className="glass-card p-4">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <ClipboardList className="w-5 h-5 text-[var(--accent-primary)]" />
                        <h3 className="font-semibold">Evaluation Test Cases</h3>
                        <span className="text-sm text-[var(--foreground-secondary)]">
                            ({testCases.length} tests)
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={selectAll}
                            className="btn-secondary text-sm"
                        >
                            {selectedCases.size === testCases.length ? 'Deselect All' : 'Select All'}
                        </button>
                        <button
                            onClick={runSuite}
                            disabled={running}
                            className="btn-primary flex items-center gap-2"
                        >
                            {running ? (
                                <>
                                    <RefreshCw className="w-4 h-4 animate-spin" />
                                    Running...
                                </>
                            ) : (
                                <>
                                    <Play className="w-4 h-4" />
                                    Run Suite
                                </>
                            )}
                        </button>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {testCases.map((tc) => (
                        <div
                            key={tc.id}
                            onClick={() => toggleCase(tc.id)}
                            className={`p-3 rounded-xl cursor-pointer transition-colors ${selectedCases.has(tc.id)
                                ? 'bg-[var(--accent-primary)]/20 border border-[var(--accent-primary)]/50'
                                : 'bg-[var(--background-tertiary)] hover:bg-[var(--background-secondary)]'
                                }`}
                        >
                            <div className="flex items-start gap-3">
                                <input
                                    type="checkbox"
                                    checked={selectedCases.has(tc.id)}
                                    onChange={() => { }}
                                    className="mt-1"
                                />
                                <div className="flex-1">
                                    <p className="font-medium text-sm">{tc.question}</p>
                                    <div className="flex items-center gap-2 mt-1 text-xs text-[var(--foreground-secondary)]">
                                        <span className="px-2 py-0.5 rounded-full bg-[var(--background-secondary)]">
                                            {tc.category}
                                        </span>
                                        <span>{tc.description}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Results */}
            {result && (
                <div className="glass-card p-4">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold">Test Results</h3>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <CheckCircle className="w-4 h-4 text-green-400" />
                                <span>{result.passed_cases} passed</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <XCircle className="w-4 h-4 text-red-400" />
                                <span>{result.failed_cases} failed</span>
                            </div>
                            <div className={`text-lg font-bold ${result.pass_rate >= 0.8 ? 'text-green-400' :
                                result.pass_rate >= 0.6 ? 'text-yellow-400' : 'text-red-400'
                                }`}>
                                {(result.pass_rate * 100).toFixed(0)}% Pass Rate
                            </div>
                        </div>
                    </div>

                    {/* Aggregate Scores */}
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4 p-4 bg-[var(--background-tertiary)] rounded-xl">
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Avg Faithfulness</p>
                            <p className={`text-xl font-bold ${getScoreColor(result.avg_faithfulness)}`}>
                                {formatScore(result.avg_faithfulness)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Avg Relevancy</p>
                            <p className={`text-xl font-bold ${getScoreColor(result.avg_relevancy)}`}>
                                {formatScore(result.avg_relevancy)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Avg Precision</p>
                            <p className={`text-xl font-bold ${getScoreColor(result.avg_precision)}`}>
                                {formatScore(result.avg_precision)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Overall</p>
                            <p className={`text-xl font-bold ${getScoreColor(result.avg_overall)}`}>
                                {formatScore(result.avg_overall)}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-[var(--foreground-secondary)]">Avg Latency</p>
                            <p className="text-xl font-bold text-blue-400">
                                {result.avg_latency_ms != null ? result.avg_latency_ms.toFixed(0) : '-'}ms
                            </p>
                        </div>
                    </div>

                    {/* Individual Results */}
                    <div className="space-y-2">
                        {(result.results || []).map((r) => (
                            <div
                                key={r.test_case_id}
                                className={`p-3 rounded-xl ${r.passed
                                    ? 'bg-green-500/10 border border-green-500/30'
                                    : 'bg-red-500/10 border border-red-500/30'
                                    }`}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        {r.passed ? (
                                            <CheckCircle className="w-5 h-5 text-green-400" />
                                        ) : (
                                            <XCircle className="w-5 h-5 text-red-400" />
                                        )}
                                        <span className="font-medium">{r.question}</span>
                                    </div>
                                    <div className="flex items-center gap-4 text-sm">
                                        <span className={getScoreColor(r.faithfulness)}>
                                            F: {formatScore(r.faithfulness)}
                                        </span>
                                        <span className={getScoreColor(r.answer_relevancy)}>
                                            R: {formatScore(r.answer_relevancy)}
                                        </span>
                                        <span className={getScoreColor(r.context_precision)}>
                                            P: {formatScore(r.context_precision)}
                                        </span>
                                        <span className="text-blue-400">{r.latency_ms != null ? r.latency_ms.toFixed(0) : '-'}ms</span>
                                    </div>
                                </div>
                                {r.failure_reason && (
                                    <div className="mt-2 text-sm text-red-400 flex items-center gap-2">
                                        <AlertCircle className="w-4 h-4" />
                                        {r.failure_reason}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    <div className="mt-4 text-sm text-[var(--foreground-secondary)]">
                        Completed in {result.duration_seconds != null ? result.duration_seconds.toFixed(1) : '-'}s at {result.end_time ? new Date(result.end_time).toLocaleTimeString() : '-'}
                    </div>
                </div>
            )}
        </div>
    );
}
