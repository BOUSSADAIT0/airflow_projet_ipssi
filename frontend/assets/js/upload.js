// upload.js - Version corrigée
const apiService = window.apiService || new ApiService();
let selectedFiles = [];

document.addEventListener('DOMContentLoaded', initUploadPage);

async function initUploadPage() {
    // Vérifier authentification
    if (!localStorage.getItem('auth_token')) {
        window.location.href = 'login.html';
        return;
    }

    initializeUploadZone();
    setupEventListeners();
}

function initializeUploadZone() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    if (!uploadZone || !fileInput) return;

    // Cliquer sur la zone déclenche le file input
    uploadZone.addEventListener('click', () => fileInput.click());

    // Drag & drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        handleFiles(Array.from(e.dataTransfer.files));
    });
}

function setupEventListeners() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            handleFiles(Array.from(e.target.files));
        });
    }

    const processButton = document.getElementById('processButton');
    if (processButton) {
        processButton.addEventListener('click', processDocuments);
    }

    // Raccourci clavier
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'u') {
            e.preventDefault();
            document.getElementById('fileInput').click();
        }
    });
}

function handleFiles(files) {
    const validFiles = files.filter(isValidFile);
    
    if (validFiles.length === 0 && files.length > 0) {
        showNotification('Certains fichiers ne sont pas supportés. Formats acceptés: PDF, JPG, PNG, TIFF', 'error');
        return;
    }

    validFiles.forEach(file => {
        if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            selectedFiles.push(file);
        }
    });

    updateFileList();
    updateProcessButton();
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

function updateFileList() {
    const fileList = document.getElementById('fileList');
    if (!fileList) return;

    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        return;
    }

    fileList.innerHTML = selectedFiles.map((file, index) => `
        <div class="result-card p-4 flex items-center justify-between fade-in">
            <div class="flex items-center">
                <div class="flex-shrink-0">
                    ${getFileIcon(file.name)}
                </div>
                <div class="ml-4">
                    <p class="text-sm font-medium text-gray-900 truncate max-w-xs">
                        ${file.name}
                    </p>
                    <p class="text-xs text-gray-500">
                        ${formatFileSize(file.size)}
                    </p>
                </div>
            </div>
            <button onclick="removeFile(${index})" 
                    class="text-gray-400 hover:text-red-500 transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>
    `).join('');
}

window.removeFile = function(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
    updateProcessButton();
};

function updateProcessButton() {
    const processButton = document.getElementById('processButton');
    if (processButton) {
        processButton.disabled = selectedFiles.length === 0;
    }
}

async function processDocuments() {
    if (selectedFiles.length === 0) return;

    const language = document.getElementById('languageSelect')?.value || 'fra+eng';
    const documentType = document.getElementById('documentType')?.value || 'auto';

    showProgress(true);

    try {
        for (let i = 0; i < selectedFiles.length; i++) {
            const file = selectedFiles[i];
            
            // Mettre à jour la progression
            updateProgress(i, selectedFiles.length, `Traitement de ${file.name}`);
            
            // Upload du fichier
            const result = await apiService.uploadFile(file, language, documentType);
            
            if (result && result.process_id) {
                // Si c'est le dernier fichier, rediriger vers les résultats
                if (i === selectedFiles.length - 1) {
                    showNotification('Traitement terminé ! Redirection...', 'success');
                    setTimeout(() => {
                        window.location.href = `results.html?process_id=${result.process_id}`;
                    }, 1500);
                }
            } else {
                throw new Error('Réponse invalide du serveur');
            }
        }
    } catch (error) {
        console.error('Processing error:', error);
        showNotification(`Erreur: ${error.message}`, 'error');
    } finally {
        showProgress(false);
        // Réinitialiser pour permettre un nouvel upload
        selectedFiles = [];
        updateFileList();
        updateProcessButton();
    }
}

function showProgress(show) {
    const progressContainer = document.getElementById('progressContainer');
    if (progressContainer) {
        progressContainer.classList.toggle('hidden', !show);
    }
    
    const processButton = document.getElementById('processButton');
    if (processButton) {
        processButton.disabled = show;
        processButton.textContent = show ? 'Traitement en cours...' : 'Démarrer l\'analyse';
    }
}

function updateProgress(current, total, text) {
    const progressBar = document.getElementById('progressBar');
    const progressPercent = document.getElementById('progressPercent');
    const progressText = document.getElementById('progressText');
    
    const percent = Math.round(((current + 1) / total) * 100);
    
    if (progressBar) progressBar.style.width = `${percent}%`;
    if (progressPercent) progressPercent.textContent = `${percent}%`;
    if (progressText) progressText.textContent = text || `Fichier ${current + 1}/${total}`;
}

// Fonctions utilitaires (déjà dans main.js mais exposées ici si besoin)
function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    const icons = {
        pdf: `<svg class="w-5 h-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>`,
        jpg: `<svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        jpeg: `<svg class="w-5 h-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        png: `<svg class="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        tiff: `<svg class="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`,
        tif: `<svg class="w-5 h-5 text-purple-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"/></svg>`
    };
    return icons[extension] || `<svg class="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"/></svg>`;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showNotification(message, type = 'info') {
    if (window.showNotification) {
        window.showNotification(message, type);
    } else {
        alert(message);
    }
}