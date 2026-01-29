// config.js - Version mise à jour
// localhost -> backend sur :8000 ; accès par IP (ex. 172.20.10.11) -> backend sur IP:8000
const CONFIG = {
    API_BASE_URL: (typeof window !== 'undefined' && window.location && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
        ? 'http://localhost:8000'
        : ('http://' + (window.location && window.location.hostname ? window.location.hostname : 'localhost') + ':8000'),
    ENDPOINTS: {
        AUTH: {
            LOGIN: '/api/auth/login',
            REGISTER: '/api/auth/register',
            ME: '/api/auth/me',
            REFRESH: '/api/auth/refresh',
            LOGOUT: '/api/auth/logout'
        },
        OCR: {
            PROCESS: '/api/ocr/process',
            BATCH_PROCESS: '/api/ocr/batch-process',
            RESULTS: '/api/ocr/results',
            HISTORY: '/api/ocr/history',
            STATS: '/api/ocr/stats',
            DOWNLOAD: '/api/ocr/results/{id}/download/{format}',
            DELETE: '/api/ocr/results/{id}'
        }
    },
    UPLOAD: {
        MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
        ALLOWED_TYPES: ['pdf', 'jpg', 'jpeg', 'png', 'tiff', 'tif']
    },
    PAGINATION: {
        ITEMS_PER_PAGE: 10
    }
};

// Export pour modules (si vous passez à ES6)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}