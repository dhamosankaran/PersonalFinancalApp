/**
 * API client for backend communication
 */

import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add default user email to requests (simplified auth)
apiClient.interceptors.request.use((config) => {
    if (!config.params) {
        config.params = {};
    }
    if (!config.params.user_email) {
        config.params.user_email = 'default@example.com';
    }
    return config;
});

// API functions

// Upload
export const uploadFile = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/api/upload/', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });

    return response.data;
};

export const uploadMultipleFiles = async (files: File[], extractionMethod: 'pdfplumber' | 'llm' = 'pdfplumber') => {
    const formData = new FormData();
    files.forEach((file) => {
        formData.append('files', file);
    });

    const response = await apiClient.post('/api/upload/batch', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        params: {
            extraction_method: extractionMethod,
        },
    });

    return response.data;
};

export const getUploadedDocuments = async () => {
    const response = await apiClient.get('/api/upload/documents');
    return response.data;
};

// Transactions
export const getTransactions = async (params?: {
    category?: string;
    merchant?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
}) => {
    const response = await apiClient.get('/api/transactions/', { params });
    return response.data;
};

export const createTransaction = async (transaction: any) => {
    const response = await apiClient.post('/api/transactions/', transaction);
    return response.data;
};

export const updateTransaction = async (id: string, transaction: any) => {
    const response = await apiClient.put(`/api/transactions/${id}`, transaction);
    return response.data;
};

export const deleteTransaction = async (id: string) => {
    const response = await apiClient.delete(`/api/transactions/${id}`);
    return response.data;
};

// Chat
export const sendChatMessage = async (query: string) => {
    const response = await apiClient.post('/api/chat/', { query });
    return response.data;
};

export const getChatHistory = async () => {
    const response = await apiClient.get('/api/chat/history');
    return response.data;
};

export const clearChatHistory = async () => {
    const response = await apiClient.delete('/api/chat/history');
    return response.data;
};

// Analytics
export const getMonthlySpend = async (months: number = 12) => {
    const response = await apiClient.get('/api/analytics/monthly', {
        params: { months },
    });
    return response.data;
};

export const getCategoryBreakdown = async (months: number = 12) => {
    const response = await apiClient.get('/api/analytics/category', {
        params: { months },
    });
    return response.data;
};

export const getTopMerchants = async (months: number = 12, limit: number = 10) => {
    const response = await apiClient.get('/api/analytics/merchants', {
        params: { months, limit },
    });
    return response.data;
};

export const getRecurringSubscriptions = async () => {
    const response = await apiClient.get('/api/analytics/subscriptions');
    return response.data;
};

export const getInsights = async (forceRefresh: boolean = false) => {
    const response = await apiClient.get('/api/analytics/insights', {
        params: { force_refresh: forceRefresh },
    });
    return response.data;
};

export const refreshInsights = async () => {
    const response = await apiClient.post('/api/analytics/insights/refresh');
    return response.data;
};

export const clearInsightsCache = async () => {
    const response = await apiClient.delete('/api/analytics/insights/cache');
    return response.data;
};

