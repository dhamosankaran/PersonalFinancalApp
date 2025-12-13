'use client';

import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    Upload,
    FileText,
    File,
    CheckCircle,
    XCircle,
    Loader2,
    AlertCircle,
    X,
    FolderUp,
} from 'lucide-react';
import { uploadMultipleFiles, getUploadedDocuments } from '@/utils/api';
import { format } from 'date-fns';

interface FileResult {
    filename: string;
    status: 'pending' | 'processed' | 'skipped' | 'failed';
    transaction_count: number;
    error: string | null;
}

interface BatchUploadResult {
    total_files: number;
    processed: number;
    skipped: number;
    failed: number;
    total_transactions: number;
    files: FileResult[];
}

export default function UploadPage() {
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [uploadResult, setUploadResult] = useState<BatchUploadResult | null>(null);
    const queryClient = useQueryClient();

    const { data: documents, isLoading } = useQuery({
        queryKey: ['documents'],
        queryFn: getUploadedDocuments,
    });

    const uploadMutation = useMutation({
        mutationFn: uploadMultipleFiles,
        onSuccess: (data: BatchUploadResult) => {
            setUploadResult(data);
            setSelectedFiles([]);
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            queryClient.invalidateQueries({ queryKey: ['transactions'] });
            queryClient.invalidateQueries({ queryKey: ['monthlySpend'] });
            queryClient.invalidateQueries({ queryKey: ['categoryBreakdown'] });
        },
    });

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    }, []);

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);

        const files = Array.from(e.dataTransfer.files).filter(
            (file) => file.type === 'application/pdf' || file.name.endsWith('.csv')
        );
        if (files.length > 0) {
            setSelectedFiles((prev) => [...prev, ...files]);
            setUploadResult(null);
        }
    }, []);

    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files) {
            const files = Array.from(e.target.files);
            setSelectedFiles((prev) => [...prev, ...files]);
            setUploadResult(null);
        }
        // Reset input so same files can be selected again
        e.target.value = '';
    }, []);

    const removeFile = useCallback((index: number) => {
        setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    }, []);

    const clearAll = useCallback(() => {
        setSelectedFiles([]);
        setUploadResult(null);
    }, []);

    const handleUpload = useCallback(() => {
        if (selectedFiles.length > 0) {
            uploadMutation.mutate(selectedFiles);
        }
    }, [selectedFiles, uploadMutation]);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'processed':
                return <CheckCircle className="w-5 h-5 text-[var(--accent-secondary)]" />;
            case 'skipped':
                return <AlertCircle className="w-5 h-5 text-[var(--accent-tertiary)]" />;
            case 'failed':
                return <XCircle className="w-5 h-5 text-[var(--accent-danger)]" />;
            default:
                return <Loader2 className="w-5 h-5 text-[var(--accent-primary)] animate-spin" />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'processed':
                return 'text-[var(--accent-secondary)]';
            case 'skipped':
                return 'text-[var(--accent-tertiary)]';
            case 'failed':
                return 'text-[var(--accent-danger)]';
            default:
                return 'text-[var(--foreground-secondary)]';
        }
    };

    return (
        <div className="space-y-8 fade-in">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold gradient-text">Upload Statements</h1>
                <p className="text-[var(--foreground-secondary)] mt-1">
                    Upload multiple credit card statements or bank CSV exports at once
                </p>
            </div>

            {/* Upload Zone */}
            <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`relative glass-card p-12 border-2 border-dashed transition-all duration-300 ${isDragging
                    ? 'border-[var(--accent-primary)] bg-[var(--accent-primary)] bg-opacity-5'
                    : 'border-[var(--glass-border)] hover:border-[var(--accent-primary-hover)]'
                    }`}
            >
                <div className="flex flex-col items-center text-center">
                    <div
                        className={`w-20 h-20 rounded-2xl flex items-center justify-center mb-6 transition-all ${isDragging
                            ? 'bg-[var(--accent-primary)] scale-110'
                            : 'bg-gradient-to-br from-[var(--gradient-start)] to-[var(--gradient-end)]'
                            }`}
                    >
                        <FolderUp className="w-10 h-10 text-white" />
                    </div>

                    <h2 className="text-2xl font-semibold mb-2">
                        {isDragging ? 'Drop files here' : 'Drag & drop your statements'}
                    </h2>
                    <p className="text-[var(--foreground-secondary)] mb-6">
                        Select multiple PDFs or CSVs to upload them all at once
                    </p>

                    <label className="btn-primary cursor-pointer inline-flex items-center gap-2">
                        <FileText className="w-5 h-5" />
                        <span>Browse Files</span>
                        <input
                            type="file"
                            className="hidden"
                            accept=".pdf,.csv"
                            multiple
                            onChange={handleFileSelect}
                        />
                    </label>

                    <p className="text-xs text-[var(--foreground-secondary)] mt-4">
                        Maximum file size: 10MB per file • Supports PDF and CSV
                    </p>
                </div>
            </div>

            {/* Selected Files Queue */}
            {selectedFiles.length > 0 && !uploadMutation.isPending && (
                <div className="glass-card p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-semibold">
                            Selected Files ({selectedFiles.length})
                        </h2>
                        <button
                            onClick={clearAll}
                            className="text-sm text-[var(--foreground-secondary)] hover:text-[var(--accent-danger)] transition-colors"
                        >
                            Clear All
                        </button>
                    </div>

                    <div className="space-y-2 mb-6 max-h-64 overflow-y-auto">
                        {selectedFiles.map((file, index) => (
                            <div
                                key={`${file.name}-${index}`}
                                className="flex items-center justify-between p-3 rounded-lg bg-[var(--background)] hover:bg-[var(--glass-bg)] transition-all"
                            >
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 rounded-lg bg-[var(--accent-primary)] bg-opacity-20 flex items-center justify-center">
                                        <FileText className="w-5 h-5 text-[var(--accent-primary)]" />
                                    </div>
                                    <div>
                                        <p className="font-medium truncate max-w-[300px]">{file.name}</p>
                                        <p className="text-xs text-[var(--foreground-secondary)]">
                                            {(file.size / 1024).toFixed(1)} KB
                                        </p>
                                    </div>
                                </div>
                                <button
                                    onClick={() => removeFile(index)}
                                    className="p-2 hover:bg-[var(--accent-danger)] hover:bg-opacity-20 rounded-lg transition-all"
                                >
                                    <X className="w-4 h-4 text-[var(--foreground-secondary)] hover:text-[var(--accent-danger)]" />
                                </button>
                            </div>
                        ))}
                    </div>

                    <button
                        onClick={handleUpload}
                        className="btn-primary w-full flex items-center justify-center gap-2"
                    >
                        <Upload className="w-5 h-5" />
                        Upload {selectedFiles.length} {selectedFiles.length === 1 ? 'File' : 'Files'}
                    </button>
                </div>
            )}

            {/* Upload Progress */}
            {uploadMutation.isPending && (
                <div className="glass-card p-8">
                    <div className="flex flex-col items-center text-center">
                        <Loader2 className="w-16 h-16 text-[var(--accent-primary)] animate-spin mb-6" />
                        <h3 className="text-xl font-semibold mb-2">Processing Statements...</h3>
                        <p className="text-[var(--foreground-secondary)]">
                            Extracting transactions from {selectedFiles.length} files. This may take a moment.
                        </p>
                    </div>
                </div>
            )}

            {/* Upload Results Summary */}
            {uploadResult && (
                <div className="glass-card p-6">
                    <h2 className="text-xl font-semibold mb-4">Upload Results</h2>

                    {/* Summary Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                        <div className="p-4 rounded-xl bg-[var(--background)]">
                            <p className="text-2xl font-bold text-[var(--accent-primary)]">{uploadResult.total_files}</p>
                            <p className="text-sm text-[var(--foreground-secondary)]">Total Files</p>
                        </div>
                        <div className="p-4 rounded-xl bg-[var(--background)]">
                            <p className="text-2xl font-bold text-[var(--accent-secondary)]">{uploadResult.processed}</p>
                            <p className="text-sm text-[var(--foreground-secondary)]">Processed</p>
                        </div>
                        <div className="p-4 rounded-xl bg-[var(--background)]">
                            <p className="text-2xl font-bold text-[var(--accent-tertiary)]">{uploadResult.skipped}</p>
                            <p className="text-sm text-[var(--foreground-secondary)]">Skipped</p>
                        </div>
                        <div className="p-4 rounded-xl bg-[var(--background)]">
                            <p className="text-2xl font-bold gradient-text">{uploadResult.total_transactions}</p>
                            <p className="text-sm text-[var(--foreground-secondary)]">Transactions</p>
                        </div>
                    </div>

                    {/* Per-file Results */}
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                        {uploadResult.files.map((file, index) => (
                            <div
                                key={`${file.filename}-${index}`}
                                className="flex items-center justify-between p-3 rounded-lg bg-[var(--background)]"
                            >
                                <div className="flex items-center gap-3">
                                    {getStatusIcon(file.status)}
                                    <div>
                                        <p className="font-medium">{file.filename}</p>
                                        {file.error && file.status !== 'skipped' && (
                                            <p className="text-xs text-[var(--accent-danger)]">{file.error}</p>
                                        )}
                                    </div>
                                </div>
                                <div className="text-right">
                                    <p className={`font-medium ${getStatusColor(file.status)}`}>
                                        {file.status === 'processed' && `${file.transaction_count} transactions`}
                                        {file.status === 'skipped' && 'Already uploaded'}
                                        {file.status === 'failed' && 'Failed'}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upload Error */}
            {uploadMutation.isError && (
                <div className="glass-card p-4 border border-[var(--accent-danger)] bg-[var(--accent-danger)] bg-opacity-10">
                    <div className="flex items-center gap-3">
                        <XCircle className="w-6 h-6 text-[var(--accent-danger)]" />
                        <div>
                            <p className="font-medium text-[var(--accent-danger)]">Upload Failed</p>
                            <p className="text-sm text-[var(--foreground-secondary)]">
                                {(uploadMutation.error as Error)?.message || 'An error occurred'}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Privacy Notice */}
            <div className="glass-card p-4 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-[var(--accent-secondary)] bg-opacity-20 flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-[var(--accent-secondary)]" />
                </div>
                <div>
                    <p className="font-medium">100% Local Processing</p>
                    <p className="text-sm text-[var(--foreground-secondary)]">
                        Your files are processed entirely on your machine. Only AI queries use the external LLM.
                    </p>
                </div>
            </div>

            {/* Uploaded Documents */}
            <div className="glass-card p-6">
                <h2 className="text-xl font-semibold mb-4">Uploaded Documents</h2>

                {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                        <div className="spinner" />
                    </div>
                ) : !documents || documents.length === 0 ? (
                    <div className="text-center py-12 text-[var(--foreground-secondary)]">
                        <File className="w-16 h-16 mx-auto mb-4 opacity-50" />
                        <p>No documents uploaded yet</p>
                        <p className="text-sm mt-1">Upload your first statement to get started</p>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {documents.map((doc: any) => (
                            <div
                                key={doc.id}
                                className="flex items-center gap-4 p-4 rounded-xl bg-[var(--background)] hover:bg-[var(--glass-bg)] transition-all"
                            >
                                <div
                                    className={`w-12 h-12 rounded-xl flex items-center justify-center ${doc.file_type === 'pdf'
                                        ? 'bg-[#ef4444] bg-opacity-20'
                                        : 'bg-[#10b981] bg-opacity-20'
                                        }`}
                                >
                                    <FileText
                                        className={`w-6 h-6 ${doc.file_type === 'pdf' ? 'text-[#ef4444]' : 'text-[#10b981]'
                                            }`}
                                    />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium truncate">{doc.filename}</p>
                                    <p className="text-sm text-[var(--foreground-secondary)]">
                                        Uploaded {format(new Date(doc.uploaded_at), 'MMM d, yyyy h:mm a')}
                                    </p>
                                </div>
                                <div className="text-right">
                                    <p className="font-medium text-[var(--accent-primary)]">
                                        {doc.transaction_count} transactions
                                    </p>
                                    <p
                                        className={`text-sm ${doc.processed ? 'text-[var(--accent-secondary)]' : 'text-[var(--accent-tertiary)]'
                                            }`}
                                    >
                                        {doc.processed ? 'Processed' : 'Processing...'}
                                    </p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
