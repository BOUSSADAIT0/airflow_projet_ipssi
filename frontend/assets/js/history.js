// history.js - Version corrigée avec données réelles
const apiService = window.apiService || new ApiService();
let historyData = [];
let filteredData = [];
let currentPage = 1;
const itemsPerPage = 10;

document.addEventListener('DOMContentLoaded', initPage);

async function initPage() {
    // Vérifier authentification
    if (!localStorage.getItem('auth_token')) {
        window.location.href = 'login.html';
        return;
    }

    await loadHistory();
    setupEventListeners();

    // Rafraîchissement auto toutes les 30 s : affiche les nouveaux résultats (ex. traités par Airflow)
    setInterval(loadHistory, 30000);
}

async function loadHistory() {
    try {
        showLoading(true);
        showEmptyState(false);
        
        // Charger depuis l'API (réponse { history: [...] } ou tableau)
        const data = await apiService.getHistory();
        historyData = (data && data.history) ? data.history : (Array.isArray(data) ? data : []);
        
        // Appliquer les filtres
        applyFilters();
        
        // Mettre à jour les statistiques
        updateStatistics();
        
    } catch (error) {
        console.error('Erreur chargement historique:', error);
        showNotification('Erreur lors du chargement de l\'historique', 'error');
        showEmptyState(true);
    } finally {
        showLoading(false);
    }
}

function applyFilters() {
    const statusFilter = getValue('statusFilter');
    const typeFilter = getValue('typeFilter');
    const periodFilter = getValue('periodFilter');
    const searchQuery = getValue('searchInput').toLowerCase();
    
    filteredData = historyData.filter(item => {
        // Filtre statut
        if (statusFilter !== 'all' && item.status !== statusFilter) return false;
        
        // Filtre type
        if (typeFilter !== 'all' && item.document_type !== typeFilter) return false;
        
        // Filtre période
        if (periodFilter !== 'all') {
            if (!item.upload_date) return false;
            const itemDate = new Date(item.upload_date);
            const now = new Date();
            
            switch(periodFilter) {
                case 'today':
                    return itemDate.toDateString() === now.toDateString();
                case 'week':
                    const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);
                    return itemDate >= weekAgo;
                case 'month':
                    const monthAgo = new Date(now - 30 * 24 * 60 * 60 * 1000);
                    return itemDate >= monthAgo;
                case 'year':
                    const yearAgo = new Date(now - 365 * 24 * 60 * 60 * 1000);
                    return itemDate >= yearAgo;
            }
        }
        
        // Filtre recherche
        if (searchQuery) {
            const searchIn = [
                item.filename,
                item.original_filename,
                JSON.stringify(item.extracted_data || {})
            ].join(' ').toLowerCase();
            
            return searchIn.includes(searchQuery);
        }
        
        return true;
    });
    
    // Trier par date (plus récent d'abord)
    filteredData.sort((a, b) => {
        const dateA = new Date(a.upload_date || a.created_at || 0);
        const dateB = new Date(b.upload_date || b.created_at || 0);
        return dateB - dateA;
    });
    
    updateDisplay();
}

function updateDisplay() {
    updateTable();
    updatePagination();
    updateResultsCount();
}

