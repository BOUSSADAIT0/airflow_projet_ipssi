"""
Application Web Flask pour l'extraction de factures
Remplace l'interface Tkinter par une interface web moderne
"""
from flask import Flask, render_template, request, jsonify, send_file, session
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from pathlib import Path

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

def allowed_file(filename):
    """Vérifie si le fichier a une extension autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Endpoint pour uploader un fichier facture"""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Retourner les informations du fichier
        return jsonify({
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'message': 'Fichier uploadé avec succès'
        })
    
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

@app.route('/api/process', methods=['POST'])
def process_invoice():
    """Endpoint pour traiter une facture"""
    data = request.json
    filepath = data.get('filepath')
    method = data.get('method', 'auto')  # ollama, tesseract, auto
    
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'Fichier introuvable'}), 404
    
    try:
        # Importer le service de traitement (adapté pour fonctionner sans Tkinter)
        from invoice_processor import InvoiceProcessor
        
        processor = InvoiceProcessor()
        result = processor.process_invoice(filepath, method)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'data': result.get('data', {}),
                'message': 'Facture traitée avec succès'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erreur inconnue lors du traitement')
            }), 500
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Erreur détaillée: {error_details}")
        return jsonify({
            'success': False,
            'error': str(e),
            'details': error_details
        }), 500

@app.route('/api/batch', methods=['POST'])
def process_batch():
    """Endpoint pour traiter plusieurs factures en lot"""
    data = request.json
    filepaths = data.get('filepaths', [])
    method = data.get('method', 'auto')
    
    if not filepaths:
        return jsonify({'error': 'Aucun fichier fourni'}), 400
    
    try:
        from invoice_processor import InvoiceProcessor
        processor = InvoiceProcessor()
        
        results = []
        for filepath in filepaths:
            if os.path.exists(filepath):
                result = processor.process_invoice(filepath, method)
                results.append({
                    'filepath': filepath,
                    'success': result.get('success', False),
                    'data': result.get('data', {}),
                    'error': result.get('error')
                })
            else:
                results.append({
                    'filepath': filepath,
                    'success': False,
                    'error': 'Fichier introuvable'
                })
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results),
            'processed': sum(1 for r in results if r.get('success'))
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/export/excel', methods=['POST'])
def export_to_excel():
    """Endpoint pour exporter vers Excel"""
    data = request.json
    invoice_data = data.get('data', {})
    
    if not invoice_data:
        return jsonify({'error': 'Aucune donnée à exporter'}), 400
    
    try:
        from invoice_processor import InvoiceProcessor
        
        processor = InvoiceProcessor()
        result = processor.export_to_excel(invoice_data)
        
        if result.get('success'):
            return jsonify({
                'success': True,
                'filepath': result.get('filepath'),
                'message': result.get('message', 'Export Excel réussi')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Erreur lors de l\'export')
            }), 500
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'details': traceback.format_exc()
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Récupère l'historique des traitements"""
    try:
        history_file = os.path.join('data', 'history.json')
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return jsonify({'success': True, 'history': history})
        return jsonify({'success': True, 'history': []})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retourne le statut de l'application"""
    return jsonify({
        'status': 'running',
        'openai_available': os.environ.get('OPENAI_API_KEY') is not None,
        'ollama_available': check_ollama_available(),
        'excel_available': True
    })

def check_ollama_available():
    """Vérifie si Ollama est disponible"""
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        return response.status_code == 200
    except:
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
