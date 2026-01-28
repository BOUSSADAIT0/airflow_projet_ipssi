"""
DAG Airflow pour le traitement automatique de factures
Orchestre l'extraction, validation et export des factures
"""
from __future__ import annotations
from datetime import datetime, timedelta
import os
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.sensors.filesystem import FileSensor

# Chemin vers le dossier d'upload des factures
INVOICE_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
INVOICE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data')

def check_invoice_files(**context):
    """Vérifie s'il y a des fichiers factures à traiter"""
    upload_folder = Path(INVOICE_UPLOAD_FOLDER)
    upload_folder.mkdir(parents=True, exist_ok=True)
    
    # Chercher les fichiers PDF et images
    invoice_files = []
    for ext in ['*.pdf', '*.png', '*.jpg', '*.jpeg', '*.bmp', '*.tiff']:
        invoice_files.extend(list(upload_folder.glob(ext)))
    
    if not invoice_files:
        print("Aucun fichier facture à traiter")
        return "no_files"
    
    # Stocker la liste des fichiers dans XCom
    context['ti'].xcom_push(key='invoice_files', value=[str(f) for f in invoice_files])
    print(f"✅ {len(invoice_files)} fichier(s) facture(s) trouvé(s)")
    return "process_invoices"

def process_single_invoice(**context):
    """Traite une seule facture"""
    ti = context['ti']
    filepath = ti.xcom_pull(task_ids='get_invoice_file', key='filepath')
    method = context.get('params', {}).get('method', 'auto')
    
    if not filepath or not os.path.exists(filepath):
        return {
            'success': False,
            'error': f'Fichier introuvable: {filepath}'
        }
    
    try:
        # Importer le processeur
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from invoice_processor import InvoiceProcessor
        
        processor = InvoiceProcessor()
        result = processor.process_invoice(filepath, method)
        
        if result.get('success'):
            # Exporter automatiquement vers Excel
            excel_result = processor.export_to_excel(result.get('data', {}))
            if excel_result.get('success'):
                print(f"✅ Facture exportée: {excel_result.get('filepath')}")
            
            return {
                'success': True,
                'data': result.get('data', {}),
                'filepath': filepath
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'Erreur inconnue'),
                'filepath': filepath
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'filepath': filepath
        }

def process_all_invoices(**context):
    """Traite toutes les factures trouvées"""
    ti = context['ti']
    invoice_files = ti.xcom_pull(task_ids='check_invoice_files', key='invoice_files')
    method = context.get('params', {}).get('method', 'auto')
    
    if not invoice_files:
        print("Aucun fichier à traiter")
        return []
    
    results = []
    
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from invoice_processor import InvoiceProcessor
        
        processor = InvoiceProcessor()
        
        for filepath in invoice_files:
            print(f"📄 Traitement de: {os.path.basename(filepath)}")
            
            result = processor.process_invoice(filepath, method)
            
            if result.get('success'):
                # Exporter vers Excel
                excel_result = processor.export_to_excel(result.get('data', {}))
                
                results.append({
                    'filepath': filepath,
                    'success': True,
                    'data': result.get('data', {}),
                    'excel_exported': excel_result.get('success', False)
                })
                print(f"✅ {os.path.basename(filepath)} traité avec succès")
            else:
                results.append({
                    'filepath': filepath,
                    'success': False,
                    'error': result.get('error')
                })
                print(f"❌ Erreur sur {os.path.basename(filepath)}: {result.get('error')}")
        
        return results
    
    except Exception as e:
        print(f"❌ Erreur lors du traitement par lot: {e}")
        return results

def validate_extracted_data(**context):
    """Valide les données extraites"""
    ti = context['ti']
    results = ti.xcom_pull(task_ids='process_all_invoices')
    
    if not results:
        return {'validated': 0, 'errors': 0}
    
    validated_count = 0
    error_count = 0
    
    try:
        from data_validator import validate_and_correct_amounts, validate_required_fields
        
        for result in results:
            if result.get('success'):
                data = result.get('data', {})
                try:
                    validated = validate_and_correct_amounts(data)
                    validated = validate_required_fields(validated)
                    validated_count += 1
                except Exception as e:
                    print(f"⚠️ Erreur de validation: {e}")
                    error_count += 1
            else:
                error_count += 1
        
        print(f"✅ {validated_count} facture(s) validée(s), {error_count} erreur(s)")
        return {
            'validated': validated_count,
            'errors': error_count,
            'total': len(results)
        }
    
    except Exception as e:
        print(f"❌ Erreur lors de la validation: {e}")
        return {'validated': 0, 'errors': len(results)}

def generate_report(**context):
    """Génère un rapport du traitement"""
    ti = context['ti']
    results = ti.xcom_pull(task_ids='process_all_invoices')
    validation = ti.xcom_pull(task_ids='validate_extracted_data')
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_files': len(results) if results else 0,
        'successful': sum(1 for r in results if r.get('success')) if results else 0,
        'failed': sum(1 for r in results if not r.get('success')) if results else 0,
        'validated': validation.get('validated', 0) if validation else 0,
        'errors': validation.get('errors', 0) if validation else 0
    }
    
    # Sauvegarder le rapport
    report_path = os.path.join(INVOICE_DATA_FOLDER, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(INVOICE_DATA_FOLDER, exist_ok=True)
    
    import json
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Rapport généré: {report_path}")
    print(f"   Total: {report['total_files']}")
    print(f"   ✅ Réussis: {report['successful']}")
    print(f"   ❌ Échoués: {report['failed']}")
    print(f"   ✓ Validés: {report['validated']}")
    
    return report

with DAG(
    dag_id="projet_facture",
    description="Traitement automatique de factures avec extraction OCR",
    start_date=datetime(2024, 1, 1),
    schedule_interval=timedelta(hours=1),  # Exécution toutes les heures
    catchup=False,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False,
        "email_on_retry": False,
    },
    tags=["m2", "invoices", "ocr", "automation"],
    params={
        "method": "auto"  # ollama, tesseract, auto
    }
) as dag:
    
    # Task 1: Vérifier s'il y a des fichiers à traiter
    check_files = BranchPythonOperator(
        task_id="check_invoice_files",
        python_callable=check_invoice_files
    )
    
    # Branche: Pas de fichiers
    no_files = EmptyOperator(
        task_id="no_files"
    )
    
    # Branche: Traiter les factures
    process_invoices = PythonOperator(
        task_id="process_all_invoices",
        python_callable=process_all_invoices
    )
    
    # Task 2: Valider les données extraites
    validate_data = PythonOperator(
        task_id="validate_extracted_data",
        python_callable=validate_extracted_data
    )
    
    # Task 3: Générer un rapport
    generate_report_task = PythonOperator(
        task_id="generate_report",
        python_callable=generate_report
    )
    
    # Définition du flux
    check_files >> [no_files, process_invoices]
    process_invoices >> validate_data >> generate_report_task
