// Configuration globale
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',
    UPLOAD_ENDPOINT: '/api/ocr/process',
    RESULTS_ENDPOINT: '/api/ocr/results',
    AUTH_ENDPOINT: '/api/auth'
};

// Variables globales
const API_BASE_URL = 'http://localhost:8000/api/ocr';
let resultsCurrentResult = null;
let currentTab = 'structured';
let allResults = [];

// Helper DOM sécurisé
class DOMHelper {
    static getElement(id) {
        const element = document.getElementById(id);
        if (!element) {
            console.warn(`Element #${id} not found`);
            return null;
        }
        return element;
    }
    
    static getElements(selector) {
        const elements = document.querySelectorAll(selector);
        if (elements.length === 0) {
            console.warn(`No elements found for selector: ${selector}`);
        }
        return elements;
    }
    
    static safeInnerHTML(element, html) {
        if (element) {
            element.innerHTML = html;
        }
    }
    
    static safeAddEventListener(element, event, handler) {
        if (element) {
            element.addEventListener(event, handler);
            return true;
        }
        return false;
    }
    
    static safeSetText(element, text) {
        if (element) {
            element.textContent = text;
        }
    }
    
    static toggleClass(element, className, state) {
        if (element) {
            if (state) {
                element.classList.add(className);
            } else {
                element.classList.remove(className);
            }
        }
    }
}

// Gestionnaire d'erreurs global
window.onerror = function(message, source, lineno, colno, error) {
    console.error('Erreur globale:', { message, source, lineno, colno, error });
    showNotification(`Erreur: ${message}`, 'error');
    return true;
};

// Initialisation - seulement sur la page results.html
document.addEventListener('DOMContentLoaded', async () => {
    console.log('DOM Content Loaded');
    
    // Vérifier qu'on est bien sur la page results.html
    const loadingState = DOMHelper.getElement('loadingState');
    const resultsContent = DOMHelper.getElement('resultsContent');
    
    if (!loadingState && !resultsContent) {
        // Pas sur la page results.html, initialiser les éléments communs
        console.log('Not on results page, initializing common elements');
        initializeCommonElements();
        return;
    }
    
    // Nous sommes sur results.html, initialiser la page
    await initializeResultsPage();
    
    // Initialiser les éléments communs
    initializeCommonElements();
});

async function initializeResultsPage() {
    console.log('Initializing results page');
    
    // Vérifier s'il y a un process_id dans l'URL
    const urlParams = new URLSearchParams(window.location.search);
    const processId = urlParams.get('process_id');
    
    if (processId) {
        await loadResultById(processId);
    } else {
        // Pas de process_id, afficher un message d'erreur
        showErrorState('Aucun identifiant de traitement fourni');
    }
    
    // Initialiser les event listeners pour cette page
    setupResultsEventListeners();
}

function initializeCommonElements() {
    // Initialiser les tooltips
    initializeTooltips();
    
    // Initialiser l'authentification
    const auth = new AuthManager();
    if (window.location.pathname.includes('upload.html') || 
        window.location.pathname.includes('results.html') || 
        window.location.pathname.includes('history.html')) {
        if (!auth.isAuthenticated() && !window.AuthManager?.isAuthenticated?.()) {
            showNotification('Veuillez vous connecter pour accéder à cette page', 'warning');
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 1000);
            return;
        }
    }
    
    // Afficher les informations utilisateur
    const user = auth.getUser();
    if (user) {
        DOMHelper.getElements('[data-user="username"]').forEach(el => {
            DOMHelper.safeSetText(el, user.username);
        });
        DOMHelper.getElements('[data-user="email"]').forEach(el => {
            DOMHelper.safeSetText(el, user.email);
        });
        DOMHelper.getElements('[data-user="full_name"]').forEach(el => {
            DOMHelper.safeSetText(el, user.full_name);
        });
    }
    
    // Initialiser les boutons de déconnexion
    DOMHelper.getElements('[data-logout]').forEach(button => {
        DOMHelper.safeAddEventListener(button, 'click', (e) => {
            e.preventDefault();
            auth.logout();
        });
    });
}

