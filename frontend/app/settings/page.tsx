'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Settings as SettingsIcon,
    Database,
    HardDrive,
    Cpu,
    CheckCircle,
    XCircle,
    RefreshCw,
    Trash2,
    Eye,
    ChevronDown,
    ChevronUp,
    FileText,
    AlertTriangle,
    Info,
    PlayCircle,
    Table,
    Layers,
    GraduationCap,
    MessageSquare,
    Upload,
    Search,
    Brain,
    Zap,
    ArrowRight,
    ArrowDown,
    Sparkles,
    ToggleLeft,
    ToggleRight,
} from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Diagnostics {
    database: {
        total_users: number;
        total_transactions: number;
        total_documents: number;
        processed_documents: number;
        total_chat_messages: number;
    };
    vector_store: {
        collection_name: string;
        total_documents: number;
        embedding_dimension: number;
    };
    statements_directory: {
        path: string;
        exists: boolean;
        pdf_count: number;
    };
    configuration: {
        embedding_model: string;
        chroma_path: string;
        openai_configured: boolean;
    };
}

interface DataSample {
    total_count: number;
    sample_count: number;
    sample: Array<{
        id: string;
        document?: string;
        metadata?: Record<string, any>;
        date?: string;
        merchant?: string;
        amount?: number;
        category?: string;
        source_file?: string;
    }>;
    error?: string;
    purpose?: string;
}

// LLM Provider types
interface ProviderInfo {
    name: string;
    available: boolean;
    active: boolean;
    model: string;
}

interface ProvidersResponse {
    providers: ProviderInfo[];
    active_provider: string | null;
}

async function getDiagnostics(): Promise<Diagnostics> {
    const res = await fetch(`${API_URL}/api/settings/diagnostics`);
    if (!res.ok) throw new Error('Failed to fetch diagnostics');
    return res.json();
}

