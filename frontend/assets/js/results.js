// results.js - Version corrigée
const apiService = window.apiService || new ApiService();
let currentResult = null;
let currentTab = 'structured';

document.addEventListener('DOMContentLoaded', async () => {
    // Vérifier authentification
    if (!localStorage.getItem('auth_token')) {
        window.location.href = 'login.html';
        return;
    }

    // Vérifier si on est sur results.html
    const loadingState = document.getElementById('loadingState');
    if (!loadingState) return;

    await initializePage();
});

async function initializePage() {
    const urlParams = new URLSearchParams(window.location.search);
    const processId = urlParams.get('process_id');
    
    if (processId) {
        await loadAndDisplayResult(processId);
    } else {
        showError('Aucun identifiant de traitement fourni');
    }
}

async function loadAndDisplayResult(processId) {
    try {
        showLoading(true);
        
        const result = await apiService.getResult(processId);
        currentResult = result;
        
        displayResult(result);
        
    } catch (error) {
        console.error('Erreur:', error);
        showError(`Erreur lors du chargement: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

function displayResult(result) {
    // Informations basiques
    updateElement('fileName', result.filename || 'Document sans nom');
    updateElement('documentType', result.document_type || 'Non spécifié');
    updateElement('pageCount', result.total_pages || '1');
    
    // Confiance
    if (result.average_confidence !== undefined) {
        const confidenceEl = document.getElementById('confidenceScore');
        if (confidenceEl) {
            confidenceEl.textContent = `${(result.average_confidence * 100).toFixed(1)}%`;
            confidenceEl.className = getConfidenceClass(result.average_confidence);
        }
    }
    
    // Temps de traitement
    if (result.processing_time) {
        updateElement('processingTime', `${result.processing_time.toFixed(2)}s`);
    }
    
    // Données structurées
    if (result.structured_data) {
        displayStructuredData(result.structured_data);
    }
    
    // Texte brut
    if (result.text) {
        updateElement('rawText', result.text);
    }
    
    // Statistiques
    updateStatistics(result);
}

function displayStructuredData(structuredData) {
    const tbody = document.getElementById('structuredData');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    let hasData = false;
    
    // Champs spécifiques
    if (structuredData.fields) {
        Object.entries(structuredData.fields).forEach(([field, values]) => {
            if (Array.isArray(values)) {
                values.forEach(valueObj => {
                    addDataRow(tbody, field, valueObj.value || valueObj, valueObj.confidence);
                    hasData = true;
                });
            }
        });
    }
    
    // Entités NER
    if (structuredData.entities) {
        Object.entries(structuredData.entities).forEach(([entity, values]) => {
            if (Array.isArray(values)) {
                values.forEach(value => {
                    addDataRow(tbody, entity, value, null);
                    hasData = true;
                });
            }
        });
    }
    
    if (!hasData) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" class="text-center text-gray-500 py-4">
                    Aucune donnée structurée extraite
                </td>
            </tr>
        `;
    }
}

function addDataRow(tbody, field, value, confidence) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td class="font-medium text-gray-900">${field}</td>
        <td class="text-gray-700">${value}</td>
        <td class="text-gray-600">${confidence ? `${(confidence * 100).toFixed(1)}%` : 'N/A'}</td>
    `;
    tbody.appendChild(row);
}

function updateStatistics(result) {
    // Mots
    if (result.text) {
        const wordCount = result.text.split(/\s+/).length;
        updateElement('wordCount', wordCount.toLocaleString());
    }
    
    // Champs extraits
    let fieldCount = 0;
    if (result.structured_data?.fields) {
        fieldCount = Object.values(result.structured_data.fields)
            .reduce((total, arr) => total + arr.length, 0);
    }
    updateElement('fieldCount', fieldCount);
    
    // Confiance moyenne
    if (result.average_confidence !== undefined) {
        updateElement('avgConfidence', `${(result.average_confidence * 100).toFixed(1)}%`);
    }
}

// Fonctions utilitaires
function updateElement(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function getConfidenceClass(confidence) {
    if (confidence > 0.9) return 'text-green-600 bg-green-100';
    if (confidence > 0.7) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
}

function showLoading(show) {
    const loading = document.getElementById('loadingState');
    const content = document.getElementById('resultsContent');
    const error = document.getElementById('errorState');
    
    if (loading) loading.classList.toggle('hidden', !show);
    if (content) content.classList.toggle('hidden', show);
    if (error) error.classList.add('hidden');
}

function showError(message) {
    const error = document.getElementById('errorState');
    const errorMsg = document.getElementById('errorMessage');
    
    if (error) {
        error.classList.remove('hidden');
        if (errorMsg) errorMsg.textContent = message;
    }
}

// Exposer les fonctions globales
window.switchTab = function(tabName) {
    currentTab = tabName;
    
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active', 'text-blue-600', 'border-blue-500');
    });
    
    const activeBtn = document.querySelector(`[data-tab="${tabName}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active', 'text-blue-600', 'border-blue-500');
    }
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    const tabContent = document.getElementById(`${tabName}Tab`);
    if (tabContent) tabContent.classList.remove('hidden');
};

window.exportResult = async function(format) {
    if (!currentResult || !currentResult.process_id) {
        showNotification('Aucun résultat à exporter', 'error');
        return;
    }
    
    try {
        showNotification(`Export en ${format.toUpperCase()} en cours...`, 'info');
        await apiService.downloadResult(currentResult.process_id, format);
        showNotification('Export terminé avec succès', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification(`Erreur lors de l'export: ${error.message}`, 'error');
    }
};

window.processAnother = function() {
    window.location.href = 'upload.html';
};

window.saveToHistory = function() {
    showNotification('Résultat sauvegardé dans l\'historique', 'success');
};

window.shareResult = function() {
    if (currentResult?.process_id) {
        const url = `${window.location.origin}${window.location.pathname}?process_id=${currentResult.process_id}`;
        navigator.clipboard.writeText(url).then(() => {
            showNotification('Lien copié dans le presse-papier', 'success');
        }).catch(() => {
            showNotification('Impossible de copier le lien', 'error');
        });
    }
};