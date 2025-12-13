'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Send,
    Sparkles,
    User,
    Bot,
    Trash2,
    RefreshCw,
    ChevronDown,
    MessageSquare,
    Loader2,
    Settings,
} from 'lucide-react';
import { sendChatMessage, getChatHistory, clearChatHistory, getProviders, type ProvidersResponse } from '@/utils/api';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: any[];
    model_info?: {
        provider: string;
        model: string;
        latency_ms?: number;
    };
    created_at: string;
}

const suggestedQuestions = [
    "What are my top spending categories this year?",
    "How much did I spend on groceries last month?",
    "What recurring subscriptions am I paying for?",
    "Where can I reduce my expenses?",
    "Show me my travel expenses",
    "Compare my spending this month vs last month",
];

export default function ChatPage() {
    const [input, setInput] = useState('');
    const [localMessages, setLocalMessages] = useState<Message[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);
    const queryClient = useQueryClient();

    const { data: history, isLoading } = useQuery({
        queryKey: ['chatHistory'],
        queryFn: getChatHistory,
    });

    const { data: providersData } = useQuery({
        queryKey: ['providers'],
        queryFn: getProviders,
    });

    const activeProvider = providersData?.providers.find(p => p.active);

    const chatMutation = useMutation({
        mutationFn: sendChatMessage,
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['chatHistory'] });
        },
    });

    const clearMutation = useMutation({
        mutationFn: clearChatHistory,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['chatHistory'] });
            setLocalMessages([]);
        },
    });

    // Scroll to bottom on new messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history, localMessages, chatMutation.isPending]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || chatMutation.isPending) return;

        const userMessage = input.trim();
        setInput('');

        // Add optimistic user message
        const tempUserMsg: Message = {
            id: `temp-${Date.now()}`,
            role: 'user',
            content: userMessage,
            created_at: new Date().toISOString(),
        };
        setLocalMessages((prev) => [...prev, tempUserMsg]);

        chatMutation.mutate(userMessage, {
            onSuccess: () => {
                setLocalMessages([]);
            },
        });
    };

    const handleSuggestion = (question: string) => {
        setInput(question);
        inputRef.current?.focus();
    };

    const allMessages = [...(history || []), ...localMessages];

    return (
        <div className="flex flex-col h-[calc(100vh-4rem)] fade-in">
            {/* Header */}
            <div className="flex items-center justify-between pb-4 border-b border-[var(--glass-border)]">
                <div>
                    <h1 className="text-3xl font-bold gradient-text">AI Financial Advisor</h1>
                    <div className="flex items-center gap-2 mt-1">
                        <p className="text-[var(--foreground-secondary)]">
                            Ask questions about your spending and get intelligent insights
                        </p>
                        {activeProvider && (
                            <a
                                href="/settings"
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-[var(--accent)]/20 text-[var(--accent)] hover:bg-[var(--accent)]/30 transition-colors"
                                title="Click to change model"
                            >
                                <Settings className="w-3 h-3" />
                                {activeProvider.name.toUpperCase()}: {activeProvider.model}
                            </a>
                        )}
                    </div>
                </div>
                <button
                    onClick={() => clearMutation.mutate()}
                    disabled={clearMutation.isPending || allMessages.length === 0}
                    className="btn-secondary inline-flex items-center gap-2 disabled:opacity-50"
                >
                    <Trash2 className="w-4 h-4" />
                    Clear History
                </button>
            </div>

            {/* Chat Area */}
            <div className="flex-1 overflow-y-auto py-6 space-y-6">
                {isLoading ? (
                    <div className="flex items-center justify-center h-full">
                        <div className="spinner" />
                    </div>
                ) : allMessages.length === 0 ? (
                    /* Welcome Screen */
                    <div className="flex flex-col items-center justify-center h-full text-center px-4">
                        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center mb-6 pulse-glow">
                            <Sparkles className="w-10 h-10 text-white" />
                        </div>
                        <h2 className="text-2xl font-bold mb-2">Welcome to FinanceAI</h2>
                        <p className="text-[var(--foreground-secondary)] max-w-lg mb-8">
                            I can analyze your financial data and answer questions about your spending patterns,
                            help you find savings opportunities, and provide personalized insights.
                        </p>

                        {/* Suggested Questions */}
                        <div className="w-full max-w-2xl">
                            <p className="text-sm text-[var(--foreground-secondary)] mb-4">
                                Try asking me:
                            </p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {suggestedQuestions.map((question, index) => (
                                    <button
                                        key={index}
                                        onClick={() => handleSuggestion(question)}
                                        className="glass-card p-4 text-left hover-glow text-sm"
                                    >
                                        <MessageSquare className="w-4 h-4 text-[var(--accent-primary)] mb-2" />
                                        {question}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                ) : (
                    /* Messages */
                    <div className="space-y-6 px-4">
                        {allMessages.map((message: Message, index: number) => (
                            <div
                                key={message.id || index}
                                className={`flex gap-4 ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                {message.role === 'assistant' && (
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center flex-shrink-0">
                                        <Bot className="w-5 h-5 text-white" />
                                    </div>
                                )}

                                <div
                                    className={`max-w-[70%] ${message.role === 'user'
                                        ? 'bg-[var(--accent-primary)] rounded-2xl rounded-tr-md'
                                        : 'glass-card rounded-2xl rounded-tl-md'
                                        } p-4`}
                                >
                                    <p className="whitespace-pre-wrap">{message.content}</p>

                                    {/* Sources */}
                                    {message.role === 'assistant' && message.sources && message.sources.length > 0 && (
                                        <div className="mt-4 pt-4 border-t border-[var(--glass-border)]">
                                            <p className="text-xs text-[var(--foreground-secondary)] mb-2">
                                                Sources ({message.sources.length} transactions)
                                            </p>
                                            <div className="flex flex-wrap gap-2">
                                                {message.sources.slice(0, 3).map((source: any, i: number) => (
                                                    <span
                                                        key={i}
                                                        className="text-xs px-2 py-1 rounded-full bg-[var(--background-secondary)]"
                                                    >
                                                        {source.merchant} • ${source.amount}
                                                    </span>
                                                ))}
                                                {message.sources.length > 3 && (
                                                    <span className="text-xs px-2 py-1 text-[var(--foreground-secondary)]">
                                                        +{message.sources.length - 3} more
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {message.role === 'user' && (
                                    <div className="w-10 h-10 rounded-xl bg-[var(--accent-secondary)] flex items-center justify-center flex-shrink-0">
                                        <User className="w-5 h-5 text-white" />
                                    </div>
                                )}
                            </div>
                        ))}

                        {/* Loading indicator */}
                        {chatMutation.isPending && (
                            <div className="flex gap-4 justify-start">
                                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center flex-shrink-0">
                                    <Bot className="w-5 h-5 text-white" />
                                </div>
                                <div className="glass-card rounded-2xl rounded-tl-md p-4">
                                    <div className="flex items-center gap-2">
                                        <Loader2 className="w-4 h-4 animate-spin text-[var(--accent-primary)]" />
                                        <span className="text-[var(--foreground-secondary)]">Analyzing your data...</span>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            {/* Input Area */}
            <div className="pt-4 border-t border-[var(--glass-border)]">
                <form onSubmit={handleSubmit} className="relative">
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about your finances..."
                        className="input-field pr-14 py-4 text-lg"
                        disabled={chatMutation.isPending}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || chatMutation.isPending}
                        className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-gradient-to-r from-[var(--gradient-start)] to-[var(--gradient-end)] flex items-center justify-center disabled:opacity-50 hover:scale-105 transition-transform"
                    >
                        <Send className="w-5 h-5 text-white" />
                    </button>
                </form>

                <p className="text-xs text-center text-[var(--foreground-secondary)] mt-3">
                    Your data stays local. Only your question and relevant context are sent to the AI.
                </p>
            </div>
        </div>
    );
}
