// api-service.js
class ApiService {
    constructor() {
        this.baseURL = 'http://localhost:8000';
        this.token = localStorage.getItem('auth_token');
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    }

    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json'
        };

        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    async get(endpoint, params = {}) {
        const url = new URL(`${this.baseURL}${endpoint}`);
        Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));

        const response = await fetch(url, {
            headers: this.getHeaders()
        });

        return this.handleResponse(response);
    }

    async post(endpoint, data = {}, isFormData = false) {
        const options = {
            method: 'POST',
            headers: isFormData ? {} : this.getHeaders(),
            body: isFormData ? data : JSON.stringify(data)
        };

        const response = await fetch(`${this.baseURL}${endpoint}`, options);
        return this.handleResponse(response);
    }

    async delete(endpoint) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });

        return this.handleResponse(response);
    }

    async handleResponse(response) {
        if (response.status === 401) {
            // Token expiré, déconnecter
            localStorage.removeItem('auth_token');
            window.location.href = 'login.html';
            throw new Error('Session expirée');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }

        return await response.text();
    }

    // OCR spécifique
    async uploadFile(file, language = 'fra+eng', documentType = 'auto') {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', language);
        formData.append('document_type', documentType);

        return await this.post('/api/ocr/process', formData, true);
    }

    async getResult(processId) {
        return await this.get(`/api/ocr/results/${processId}`);
    }

    async getHistory(filters = {}) {
        return await this.get('/api/ocr/history', filters);
    }

    async downloadResult(processId, format = 'json') {
        const response = await fetch(`${this.baseURL}/api/ocr/results/${processId}/download/${format}`, {
            headers: this.getHeaders()
        });

        if (!response.ok) throw new Error('Download failed');

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ocr-result-${processId}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    async deleteResult(processId) {
        return await this.delete(`/api/ocr/results/${processId}`);
    }

    async getStats() {
        return await this.get('/api/ocr/stats');
    }
}

// Singleton
const apiService = new ApiService();
window.apiService = apiService;