async function getVectorSample(limit: number = 50): Promise<DataSample> {
    const res = await fetch(`${API_URL}/api/settings/vector-db/sample?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch vector sample');
    return res.json();
}

async function getDatabaseSample(limit: number = 50): Promise<DataSample> {
    const res = await fetch(`${API_URL}/api/settings/database/transactions?limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch database sample');
    return res.json();
}

async function resetVectorDb(): Promise<{ success: boolean; message?: string; error?: string }> {
    const res = await fetch(`${API_URL}/api/settings/vector-db/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset vector DB');
    return res.json();
}

async function resetDatabase(): Promise<{ success: boolean; message?: string; error?: string }> {
    const res = await fetch(`${API_URL}/api/settings/database/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset database');
    return res.json();
}

async function reprocessDocuments(): Promise<any> {
    const res = await fetch(`${API_URL}/api/settings/reprocess`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reprocess documents');
    return res.json();
}

async function getProviders(): Promise<ProvidersResponse> {
    const res = await fetch(`${API_URL}/api/settings/providers`);
    if (!res.ok) throw new Error('Failed to fetch providers');
    return res.json();
}

async function switchProvider(provider: string): Promise<{ success: boolean; message: string; active_provider: string; model: string }> {
    const res = await fetch(`${API_URL}/api/settings/providers/switch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
    });
    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to switch provider');
    }
    return res.json();
}

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState<'overview' | 'database' | 'vector' | 'ai-model' | 'tutorial'>('overview');
    const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());
    const queryClient = useQueryClient();


    const { data: diagnostics, isLoading: loadingDiagnostics, refetch: refetchDiagnostics } = useQuery({
        queryKey: ['diagnostics'],
        queryFn: getDiagnostics,
        refetchInterval: 10000,
    });

    const { data: vectorSample, isLoading: loadingVector, refetch: refetchVector } = useQuery({
        queryKey: ['vectorSample'],
        queryFn: () => getVectorSample(50),
        enabled: activeTab === 'vector',
    });

    const { data: dbSample, isLoading: loadingDb, refetch: refetchDb } = useQuery({
        queryKey: ['dbSample'],
        queryFn: () => getDatabaseSample(50),
        enabled: activeTab === 'database',
    });

    const resetVectorMutation = useMutation({
        mutationFn: resetVectorDb,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['diagnostics'] });
            queryClient.invalidateQueries({ queryKey: ['vectorSample'] });
        },
    });

    const resetDbMutation = useMutation({
        mutationFn: resetDatabase,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['diagnostics'] });
            queryClient.invalidateQueries({ queryKey: ['dbSample'] });
        },
    });

    const reprocessMutation = useMutation({
        mutationFn: reprocessDocuments,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['diagnostics'] });
            queryClient.invalidateQueries({ queryKey: ['vectorSample'] });
            queryClient.invalidateQueries({ queryKey: ['dbSample'] });
        },
    });

    // LLM Provider queries
    const { data: providersData, isLoading: loadingProviders, refetch: refetchProviders } = useQuery({
        queryKey: ['providers'],
        queryFn: getProviders,
        enabled: activeTab === 'ai-model' || activeTab === 'overview',
    });

    const switchProviderMutation = useMutation({
        mutationFn: switchProvider,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['providers'] });
        },
    });

    const toggleExpanded = (index: number) => {
        const newExpanded = new Set(expandedItems);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            newExpanded.add(index);
        }
        setExpandedItems(newExpanded);
    };

    return (
        <div className="space-y-8 fade-in">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">Settings & Diagnostics</h1>
                    <p className="text-[var(--foreground-secondary)] mt-1">
                        System status, data management, and configuration
                    </p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => reprocessMutation.mutate()}
                        disabled={reprocessMutation.isPending}
                        className="btn-primary inline-flex items-center gap-2"
                    >
                        <PlayCircle className="w-4 h-4" />
                        {reprocessMutation.isPending ? 'Processing...' : 'Reprocess All'}
                    </button>
                    <button
                        onClick={() => refetchDiagnostics()}
                        className="btn-secondary inline-flex items-center gap-2"
                    >
                        <RefreshCw className="w-4 h-4" />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-2 border-b border-[var(--glass-border)] overflow-x-auto">
                {[
                    { id: 'overview', label: 'Overview', icon: SettingsIcon },
                    { id: 'ai-model', label: 'AI Model', icon: Sparkles },
                    { id: 'database', label: 'SQL Database', icon: Table },
                    { id: 'vector', label: 'Vector Store', icon: Layers },
                    { id: 'tutorial', label: 'How It Works', icon: GraduationCap },
                ].map((tab) => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={`px-4 py-3 flex items-center gap-2 text-sm font-medium transition-all
                            ${activeTab === tab.id
                                ? 'border-b-2 border-[var(--accent)] text-[var(--accent)]'
                                : 'text-[var(--foreground-secondary)] hover:text-[var(--foreground)]'
                            }`}
                    >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                    </button>
                ))}
            </div>

            {loadingDiagnostics ? (
                <div className="flex items-center justify-center h-64">
                    <div className="spinner" />
                </div>
            ) : diagnostics ? (
                <>
                    {/* Overview Tab */}
                    {activeTab === 'overview' && (
                        <>
                            {/* Status Cards */}
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                {/* Database Stats */}
                                <div className="glass-card p-6">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                                            <Database className="w-5 h-5 text-white" />
                                        </div>
                                        <h3 className="font-semibold">SQL Database</h3>
                                    </div>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Transactions</span>
                                            <span className="font-medium">{diagnostics.database.total_transactions}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Documents</span>
                                            <span className="font-medium">{diagnostics.database.total_documents}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Processed</span>
                                            <span className="font-medium">{diagnostics.database.processed_documents}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Vector Store Stats */}
                                <div className="glass-card p-6">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center">
                                            <Cpu className="w-5 h-5 text-white" />
                                        </div>
                                        <h3 className="font-semibold">Vector Store</h3>
                                    </div>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Embeddings</span>
                                            <span className="font-medium">{diagnostics.vector_store.total_documents}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Dimension</span>
                                            <span className="font-medium">{diagnostics.vector_store.embedding_dimension}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Collection</span>
                                            <span className="font-medium text-xs">{diagnostics.vector_store.collection_name}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Statements Directory */}
                                <div className="glass-card p-6">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center">
                                            <FileText className="w-5 h-5 text-white" />
                                        </div>
                                        <h3 className="font-semibold">Statements</h3>
                                    </div>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">PDF Files</span>
                                            <span className="font-medium">{diagnostics.statements_directory.pdf_count}</span>
                                        </div>
                                        <div className="flex justify-between items-center">
                                            <span className="text-[var(--foreground-secondary)]">Directory</span>
                                            {diagnostics.statements_directory.exists ? (
                                                <CheckCircle className="w-4 h-4 text-green-500" />
                                            ) : (
                                                <XCircle className="w-4 h-4 text-red-500" />
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {/* Configuration */}
                                <div className="glass-card p-6">
                                    <div className="flex items-center gap-3 mb-4">
                                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center">
                                            <SettingsIcon className="w-5 h-5 text-white" />
                                        </div>
                                        <h3 className="font-semibold">Configuration</h3>
                                    </div>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between items-center">
                                            <span className="text-[var(--foreground-secondary)]">OpenAI</span>
                                            {diagnostics.configuration.openai_configured ? (
                                                <CheckCircle className="w-4 h-4 text-green-500" />
                                            ) : (
                                                <XCircle className="w-4 h-4 text-red-500" />
                                            )}
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-[var(--foreground-secondary)]">Model</span>
                                            <span className="font-medium text-xs truncate max-w-[120px]" title={diagnostics.configuration.embedding_model}>
                                                {diagnostics.configuration.embedding_model.split('/').pop()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Why Two Databases? Explanation */}
                            <div className="glass-card p-6">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center flex-shrink-0">
                                        <Info className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold mb-2">Why Two Databases?</h3>
                                        <div className="text-sm text-[var(--foreground-secondary)] space-y-3">
                                            <div>
                                                <span className="font-medium text-blue-400">SQL Database (SQLite)</span>
                                                <p className="mt-1">Stores structured transaction data for fast queries, filtering, and aggregation.
                                                    Used for: dashboard stats, spending by category, date range queries, exporting data.</p>
                                            </div>
                                            <div>
                                                <span className="font-medium text-purple-400">Vector Store (ChromaDB)</span>
                                                <p className="mt-1">Stores AI embeddings (384-dimensional vectors) for semantic search during RAG.
                                                    Used for: AI chat, finding similar transactions by meaning (e.g., "grocery spending" finds Kroger, Walmart, etc.)</p>
                                            </div>
                                            <p className="text-xs opacity-75 italic">
                                                Both are synced: uploading a PDF extracts transactions → saves to SQL → generates embeddings → saves to Vector Store.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Paths and Configuration */}
                            <div className="glass-card p-6">
                                <h2 className="text-xl font-semibold mb-4">Paths & Configuration</h2>
                                <div className="space-y-3 text-sm">
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[var(--foreground-secondary)]">Statements Directory</span>
                                        <code className="bg-[var(--background-secondary)] px-3 py-2 rounded text-xs break-all">
                                            {diagnostics.statements_directory.path}
                                        </code>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[var(--foreground-secondary)]">ChromaDB Path</span>
                                        <code className="bg-[var(--background-secondary)] px-3 py-2 rounded text-xs break-all">
                                            {diagnostics.configuration.chroma_path}
                                        </code>
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <span className="text-[var(--foreground-secondary)]">Embedding Model</span>
                                        <code className="bg-[var(--background-secondary)] px-3 py-2 rounded text-xs break-all">
                                            {diagnostics.configuration.embedding_model}
                                        </code>
                                    </div>
                                </div>
                            </div>
                        </>
                    )}

                    {/* Database Tab */}
                    {activeTab === 'database' && (
                        <div className="space-y-6">
                            <div className="glass-card p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h2 className="text-xl font-semibold">SQL Database Transactions</h2>
                                        <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                            Structured data for queries, filtering, and analytics
                                        </p>
                                    </div>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => refetchDb()}
                                            className="btn-secondary inline-flex items-center gap-2"
                                        >
                                            <RefreshCw className="w-4 h-4" />
                                            Refresh
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (confirm('Delete all transactions, documents, and chat history? This cannot be undone.')) {
                                                    resetDbMutation.mutate();
                                                }
                                            }}
                                            disabled={resetDbMutation.isPending}
                                            className="btn-secondary inline-flex items-center gap-2 text-red-400 hover:text-red-300"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                            Reset Database
                                        </button>
                                    </div>
                                </div>

                                {resetDbMutation.isSuccess && (
                                    <div className="mb-4 p-3 rounded-lg bg-green-500/20 text-green-400 text-sm">
                                        ✓ Database reset successfully!
                                    </div>
                                )}

                                {loadingDb ? (
                                    <div className="flex items-center justify-center py-8">
                                        <div className="spinner" />
                                    </div>
                                ) : dbSample?.error ? (
                                    <div className="p-4 rounded-lg bg-red-500/20 text-red-400">
                                        <AlertTriangle className="w-5 h-5 inline mr-2" />
                                        Error: {dbSample.error}
                                    </div>
                                ) : dbSample?.sample.length === 0 ? (
                                    <div className="text-center py-8 text-[var(--foreground-secondary)]">
                                        <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                        <p>No transactions in database</p>
                                        <p className="text-sm mt-1">Upload and process statements to add transactions</p>
                                    </div>
                                ) : (
                                    <>
                                        <div className="text-sm text-[var(--foreground-secondary)] mb-4">
                                            Showing {dbSample?.sample_count} of {dbSample?.total_count} transactions
                                        </div>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-sm">
                                                <thead>
                                                    <tr className="border-b border-[var(--glass-border)]">
                                                        <th className="text-left py-2 px-3 text-[var(--foreground-secondary)]">Date</th>
                                                        <th className="text-left py-2 px-3 text-[var(--foreground-secondary)]">Merchant</th>
                                                        <th className="text-right py-2 px-3 text-[var(--foreground-secondary)]">Amount</th>
                                                        <th className="text-left py-2 px-3 text-[var(--foreground-secondary)]">Category</th>
                                                        <th className="text-left py-2 px-3 text-[var(--foreground-secondary)]">Source</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {dbSample?.sample.map((t, i) => (
                                                        <tr key={t.id} className="border-b border-[var(--glass-border)]/50 hover:bg-[var(--background-secondary)]">
                                                            <td className="py-2 px-3 whitespace-nowrap">{t.date?.split('T')[0]}</td>
                                                            <td className="py-2 px-3 max-w-[200px] truncate" title={t.merchant}>{t.merchant}</td>
                                                            <td className="py-2 px-3 text-right font-medium">${t.amount?.toFixed(2)}</td>
                                                            <td className="py-2 px-3">
                                                                <span className="px-2 py-1 rounded-full text-xs bg-[var(--accent)]/20 text-[var(--accent)]">
                                                                    {t.category || 'Uncategorized'}
                                                                </span>
                                                            </td>
                                                            <td className="py-2 px-3 text-xs text-[var(--foreground-secondary)] max-w-[150px] truncate">
                                                                {t.source_file}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Vector Store Tab */}
                    {activeTab === 'vector' && (
                        <div className="space-y-6">
                            <div className="glass-card p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <h2 className="text-xl font-semibold">Vector Store Embeddings</h2>
                                        <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                            AI embeddings for semantic search during RAG chat
                                        </p>
                                    </div>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => refetchVector()}
                                            className="btn-secondary inline-flex items-center gap-2"
                                        >
                                            <RefreshCw className="w-4 h-4" />
                                            Refresh
                                        </button>
                                        <button
                                            onClick={() => {
                                                if (confirm('Delete all embeddings from vector database? You will need to reprocess documents.')) {
                                                    resetVectorMutation.mutate();
                                                }
                                            }}
                                            disabled={resetVectorMutation.isPending}
                                            className="btn-secondary inline-flex items-center gap-2 text-red-400 hover:text-red-300"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                            Reset Vector DB
                                        </button>
                                    </div>
                                </div>

                                {resetVectorMutation.isSuccess && (
                                    <div className="mb-4 p-3 rounded-lg bg-green-500/20 text-green-400 text-sm">
                                        ✓ Vector database reset successfully!
                                    </div>
                                )}

                                {loadingVector ? (
                                    <div className="flex items-center justify-center py-8">
                                        <div className="spinner" />
                                    </div>
                                ) : vectorSample?.error ? (
                                    <div className="p-4 rounded-lg bg-red-500/20 text-red-400">
                                        <AlertTriangle className="w-5 h-5 inline mr-2" />
                                        Error: {vectorSample.error}
                                    </div>
                                ) : vectorSample?.sample.length === 0 ? (
                                    <div className="text-center py-8 text-[var(--foreground-secondary)]">
                                        <Cpu className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                        <p>No embeddings in vector database</p>
                                        <p className="text-sm mt-1">Process statements to generate embeddings</p>
                                    </div>
                                ) : (
                                    <>
                                        <div className="text-sm text-[var(--foreground-secondary)] mb-4">
                                            Showing {vectorSample?.sample_count} of {vectorSample?.total_count} embeddings
                                        </div>
                                        <div className="space-y-2 max-h-[500px] overflow-y-auto">
                                            {vectorSample?.sample.map((item, index) => (
                                                <div key={item.id} className="bg-[var(--background-secondary)] rounded-lg p-4">
                                                    <button
                                                        onClick={() => toggleExpanded(index)}
                                                        className="w-full flex items-center justify-between text-left"
                                                    >
                                                        <div className="flex-1 min-w-0">
                                                            <div className="font-medium text-sm truncate">
                                                                {item.metadata?.merchant || 'Unknown Merchant'}
                                                            </div>
                                                            <div className="text-xs text-[var(--foreground-secondary)]">
                                                                {item.metadata?.date} • ${item.metadata?.amount} • {item.metadata?.category}
                                                            </div>
                                                        </div>
                                                        {expandedItems.has(index) ? (
                                                            <ChevronUp className="w-4 h-4 flex-shrink-0" />
                                                        ) : (
                                                            <ChevronDown className="w-4 h-4 flex-shrink-0" />
                                                        )}
                                                    </button>
                                                    {expandedItems.has(index) && (
                                                        <div className="mt-3 pt-3 border-t border-[var(--glass-border)] text-sm">
                                                            <div className="mb-2">
                                                                <span className="text-[var(--foreground-secondary)]">Embedded Document:</span>
                                                                <p className="mt-1 text-xs bg-[var(--background)] p-2 rounded">
                                                                    {item.document}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <span className="text-[var(--foreground-secondary)]">Metadata:</span>
                                                                <pre className="mt-1 text-xs bg-[var(--background)] p-2 rounded overflow-x-auto">
                                                                    {JSON.stringify(item.metadata, null, 2)}
                                                                </pre>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </>
                                )}
                            </div>
                        </div>
                    )}

                    {/* AI Model Tab */}
                    {activeTab === 'ai-model' && (
                        <div className="space-y-6">
                            {/* Model Switch Card */}
                            <div className="glass-card p-6">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                                        <Sparkles className="w-6 h-6 text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-semibold">AI Model Provider</h2>
                                        <p className="text-sm text-[var(--foreground-secondary)]">
                                            Switch between OpenAI and Google Gemini models for AI chat
                                        </p>
                                    </div>
                                </div>

                                {loadingProviders ? (
                                    <div className="flex items-center justify-center py-8">
                                        <div className="spinner" />
                                    </div>
                                ) : providersData?.providers.length === 0 ? (
                                    <div className="p-4 rounded-lg bg-yellow-500/20 text-yellow-400">
                                        <AlertTriangle className="w-5 h-5 inline mr-2" />
                                        No LLM providers configured. Please set OPENAI_API_KEY or GEMINI_API_KEY in your .env file.
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {providersData?.providers.map((provider) => (
                                            <div
                                                key={provider.name}
                                                className={`p-5 rounded-xl border-2 transition-all cursor-pointer ${provider.active
                                                        ? 'border-[var(--accent)] bg-[var(--accent)]/10'
                                                        : provider.available
                                                            ? 'border-[var(--glass-border)] hover:border-[var(--accent)]/50'
                                                            : 'border-[var(--glass-border)] opacity-50 cursor-not-allowed'
                                                    }`}
                                                onClick={() => {
                                                    if (provider.available && !provider.active && !switchProviderMutation.isPending) {
                                                        switchProviderMutation.mutate(provider.name);
                                                    }
                                                }}
                                            >
                                                <div className="flex items-center justify-between mb-3">
                                                    <div className="flex items-center gap-3">
                                                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${provider.name === 'openai'
                                                                ? 'bg-gradient-to-br from-emerald-500 to-teal-600'
                                                                : 'bg-gradient-to-br from-blue-500 to-indigo-600'
                                                            }`}>
                                                            <Brain className="w-5 h-5 text-white" />
                                                        </div>
                                                        <div>
                                                            <h3 className="font-semibold capitalize">{provider.name}</h3>
                                                            <p className="text-xs text-[var(--foreground-secondary)]">
                                                                {provider.model}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    {provider.active ? (
                                                        <div className="flex items-center gap-2 text-green-400">
                                                            <CheckCircle className="w-5 h-5" />
                                                            <span className="text-sm font-medium">Active</span>
                                                        </div>
                                                    ) : provider.available ? (
                                                        <button
                                                            className="btn-secondary text-sm py-1 px-3"
                                                            disabled={switchProviderMutation.isPending}
                                                        >
                                                            {switchProviderMutation.isPending ? 'Switching...' : 'Switch'}
                                                        </button>
                                                    ) : (
                                                        <div className="flex items-center gap-2 text-red-400">
                                                            <XCircle className="w-5 h-5" />
                                                            <span className="text-sm">Not Configured</span>
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="text-xs text-[var(--foreground-secondary)]">
                                                    {provider.name === 'openai' ? (
                                                        <p>OpenAI GPT models - excellent for complex reasoning and nuanced responses</p>
                                                    ) : (
                                                        <p>Google Gemini - fast, cost-effective with strong multi-modal capabilities</p>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}

                                {switchProviderMutation.isSuccess && (
                                    <div className="mt-4 p-3 rounded-lg bg-green-500/20 text-green-400 text-sm">
                                        ✓ Successfully switched to {switchProviderMutation.data?.active_provider}!
                                    </div>
                                )}

                                {switchProviderMutation.isError && (
                                    <div className="mt-4 p-3 rounded-lg bg-red-500/20 text-red-400 text-sm">
                                        ✗ Error: {(switchProviderMutation.error as Error)?.message}
                                    </div>
                                )}
                            </div>

                            {/* MCP Information */}
                            <div className="glass-card p-6">
                                <div className="flex items-start gap-4">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-cyan-600 flex items-center justify-center flex-shrink-0">
                                        <Info className="w-5 h-5 text-white" />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold mb-2">MCP-Inspired Model Switching</h3>
                                        <div className="text-sm text-[var(--foreground-secondary)] space-y-3">
                                            <p>
                                                This feature is inspired by Anthropic's <strong>Model Context Protocol (MCP)</strong> -
                                                an open standard for AI applications to connect with external systems and switch between different LLM providers.
                                            </p>
                                            <div>
                                                <span className="font-medium text-green-400">Benefits:</span>
                                                <ul className="mt-1 ml-4 list-disc space-y-1">
                                                    <li>Switch models without restarting the app</li>
                                                    <li>Compare responses from different providers</li>
                                                    <li>Fall back to an alternative if one provider is unavailable</li>
                                                    <li>Optimize for cost vs quality based on your needs</li>
                                                </ul>
                                            </div>
                                            <p className="text-xs opacity-75 italic">
                                                Configure providers by adding OPENAI_API_KEY and/or GEMINI_API_KEY to your .env file.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Tutorial Tab */}
                    {activeTab === 'tutorial' && (
                        <div className="space-y-8">
                            {/* Introduction */}
                            <div className="glass-card p-6">
                                <div className="flex items-start gap-4">
                                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                                        <GraduationCap className="w-6 h-6 text-white" />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-bold mb-2">How This App Works</h2>
                                        <p className="text-[var(--foreground-secondary)]">
                                            This Personal Finance Planner uses modern AI and RAG (Retrieval-Augmented Generation) to help you
                                            understand your spending. Below is a detailed explanation of the technical architecture.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Flow 1: Document Processing */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <Upload className="w-5 h-5 text-green-400" />
                                    1. Document Upload & Processing
                                </h3>
                                <div className="bg-[var(--background-secondary)] rounded-xl p-6">
                                    <div className="flex flex-col md:flex-row items-stretch gap-4">
                                        {/* Step 1 */}
                                        <div className="flex-1 p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="w-8 h-8 rounded-full bg-green-500/20 text-green-400 flex items-center justify-center text-sm font-bold mb-2">1</div>
                                            <h4 className="font-medium mb-1">PDF Upload</h4>
                                            <p className="text-xs text-[var(--foreground-secondary)]">User uploads credit card statement PDF</p>
                                        </div>
                                        <ArrowRight className="w-6 h-6 text-[var(--foreground-secondary)] self-center hidden md:block" />
                                        <ArrowDown className="w-6 h-6 text-[var(--foreground-secondary)] self-center md:hidden" />

                                        {/* Step 2 */}
                                        <div className="flex-1 p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-sm font-bold mb-2">2</div>
                                            <h4 className="font-medium mb-1">PDF Parsing</h4>
                                            <p className="text-xs text-[var(--foreground-secondary)]">PDFPlumber + PyMuPDF extract transactions from PDF</p>
                                        </div>
                                        <ArrowRight className="w-6 h-6 text-[var(--foreground-secondary)] self-center hidden md:block" />
                                        <ArrowDown className="w-6 h-6 text-[var(--foreground-secondary)] self-center md:hidden" />

                                        {/* Step 3 */}
                                        <div className="flex-1 p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="w-8 h-8 rounded-full bg-purple-500/20 text-purple-400 flex items-center justify-center text-sm font-bold mb-2">3</div>
                                            <h4 className="font-medium mb-1">Dual Storage</h4>
                                            <p className="text-xs text-[var(--foreground-secondary)]">Save to SQL DB + Generate embeddings for Vector DB</p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Flow 2: AI Chat (RAG) */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <MessageSquare className="w-5 h-5 text-blue-400" />
                                    2. AI Chat - RAG (Retrieval-Augmented Generation)
                                </h3>
                                <p className="text-sm text-[var(--foreground-secondary)] mb-4">
                                    When you ask a question in AI Chat, here's what happens behind the scenes:
                                </p>

                                <div className="bg-[var(--background-secondary)] rounded-xl p-6 space-y-6">
                                    {/* Step 1: User Question */}
                                    <div className="flex gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                                            <MessageSquare className="w-6 h-6 text-blue-400" />
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-medium text-blue-400">Step 1: Your Question</h4>
                                            <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                                Example: "What did I spend on food last month?"
                                            </p>
                                        </div>
                                    </div>

                                    <div className="flex justify-center">
                                        <ArrowDown className="w-6 h-6 text-[var(--foreground-secondary)]" />
                                    </div>

                                    {/* Step 2: Vector Search */}
                                    <div className="flex gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center flex-shrink-0">
                                            <Search className="w-6 h-6 text-purple-400" />
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-medium text-purple-400">Step 2: Semantic Search (Vector DB)</h4>
                                            <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                                Your question is converted to a 384-dimensional vector using the embedding model.
                                                ChromaDB finds the most similar transactions by comparing vectors.
                                            </p>
                                            <div className="mt-2 p-3 bg-[var(--background)] rounded-lg">
                                                <code className="text-xs">
                                                    "food" → finds: KROGER, UBER EATS, IN-N-OUT, CHIPOTLE...
                                                </code>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex justify-center">
                                        <ArrowDown className="w-6 h-6 text-[var(--foreground-secondary)]" />
                                    </div>

                                    {/* Step 3: Context Building */}
                                    <div className="flex gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center flex-shrink-0">
                                            <FileText className="w-6 h-6 text-orange-400" />
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-medium text-orange-400">Step 3: Context Building</h4>
                                            <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                                Retrieved transactions are formatted into context:
                                            </p>
                                            <div className="mt-2 p-3 bg-[var(--background)] rounded-lg text-xs font-mono">
                                                <div>1. Oct 15, 2025 - KROGER - $45.32 - Groceries</div>
                                                <div>2. Oct 12, 2025 - UBER EATS - $28.50 - Food</div>
                                                <div>3. Oct 10, 2025 - IN-N-OUT - $12.99 - Food</div>
                                                <div className="text-[var(--foreground-secondary)]">...</div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex justify-center">
                                        <ArrowDown className="w-6 h-6 text-[var(--foreground-secondary)]" />
                                    </div>

                                    {/* Step 4: LLM Generation */}
                                    <div className="flex gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center flex-shrink-0">
                                            <Brain className="w-6 h-6 text-green-400" />
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-medium text-green-400">Step 4: LLM Answer Generation</h4>
                                            <p className="text-sm text-[var(--foreground-secondary)] mt-1">
                                                OpenAI GPT-4 receives your question + the transaction context and generates a natural language answer:
                                            </p>
                                            <div className="mt-2 p-3 bg-[var(--background)] rounded-lg">
                                                <p className="text-sm italic">
                                                    "Based on your transactions, you spent $156.82 on food last month across 8 transactions.
                                                    Your top food merchants were KROGER ($45.32), UBER EATS ($28.50), and IN-N-OUT ($12.99)..."
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Flow 3: Analytics */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <Zap className="w-5 h-5 text-yellow-400" />
                                    3. Dashboard & Analytics
                                </h3>
                                <p className="text-sm text-[var(--foreground-secondary)] mb-4">
                                    The dashboard uses a different path - direct SQL queries for speed:
                                </p>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)] border border-[var(--glass-border)]">
                                        <h4 className="font-medium text-blue-400 mb-2">PostgreSQL/DuckDB</h4>
                                        <ul className="text-sm text-[var(--foreground-secondary)] space-y-1">
                                            <li>• Total spending calculations</li>
                                            <li>• Category breakdowns</li>
                                            <li>• Monthly trends</li>
                                            <li>• Top merchants</li>
                                            <li>• Recurring subscriptions</li>
                                        </ul>
                                    </div>
                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)] border border-[var(--glass-border)]">
                                        <h4 className="font-medium text-purple-400 mb-2">Vector DB (for AI only)</h4>
                                        <ul className="text-sm text-[var(--foreground-secondary)] space-y-1">
                                            <li>• Semantic search</li>
                                            <li>• AI chat context retrieval</li>
                                            <li>• AI-generated insights</li>
                                            <li>• Finding similar transactions</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Tech Stack */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <Layers className="w-5 h-5 text-cyan-400" />
                                    4. Technology Stack
                                </h3>

                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-[var(--glass-border)]">
                                                <th className="text-left py-3 px-4 text-[var(--foreground-secondary)]">Component</th>
                                                <th className="text-left py-3 px-4 text-[var(--foreground-secondary)]">Technology</th>
                                                <th className="text-left py-3 px-4 text-[var(--foreground-secondary)]">Purpose</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-[var(--glass-border)]">
                                            <tr>
                                                <td className="py-3 px-4 font-medium">Frontend</td>
                                                <td className="py-3 px-4"><code className="text-blue-400">Next.js 14</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">React framework with App Router</td>
                                            </tr>
                                            <tr>
                                                <td className="py-3 px-4 font-medium">Backend</td>
                                                <td className="py-3 px-4"><code className="text-green-400">FastAPI</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">Python async API server</td>
                                            </tr>
                                            <tr>
                                                <td className="py-3 px-4 font-medium">SQL Database</td>
                                                <td className="py-3 px-4"><code className="text-cyan-400">PostgreSQL + DuckDB</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">Structured data storage & analytics</td>
                                            </tr>
                                            <tr>
                                                <td className="py-3 px-4 font-medium">Vector Store</td>
                                                <td className="py-3 px-4"><code className="text-purple-400">ChromaDB</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">Embedding storage for semantic search</td>
                                            </tr>
                                            <tr>
                                                <td className="py-3 px-4 font-medium">Embedding Model</td>
                                                <td className="py-3 px-4"><code className="text-orange-400">all-MiniLM-L6-v2</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">Local 384-dim sentence embeddings</td>
                                            </tr>
                                            <tr>
                                                <td className="py-3 px-4 font-medium">LLM</td>
                                                <td className="py-3 px-4"><code className="text-pink-400">OpenAI GPT-4o</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">Answer generation & insights</td>
                                            </tr>
                                            <tr>
                                                <td className="py-3 px-4 font-medium">PDF Extraction</td>
                                                <td className="py-3 px-4"><code className="text-yellow-400">PDFPlumber + Tesseract</code></td>
                                                <td className="py-3 px-4 text-[var(--foreground-secondary)]">Parse PDFs with OCR fallback for scanned docs</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Key Concepts */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <Info className="w-5 h-5 text-indigo-400" />
                                    5. Key Concepts Explained
                                </h3>

                                <div className="space-y-4">
                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)]">
                                        <h4 className="font-medium text-indigo-400 mb-2">What is RAG?</h4>
                                        <p className="text-sm text-[var(--foreground-secondary)]">
                                            <strong>Retrieval-Augmented Generation</strong> combines search with AI generation.
                                            Instead of the LLM making up answers, it first retrieves relevant data from your transactions,
                                            then generates an answer based on that real data. This makes responses accurate and grounded.
                                        </p>
                                    </div>

                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)]">
                                        <h4 className="font-medium text-purple-400 mb-2">What are Embeddings?</h4>
                                        <p className="text-sm text-[var(--foreground-secondary)]">
                                            Embeddings are numerical representations (vectors) of text that capture meaning.
                                            Similar concepts have similar vectors. This allows finding "UBER EATS" when searching for "food delivery"
                                            even though the words are different.
                                        </p>
                                    </div>

                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)]">
                                        <h4 className="font-medium text-blue-400 mb-2">Why Two Databases?</h4>
                                        <p className="text-sm text-[var(--foreground-secondary)]">
                                            <strong>SQL</strong> is fast for structured queries (sum, filter, group by).
                                            <strong> Vector DB</strong> is designed for similarity search across embeddings.
                                            Each is optimized for different tasks, so we use both.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* RAGAS Quality Evaluation */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <Search className="w-5 h-5 text-cyan-400" />
                                    6. RAGAS - RAG Quality Evaluation
                                </h3>
                                <p className="text-sm text-[var(--foreground-secondary)] mb-4">
                                    RAGAS (Retrieval-Augmented Generation Assessment) is a framework for evaluating the quality of RAG systems.
                                    It answers: "Is my RAG system giving good answers?"
                                </p>

                                <div className="bg-[var(--background-secondary)] rounded-xl p-6 space-y-4">
                                    <h4 className="font-medium mb-3">RAGAS Metrics Explained</h4>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="w-3 h-3 rounded-full bg-green-400"></div>
                                                <h5 className="font-medium text-green-400">Faithfulness</h5>
                                            </div>
                                            <p className="text-xs text-[var(--foreground-secondary)]">
                                                <strong>Is the answer grounded in the context?</strong><br />
                                                Measures if claims in the answer can be inferred from retrieved transactions.
                                                High score = no hallucinations.
                                            </p>
                                            <div className="mt-2 text-xs">
                                                <span className="text-[var(--foreground-secondary)]">Example: </span>
                                                <span className="italic">"You spent $45 at Kroger" ✓ (if context shows Kroger $45)</span>
                                            </div>
                                        </div>

                                        <div className="p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="w-3 h-3 rounded-full bg-blue-400"></div>
                                                <h5 className="font-medium text-blue-400">Answer Relevancy</h5>
                                            </div>
                                            <p className="text-xs text-[var(--foreground-secondary)]">
                                                <strong>Does the answer address the question?</strong><br />
                                                Penalizes answers that are off-topic or incomplete.
                                                High score = direct, complete response.
                                            </p>
                                            <div className="mt-2 text-xs">
                                                <span className="text-[var(--foreground-secondary)]">Example: </span>
                                                <span className="italic">Q: "Food spending?" A: "You spent $156 on food" ✓</span>
                                            </div>
                                        </div>

                                        <div className="p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="w-3 h-3 rounded-full bg-purple-400"></div>
                                                <h5 className="font-medium text-purple-400">Context Precision</h5>
                                            </div>
                                            <p className="text-xs text-[var(--foreground-secondary)]">
                                                <strong>Are retrieved documents relevant?</strong><br />
                                                Measures the signal-to-noise ratio of retrieval.
                                                High score = good embedding/search quality.
                                            </p>
                                            <div className="mt-2 text-xs">
                                                <span className="text-[var(--foreground-secondary)]">Example: </span>
                                                <span className="italic">"Food" query finds Kroger, Uber Eats (not Netflix) ✓</span>
                                            </div>
                                        </div>

                                        <div className="p-4 rounded-lg bg-[var(--glass-bg)] border border-[var(--glass-border)]">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="w-3 h-3 rounded-full bg-orange-400"></div>
                                                <h5 className="font-medium text-orange-400">Context Recall</h5>
                                            </div>
                                            <p className="text-xs text-[var(--foreground-secondary)]">
                                                <strong>Were all needed facts retrieved?</strong><br />
                                                Requires ground truth answer. Checks if retrieval missed important data.
                                                High score = comprehensive retrieval.
                                            </p>
                                            <div className="mt-2 text-xs">
                                                <span className="text-[var(--foreground-secondary)]">Example: </span>
                                                <span className="italic">Found all 8 food transactions, not just 3 ✓</span>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="mt-4 p-3 rounded-lg bg-[var(--background)] border border-cyan-500/30">
                                        <h5 className="text-sm font-medium text-cyan-400 mb-2">Score Interpretation</h5>
                                        <div className="flex gap-4 text-xs">
                                            <span><span className="text-green-400">●</span> &gt;90% Excellent</span>
                                            <span><span className="text-yellow-400">●</span> 70-90% Good</span>
                                            <span><span className="text-orange-400">●</span> 50-70% Fair</span>
                                            <span><span className="text-red-400">●</span> &lt;50% Poor</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Observability & Metrics */}
                            <div className="glass-card p-6">
                                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                                    <Zap className="w-5 h-5 text-yellow-400" />
                                    7. Observability & Performance Metrics
                                </h3>
                                <p className="text-sm text-[var(--foreground-secondary)] mb-4">
                                    The app tracks performance metrics across all flows to help you understand system health and identify bottlenecks.
                                </p>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)]">
                                        <h4 className="font-medium text-yellow-400 mb-3">Operational Metrics</h4>
                                        <ul className="text-sm text-[var(--foreground-secondary)] space-y-2">
                                            <li className="flex items-start gap-2">
                                                <span className="text-green-400">✓</span>
                                                <span><strong>Latency</strong> - p50, p95, p99 response times per flow</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-green-400">✓</span>
                                                <span><strong>Throughput</strong> - Requests processed per flow</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-green-400">✓</span>
                                                <span><strong>Error Rate</strong> - Failures and exceptions tracked</span>
                                            </li>
                                            <li className="flex items-start gap-2">
                                                <span className="text-green-400">✓</span>
                                                <span><strong>Counters</strong> - Embeddings generated, queries processed</span>
                                            </li>
                                        </ul>
                                    </div>

                                    <div className="p-4 rounded-lg bg-[var(--background-secondary)]">
                                        <h4 className="font-medium text-cyan-400 mb-3">Tracked Flows</h4>
                                        <ul className="text-sm text-[var(--foreground-secondary)] space-y-2">
                                            <li><span className="text-blue-400">Document Processing</span> - PDF parsing, extraction</li>
                                            <li><span className="text-purple-400">Embedding</span> - Text to vector conversion</li>
                                            <li><span className="text-green-400">Vector Store</span> - Add, search, delete operations</li>
                                            <li><span className="text-orange-400">RAG Pipeline</span> - Retrieval + LLM generation</li>
                                            <li><span className="text-pink-400">Analytics</span> - DuckDB query performance</li>
                                        </ul>
                                    </div>
                                </div>

                                <div className="mt-4 p-3 rounded-lg bg-[var(--background)] text-sm">
                                    <span className="text-[var(--foreground-secondary)]">View metrics at: </span>
                                    <a href="/metrics" className="text-cyan-400 hover:underline font-medium">Metrics Dashboard →</a>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            ) : (
                <div className="glass-card p-8 text-center">
                    <AlertTriangle className="w-12 h-12 mx-auto mb-4 text-yellow-500" />
                    <p>Failed to load diagnostics. Is the backend running?</p>
                </div>
            )}
        </div>
    );
}