function setupResultsEventListeners() {
    // Setup pour les onglets
    DOMHelper.getElements('.tab-button').forEach(btn => {
        DOMHelper.safeAddEventListener(btn, 'click', () => {
            const tab = btn.getAttribute('data-tab');
            if (tab) {
                switchTab(tab);
            }
        });
    });
    
    // Setup pour la modale si elle existe
    const resultModal = DOMHelper.getElement('resultModal');
    if (resultModal) {
        DOMHelper.safeAddEventListener(resultModal, 'click', (e) => {
            if (e.target.id === 'resultModal') {
                closeModal();
            }
        });
    }
    
    // Setup pour les filtres si on est sur history.html
    const filterType = DOMHelper.getElement('filterType');
    const searchInput = DOMHelper.getElement('searchInput');
    
    if (filterType) {
        DOMHelper.safeAddEventListener(filterType, 'change', filterResults);
    }
    
    if (searchInput) {
        DOMHelper.safeAddEventListener(searchInput, 'input', debounce(filterResults, 300));
    }
    
    // Setup pour le bouton fermer la modale
    const closeModalBtn = DOMHelper.getElement('closeModal');
    if (closeModalBtn) {
        DOMHelper.safeAddEventListener(closeModalBtn, 'click', closeModal);
    }
}

async function loadResultById(processId) {
    try {
        console.log(`Loading result: ${processId}`);
        const token = localStorage.getItem('auth_token');
        let url = `${API_BASE_URL}/results/${processId}`;
        
        // Ajouter le token en query parameter si disponible
        if (token) {
            url += `?token=${token}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}: ${response.statusText}`);
        }
        
        currentResult = await response.json();
        displayResult(currentResult);
        
    } catch (error) {
        console.error('Erreur de chargement:', error);
        showErrorState(`Erreur lors du chargement: ${error.message}`);
    }
}

function displayResult(result) {
    // Cacher l'état de chargement
    DOMHelper.toggleClass(DOMHelper.getElement('loadingState'), 'hidden', true);
    DOMHelper.toggleClass(DOMHelper.getElement('errorState'), 'hidden', true);
    DOMHelper.toggleClass(DOMHelper.getElement('resultsContent'), 'hidden', false);
    
    // Mettre à jour les informations du document
    DOMHelper.safeSetText(DOMHelper.getElement('fileName'), result.filename || 'Document sans nom');
    DOMHelper.safeSetText(DOMHelper.getElement('documentType'), result.document_type || 'Non spécifié');
    DOMHelper.safeSetText(DOMHelper.getElement('pageCount'), result.total_pages || '1');
    
    if (result.average_confidence !== undefined) {
        const percent = Math.round(result.average_confidence * 100);
        DOMHelper.safeSetText(DOMHelper.getElement('confidenceScore'), `${percent}% confiance`);
    }
    
    // Mettre à jour le statut
    const statusBadge = DOMHelper.getElement('statusBadge');
    if (statusBadge) {
        statusBadge.textContent = 'Terminé';
        statusBadge.className = 'badge status-completed';
    }
    
    // Mettre à jour le process ID
    DOMHelper.safeSetText(DOMHelper.getElement('processId'), result.process_id ? `ID: ${result.process_id}` : '');
    
    // Afficher les données structurées
    if (result.structured_data) {
        displayStructuredData(result.structured_data);
    }
    
    // Afficher le texte brut
    if (result.text) {
        DOMHelper.safeSetText(DOMHelper.getElement('rawText'), result.text);
    }
    
    // Afficher les zones
    if (result.zones && result.zones.length > 0) {
        displayZones(result.zones);
    }
    
    // Afficher l'aperçu si disponible
    if (result.preview_url) {
        displayPreview(result.preview_url);
    }
}

