import json
import csv
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
import io

class DataExporter:
    """Exportateur de données dans différents formats"""
    
    def export(self, data: Dict[str, Any], format: str = 'json') -> Dict[str, Any]:
        """Exporte les données dans le format spécifié"""
        format = format.lower()
        
        if format == 'json':
            return self._export_json(data)
        elif format == 'csv':
            return self._export_csv(data)
        elif format == 'excel':
            return self._export_excel(data)
        elif format == 'xml':
            return self._export_xml(data)
        else:
            raise ValueError(f"Format non supporté: {format}")
    
    def _export_json(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export en JSON"""
        # Nettoyage des données pour la sérialisation JSON
        def clean_data(obj):
            if isinstance(obj, dict):
                return {k: clean_data(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_data(item) for item in obj]
            elif isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            else:
                return str(obj)
        
        cleaned_data = clean_data(data)
        json_str = json.dumps(cleaned_data, indent=2, ensure_ascii=False)
        
        return {
            'format': 'json',
            'data': json_str,
            'filename': f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            'content_type': 'application/json'
        }
    
    def _export_csv(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export en CSV"""
        # Extraction des champs structurés
        fields_data = data.get('extracted_data', {}).get('fields', {})
        
        # Préparation des lignes CSV
        rows = []
        
        # Ligne d'en-tête
        headers = ['Field', 'Value', 'Confidence', 'Source']
        
        # Ajout des données de champ
        for field_name, field_items in fields_data.items():
            for item in field_items:
                rows.append([
                    field_name,
                    item.get('value', ''),
                    item.get('confidence', 0),
                    item.get('source', '')
                ])
        
        # Ajout des métadonnées
        rows.append(['', '', '', ''])
        rows.append(['Metadata', '', '', ''])
        rows.append(['Document Type', data.get('document_type', ''), '', ''])
        rows.append(['Filename', data.get('filename', ''), '', ''])
        rows.append(['Confidence', data.get('confidence', 0), '', ''])
        rows.append(['Extraction Date', data.get('extraction_date', ''), '', ''])
        
        # Génération CSV
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(rows)
        
        csv_content = output.getvalue()
        output.close()
        
        return {
            'format': 'csv',
            'data': csv_content,
            'filename': f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            'content_type': 'text/csv'
        }
    
    def _export_excel(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export en Excel"""
        # Création d'un DataFrame pour les données extraites
        fields_data = data.get('extracted_data', {}).get('fields', {})
        
        # Préparation des données
        excel_data = []
        for field_name, field_items in fields_data.items():
            for item in field_items:
                excel_data.append({
                    'Champ': field_name,
                    'Valeur': item.get('value', ''),
                    'Confiance': item.get('confidence', 0),
                    'Source': item.get('source', '')
                })
        
        # Création du DataFrame
        df = pd.DataFrame(excel_data)
        
        # Création d'un writer Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Données Extraites', index=False)
            
            # Ajout des métadonnées dans une autre feuille
            metadata_df = pd.DataFrame([
                {'Paramètre': 'Type de Document', 'Valeur': data.get('document_type', '')},
                {'Paramètre': 'Fichier', 'Valeur': data.get('filename', '')},
                {'Paramètre': 'Confiance Globale', 'Valeur': data.get('confidence', 0)},
                {'Paramètre': 'Date Extraction', 'Valeur': data.get('extraction_date', '')},
                {'Paramètre': 'Nombre de Zones', 'Valeur': data.get('metadata', {}).get('zone_count', 0)}
            ])
            metadata_df.to_excel(writer, sheet_name='Métadonnées', index=False)
        
        excel_content = output.getvalue()
        output.close()
        
        return {
            'format': 'excel',
            'data': excel_content,
            'filename': f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
    
    def _export_xml(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Export en XML"""
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        
        # Création de la racine
        root = ET.Element('OCRResult')
        
        # Métadonnées
        metadata = ET.SubElement(root, 'metadata')
        ET.SubElement(metadata, 'filename').text = data.get('filename', '')
        ET.SubElement(metadata, 'document_type').text = data.get('document_type', '')
        ET.SubElement(metadata, 'confidence').text = str(data.get('confidence', 0))
        ET.SubElement(metadata, 'extraction_date').text = data.get('extraction_date', '')
        
        # Données extraites
        extracted = ET.SubElement(root, 'extracted_data')
        fields_data = data.get('extracted_data', {}).get('fields', {})
        
        for field_name, field_items in fields_data.items():
            field_elem = ET.SubElement(extracted, 'field', name=field_name)
            for item in field_items:
                item_elem = ET.SubElement(field_elem, 'item')
                ET.SubElement(item_elem, 'value').text = str(item.get('value', ''))
                ET.SubElement(item_elem, 'confidence').text = str(item.get('confidence', 0))
                ET.SubElement(item_elem, 'source').text = item.get('source', '')
        
        # Conversion en string XML formaté
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        xml_str = reparsed.toprettyxml(indent="  ")
        
        return {
            'format': 'xml',
            'data': xml_str,
            'filename': f"ocr_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml",
            'content_type': 'application/xml'
        }
    
    def export_batch(self, results: List[Dict[str, Any]], 
                    format: str = 'json') -> Dict[str, Any]:
        """Exporte plusieurs résultats en batch"""
        if format == 'json':
            # Combine tous les résultats en un seul JSON
            combined = {
                'batch_export_date': datetime.now().isoformat(),
                'total_documents': len(results),
                'successful_documents': len([r for r in results if 'error' not in r]),
                'failed_documents': len([r for r in results if 'error' in r]),
                'results': results
            }
            
            json_str = json.dumps(combined, indent=2, ensure_ascii=False)
            
            return {
                'format': 'json',
                'data': json_str,
                'filename': f"ocr_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                'content_type': 'application/json'
            }
        
        elif format == 'excel':
            # Création d'un Excel avec une feuille par document
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for i, result in enumerate(results):
                    if 'error' in result:
                        continue
                    
                    # Données extraites
                    fields_data = result.get('extracted_data', {}).get('fields', {})
                    excel_data = []
                    
                    for field_name, field_items in fields_data.items():
                        for item in field_items:
                            excel_data.append({
                                'Champ': field_name,
                                'Valeur': item.get('value', ''),
                                'Confiance': item.get('confidence', 0),
                                'Source': item.get('source', '')
                            })
                    
                    if excel_data:
                        df = pd.DataFrame(excel_data)
                        sheet_name = result.get('filename', f'Document_{i+1}')[:31]
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                       
            excel_content = output.getvalue()
            output.close()
            
            return {
                'format': 'excel',
                'data': excel_content,
                'filename': f"ocr_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        
        else:
            raise ValueError(f"Format batch non supporté: {format}")