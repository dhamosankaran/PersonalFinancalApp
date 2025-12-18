'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Brain,
    PlayCircle,
    RefreshCw,
    Sparkles,
    AlertTriangle,
    Info,
    TrendingUp,
    CheckCircle,
    Loader2,
    ChevronDown,
    ChevronUp,
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Types
interface AgentInfo {
    id: string;
    name: string;
    description: string;
    icon: string;
}

interface AgentInsight {
    type: 'warning' | 'info' | 'metric';
    title: string;
    detail: string;
    agent?: string;
}

interface AgentResult {
    agent_id: string;
    agent_name: string;
    status: 'success' | 'error' | 'no_data';
    summary: string;
    insights: AgentInsight[];
    recommendations: string[];
    data?: Record<string, any>;
    llm_analysis?: string;
}

interface AllAgentsResult {
    summary: string;
    agents: Record<string, AgentResult>;
    combined_insights: AgentInsight[];
    combined_recommendations: { agent: string; recommendation: string }[];
    stats: {
        total_agents: number;
        successful: number;
        total_insights: number;
        total_recommendations: number;
    };
}

// API calls
async function listAgents(): Promise<{ agents: AgentInfo[]; count: number }> {
    const res = await fetch(`${API_BASE}/api/agents`);
    if (!res.ok) throw new Error('Failed to list agents');
    return res.json();
}

