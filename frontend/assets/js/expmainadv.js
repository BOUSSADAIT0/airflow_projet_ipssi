// ==============================================
// OCR Intelligent - Main Application Script
// ==============================================

// Utiliser un pattern IIFE pour éviter les conflits de variables
(function() {
    'use strict';

    // Configuration globale - DÉCLARATION UNIQUE
    const CONFIG = {
        API_BASE_URL: 'http://localhost:8000',
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
                STATS: '/api/ocr/stats',
                DOWNLOAD: '/api/ocr/results/{id}/download/{format}'
            }
        },
        DEMO_CREDENTIALS: {
            USERNAME: 'aitdjoudi@gmail.com',
            PASSWORD: 'boussad'
        }
    };

    // Variables globales de l'application - DÉCLARATION UNIQUE
    let api = null;
    let auth = null;
    let currentResults = null;
    let currentProcessId = null;

    // ==============================================
    // GESTION D'AUTHENTIFICATION
    // ==============================================

    class AuthManager {
        constructor() {
            this.tokenKey = 'ocr_auth_token';
            this.userKey = 'ocr_user_data';
        }

        isAuthenticated() {
            return !!this.getToken();
        }

        getToken() {
            return localStorage.getItem(this.tokenKey);
        }

        setToken(token) {
            localStorage.setItem(this.tokenKey, token);
        }

        getUser() {
            const userData = localStorage.getItem(this.userKey);
            return userData ? JSON.parse(userData) : null;
        }

        setUser(user) {
            localStorage.setItem(this.userKey, JSON.stringify(user));
        }

        logout() {
            localStorage.removeItem(this.tokenKey);
            localStorage.removeItem(this.userKey);
            
            // Redirection appropriée selon la page
            const currentPage = window.location.pathname;
            if (currentPage.includes('index_advanced.html')) {
                window.location.reload();
            } else if (!currentPage.includes('login.html') && 
                      !currentPage.includes('register.html') && 
                      !currentPage.includes('index.html')) {
                window.location.href = 'login.html';
            }
        }

        async checkAuth() {
            if (!this.isAuthenticated()) {
                const currentPage = window.location.pathname;
                const publicPages = ['/index.html', '/login.html', '/register.html', '/'];
                
                if (!publicPages.some(page => currentPage.includes(page))) {
                    window.location.href = 'login.html';
                }
            }
        }

        async autoLoginDemo() {
            try {
                console.log('Tentative de connexion automatique avec compte démo...');
                
                const response = await fetch(`${CONFIG.API_BASE_URL}/api/auth/login`, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        username: CONFIG.DEMO_CREDENTIALS.USERNAME,
                        password: CONFIG.DEMO_CREDENTIALS.PASSWORD
                    })
                });

                if (!response.ok) {
                    console.error('Échec auto-login:', response.status, response.statusText);
                    return false;
                }

                const data = await response.json();
                
                if (!data.access_token) {
                    console.error('Token non reçu dans la réponse');
                    return false;
                }

                this.setToken(data.access_token);
                console.log('Token démo reçu et stocké');

                // Récupérer les infos utilisateur
                try {
                    const userResponse = await fetch(`${CONFIG.API_BASE_URL}/api/auth/me`, {
                        headers: { 
                            'Authorization': `Bearer ${data.access_token}`,
                            'Accept': 'application/json'
                        }
                    });

                    if (userResponse.ok) {
                        const userData = await userResponse.json();
                        this.setUser(userData);
                        console.log('Informations utilisateur récupérées:', userData);
                    }
                } catch (userError) {
                    console.warn('Impossible de récupérer les infos utilisateur:', userError);
                }

                return true;
                
            } catch (error) {
                console.error('Erreur auto-login:', error);
                return false;
            }
        }
    }

    // ==============================================
    // CLIENT API
    // ==============================================

    class APIClient {
        constructor() {
            this.baseURL = CONFIG.API_BASE_URL;
        }

        async request(endpoint, options = {}) {
            const url = `${this.baseURL}${endpoint}`;
            const headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                ...options.headers
            };

            // Ajouter le token d'authentification si disponible
            const token = auth.getToken();
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            try {
                const response = await fetch(url, {
                    ...options,
                    headers,
                    credentials: 'include'
                });

                // Gérer les erreurs HTTP
                if (!response.ok) {
                    // Si 401 Unauthorized, déconnecter
                    if (response.status === 401) {
                        auth.logout();
                        throw new Error('Session expirée. Veuillez vous reconnecter.');
                    }
                    
                    // Essayer de parser le message d'erreur
                    let errorMessage = `Erreur ${response.status}: ${response.statusText}`;
                    try {
                        const errorData = await response.json();
                        if (errorData.detail) {
                            errorMessage = errorData.detail;
                        } else if (errorData.message) {
                            errorMessage = errorData.message;
                        }
                    } catch {
                        const text = await response.text();
                        if (text) {
                            errorMessage = text;
                        }
                    }
                    
                    throw new Error(errorMessage);
                }

                // Parser la réponse
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return await response.json();
                } else if (contentType && contentType.includes('text/')) {
                    return await response.text();
                } else {
                    return response;
                }
            } catch (error) {
                console.error('Erreur API:', {
                    endpoint,
                    error: error.message,
                    url
                });
                
                throw error;
            }
        }

        // Méthodes d'authentification
        async login(username, password) {
            return this.request('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
        }

        async register(userData) {
            return this.request('/api/auth/register', {
                method: 'POST',
                body: JSON.stringify(userData)
            });
        }

        async getCurrentUser() {
            return this.request('/api/auth/me');
        }

        // Méthodes OCR
        async processDocument(file, language = 'fra+eng') {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('language', language);

            const token = auth.getToken();
            const url = `${this.baseURL}/api/ocr/process`;

            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();

                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable && typeof onUploadProgress === 'function') {
                        const progress = Math.round((event.loaded / event.total) * 100);
                        onUploadProgress(progress);
                    }
                });

                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            resolve(JSON.parse(xhr.responseText));
                        } catch {
                            resolve(xhr.responseText);
                        }
                    } else {
                        let errorMessage = `Erreur ${xhr.status}: ${xhr.statusText}`;
                        try {
                            const errorData = JSON.parse(xhr.responseText);
                            if (errorData.detail) {
                                errorMessage = errorData.detail;
                            }
                        } catch {
                            // Ignorer si pas de JSON
                        }
                        reject(new Error(errorMessage));
                    }
                });

                xhr.addEventListener('error', () => {
                    reject(new Error('Erreur réseau lors de l\'upload'));
                });

                xhr.open('POST', url);
                if (token) {
                    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                }
                xhr.send(formData);
            });
        }

        async getResults(processId) {
            return this.request(`/api/ocr/results/${processId}`);
        }

        async downloadResults(processId, format = 'json') {
            const token = auth.getToken();
            const response = await fetch(
                `${this.baseURL}/api/ocr/results/${processId}/download/${format}`, {
                headers: token ? { 
                    'Authorization': `Bearer ${token}`,
                    'Accept': 'application/json'
                } : {}
            });

            if (!response.ok) {
                throw new Error('Échec du téléchargement');
            }

            return response.blob();
        }

        async getStats() {
            return this.request('/api/ocr/stats');
        }

        async batchProcess(files, language = 'fra+eng') {
            const formData = new FormData();
            files.forEach(file => {
                formData.append('files', file);
            });
            formData.append('language', language);

            const token = auth.getToken();
            const url = `${this.baseURL}/api/ocr/batch-process`;

            return new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();

                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        try {
                            resolve(JSON.parse(xhr.responseText));
                        } catch {
                            resolve(xhr.responseText);
                        }
                    } else {
                        reject(new Error(`Erreur batch: ${xhr.statusText}`));
                    }
                });

                xhr.addEventListener('error', () => {
                    reject(new Error('Erreur réseau lors du traitement batch'));
                });

                xhr.open('POST', url);
                if (token) {
                    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
                }
                xhr.send(formData);
            });
        }
    }

    // ==============================================
    // FONCTIONS UTILITAIRES GLOBALES
    // ==============================================

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return new Intl.DateTimeFormat('fr-FR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }).format(date);
        } catch {
            return dateString;
        }
    }

    function showNotification(message, type = 'info', duration = 5000) {
        // Supprimer les notifications existantes
        document.querySelectorAll('.notification').forEach(n => n.remove());

        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 max-w-sm ${getNotificationClasses(type)} rounded-lg shadow-lg p-4`;
        
        const icons = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        notification.innerHTML = `
            <div class="flex items-start">
                <div class="flex-shrink-0">
                    <i class="${icons[type] || icons.info} text-lg"></i>
                </div>
                <div class="ml-3 flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <div class="ml-4 flex-shrink-0">
                    <button onclick="this.parentElement.parentElement.parentElement.remove()" 
                            class="inline-flex text-current hover:opacity-75">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(notification);

        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, duration);
        }

        return notification;
    }

    function getNotificationClasses(type) {
        const classes = {
            success: 'bg-green-50 border border-green-200 text-green-800',
            error: 'bg-red-50 border border-red-200 text-red-800',
            warning: 'bg-yellow-50 border border-yellow-200 text-yellow-800',
            info: 'bg-blue-50 border border-blue-200 text-blue-800'
        };
        return classes[type] || classes.info;
    }

    function showToast(type, title, message) {
        const toast = document.getElementById('toast');
        if (!toast) return;

        const colors = {
            success: 'border-green-500',
            error: 'border-red-500',
            warning: 'border-yellow-500',
            info: 'border-blue-500'
        };

        const icons = {
            success: 'fas fa-check-circle text-green-500',
            error: 'fas fa-exclamation-circle text-red-500',
            warning: 'fas fa-exclamation-triangle text-yellow-500',
            info: 'fas fa-info-circle text-blue-500'
        };

        const borderColor = colors[type] || colors.info;
        const iconClass = icons[type] || icons.info;

        toast.className = `fixed top-4 right-4 max-w-sm bg-white rounded-lg shadow-lg p-4 z-50 border-l-4 ${borderColor}`;
        
        const toastIcon = document.getElementById('toastIcon');
        const toastTitle = document.getElementById('toastTitle');
        const toastMessage = document.getElementById('toastMessage');
        
        if (toastIcon) toastIcon.innerHTML = `<i class="${iconClass} text-lg"></i>`;
        if (toastTitle) toastTitle.textContent = title;
        if (toastMessage) toastMessage.textContent = message;

        toast.classList.remove('hidden');

        setTimeout(() => {
            toast.classList.add('hidden');
        }, 5000);
    }

    // ==============================================
    // INITIALISATION DE L'APPLICATION
    // ==============================================

    async function initializeApp() {
        console.log('Initialisation de l\'application OCR Intelligent...');

        try {
            // Initialiser les gestionnaires
            auth = new AuthManager();
            api = new APIClient();

            // Vérifier si le backend est accessible
            await checkBackendHealth();

            // Gérer l'authentification
            await handleAuthentication();

            // Initialiser les composants UI
            initializeUI();

            // Initialiser les écouteurs d'événements
            initializeEventListeners();

            console.log('Application initialisée avec succès');

        } catch (error) {
            console.error('Erreur lors de l\'initialisation:', error);
            showNotification('Erreur d\'initialisation: ' + error.message, 'error');
        }
    }

    async function checkBackendHealth() {
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}/health`, {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            
            if (!response.ok) {
                throw new Error(`Backend non accessible (${response.status})`);
            }
            
            const data = await response.json();
            console.log('Backend en ligne:', data);
            return true;
            
        } catch (error) {
            console.error('Backend hors ligne:', error);
            showNotification(
                'Le serveur backend n\'est pas accessible. Assurez-vous qu\'il est démarré sur localhost:8000',
                'error',
                10000
            );
            throw error;
        }
    }

    async function handleAuthentication() {
        const currentPage = window.location.pathname;
        
        // Pages publiques
        const publicPages = ['/index.html', '/login.html', '/register.html', '/'];
        
        if (publicPages.some(page => currentPage.includes(page))) {
            // Pour les pages publiques, essayer auto-login démo
            if (!auth.isAuthenticated()) {
                const success = await auth.autoLoginDemo();
                if (success) {
                    console.log('Auto-login démo réussi');
                }
            }
        } else {
            // Pour les pages protégées, vérifier l'authentification
            await auth.checkAuth();
            
            if (!auth.isAuthenticated()) {
                // Essayer auto-login démo
                const success = await auth.autoLoginDemo();
                if (!success) {
                    window.location.href = 'login.html';
                    return;
                }
            }
        }

        // Mettre à jour l'interface avec les infos utilisateur
        updateUserInterface();
    }

    function updateUserInterface() {
        const user = auth.getUser();
        
        if (user) {
            // Mettre à jour les éléments avec data-user
            document.querySelectorAll('[data-user]').forEach(element => {
                const field = element.getAttribute('data-user');
                if (field === 'username' && user.username) {
                    element.textContent = user.username;
                } else if (field === 'email' && user.email) {
                    element.textContent = user.email;
                } else if (field === 'full_name' && user.full_name) {
                    element.textContent = user.full_name;
                }
            });

            // Mettre à jour le statut d'authentification
            const authStatus = document.getElementById('authStatus');
            const loginBtn = document.getElementById('loginBtn');
            const logoutBtn = document.getElementById('logoutBtn');

            if (authStatus) authStatus.classList.remove('hidden');
            if (loginBtn) loginBtn.classList.add('hidden');
            if (logoutBtn) logoutBtn.classList.remove('hidden');
        }
    }

    function initializeUI() {
        // Initialiser les tooltips
        initializeTooltips();

        // Initialiser les tabs
        initializeTabs();

        // Initialiser les modals
        initializeModals();
    }

    function initializeTooltips() {
        // Implémenter si nécessaire
    }

    function initializeTabs() {
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', function() {
                const tabName = this.getAttribute('data-tab');
                switchTab(tabName);
            });
        });
    }

    function initializeModals() {
        // Fermer la modal avec Échap
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const modal = document.querySelector('.modal-overlay:not(.hidden)');
                if (modal) {
                    modal.classList.add('hidden');
                    document.body.style.overflow = 'auto';
                }
            }
        });

        // Fermer la modal en cliquant à l'extérieur
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.classList.add('hidden');
                    document.body.style.overflow = 'auto';
                }
            });
        });
    }

    function initializeEventListeners() {
        // Gestion de la déconnexion
        document.addEventListener('click', (e) => {
            if (e.target.closest('[data-logout]')) {
                e.preventDefault();
                auth.logout();
            }
        });

        // Gestion des formulaires de connexion
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', handleLogin);
        }

        // Gestion des formulaires d'inscription
        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', handleRegister);
        }

        // Gestion de l'upload de fichiers
        setupFileUpload();
    }

    async function handleLogin(event) {
        event.preventDefault();
        
        const username = document.getElementById('username')?.value;
        const password = document.getElementById('password')?.value;
        
        if (!username || !password) {
            showNotification('Veuillez remplir tous les champs', 'error');
            return;
        }

        try {
            const button = event.target.querySelector('button[type="submit"]');
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Connexion...';
            button.disabled = true;

            const response = await api.login(username, password);
            
            auth.setToken(response.access_token);
            
            // Récupérer les infos utilisateur
            const userData = await api.getCurrentUser();
            auth.setUser(userData);
            
            showNotification('Connexion réussie !', 'success');
            
            // Rediriger vers la page principale
            setTimeout(() => {
                window.location.href = 'index_advanced.html';
            }, 1000);
            
        } catch (error) {
            console.error('Erreur de connexion:', error);
            showNotification('Échec de la connexion: ' + error.message, 'error');
            
            const button = event.target.querySelector('button[type="submit"]');
            button.innerHTML = 'Se connecter';
            button.disabled = false;
        }
    }

    async function handleRegister(event) {
        event.preventDefault();
        
        const formData = {
            username: document.getElementById('username')?.value,
            email: document.getElementById('email')?.value,
            password: document.getElementById('password')?.value,
            full_name: document.getElementById('full_name')?.value || ''
        };

        if (!formData.username || !formData.email || !formData.password) {
            showNotification('Veuillez remplir tous les champs obligatoires', 'error');
            return;
        }

        try {
            const button = event.target.querySelector('button[type="submit"]');
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Création du compte...';
            button.disabled = true;

            const response = await api.register(formData);
            
            showNotification('Compte créé avec succès !', 'success');
            
            // Auto-connexion après inscription
            setTimeout(async () => {
                try {
                    const loginResponse = await api.login(formData.username, formData.password);
                    auth.setToken(loginResponse.access_token);
                    
                    const userData = await api.getCurrentUser();
                    auth.setUser(userData);
                    
                    window.location.href = 'index_advanced.html';
                } catch (loginError) {
                    window.location.href = 'login.html';
                }
            }, 1500);
            
        } catch (error) {
            console.error('Erreur d\'inscription:', error);
            showNotification('Échec de l\'inscription: ' + error.message, 'error');
            
            const button = event.target.querySelector('button[type="submit"]');
            button.innerHTML = 'Créer un compte';
            button.disabled = false;
        }
    }

    function setupFileUpload() {
        const dropZone = document.getElementById('dropZone');
        const fileInput = document.getElementById('fileInput');
        
        if (!dropZone || !fileInput) return;

        // Click sur la zone
        dropZone.addEventListener('click', () => fileInput.click());

        // Drag & drop
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFileSelection(files);
            }
        });

        // Sélection via input
        fileInput.addEventListener('change', (e) => {
            handleFileSelection(e.target.files);
        });
    }

    function handleFileSelection(files) {
        const fileList = document.getElementById('fileList');
        const processBtn = document.getElementById('processBtn');
        
        if (!fileList || !processBtn) return;

        // Vider la liste actuelle
        fileList.innerHTML = '';

        let validFiles = [];
        
        Array.from(files).forEach((file, index) => {
            if (isValidFile(file)) {
                validFiles.push(file);
                
                const fileElement = createFileElement(file, index);
                fileList.appendChild(fileElement);
            } else {
                showNotification(
                    `Fichier non supporté: ${file.name}. Formats acceptés: PDF, JPG, PNG, TIFF`,
                    'warning'
                );
            }
        });

        // Mettre à jour l'input file avec les fichiers valides
        const dataTransfer = new DataTransfer();
        validFiles.forEach(file => dataTransfer.items.add(file));
        document.getElementById('fileInput').files = dataTransfer.files;

        // Activer/désactiver le bouton de traitement
        processBtn.disabled = validFiles.length === 0;
    }

    function isValidFile(file) {
        const allowedTypes = [
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/tiff',
            'image/tif'
        ];
        
        const allowedExtensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'];
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        
        return allowedTypes.includes(file.type) || allowedExtensions.includes(extension);
    }

    function createFileElement(file, index) {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between p-3 bg-gray-50 rounded-lg mb-2';
        div.innerHTML = `
            <div class="flex items-center">
                <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                    <i class="fas fa-file text-blue-600"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <p class="font-medium text-sm truncate">${file.name}</p>
                    <p class="text-xs text-gray-500">${formatFileSize(file.size)}</p>
                </div>
            </div>
            <button onclick="removeFile(${index})" class="text-gray-400 hover:text-red-500 ml-2">
                <i class="fas fa-times"></i>
            </button>
        `;
        return div;
    }

    // Fonction pour retirer un fichier (exposée globalement)
    window.removeFile = function(index) {
        const fileInput = document.getElementById('fileInput');
        const fileList = document.getElementById('fileList');
        
        if (!fileInput || !fileList) return;

        const dt = new DataTransfer();
        const files = Array.from(fileInput.files);
        
        files.forEach((file, i) => {
            if (i !== index) {
                dt.items.add(file);
            }
        });
        
        fileInput.files = dt.files;
        handleFileSelection(fileInput.files);
    };

    // Fonction pour traiter les documents (exposée globalement)
    window.processDocuments = async function() {
        const fileInput = document.getElementById('fileInput');
        const files = fileInput.files;
        
        if (files.length === 0) {
            showNotification('Veuillez sélectionner au moins un fichier', 'warning');
            return;
        }

        // Vérifier l'authentification
        if (!auth.isAuthenticated()) {
            const success = await auth.autoLoginDemo();
            if (!success) {
                showNotification('Veuillez vous connecter pour traiter des documents', 'error');
                return;
            }
        }

        const language = document.getElementById('languageSelect')?.value || 'fra+eng';
        
        // Afficher la progression
        const progressContainer = document.getElementById('progressContainer');
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (progressContainer) progressContainer.classList.remove('hidden');
        if (progressBar) progressBar.style.width = '0%';
        if (progressText) progressText.textContent = 'Démarrage du traitement...';

        try {
            let result;
            
            if (files.length === 1) {
                // Traitement d'un seul fichier
                if (progressText) progressText.textContent = 'Envoi du fichier...';
                
                result = await api.processDocument(files[0], language, (progress) => {
                    if (progressBar) progressBar.style.width = `${progress}%`;
                    if (progressText) progressText.textContent = `Upload: ${progress}%`;
                });
                
            } else {
                // Traitement batch
                if (progressText) progressText.textContent = 'Envoi des fichiers...';
                
                result = await api.batchProcess(Array.from(files), language);
            }

            // Récupérer les résultats complets
            if (progressText) progressText.textContent = 'Récupération des résultats...';
            if (progressBar) progressBar.style.width = '90%';

            currentProcessId = result.process_id;
            currentResults = await api.getResults(result.process_id);

            // Afficher les résultats
            displayResults(currentResults);
            
            showNotification('Traitement terminé avec succès !', 'success');

        } catch (error) {
            console.error('Erreur de traitement:', error);
            showNotification('Erreur lors du traitement: ' + error.message, 'error');
        } finally {
            if (progressContainer) {
                setTimeout(() => {
                    progressContainer.classList.add('hidden');
                }, 2000);
            }
        }
    };

    function displayResults(result) {
        const modalContent = document.getElementById('modalContent');
        const modalTitle = document.getElementById('modalTitle');
        const resultModal = document.getElementById('resultModal');
        
        if (!modalContent || !modalTitle || !resultModal) return;

        modalTitle.textContent = `Résultats: ${result.filename || 'Document'}`;
        modalContent.innerHTML = createResultsHTML(result);
        
        resultModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function createResultsHTML(result) {
        const personalInfo = result.structured_data?.personal_info || {};
        const entities = result.structured_data?.entities || {};
        
        return `
            <div class="space-y-6">
                <!-- Informations du document -->
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="bg-gray-50 p-4 rounded-lg">
                        <p class="text-sm text-gray-500">Type de document</p>
                        <p class="font-medium text-lg">${result.document_type || 'Non détecté'}</p>
                    </div>
                    <div class="bg-gray-50 p-4 rounded-lg">
                        <p class="text-sm text-gray-500">Confiance OCR</p>
                        <p class="font-medium text-lg">${(result.average_confidence * 100).toFixed(1)}%</p>
                    </div>
                    <div class="bg-gray-50 p-4 rounded-lg">
                        <p class="text-sm text-gray-500">Pages</p>
                        <p class="font-medium text-lg">${result.total_pages || 1}</p>
                    </div>
                </div>
                
                <!-- Informations personnelles -->
                ${personalInfo.full_name || personalInfo.email || personalInfo.phone ? `
                    <div class="bg-blue-50 border border-blue-100 rounded-lg p-4">
                        <h4 class="font-semibold text-blue-800 mb-3">
                            <i class="fas fa-user-circle mr-2"></i>Informations personnelles
                        </h4>
                        <div class="space-y-2">
                            ${personalInfo.full_name ? `
                                <div class="flex items-center">
                                    <span class="w-32 text-gray-600">Nom complet:</span>
                                    <span class="font-medium">${personalInfo.full_name}</span>
                                </div>
                            ` : ''}
                            
                            ${personalInfo.email ? `
                                <div class="flex items-center">
                                    <span class="w-32 text-gray-600">Email:</span>
                                    <span class="font-medium">${personalInfo.email}</span>
                                </div>
                            ` : ''}
                            
                            ${personalInfo.phone ? `
                                <div class="flex items-center">
                                    <span class="w-32 text-gray-600">Téléphone:</span>
                                    <span class="font-medium">${personalInfo.phone}</span>
                                </div>
                            ` : ''}
                            
                            ${personalInfo.address ? `
                                <div class="flex items-center">
                                    <span class="w-32 text-gray-600">Adresse:</span>
                                    <span class="font-medium">${personalInfo.address}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                ` : ''}
                
                <!-- Données structurées -->
                ${Object.keys(entities).length > 0 ? `
                    <div>
                        <h4 class="font-semibold mb-3">Données extraites</h4>
                        <div class="space-y-3">
                            ${Object.entries(entities).map(([key, values]) => `
                                <div class="border rounded-lg p-3">
                                    <p class="font-medium text-sm text-gray-700 mb-2">${key}:</p>
                                    <div class="space-y-1">
                                        ${Array.isArray(values) ? values.map(val => `
                                            <div class="text-sm bg-gray-50 rounded px-3 py-2">${val}</div>
                                        `).join('') : `<div class="text-sm">${values}</div>`}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}
                
                <!-- Aperçu du texte -->
                <div>
                    <h4 class="font-semibold mb-3">Texte extrait</h4>
                    <div class="bg-gray-50 border rounded-lg p-4 max-h-64 overflow-y-auto">
                        <pre class="text-sm whitespace-pre-wrap">${result.text?.substring(0, 1000) || 'Aucun texte extrait'}${result.text?.length > 1000 ? '...' : ''}</pre>
                    </div>
                </div>
            </div>
        `;
    }

    // Fonction pour télécharger les résultats (exposée globalement)
    window.downloadResult = async function(format = 'json') {
        if (!currentProcessId) {
            showNotification('Aucun résultat à télécharger', 'warning');
            return;
        }

        try {
            const blob = await api.downloadResults(currentProcessId, format);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ocr_result_${currentProcessId}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showNotification(`Fichier ${format} téléchargé avec succès`, 'success');
        } catch (error) {
            showNotification('Erreur lors du téléchargement: ' + error.message, 'error');
        }
    };

    // Fonction pour fermer la modal (exposée globalement)
    window.closeModal = function() {
        const modal = document.getElementById('resultModal');
        if (modal) {
            modal.classList.add('hidden');
            document.body.style.overflow = 'auto';
        }
    };

    // Fonction pour changer d'onglet (exposée globalement)
    window.switchTab = function(tabName) {
        // Mettre à jour les boutons d'onglets
        document.querySelectorAll('.tab-button').forEach(button => {
            if (button.getAttribute('data-tab') === tabName) {
                button.classList.add('active');
            } else {
                button.classList.remove('active');
            }
        });
        
        // é de l'onglet correspondant
        document.querySelectorAll('.tab-content').forEach(content => {
            if (content.getAttribute('data-tab-content') === tabName) {
                content.classList.remove('hidden');
            } else {
                content.classList.add('hidden');
            }
        });
    };

    // Fonction pour afficher les statistiques (exposée globalement)
    window.showStats = async function() {
        try {
            if (!auth.isAuthenticated()) {
                const success = await auth.autoLoginDemo();
                if (!success) {
                    showNotification('Veuillez vous connecter pour voir les statistiques', 'error');
                    return;
                }
            }

            const stats = await api.getStats();
            
            const modalContent = document.getElementById('modalContent');
            const modalTitle = document.getElementById('modalTitle');
            const resultModal = document.getElementById('resultModal');
            
            if (!modalContent || !modalTitle || !resultModal) return;

            modalTitle.textContent = 'Statistiques OCR';
            modalContent.innerHTML = `
                <div class="space-y-6">
                    <!-- Cartes de statistiques -->
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div class="bg-blue-50 p-6 rounded-lg border border-blue-100">
                            <div class="flex items-center">
                                <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-4">
                                    <i class="fas fa-file-alt text-blue-600 text-xl"></i>
                                </div>
                                <div>
                                    <p class="text-sm text-gray-500">Documents traités</p>
                                    <p class="text-2xl font-bold">${stats.total_documents || 0}</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="bg-green-50 p-6 rounded-lg border border-green-100">
                            <div class="flex items-center">
                                <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mr-4">
                                    <i class="fas fa-chart-line text-green-600 text-xl"></i>
                                </div>
                                <div>
                                    <p class="text-sm text-gray-500">Confiance moyenne</p>
                                    <p class="text-2xl font-bold">${stats.average_confidence ? (stats.average_confidence * 100).toFixed(1) + '%' : '0%'}</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="bg-purple-50 p-6 rounded-lg border border-purple-100">
                            <div class="flex items-center">
                                <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mr-4">
                                    <i class="fas fa-clock text-purple-600 text-xl"></i>
                                </div>
                                <div>
                                    <p class="text-sm text-gray-500">Temps moyen</p>
                                    <p class="text-2xl font-bold">${stats.average_processing_time ? (stats.average_processing_time).toFixed(2) + 's' : '0s'}</p>
                                </div>
                            </div>
                        </div>
                        
                        <div class="bg-yellow-50 p-6 rounded-lg border border-yellow-100">
                            <div class="flex items-center">
                                <div class="w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center mr-4">
                                    <i class="fas fa-layer-group text-yellow-600 text-xl"></i>
                                </div>
                                <div>
                                    <p class="text-sm text-gray-500">Pages totales</p>
                                    <p class="text-2xl font-bold">${stats.total_pages || 0}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Répartition par type de document -->
                    ${stats.document_types && Object.keys(stats.document_types).length > 0 ? `
                        <div>
                            <h4 class="font-semibold mb-4">Répartition par type de document</h4>
                            <div class="bg-white border rounded-lg p-4">
                                <div class="space-y-3">
                                    ${Object.entries(stats.document_types).map(([type, count]) => `
                                        <div class="flex items-center justify-between">
                                            <span class="font-medium">${type}</span>
                                            <div class="flex items-center">
                                                <div class="w-48 bg-gray-200 rounded-full h-2 mr-4">
                                                    <div class="bg-blue-600 h-2 rounded-full" 
                                                         style="width: ${(count / stats.total_documents * 100).toFixed(0)}%">
                                                    </div>
                                                </div>
                                                <span class="text-sm text-gray-600">${count}</span>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    <!-- Activité récente -->
                    ${stats.recent_activity && stats.recent_activity.length > 0 ? `
                        <div>
                            <h4 class="font-semibold mb-4">Activité récente</h4>
                            <div class="bg-white border rounded-lg overflow-hidden">
                                <div class="divide-y">
                                    ${stats.recent_activity.map(activity => `
                                        <div class="p-4 hover:bg-gray-50">
                                            <div class="flex justify-between items-start">
                                                <div>
                                                    <p class="font-medium">${activity.filename || 'Document'}</p>
                                                    <p class="text-sm text-gray-500 mt-1">
                                                        Type: ${activity.document_type || 'Inconnu'} | 
                                                        Pages: ${activity.pages || 1} | 
                                                        Confiance: ${(activity.confidence * 100).toFixed(1)}%
                                                    </p>
                                                </div>
                                                <span class="text-sm text-gray-500">${formatDate(activity.processed_at)}</span>
                                            </div>
                                        </div>
                                    `).join('')}
                                </div>
                            </div>
                        </div>
                    ` : ''}
                    
                    <!-- Usage du stockage -->
                    <div>
                        <h4 class="font-semibold mb-4">Usage du stockage</h4>
                        <div class="bg-gradient-to-r from-blue-50 to-green-50 border rounded-lg p-6">
                            <div class="flex justify-between items-center mb-2">
                                <span class="font-medium">Espace utilisé</span>
                                <span class="font-bold">${formatFileSize(stats.storage_used || 0)} / ${formatFileSize(stats.storage_limit || 0)}</span>
                            </div>
                            <div class="w-full bg-gray-200 rounded-full h-4">
                                <div class="bg-gradient-to-r from-blue-500 to-green-500 h-4 rounded-full" 
                                     style="width: ${Math.min(100, ((stats.storage_used || 0) / (stats.storage_limit || 1) * 100)).toFixed(1)}%">
                                </div>
                            </div>
                            <p class="text-sm text-gray-500 mt-2">
                                ${(((stats.storage_used || 0) / (stats.storage_limit || 1)) * 100).toFixed(1)}% du stockage utilisé
                            </p>
                        </div>
                    </div>
                </div>
            `;
            
            resultModal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            
        } catch (error) {
            console.error('Erreur lors de la récupération des statistiques:', error);
            showNotification('Impossible de charger les statistiques: ' + error.message, 'error');
        }
    };

    // Fonction pour vérifier la connexion au backend (exposée globalement)
    window.checkConnection = async function() {
        try {
            showNotification('Vérification de la connexion au serveur...', 'info');
            await checkBackendHealth();
            showNotification('Connexion au serveur établie avec succès !', 'success');
        } catch (error) {
            showNotification('Impossible de se connecter au serveur', 'error');
        }
    };

    // ==============================================
    // FONCTIONS POUR LA PAGE D'ACCUEIL
    // ==============================================

    // Initialiser le carrousel d'images (exposée globalement)
    window.initializeImageCarousel = function() {
        const carousel = document.getElementById('imageCarousel');
        if (!carousel) return;

        const images = carousel.querySelectorAll('img');
        let currentIndex = 0;

        function showImage(index) {
            images.forEach((img, i) => {
                img.classList.toggle('hidden', i !== index);
            });
            
            // Mettre à jour les indicateurs
            const indicators = document.querySelectorAll('.carousel-indicator');
            indicators.forEach((indicator, i) => {
                indicator.classList.toggle('bg-blue-600', i === index);
                indicator.classList.toggle('bg-gray-300', i !== index);
            });
        }

        // Boutons précédent/suivant
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                currentIndex = (currentIndex - 1 + images.length) % images.length;
                showImage(currentIndex);
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                currentIndex = (currentIndex + 1) % images.length;
                showImage(currentIndex);
            });
        }

        // Créer les indicateurs
        const indicatorsContainer = document.createElement('div');
        indicatorsContainer.className = 'flex justify-center space-x-2 mt-4';
        
        images.forEach((_, index) => {
            const button = document.createElement('button');
            button.className = `w-3 h-3 rounded-full ${index === 0 ? 'bg-blue-600' : 'bg-gray-300'} carousel-indicator`;
            button.addEventListener('click', () => {
                currentIndex = index;
                showImage(currentIndex);
            });
            indicatorsContainer.appendChild(button);
        });

        carousel.parentNode.insertBefore(indicatorsContainer, carousel.nextSibling);

        // Rotation automatique
        setInterval(() => {
            currentIndex = (currentIndex + 1) % images.length;
            showImage(currentIndex);
        }, 5000);

        showImage(0);
    };

    // ==============================================
    // FONCTIONS DE DÉMARRAGE
    // ==============================================

    // Attendre que le DOM soit chargé
    document.addEventListener('DOMContentLoaded', function() {
        // Initialiser l'application
        initializeApp();
        
        // Initialiser le carrousel d'images si présent
        if (typeof initializeImageCarousel === 'function') {
            initializeImageCarousel();
        }
        
        // Gérer le bouton de déconnexion
        document.getElementById('logoutBtn')?.addEventListener('click', function(e) {
            e.preventDefault();
            auth?.logout();
        });
        
        // Gérer le bouton de vérification de connexion
        document.getElementById('checkConnectionBtn')?.addEventListener('click', function() {
            if (typeof checkConnection === 'function') {
                checkConnection();
            }
        });
    });

    // Exposer certaines fonctions globalement
    window.APP = {
        auth: {
            getToken: () => auth?.getToken(),
            getUser: () => auth?.getUser(),
            isAuthenticated: () => auth?.isAuthenticated(),
            logout: () => auth?.logout()
        },
        api: {
            processDocument: (file, language) => api?.processDocument(file, language),
            downloadResults: (processId, format) => api?.downloadResults(processId, format),
            getStats: () => api?.getStats()
        },
        utils: {
            formatFileSize,
            formatDate,
            showNotification,
            showToast
        }
    };

})(); // Fin de l'IIFE