function updateTable() {
    const tableBody = document.getElementById('historyTable');
    const emptyState = document.getElementById('emptyState');
    
    if (!tableBody) return;
    
    if (filteredData.length === 0) {
        tableBody.innerHTML = '';
        if (emptyState) emptyState.classList.remove('hidden');
        return;
    }
    
    if (emptyState) emptyState.classList.add('hidden');
    
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageItems = filteredData.slice(start, end);
    
    tableBody.innerHTML = pageItems.map(item => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    ${getFileIcon(item.filename)}
                    <div class="ml-4">
                        <div class="text-sm font-medium text-gray-900 truncate max-w-xs">
                            ${item.filename || 'Document'}
                        </div>
                        <div class="text-sm text-gray-500">
                            ${formatFileSize(item.file_size || 0)}
                            ${item.total_pages ? ` · ${item.total_pages} pages` : ''}
                        </div>
                    </div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                      ${getTypeColor(item.document_type)}">
                    ${getDocumentTypeLabel(item.document_type)}
                </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                ${getStatusBadge(item.status)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
                ${item.average_confidence ? `
                    <div class="flex items-center">
                        <div class="w-24 bg-gray-200 rounded-full h-2 mr-2">
                            <div class="h-2 rounded-full ${getConfidenceColor(item.average_confidence)}"
                                 style="width: ${item.average_confidence * 100}%"></div>
                        </div>
                        <span class="text-sm text-gray-600">${(item.average_confidence * 100).toFixed(0)}%</span>
                    </div>
                ` : '<span class="text-gray-400">-</span>'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${formatDate(item.upload_date || item.created_at)}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                ${item.processing_time ? `${item.processing_time.toFixed(1)}s` : '-'}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <div class="flex space-x-2">
                    ${item.status === 'completed' ? `
                        <button onclick="viewResult('${item.process_id || item.id}')"
                                class="text-blue-600 hover:text-blue-900"
                                title="Voir les résultats">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                            </svg>
                        </button>
                        <button onclick="exportSingle('${item.process_id || item.id}')"
                                class="text-green-600 hover:text-green-900"
                                title="Exporter">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                            </svg>
                        </button>
                    ` : ''}
                    <button onclick="openDeleteModal('${item.process_id || item.id}', '${item.filename || 'Document'}')"
                            class="text-red-600 hover:text-red-900"
                            title="Supprimer">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function exportSingle(processId) {
    try {
        showNotification('Export en cours...', 'info');
        await apiService.downloadResult(processId, 'json');
        showNotification('Document exporté avec succès', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showNotification(`Erreur d'export: ${error.message}`, 'error');
    }
}

async function deleteItem(processId) {
    try {
        await apiService.deleteResult(processId);
        
        // Mettre à jour les données locales
        historyData = historyData.filter(item => item.process_id !== processId);
        filteredData = filteredData.filter(item => item.process_id !== processId);
        
        updateDisplay();
        updateStatistics();
        showNotification('Document supprimé avec succès', 'success');
        
    } catch (error) {
        console.error('Delete error:', error);
        showNotification(`Erreur lors de la suppression: ${error.message}`, 'error');
    }
}

function updateStatistics() {
    const totalDocs = historyData.length;
    const completedDocs = historyData.filter(d => d.status === 'completed').length;
    const successRate = totalDocs > 0 ? Math.round((completedDocs / totalDocs) * 100) : 0;
    
    const totalProcessingTime = historyData
        .filter(d => d.processing_time)
        .reduce((sum, d) => sum + d.processing_time, 0);
    
    const avgProcessingTime = completedDocs > 0 ? 
        (totalProcessingTime / completedDocs).toFixed(1) : 0;
    
    const totalPages = historyData.reduce((sum, d) => sum + (d.total_pages || 1), 0);
    
    updateElement('totalDocuments', totalDocs.toLocaleString());
    updateElement('successRate', `${successRate}%`);
    updateElement('avgProcessingTime', `${avgProcessingTime}s`);
    updateElement('totalPages', totalPages.toLocaleString());
}

// Fonctions utilitaires
function getValue(id) {
    const el = document.getElementById(id);
    return el ? el.value : '';
}

function updateElement(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function getTypeColor(type) {
    const colors = {
        'invoice': 'bg-red-100 text-red-800',
        'receipt': 'bg-green-100 text-green-800',
        'contract': 'bg-yellow-100 text-yellow-800',
        'form': 'bg-purple-100 text-purple-800',
        'letter': 'bg-blue-100 text-blue-800',
        'report': 'bg-indigo-100 text-indigo-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
}

function getConfidenceColor(confidence) {
    if (confidence > 0.9) return 'bg-green-500';
    if (confidence > 0.7) return 'bg-yellow-500';
    return 'bg-red-500';
}

function getDocumentTypeLabel(type) {
    const labels = {
        'invoice': 'Facture',
        'receipt': 'Reçu',
        'contract': 'Contrat',
        'form': 'Formulaire',
        'letter': 'Lettre',
        'report': 'Rapport'
    };
    return labels[type] || type || 'Document';
}

function getStatusBadge(status) {
    const badges = {
        'completed': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Terminé</span>',
        'processing': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">En cours</span>',
        'failed': '<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">Échoué</span>'
    };
    return badges[status] || `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">${status || 'Inconnu'}</span>`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
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
    const extension = (filename || '').split('.').pop().toLowerCase();
    const icons = {
        pdf: `<svg class="w-6 h-6 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>`,
        jpg: `<svg class="w-6 h-6 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        jpeg: `<svg class="w-6 h-6 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        png: `<svg class="w-6 h-6 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        tiff: `<svg class="w-6 h-6 text-purple-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        tif: `<svg class="w-6 h-6 text-purple-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`
    };
    return icons[extension] || `<svg class="w-6 h-6 text-gray-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>`;
}

// Gestion pagination (similaire à votre version)
function updatePagination() {
    // Implémentez votre logique de pagination existante
    // ... (votre code existant)
}

function updateResultsCount() {
    const countEl = document.getElementById('resultsCount');
    if (countEl) {
        countEl.textContent = filteredData.length.toLocaleString();
    }
}

function showLoading(show) {
    const loading = document.getElementById('loadingState');
    if (loading) {
        loading.classList.toggle('hidden', !show);
    }
}

function showEmptyState(show) {
    const empty = document.getElementById('emptyState');
    if (empty) {
        empty.classList.toggle('hidden', !show);
    }
}

function showNotification(message, type = 'info') {
    // Utilisez votre système de notification existant
    if (window.showNotification) {
        window.showNotification(message, type);
    } else {
        alert(message);
    }
}

// Gestion modale suppression
let deleteItemId = null;
let deleteItemName = null;

function openDeleteModal(processId, filename) {
    deleteItemId = processId;
    deleteItemName = filename;
    
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
}

function closeDeleteModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
    deleteItemId = null;
    deleteItemName = null;
}

async function confirmDelete() {
    if (!deleteItemId) return;
    
    try {
        await deleteItem(deleteItemId);
        closeDeleteModal();
    } catch (error) {
        showNotification(`Erreur: ${error.message}`, 'error');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Filtres
    document.querySelectorAll('select').forEach(select => {
        select.addEventListener('change', () => {
            currentPage = 1;
            applyFilters();
        });
    });
    
    // Recherche avec debounce
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let timeout;
        searchInput.addEventListener('input', () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                currentPage = 1;
                applyFilters();
            }, 300);
        });
    }
    
    // Fermer modal avec Échap
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDeleteModal();
    });
}

// Exposer les fonctions globales
window.viewResult = function(processId) {
    window.location.href = `results.html?process_id=${processId}`;
};

window.exportSingle = exportSingle;
window.openDeleteModal = openDeleteModal;
window.closeDeleteModal = closeDeleteModal;
window.confirmDelete = confirmDelete;
window.refreshHistory = async function() {
    await loadHistory();
    showNotification('Historique actualisé', 'success');
};

window.exportAll = async function() {
    if (filteredData.length === 0) {
        showNotification('Aucun document à exporter', 'warning');
        return;
    }
    
    try {
        showNotification('Export de tous les documents en cours...', 'info');
        
        // Créer un ZIP avec tous les résultats
        // Note: Cette fonctionnalité nécessite une implémentation backend
        // Pour l'instant, exporter le premier document
        if (filteredData[0]?.process_id) {
            await exportSingle(filteredData[0].process_id);
        }
        
    } catch (error) {
        showNotification(`Erreur d'export: ${error.message}`, 'error');
    }
};

window.clearFilters = function() {
    document.getElementById('statusFilter').value = 'all';
    document.getElementById('typeFilter').value = 'all';
    document.getElementById('periodFilter').value = 'all';
    document.getElementById('searchInput').value = '';
    currentPage = 1;
    applyFilters();
};

window.filterHistory = applyFilters;
window.debouncedSearch = function() {
    currentPage = 1;
    applyFilters();
};