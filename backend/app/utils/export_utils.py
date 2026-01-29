import json
import csv
import pandas as pd
import os
from typing import Dict, Any, List
from datetime import datetime
import uuid

class ExportUtils:
    @staticmethod
    def to_json(data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        Exporte les données en JSON
        """
        try:
            # Ajouter des métadonnées
            export_data = {
                'metadata': {
                    'export_date': datetime.now().isoformat(),
                    'format': 'json',
                    'version': '1.0'
                },
                'data': data
            }
            
            # Sauvegarder le fichier
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'path': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def to_csv(data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        Exporte les données en CSV
        """
        try:
            # Aplatir les données structurées
            flattened_data = ExportUtils._flatten_data(data)
            
            # Créer le DataFrame
            df = pd.DataFrame([flattened_data])
            
            # Sauvegarder en CSV
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            return {
                'success': True,
                'path': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def to_excel(data: Dict[str, Any], output_path: str) -> Dict[str, Any]:
        """
        Exporte les données en Excel
        """
        try:
            # Aplatir les données structurées
            flattened_data = ExportUtils._flatten_data(data)
            
            # Créer le DataFrame
            df = pd.DataFrame([flattened_data])
            
            # Sauvegarder en Excel
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Données', index=False)
                
                # Ajouter une feuille pour le texte brut si présent
                if 'raw_text' in data:
                    text_df = pd.DataFrame({'Texte brut': [data['raw_text']]})
                    text_df.to_excel(writer, sheet_name='Texte brut', index=False)
            
            return {
                'success': True,
                'path': output_path,
                'size': os.path.getsize(output_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def _flatten_data(data: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """
        Aplatit un dictionnaire imbriqué
        """
        items = {}
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.update(ExportUtils._flatten_data(v, new_key, sep=sep))
            elif isinstance(v, list):
                # Convertir les listes en chaînes séparées par des virgules
                items[new_key] = ', '.join(str(item) for item in v)
            else:
                items[new_key] = v
        
        return items
    
    @staticmethod
    def export_all_formats(data: Dict[str, Any], output_dir: str, base_filename: str) -> Dict[str, Any]:
        """
        Exporte les données dans tous les formats
        """
        results = {}
        
        # JSON
        json_path = os.path.join(output_dir, f"{base_filename}.json")
        json_result = ExportUtils.to_json(data, json_path)
        results['json'] = json_result
        
        # CSV
        csv_path = os.path.join(output_dir, f"{base_filename}.csv")
        csv_result = ExportUtils.to_csv(data, csv_path)
        results['csv'] = csv_result
        
        # Excel
        excel_path = os.path.join(output_dir, f"{base_filename}.xlsx")
        excel_result = ExportUtils.to_excel(data, excel_path)
        results['excel'] = excel_result
        
        return results