async function runAgent(agentId: string): Promise<AgentResult> {
    const res = await fetch(`${API_BASE}/api/agents/${agentId}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: {} }),
    });
    if (!res.ok) throw new Error('Failed to run agent');
    return res.json();
}

async function runAllAgents(): Promise<AllAgentsResult> {
    const res = await fetch(`${API_BASE}/api/agents/insights`);
    if (!res.ok) throw new Error('Failed to run all agents');
    return res.json();
}

// Agent icon mapping
const agentIcons: Record<string, string> = {
    budget: '📊',
    subscription: '🔄',
    savings: '💰',
    anomaly: '🚨',
    forecast: '📈',
    goals: '🎯',
};

// Gradient colors for agents
const agentColors: Record<string, string> = {
    budget: 'from-blue-500 to-blue-600',
    subscription: 'from-purple-500 to-purple-600',
    savings: 'from-green-500 to-green-600',
    anomaly: 'from-red-500 to-red-600',
    forecast: 'from-cyan-500 to-cyan-600',
    goals: 'from-orange-500 to-orange-600',
};

export default function AgentsPage() {
    const queryClient = useQueryClient();
    const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
    const [agentResults, setAgentResults] = useState<Record<string, AgentResult>>({});
    const [allResults, setAllResults] = useState<AllAgentsResult | null>(null);
    const [runningAgent, setRunningAgent] = useState<string | null>(null);

    const { data: agentsData, isLoading } = useQuery({
        queryKey: ['agents'],
        queryFn: listAgents,
    });

    const runAgentMutation = useMutation({
        mutationFn: runAgent,
        onSuccess: (result) => {
            setAgentResults((prev) => ({ ...prev, [result.agent_id]: result }));
            setRunningAgent(null);
            setExpandedAgent(result.agent_id);
        },
        onError: () => setRunningAgent(null),
    });

    const runAllMutation = useMutation({
        mutationFn: runAllAgents,
        onSuccess: (result) => {
            setAllResults(result);
            setAgentResults(result.agents);
        },
    });

    const handleRunAgent = (agentId: string) => {
        setRunningAgent(agentId);
        runAgentMutation.mutate(agentId);
    };

    const getInsightIcon = (type: string) => {
        switch (type) {
            case 'warning':
                return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
            case 'metric':
                return <TrendingUp className="w-4 h-4 text-blue-400" />;
            default:
                return <Info className="w-4 h-4 text-cyan-400" />;
        }
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
            </div>
        );
    }

    const agents = agentsData?.agents || [];

    return (
        <div className="space-y-8 fade-in">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">AI Agents</h1>
                    <p className="text-[var(--foreground-secondary)] mt-1">
                        Automated financial analysis powered by AI
                    </p>
                </div>
                <button
                    onClick={() => runAllMutation.mutate()}
                    disabled={runAllMutation.isPending}
                    className="btn-primary inline-flex items-center gap-2"
                >
                    {runAllMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        <Sparkles className="w-4 h-4" />
                    )}
                    {runAllMutation.isPending ? 'Running All...' : 'Run All Agents'}
                </button>
            </div>

            {/* Combined Insights (when Run All is executed) */}
            {allResults && (
                <div className="glass-card p-6">
                    <div className="flex items-center gap-3 mb-4">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                            <Brain className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h2 className="text-xl font-semibold">Combined Insights</h2>
                            <p className="text-sm text-[var(--foreground-secondary)]">
                                {allResults.stats.successful}/{allResults.stats.total_agents} agents ran successfully
                            </p>
                        </div>
                    </div>

                    {/* Top Insights */}
                    <div className="grid gap-3 mb-6">
                        {allResults.combined_insights.slice(0, 6).map((insight, i) => (
                            <div
                                key={i}
                                className={`p-3 rounded-lg border ${insight.type === 'warning'
                                    ? 'bg-yellow-500/10 border-yellow-500/30'
                                    : insight.type === 'metric'
                                        ? 'bg-blue-500/10 border-blue-500/30'
                                        : 'bg-cyan-500/10 border-cyan-500/30'
                                    }`}
                            >
                                <div className="flex items-start gap-3">
                                    {getInsightIcon(insight.type)}
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2">
                                            <span className="font-medium text-sm">{insight.title}</span>
                                            {insight.agent && (
                                                <span className="text-xs bg-[var(--background-secondary)] px-2 py-0.5 rounded-full">
                                                    {insight.agent}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                            {insight.detail}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Top Recommendations */}
                    {allResults.combined_recommendations.length > 0 && (
                        <div>
                            <h3 className="text-sm font-semibold mb-3 text-[var(--foreground-secondary)]">
                                Top Recommendations
                            </h3>
                            <div className="space-y-2">
                                {allResults.combined_recommendations.slice(0, 5).map((rec, i) => (
                                    <div key={i} className="flex items-start gap-2 text-sm">
                                        <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                                        <span>
                                            <span className="text-[var(--foreground-secondary)]">[{rec.agent}]</span>{' '}
                                            {rec.recommendation}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Agent Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {agents.map((agent) => {
                    const result = agentResults[agent.id];
                    const isRunning = runningAgent === agent.id;
                    const isExpanded = expandedAgent === agent.id;
                    const color = agentColors[agent.id] || 'from-gray-500 to-gray-600';

                    return (
                        <div key={agent.id} className="glass-card overflow-hidden">
                            {/* Agent Header */}
                            <div className="p-5">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-3">
                                        <div
                                            className={`w-12 h-12 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center text-2xl`}
                                        >
                                            {agentIcons[agent.id] || '🤖'}
                                        </div>
                                        <div>
                                            <h3 className="font-semibold">{agent.name}</h3>
                                            <p className="text-xs text-[var(--foreground-secondary)] line-clamp-2">
                                                {agent.description}
                                            </p>
                                        </div>
                                    </div>
                                </div>

                                {/* Run Button */}
                                <button
                                    onClick={() => handleRunAgent(agent.id)}
                                    disabled={isRunning}
                                    className={`w-full mt-3 py-2 px-4 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2
                                        ${result?.status === 'success'
                                            ? 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30'
                                            : 'bg-[var(--background-secondary)] hover:bg-[var(--glass-bg)] border border-[var(--glass-border)]'
                                        }`}
                                >
                                    {isRunning ? (
                                        <>
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                            Running...
                                        </>
                                    ) : result ? (
                                        <>
                                            <RefreshCw className="w-4 h-4" />
                                            Run Again
                                        </>
                                    ) : (
                                        <>
                                            <PlayCircle className="w-4 h-4" />
                                            Run Agent
                                        </>
                                    )}
                                </button>

                                {/* Result Summary */}
                                {result && (
                                    <div className="mt-3">
                                        <button
                                            onClick={() => setExpandedAgent(isExpanded ? null : agent.id)}
                                            className="w-full flex items-center justify-between text-sm text-[var(--foreground-secondary)] hover:text-[var(--foreground)]"
                                        >
                                            <span className="truncate">{result.summary}</span>
                                            {isExpanded ? (
                                                <ChevronUp className="w-4 h-4 flex-shrink-0" />
                                            ) : (
                                                <ChevronDown className="w-4 h-4 flex-shrink-0" />
                                            )}
                                        </button>
                                    </div>
                                )}
                            </div>

                            {/* Expanded Results */}
                            {result && isExpanded && (
                                <div className="border-t border-[var(--glass-border)] p-4 bg-[var(--background-secondary)]">
                                    {/* Insights */}
                                    {result.insights.length > 0 && (
                                        <div className="mb-4">
                                            <h4 className="text-xs font-semibold text-[var(--foreground-secondary)] mb-2">
                                                INSIGHTS
                                            </h4>
                                            <div className="space-y-2">
                                                {result.insights.map((insight, i) => (
                                                    <div key={i} className="flex items-start gap-2 text-sm">
                                                        {getInsightIcon(insight.type)}
                                                        <div>
                                                            <span className="font-medium">{insight.title}:</span>{' '}
                                                            <span className="text-[var(--foreground-secondary)]">
                                                                {insight.detail}
                                                            </span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Recommendations */}
                                    {result.recommendations.length > 0 && (
                                        <div>
                                            <h4 className="text-xs font-semibold text-[var(--foreground-secondary)] mb-2">
                                                RECOMMENDATIONS
                                            </h4>
                                            <div className="space-y-1">
                                                {result.recommendations.map((rec, i) => (
                                                    <div key={i} className="flex items-start gap-2 text-sm">
                                                        <CheckCircle className="w-3 h-3 text-green-400 mt-1 flex-shrink-0" />
                                                        <span>{rec}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* LLM Analysis */}
                                    {result.llm_analysis && (
                                        <div className="mt-4 pt-4 border-t border-[var(--glass-border)]">
                                            <h4 className="text-xs font-semibold text-[var(--foreground-secondary)] mb-2 flex items-center gap-2">
                                                <Sparkles className="w-3 h-3 text-violet-400" />
                                                AI ANALYSIS
                                            </h4>
                                            <div className="text-sm text-[var(--foreground-secondary)] whitespace-pre-line bg-[var(--background)] p-3 rounded-lg border border-violet-500/20">
                                                {result.llm_analysis}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Empty State */}
            {agents.length === 0 && (
                <div className="glass-card p-12 text-center">
                    <Brain className="w-16 h-16 text-[var(--foreground-secondary)] mx-auto mb-4" />
                    <h2 className="text-xl font-semibold mb-2">No Agents Available</h2>
                    <p className="text-[var(--foreground-secondary)]">
                        Agents are not configured. Please check backend setup.
                    </p>
                </div>
            )}
        </div>
    );
}
