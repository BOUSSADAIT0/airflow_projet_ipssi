// Configuration de l'API
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    get LOGIN_URL() { return `${this.BASE_URL}/api/auth/login`; },
    get REGISTER_URL() { return `${this.BASE_URL}/api/auth/register`; },
    get ME_URL() { return `${this.BASE_URL}/api/auth/me`; },
    get LOGOUT_URL() { return `${this.BASE_URL}/api/auth/logout`; },
    get REFRESH_URL() { return `${this.BASE_URL}/api/auth/refresh`; }
};

// Gestionnaire d'authentification
const AuthManager = {
    token: localStorage.getItem('auth_token'),
    user: JSON.parse(localStorage.getItem('user_data')) || null,
    
    setToken(token) {
        this.token = token;
        localStorage.setItem('auth_token', token);
    },
    
    setUser(user) {
        this.user = user;
        localStorage.setItem('user_data', JSON.stringify(user));
    },
    
    clear() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        localStorage.removeItem('remember_me');
    },
    
    isAuthenticated() {
        return !!this.token;
    },
    
    async getCurrentUser() {
        if (!this.token) return null;
        
        try {
            // Votre backend attend le token dans l'URL, pas dans les headers
            const response = await fetch(`${API_CONFIG.ME_URL}?token=${this.token}`);
            
            if (response.ok) {
                const user = await response.json();
                this.setUser(user);
                return user;
            } else {
                console.error('Erreur récupération utilisateur:', response.status);
                // Si le token est invalide, on se déconnecte
                this.clear();
            }
        } catch (error) {
            console.error('Erreur lors de la récupération du profil:', error);
        }
        return null;
    },
    
    async logout() {
        if (!this.token) return;
        
        try {
            await fetch(`${API_CONFIG.LOGOUT_URL}?token=${this.token}`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Erreur lors de la déconnexion:', error);
        } finally {
            this.clear();
            window.location.href = 'login.html';
        }
    },
    
    async refreshToken() {
        if (!this.token) return null;
        
        try {
            const response = await fetch(`${API_CONFIG.REFRESH_URL}?token=${this.token}`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.access_token) {
                    this.setToken(data.access_token);
                    return data.access_token;
                }
            }
        } catch (error) {
            console.error('Erreur lors du refresh du token:', error);
        }
        return null;
    }
};

// Fonctions API avec support query parameters
async function apiLogin(username, password) {
    try {
        const response = await fetch(API_CONFIG.LOGIN_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Login error response:', errorText);
            throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.access_token) {
            AuthManager.setToken(data.access_token);
            
            // Récupérer les infos utilisateur
            await AuthManager.getCurrentUser();
            
            return { success: true, data };
        } else {
            throw new Error('Token non reçu');
        }
        
    } catch (error) {
        console.error('Erreur de connexion:', error);
        return { 
            success: false, 
            error: error.message || 'Erreur de connexion au serveur'
        };
    }
}