function displayStructuredData(structuredData) {
    const tbody = DOMHelper.getElement('structuredData');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (structuredData.fields) {
        Object.entries(structuredData.fields).forEach(([fieldName, fieldValues]) => {
            if (Array.isArray(fieldValues) && fieldValues.length > 0) {
                fieldValues.forEach(fieldValue => {
                    const row = document.createElement('tr');
                    const value = fieldValue.value || (typeof fieldValue === 'string' ? fieldValue : JSON.stringify(fieldValue));
                    const confidence = fieldValue.confidence !== undefined ? 
                        `${Math.round(fieldValue.confidence * 100)}%` : 'N/A';
                    
                    row.innerHTML = `
                        <td class="font-medium">${fieldName}</td>
                        <td>${value}</td>
                        <td>${confidence}</td>
                    `;
                    tbody.appendChild(row);
                });
            }
        });
    }
    
    // Si pas de champs, afficher les entités
    if (structuredData.entities && Object.keys(structuredData.entities).length > 0) {
        Object.entries(structuredData.entities).forEach(([entityType, values]) => {
            if (Array.isArray(values)) {
                values.forEach(value => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="font-medium">${entityType}</td>
                        <td>${value}</td>
                        <td>N/A</td>
                    `;
                    tbody.appendChild(row);
                });
            }
        });
    }
}

function displayZones(zones) {
    const zonesList = DOMHelper.getElement('zonesList');
    if (!zonesList) return;
    
    zonesList.innerHTML = zones.map((zone, index) => `
        <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex justify-between items-center mb-2">
                <span class="font-medium">Zone ${index + 1}</span>
                <span class="text-xs px-2 py-1 bg-gray-100 rounded">${zone.type || 'texte'}</span>
            </div>
            ${zone.text ? `<p class="text-sm text-gray-700 mt-2">${zone.text}</p>` : ''}
            ${zone.position ? `
                <p class="text-xs text-gray-500 mt-2">
                    Position: (${zone.position.x}, ${zone.position.y}) - 
                    Taille: ${zone.position.width}x${zone.position.height}
                </p>
            ` : ''}
        </div>
    `).join('');
}

function displayPreview(previewUrl) {
    const previewEl = DOMHelper.getElement('documentPreview');
    if (previewEl) {
        previewEl.innerHTML = `
            <img src="${previewUrl}" alt="Aperçu du document" class="w-full h-auto rounded-lg shadow">
        `;
    }
}

function showErrorState(message) {
    DOMHelper.toggleClass(DOMHelper.getElement('loadingState'), 'hidden', true);
    DOMHelper.toggleClass(DOMHelper.getElement('resultsContent'), 'hidden', true);
    DOMHelper.toggleClass(DOMHelper.getElement('errorState'), 'hidden', false);
    DOMHelper.safeSetText(DOMHelper.getElement('errorMessage'), message);
}

function switchTab(tabName) {
    currentTab = tabName;
    
    // Mettre à jour les boutons d'onglets
    DOMHelper.getElements('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeTab) activeTab.classList.add('active');
    
    // Afficher/masquer les contenus
    DOMHelper.getElements('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    const targetTab = DOMHelper.getElement(`${tabName}Tab`);
    DOMHelper.toggleClass(targetTab, 'hidden', false);
}

// Exposer les fonctions globales
window.switchTab = switchTab;

window.exportResult = function(format) {
    if (!currentResult || !currentResult.process_id) {
        alert('Aucun résultat à exporter');
        return;
    }
    
    const url = `${API_BASE_URL}/results/${currentResult.process_id}/download/${format}`;
    const token = localStorage.getItem('auth_token');
    const finalUrl = token ? `${url}?token=${token}` : url;
    
    window.open(finalUrl, '_blank');
};

window.processAnother = function() {
    window.location.href = 'upload.html';
};

window.saveToHistory = function() {
    if (currentResult) {
        // Sauvegarder dans localStorage
        let history = JSON.parse(localStorage.getItem('ocr_history') || '[]');
        history.push(currentResult);
        localStorage.setItem('ocr_history', JSON.stringify(history));
        showNotification('Résultat sauvegardé dans l\'historique', 'success');
    }
};

window.shareResult = function() {
    if (currentResult && currentResult.process_id) {
        const url = `${window.location.origin}${window.location.pathname}?process_id=${currentResult.process_id}`;
        navigator.clipboard.writeText(url).then(() => {
            showNotification('Lien copié dans le presse-papier !', 'success');
        }).catch(() => {
            // Fallback pour les navigateurs qui ne supportent pas clipboard API
            const textArea = document.createElement('textarea');
            textArea.value = url;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showNotification('Lien copié dans le presse-papier !', 'success');
        });
    }
};

// Fonctions pour history.html
function showTab(tabName) {
    currentTab = tabName;
    
    // Mettre à jour l'état des onglets
    DOMHelper.getElements('.tab-button').forEach(btn => {
        btn.classList.remove('active');
        btn.classList.add('text-gray-500');
    });
    
    const activeTab = DOMHelper.getElement(`tab-${tabName}`);
    if (activeTab) {
        activeTab.classList.add('active');
        activeTab.classList.remove('text-gray-500');
    }
    
    // Filtrer les résultats
    filterResults();
}

function filterResults() {
    const filterTypeEl = DOMHelper.getElement('filterType');
    const searchInputEl = DOMHelper.getElement('searchInput');
    
    if (!filterTypeEl || !searchInputEl) return;
    
    const filterType = filterTypeEl.value;
    const searchQuery = searchInputEl.value.toLowerCase();
    
    let filteredResults = [...allResults];
    
    // Filtrer par type
    if (filterType !== 'all') {
        filteredResults = filteredResults.filter(result => 
            result.document_type === filterType
        );
    }
    
    // Filtrer par recherche
    if (searchQuery) {
        filteredResults = filteredResults.filter(result => 
            result.filename.toLowerCase().includes(searchQuery) ||
            JSON.stringify(result.extracted_data).toLowerCase().includes(searchQuery)
        );
    }
    
    // Filtrer par onglet
    switch (currentTab) {
        case 'recent':
            // Trier par date récente (limiter aux 10 derniers)
            filteredResults.sort((a, b) => new Date(b.timestamp || b.extraction_date) - new Date(a.timestamp || a.extraction_date));
            filteredResults = filteredResults.slice(0, 10);
            break;
            
        case 'high-confidence':
            // Résultats avec haute confiance (> 90%)
            filteredResults = filteredResults.filter(result => result.confidence >= 0.9);
            filteredResults.sort((a, b) => b.confidence - a.confidence);
            break;
            
        case 'all':
        default:
            // Trier par date récente
            filteredResults.sort((a, b) => new Date(b.timestamp || b.extraction_date) - new Date(a.timestamp || a.extraction_date));
            break;
    }
    
    displayResults(filteredResults);
}

function displayResults(results = null) {
    const container = DOMHelper.getElement('resultsContainer');
    if (!container) return;
    
    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="text-center py-12">
                <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                <h3 class="mt-2 text-sm font-medium text-gray-900">Aucun résultat</h3>
                <p class="mt-1 text-sm text-gray-500">Aucun résultat ne correspond aux critères.</p>
                <div class="mt-6">
                    <a href="upload.html" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
                        Télécharger un document
                    </a>
                </div>
            </div>
        `;
        return;
    }
    
    let html = '<div class="space-y-4">';
    
    results.forEach(result => {
        const date = new Date(result.timestamp || result.extraction_date);
        const formattedDate = date.toLocaleDateString('fr-FR', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const confidencePercent = Math.round(result.confidence * 100);
        const confidenceColor = confidencePercent >= 90 ? 'green' : confidencePercent >= 70 ? 'yellow' : 'red';
        
        html += `
            <div class="result-card bg-white rounded-lg shadow-sm p-6">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-medium text-gray-900">${result.filename}</h3>
                        <p class="text-sm text-gray-500 mt-1">Traité le ${formattedDate}</p>
                        <span class="inline-block mt-2 px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800">
                            ${result.document_type || 'Document'}
                        </span>
                    </div>
                    <div class="flex items-center space-x-2">
                        <span class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-${confidenceColor}-100 text-${confidenceColor}-800">
                            ${confidencePercent}% confiance
                        </span>
                    </div>
                </div>
                
                <!-- Données extraites -->
                <div class="mb-4">
                    <h4 class="text-sm font-medium text-gray-700 mb-2">Données extraites :</h4>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                        ${renderExtractedFields(result.extracted_data)}
                    </div>
                </div>
                
                <!-- Actions -->
                <div class="flex justify-end space-x-3 mt-4">
                    <button onclick="viewResultDetails('${result.process_id}')" class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                        </svg>
                        Voir Détails
                    </button>
                    <button onclick="exportResultById('${result.process_id}', 'json')" class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        JSON
                    </button>
                    <button onclick="exportResultById('${result.process_id}', 'csv')" class="px-4 py-2 bg-green-600 text-white rounded-md text-sm font-medium hover:bg-green-700 flex items-center">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        CSV
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function renderExtractedFields(data) {
    if (!data || !data.fields) return '<p class="text-gray-500">Aucune donnée extraite</p>';
    
    let html = '';
    const fields = data.fields;
    
    // Prendre les 4 premiers champs les plus importants
    const importantFields = Object.entries(fields).slice(0, 4);
    
    importantFields.forEach(([fieldName, fieldValues]) => {
        if (fieldValues && fieldValues.length > 0) {
            const value = fieldValues[0].value;
            html += `
                <div class="bg-gray-50 rounded-lg p-3">
                    <p class="text-xs font-medium text-gray-500 uppercase mb-1">${fieldName}</p>
                    <p class="text-sm font-semibold text-gray-900 truncate">${value}</p>
                </div>
            `;
        }
    });
    
    return html;
}

async function viewResultDetails(processId) {
    try {
        showLoadingModal();
        
        // Récupérer les détails du résultat
        const result = allResults.find(r => r.process_id === processId);
        
        if (!result) {
            throw new Error('Résultat non trouvé');
        }
        
        const modalContent = DOMHelper.getElement('modalContent');
        if (!modalContent) {
            throw new Error('Modal content non trouvé');
        }
        
        modalContent.innerHTML = `
            <div class="space-y-6">
                <!-- En-tête -->
                <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <div class="flex justify-between items-start">
                        <div>
                            <h4 class="text-lg font-semibold text-gray-900">${result.filename}</h4>
                            <p class="text-sm text-gray-600">Type: ${result.document_type}</p>
                            <p class="text-sm text-gray-600">Confiance: ${Math.round(result.confidence * 100)}%</p>
                        </div>
                        <span class="px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                            ✓ Extrait
                        </span>
                    </div>
                </div>
                
                <!-- Données extraites complètes -->
                <div>
                    <h5 class="text-md font-medium text-gray-900 mb-3">Données extraites :</h5>
                    <div class="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                        <pre class="text-sm text-gray-800 whitespace-pre-wrap">${JSON.stringify(result.extracted_data, null, 2)}</pre>
                    </div>
                </div>
                
                <!-- Zones détectées -->
                ${result.zones && result.zones.length > 0 ? `
                <div>
                    <h5 class="text-md font-medium text-gray-900 mb-3">Zones détectées (${result.zones.length}) :</h5>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                        ${result.zones.map((zone, index) => `
                            <div class="border border-gray-200 rounded-lg p-3">
                                <div class="flex justify-between items-center mb-2">
                                    <span class="text-sm font-medium text-gray-700">Zone ${index + 1}</span>
                                    <span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">
                                        ${zone.type || 'texte'}
                                    </span>
                                </div>
                                <div class="text-xs text-gray-600">
                                    Position: (${zone.x}, ${zone.y}) - Taille: ${zone.width}x${zone.height}
                                </div>
                                ${zone.text ? `<div class="mt-2 text-sm text-gray-800 truncate">"${zone.text}"</div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
                
                <!-- Texte brut -->
                ${result.raw_text ? `
                <div>
                    <h5 class="text-md font-medium text-gray-900 mb-3">Texte brut extrait :</h5>
                    <div class="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
                        <p class="text-sm text-gray-800 whitespace-pre-wrap">${result.raw_text}</p>
                    </div>
                </div>
                ` : ''}
                
                <!-- Métadonnées -->
                <div>
                    <h5 class="text-md font-medium text-gray-900 mb-3">Métadonnées :</h5>
                    <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div class="bg-gray-50 rounded-lg p-3">
                            <p class="text-xs text-gray-500">Temps de traitement</p>
                            <p class="text-sm font-medium">${result.processing_time ? result.processing_time.toFixed(2) + 's' : 'N/A'}</p>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3">
                            <p class="text-xs text-gray-500">Nombre de pages</p>
                            <p class="text-sm font-medium">${result.page_count || 1}</p>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-3">
                            <p class="text-xs text-gray-500">Process ID</p>
                            <p class="text-sm font-medium font-mono">${result.process_id}</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        DOMHelper.safeSetText(DOMHelper.getElement('modalTitle'), `Résultat: ${result.filename}`);
        openModal();
        
    } catch (error) {
        console.error('Erreur:', error);
        showErrorModal('Impossible de charger les détails');
    }
}

// Export depuis l'historique
async function exportResultById(processId, format) {
    try {
        showNotification(`Export en cours au format ${format.toUpperCase()}...`, 'info');
        
        const token = localStorage.getItem('auth_token');
        let downloadUrl;
        
        if (token) {
            // Export via l'API
            const response = await fetch(`${API_BASE_URL}/results/${processId}/export/${format}?token=${token}`);
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                downloadFile(url, `ocr_result_${processId}.${format}`);
            } else {
                // Fallback sur l'export local
                exportLocalResult(processId, format);
            }
        } else {
            // Export local
            exportLocalResult(processId, format);
        }
        
    } catch (error) {
        console.error('Erreur d\'export:', error);
        showNotification('Erreur lors de l\'export', 'error');
    }
}

function exportLocalResult(processId, format) {
    const result = allResults.find(r => r.process_id === processId);
    
    if (!result) {
        showNotification('Résultat non trouvé', 'error');
        return;
    }
    
    let content, filename, mimeType;
    
    switch (format) {
        case 'json':
            content = JSON.stringify(result, null, 2);
            filename = `ocr_result_${processId}.json`;
            mimeType = 'application/json';
            break;
            
        case 'csv':
            content = convertToCSV(result);
            filename = `ocr_result_${processId}.csv`;
            mimeType = 'text/csv';
            break;
            
        case 'excel':
            // Pour Excel, on utiliserait une bibliothèque comme SheetJS
            // Ici, on exporte en CSV pour simplifier
            content = convertToCSV(result);
            filename = `ocr_result_${processId}.csv`;
            mimeType = 'text/csv';
            break;
            
        default:
            showNotification('Format non supporté', 'error');
            return;
    }
    
    const blob = new Blob([content], { type: mimeType });
    const url = window.URL.createObjectURL(blob);
    downloadFile(url, filename);
}

function convertToCSV(result) {
    let csv = 'Field,Value,Confidence\n';
    
    if (result.extracted_data && result.extracted_data.fields) {
        Object.entries(result.extracted_data.fields).forEach(([fieldName, fieldValues]) => {
            fieldValues.forEach(fieldValue => {
                csv += `"${fieldName}","${fieldValue.value}",${fieldValue.confidence}\n`;
            });
        });
    }
    
    return csv;
}

function downloadFile(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showNotification('Export terminé avec succès', 'success');
}

// Utilitaires
function showLoading() {
    const container = DOMHelper.getElement('resultsContainer');
    if (!container) return;
    
    container.innerHTML = `
        <div class="text-center py-12">
            <svg class="animate-spin mx-auto h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p class="mt-2 text-sm text-gray-600">Chargement des résultats...</p>
        </div>
    `;
}

function showLoadingModal() {
    const modalContent = DOMHelper.getElement('modalContent');
    if (!modalContent) return;
    
    modalContent.innerHTML = `
        <div class="text-center py-8">
            <svg class="animate-spin mx-auto h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p class="mt-2 text-sm text-gray-600">Chargement des détails...</p>
        </div>
    `;
}

function showError(message) {
    const container = DOMHelper.getElement('resultsContainer');
    if (!container) return;
    
    container.innerHTML = `
        <div class="text-center py-12">
            <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <h3 class="mt-2 text-sm font-medium text-gray-900">Erreur</h3>
            <p class="mt-1 text-sm text-gray-500">${message}</p>
            <div class="mt-6">
                <button onclick="loadResults()" class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
                    Réessayer
                </button>
            </div>
        </div>
    `;
}

function showErrorModal(message) {
    const modalContent = DOMHelper.getElement('modalContent');
    if (!modalContent) return;
    
    modalContent.innerHTML = `
        <div class="text-center py-8">
            <svg class="mx-auto h-12 w-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <h3 class="mt-2 text-sm font-medium text-gray-900">Erreur</h3>
            <p class="mt-1 text-sm text-gray-500">${message}</p>
        </div>
    `;
}

function showNotification(message, type = 'info') {
    // Supprimer les notifications existantes
    document.querySelectorAll('.notification').forEach(n => n.remove());

    const colors = {
        info: 'blue',
        success: 'green',
        error: 'red',
        warning: 'yellow'
    };
    
    const color = colors[type];
    
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-4 py-3 rounded-md shadow-lg z-50 bg-${color}-100 border border-${color}-400 text-${color}-700 notification`;
    notification.innerHTML = `
        <div class="flex items-center">
            ${getNotificationIcon(type)}
            <span class="ml-2">${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

function getNotificationIcon(type) {
    const icons = {
        success: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>`,
        error: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>`,
        warning: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.998-.833-2.732 0L4.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
        </svg>`,
        info: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>`
    };
    return icons[type] || icons.info;
}

function openModal() {
    const modal = DOMHelper.getElement('resultModal');
    DOMHelper.toggleClass(modal, 'hidden', false);
}

function closeModal() {
    const modal = DOMHelper.getElement('resultModal');
    DOMHelper.toggleClass(modal, 'hidden', true);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function initializeTooltips() {
    const tooltips = DOMHelper.getElements('.tooltip');
    tooltips.forEach(tooltip => {
        DOMHelper.safeAddEventListener(tooltip, 'mouseenter', showTooltip);
        DOMHelper.safeAddEventListener(tooltip, 'mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const tooltip = event.currentTarget;
    const text = tooltip.getAttribute('data-tooltip');
    if (!text) return;

    const tooltipEl = document.createElement('div');
    tooltipEl.className = 'tooltip-text';
    tooltipEl.textContent = text;
    tooltip.appendChild(tooltipEl);
}

function hideTooltip(event) {
    const tooltip = event.currentTarget;
    const tooltipEl = tooltip.querySelector('.tooltip-text');
    if (tooltipEl) {
        tooltip.removeChild(tooltipEl);
    }
}

// Fonctions utilitaires
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    const icons = {
        pdf: `<svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clip-rule="evenodd"/>
        </svg>`,
        jpg: `<svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
        </svg>`,
        jpeg: `<svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
        </svg>`,
        png: `<svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
        </svg>`,
        tiff: `<svg class="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
        </svg>`,
        tif: `<svg class="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/>
        </svg>`
    };
    return icons[extension] || `<svg class="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/>
    </svg>`;
}

// Gestion de l'authentification
class AuthManager {
    constructor() {
        this.tokenKey = 'auth_token';
        this.userKey = 'user_data';
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
        window.location.href = 'login.html';
    }

    async checkAuth() {
        if (!this.isAuthenticated() && 
            !window.location.pathname.includes('login.html') && 
            !window.location.pathname.includes('register.html') && 
            !window.location.pathname.includes('index.html')) {
            window.location.href = 'login.html';
        }
    }

    async testConnection() {
        const token = this.getToken();
        if (!token) return false;
        
        try {
            const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.AUTH_ENDPOINT}/me?token=${token}`);
            return response.ok;
        } catch (error) {
            return false;
        }
    }
}

// API Client
class APIClient {
    constructor() {
        this.baseURL = CONFIG.API_BASE_URL;
    }

    getToken() {
        const auth = new AuthManager();
        return auth.getToken();
    }

    async request(endpoint, options = {}) {
        const token = this.getToken();
        let url = `${this.baseURL}${endpoint}`;
        
        // Ajouter le token comme query parameter
        if (token) {
            const separator = url.includes('?') ? '&' : '?';
            url = `${url}${separator}token=${token}`;
        }
        
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (!response.ok) {
                if (response.status === 401 || response.status === 403) {
                    const auth = new AuthManager();
                    auth.logout();
                    showNotification('Session expirée. Veuillez vous reconnecter.', 'error');
                    window.location.href = 'login.html';
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    async uploadFile(file, language = 'fra+eng', onProgress = null) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('language', language);

        const token = this.getToken();
        let url = `${this.baseURL}${CONFIG.UPLOAD_ENDPOINT}`;
        
        if (token) {
            url = `${url}?token=${token}`;
        }
        
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            xhr.upload.addEventListener('progress', (event) => {
                if (onProgress && event.lengthComputable) {
                    const progress = Math.round((event.loaded / event.total) * 100);
                    onProgress(progress);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve(response);
                    } catch (error) {
                        console.error('Erreur parsing réponse:', xhr.responseText);
                        reject(new Error(`Réponse invalide du serveur: ${xhr.responseText}`));
                    }
                } else {
                    let errorMessage = `Upload failed: ${xhr.statusText}`;
                    try {
                        const errorResponse = JSON.parse(xhr.responseText);
                        errorMessage = errorResponse.detail || errorResponse.message || errorMessage;
                    } catch (e) {
                        errorMessage = xhr.responseText || errorMessage;
                    }
                    reject(new Error(errorMessage));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                reject(new Error('Upload aborted'));
            });

            xhr.open('POST', url);
            xhr.send(formData);
        });
    }

    async getCurrentUser() {
        const token = this.getToken();
        if (!token) return null;
        
        try {
            const response = await fetch(`${this.baseURL}${CONFIG.AUTH_ENDPOINT}/me?token=${token}`);
            
            if (response.ok) {
                const user = await response.json();
                const auth = new AuthManager();
                auth.setUser(user);
                return user;
            }
        } catch (error) {
            console.error('Erreur récupération utilisateur:', error);
        }
        return null;
    }

    async login(username, password) {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.AUTH_ENDPOINT}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.access_token) {
            const auth = new AuthManager();
            auth.setToken(data.access_token);
            
            const user = await this.getCurrentUser();
            if (user) {
                auth.setUser(user);
            }
            
            return data;
        } else {
            throw new Error('Token non reçu');
        }
    }

    async register(userData) {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.AUTH_ENDPOINT}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
}

// Initialiser le client API
const api = new APIClient();
const auth = new AuthManager();

// Exposer les fonctions globales
window.showNotification = showNotification;
window.formatFileSize = formatFileSize;
window.formatDate = formatDate;
window.auth = auth;
window.api = api;
window.exportResultById = exportResultById;
window.viewResultDetails = viewResultDetails;
window.closeModal = closeModal;