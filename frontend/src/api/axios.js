import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api', // Proxy is usually set in vite.config, but direct here for simplicity
    headers: {
        'Content-Type': 'application/json',
    },
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }

    // Auto-inject Workspace ID for data routes
    const activeWorkspaceId = localStorage.getItem('activeWorkspace');
    if (activeWorkspaceId && config.url && !config.url.includes('/auth') && !config.url.includes('/workspaces/') && !config.url.includes('/social')) {
        config.params = { ...config.params, workspace_id: activeWorkspaceId };
    }

    return config;
});

export default api;
