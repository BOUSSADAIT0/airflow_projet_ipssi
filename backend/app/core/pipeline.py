import os
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
import numpy as np

from app.config import settings
from app.core.preprocessor import ImagePreprocessor
from app.core.zone_detector import ZoneDetector
from app.core.ocr_engine import OCREngine
from app.core.semantic_extractor import SemanticExtractor
from app.core.exporter import DataExporter

class OCRPipeline:
    """Pipeline complet de traitement OCR"""
    
    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.zone_detector = ZoneDetector()
        self.ocr_engine = OCREngine()
        self.semantic_extractor = SemanticExtractor()
        self.exporter = DataExporter()
        
        # Statistiques
        self.stats = {
            'documents_processed': 0,
            'total_pages': 0,
            'average_confidence': 0.0
        }
    
    def process_document(self, file_bytes: bytes, filename: str, 
                        user_id: Optional[int] = None) -> Dict[str, Any]:
        """Traite un document complet"""
        try:
            print(f"Début du traitement: {filename}")
            
            # Chargement de l'image
            original_image = self.preprocessor.load_image(file_bytes, filename)
            if original_image is None:
                raise ValueError(f"Impossible de charger le document: {filename}")
            
            # Prétraitement
            print("Étape 1/5: Prétraitement de l'image...")
            processed_image = self.preprocessor.preprocess(
                original_image,
                grayscale=True,
                denoise=True,
                threshold=True,
                deskew_img=True,
                enhance=True
            )
            
            # Détection des zones
            print("Étape 2/5: Détection des zones d'intérêt...")
            text_zones = self.zone_detector.detect_text_blocks(processed_image)
            table_zones = self.zone_detector.detect_tables(processed_image)
            signature_zones = self.zone_detector.detect_signatures(processed_image)
            
            all_zones = text_zones + table_zones + signature_zones
            doc_type = self.zone_detector.detect_document_type(processed_image, all_zones)
            
            # Extraction OCR
            print("Étape 3/5: Extraction OCR...")
            full_text = self.ocr_engine.extract_text(processed_image)
            
            # Extraction par zone
            zone_texts = []
            for zone in all_zones:
                zone_text = self.ocr_engine.extract_from_zone(
                    processed_image, 
                    (zone.x, zone.y, zone.width, zone.height)
                )
                if zone_text:
                    zone.text = zone_text
                    zone_texts.append(zone_text)
            
            # Extraction sémantique
            print("Étape 4/5: Extraction sémantique...")
            combined_text = full_text + "\n" + "\n".join(zone_texts)
            structured_data = self.semantic_extractor.structure_data(combined_text, all_zones)
            
            # Calcul des métriques
            ocr_details = self.ocr_engine.extract_with_details(processed_image)
            avg_confidence = np.mean([r.confidence for r in ocr_details]) if ocr_details else 0.0
            
            # Génération d'un ID unique pour le traitement
            process_id = str(uuid.uuid4())
            
            # Sauvegarde des résultats
            print("Étape 5/5: Structuration des résultats...")
            result = {
                'process_id': process_id,
                'filename': filename,
                'document_type': doc_type,
                'extraction_date': datetime.now().isoformat(),
                'processing_time': 0,  # À calculer avec time.time()
                'confidence': avg_confidence,
                'page_count': 1,  # À adapter pour les PDF multi-pages
                'metadata': {
                    'original_size': original_image.shape,
                    'processed_size': processed_image.shape,
                    'zone_count': len(all_zones)
                },
                'extracted_data': structured_data,
                'zones': [
                    {
                        'type': zone.label or 'text',
                        'position': {
                            'x': zone.x,
                            'y': zone.y,
                            'width': zone.width,
                            'height': zone.height
                        },
                        'text': zone.text,
                        'confidence': zone.confidence
                    }
                    for zone in all_zones
                ],
                'raw_text': full_text,
                'user_id': user_id
            }
            
            # Mise à jour des statistiques
            self.stats['documents_processed'] += 1
            self.stats['total_pages'] += result['page_count']
            self.stats['average_confidence'] = (
                (self.stats['average_confidence'] * (self.stats['documents_processed'] - 1) + avg_confidence) 
                / self.stats['documents_processed']
            )
            
            print(f"Traitement terminé: {filename} (confiance: {avg_confidence:.2%})")
            return result
            
        except Exception as e:
            print(f"Erreur lors du traitement de {filename}: {str(e)}")
            raise
    
    def export_results(self, results: Dict[str, Any], 
                      format: str = 'json') -> Dict[str, Any]:
        """Exporte les résultats dans différents formats"""
        return self.exporter.export(results, format)
    
    def batch_process(self, files: List[Dict[str, bytes]], 
                     user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Traite plusieurs documents en batch"""
        all_results = []
        
        for file_info in files:
            try:
                result = self.process_document(
                    file_info['bytes'],
                    file_info['filename'],
                    user_id
                )
                all_results.append(result)
            except Exception as e:
                error_result = {
                    'filename': file_info['filename'],
                    'error': str(e),
                    'success': False
                }
                all_results.append(error_result)
        
        return all_results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du pipeline"""
        return self.stats.copy()