async function apiRegister(userData) {
    try {
        const response = await fetch(API_CONFIG.REGISTER_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Register error response:', errorText);
            throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        return { success: true, data };
        
    } catch (error) {
        console.error('Erreur d\'inscription:', error);
        return { 
            success: false, 
            error: error.message || 'Erreur lors de l\'inscription'
        };
    }
}

// Fonction pour tester la connexion au backend
async function testBackendConnection() {
    console.log('🔗 Test de connexion au backend...');
    
    try {
        // Vérifier si le serveur est en ligne via /health (plus léger que /docs)
        const healthResponse = await fetch('http://localhost:8000/health');
        if (!healthResponse.ok) {
            console.error('❌ Serveur backend non accessible');
            return false;
        }
        console.log('✅ Serveur backend accessible');

        // On se contente de vérifier la disponibilité, sans créer ni connecter d'utilisateur automatiquement
        return true;
    } catch (error) {
        console.error('❌ Erreur de test:', error);
        return false;
    }
}

// Fonctions de notification améliorées
function showNotification(message, type = 'info', duration = 5000) {
    // Supprimer les notifications existantes
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());
    
    const icons = {
        success: `<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>`,
        error: `<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>`,
        warning: `<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.998-.833-2.732 0L4.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
        </svg>`,
        info: `<svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>`
    };
    
    const notification = document.createElement('div');
    notification.className = `notification fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg border-l-4 transform transition-all duration-300 ${
        type === 'success' ? 'bg-green-50 border-green-500 text-green-700' :
        type === 'error' ? 'bg-red-50 border-red-500 text-red-700' :
        type === 'warning' ? 'bg-yellow-50 border-yellow-500 text-yellow-700' :
        'bg-blue-50 border-blue-500 text-blue-700'
    }`;
    
    notification.innerHTML = `
        <div class="flex items-center">
            ${icons[type] || icons.info}
            <span class="mr-3">${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" 
                    class="ml-auto text-current hover:opacity-75 focus:outline-none">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Animation d'entrée
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 10);
    
    if (duration > 0) {
        setTimeout(() => {
            if (notification.parentNode) {
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    if (notification.parentNode) {
                        notification.remove();
                    }
                }, 300);
            }
        }, duration);
    }
}

// Gestion de la connexion
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const rememberMe = document.getElementById('remember-me')?.checked || false;
    
    if (!username || !password) {
        showNotification('Veuillez remplir tous les champs', 'error');
        return;
    }
    
    // Désactiver le bouton
    const loginButton = document.getElementById('loginButton');
    const buttonText = document.getElementById('buttonText');
    const buttonSpinner = document.getElementById('buttonSpinner');
    
    if (loginButton) {
        loginButton.disabled = true;
        if (buttonText) buttonText.textContent = 'Connexion en cours...';
        if (buttonSpinner) buttonSpinner.classList.remove('hidden');
    }
    
    try {
        const result = await apiLogin(username, password);
        
        if (result.success) {
            showNotification('Connexion réussie ! Redirection...', 'success');
            
            // Stocker remember me
            if (rememberMe) {
                localStorage.setItem('remember_me', 'true');
            }
            
            // Redirection vers la page upload
            setTimeout(() => {
                window.location.href = 'upload.html';
            }, 1000);
            
        } else {
            throw new Error(result.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        
        let errorMessage = 'Erreur de connexion';
        if (error.message.includes('401')) {
            errorMessage = 'Identifiants incorrects';
        } else if (error.message.includes('network') || error.message.includes('Failed to fetch')) {
            errorMessage = 'Impossible de se connecter au serveur. Vérifiez que le serveur est en cours d\'exécution.';
            // Ajouter un bouton pour tester la connexion
            setTimeout(() => {
                const testBtn = document.createElement('button');
                testBtn.className = 'mt-2 text-sm text-blue-600 hover:text-blue-800';
                testBtn.textContent = 'Tester la connexion au serveur';
                testBtn.onclick = () => {
                    testBackendConnection().then(success => {
                        if (success) {
                            showNotification('Serveur accessible ! Réessayez la connexion.', 'success');
                        }
                    });
                };
                document.querySelector('.notification')?.appendChild(testBtn);
            }, 500);
        } else {
            errorMessage = error.message || 'Erreur de connexion';
        }
        
        showNotification(errorMessage, 'error');
        
        // Réactiver le bouton
        if (loginButton) {
            loginButton.disabled = false;
            if (buttonText) buttonText.textContent = 'Se connecter';
            if (buttonSpinner) buttonSpinner.classList.add('hidden');
        }
    }
}

// Gestion de l'inscription
async function handleRegister(event) {
    event.preventDefault();
    
    // Récupérer les données
    const firstName = document.getElementById('firstName')?.value.trim();
    const lastName = document.getElementById('lastName')?.value.trim();
    const email = document.getElementById('email')?.value.trim();
    const username = document.getElementById('username')?.value.trim();
    const password = document.getElementById('password')?.value;
    const confirmPassword = document.getElementById('confirmPassword')?.value;
    
    // Validation basique
    if (!firstName || !lastName || !email || !username || !password || !confirmPassword) {
        showNotification('Veuillez remplir tous les champs', 'error');
        return;
    }
    
    // Vérification des mots de passe
    if (password !== confirmPassword) {
        showNotification('Les mots de passe ne correspondent pas', 'error');
        return;
    }
    
    // Vérification du mot de passe
    if (password.length < 8) {
        showNotification('Le mot de passe doit contenir au moins 8 caractères', 'error');
        return;
    }
    
    // Créer l'objet complet pour l'API
    const apiData = {
        email: email,
        username: username,
        full_name: `${firstName} ${lastName}`,
        password: password
    };
    
    // Désactiver le bouton
    const registerButton = document.getElementById('registerButton');
    const buttonText = document.getElementById('buttonText');
    const buttonSpinner = document.getElementById('buttonSpinner');
    
    if (registerButton) {
        registerButton.disabled = true;
        if (buttonText) buttonText.textContent = 'Création en cours...';
        if (buttonSpinner) buttonSpinner.classList.remove('hidden');
    }
    
    try {
        const result = await apiRegister(apiData);
        
        if (result.success) {
            showNotification('Compte créé avec succès ! Connexion automatique...', 'success');
            
            // Connexion automatique
            const loginResult = await apiLogin(username, password);
            
            if (loginResult.success) {
                setTimeout(() => {
                    window.location.href = 'upload.html';
                }, 1500);
            } else {
                // Rediriger vers la page de connexion
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1500);
            }
            
        } else {
            throw new Error(result.error);
        }
        
    } catch (error) {
        console.error('Erreur:', error);
        
        let errorMessage = 'Erreur lors de la création du compte';
        if (error.message.includes('400') || error.message.includes('409')) {
            errorMessage = 'Email ou nom d\'utilisateur déjà utilisé';
        } else if (error.message.includes('422')) {
            errorMessage = 'Données invalides. Vérifiez les informations saisies.';
        } else {
            errorMessage = error.message || 'Erreur lors de l\'inscription';
        }
        
        showNotification(errorMessage, 'error');
        
        // Réactiver le bouton
        if (registerButton) {
            registerButton.disabled = false;
            if (buttonText) buttonText.textContent = 'Créer mon compte';
            if (buttonSpinner) buttonSpinner.classList.add('hidden');
        }
    }
}

// Validation de mot de passe pour l'inscription
function validatePassword() {
    const password = document.getElementById('password')?.value || '';
    const confirmPassword = document.getElementById('confirmPassword')?.value || '';
    
    // Validation longueur
    const lengthValid = password.length >= 8;
    const lengthCheck = document.getElementById('lengthCheck');
    if (lengthCheck) {
        lengthCheck.className = `w-2 h-2 rounded-full mr-2 ${lengthValid ? 'bg-green-500' : 'bg-red-500'}`;
    }
    
    // Validation complexité
    const hasLetter = /[a-zA-Z]/.test(password);
    const hasNumber = /\d/.test(password);
    const complexityValid = hasLetter && hasNumber;
    const complexityCheck = document.getElementById('complexityCheck');
    if (complexityCheck) {
        complexityCheck.className = `w-2 h-2 rounded-full mr-2 ${complexityValid ? 'bg-green-500' : 'bg-red-500'}`;
    }
    
    // Validation correspondance
    const matchValid = password === confirmPassword && password.length > 0;
    const matchCheck = document.getElementById('matchCheck');
    if (matchCheck) {
        matchCheck.className = `w-2 h-2 rounded-full mr-2 ${matchValid ? 'bg-green-500' : 'bg-red-500'}`;
    }
    
    // Activer/désactiver bouton d'inscription
    const termsChecked = document.getElementById('terms')?.checked || false;
    const registerButton = document.getElementById('registerButton');
    if (registerButton) {
        registerButton.disabled = !(lengthValid && complexityValid && matchValid && termsChecked);
    }
}

// Vérifier l'authentification au chargement
function checkAuth() {
    const currentPage = window.location.pathname.split('/').pop();
    const protectedPages = ['upload.html', 'results.html', 'history.html'];
    
    if (protectedPages.includes(currentPage) && !AuthManager.isAuthenticated()) {
        showNotification('Veuillez vous connecter pour accéder à cette page', 'warning');
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1500);
        return false;
    }
    
    // Si on est sur la page de connexion et déjà connecté
    if ((currentPage === 'login.html' || currentPage === 'register.html') && AuthManager.isAuthenticated()) {
        setTimeout(() => {
            window.location.href = 'upload.html';
        }, 1000);
        return false;
    }
    
    return true;
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔧 Initialisation de l\'authentification...');
    
    // Vérifier l'authentification
    checkAuth();
    
    // Remplir les champs avec les valeurs d'URL (pour les tests)
    const urlParams = new URLSearchParams(window.location.search);
    const username = urlParams.get('username');
    const password = urlParams.get('password');
    
    if (username && document.getElementById('username')) {
        document.getElementById('username').value = username;
    }
    if (password && document.getElementById('password')) {
        document.getElementById('password').value = password;
    }
    
    // Plus d'auto-remplissage avec les identifiants démo,
    // ni de test automatique qui se connecte tout seul.
});

// Exporter les fonctions globales
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.AuthManager = AuthManager;
window.showNotification = showNotification;
window.validatePassword = validatePassword;
window.testBackendConnection = testBackendConnection;

// Ajouter des écouteurs d'événements pour la validation en temps réel
document.addEventListener('input', function(event) {
    if (event.target.id === 'password' || event.target.id === 'confirmPassword' || event.target.id === 'terms') {
        validatePassword();
    }
});