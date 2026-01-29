import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import pytesseract
from dataclasses import dataclass

@dataclass
class Zone:
    """Représente une zone d'intérêt dans un document"""
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    confidence: float = 0.0
    label: str = ""
    page: int = 1

class ZoneDetector:
    """Détecteur de zones d'intérêt dans les documents"""
    
    def __init__(self, min_zone_area: int = 500):
        self.min_zone_area = min_zone_area
        self.margin = 10
        
    def detect_text_blocks(self, image: np.ndarray) -> List[Zone]:
        """Détecte les blocs de texte dans l'image"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Binarisation
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Dilation pour regrouper les caractères
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilated = cv2.dilate(binary, kernel, iterations=3)
        
        # Recherche des contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        zones = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_zone_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Ajout de marges
                x = max(0, x - self.margin)
                y = max(0, y - self.margin)
                w = min(image.shape[1] - x, w + 2 * self.margin)
                h = min(image.shape[0] - y, h + 2 * self.margin)
                
                zone = Zone(x=x, y=y, width=w, height=h)
                zones.append(zone)
        
        # Tri des zones de haut en bas, gauche à droite
        zones.sort(key=lambda z: (z.y // 50, z.x))
        return zones
    
    def detect_tables(self, image: np.ndarray) -> List[Zone]:
        """Détecte les zones de tableau"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Détection des lignes verticales
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        vertical_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        
        # Détection des lignes horizontales
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        horizontal_lines = cv2.morphologyEx(gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Combinaison des lignes
        table_structure = cv2.add(vertical_lines, horizontal_lines)
        
        # Recherche des contours des cellules
        contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        zones = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Zone de tableau minimale
                x, y, w, h = cv2.boundingRect(contour)
                zone = Zone(x=x, y=y, width=w, height=h, label="table")
                zones.append(zone)
        
        return zones
    
    def detect_signatures(self, image: np.ndarray) -> List[Zone]:
        """Détecte les zones de signature"""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Détection des zones à forte densité de pixels sombres
        _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
        
        # Recherche de zones compactes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (20, 20))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        zones = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if 1000 < area < 10000:  # Taille typique d'une signature
                x, y, w, h = cv2.boundingRect(contour)
                zone = Zone(x=x, y=y, width=w, height=h, label="signature")
                zones.append(zone)
        
        return zones
    
    def detect_document_type(self, image: np.ndarray, zones: List[Zone]) -> str:
        """Détecte le type de document basé sur les zones"""
        if not zones:
            return "unknown"
        
        # Analyse de la distribution des zones
        heights = [z.height for z in zones]
        widths = [z.width for z in zones]
        
        avg_height = np.mean(heights)
        avg_width = np.mean(widths)
        
        # Détection de factures
        table_zones = [z for z in zones if z.label == "table"]
        if len(table_zones) > 0:
            return "invoice"
        
        # Détection de CVs (zones de texte variées)
        if len(zones) > 10 and avg_height < 100:
            return "cv"
        
        # Détection de formulaires
        if 5 <= len(zones) <= 10:
            return "form"
        
        return "document"
    
    def visualize_zones(self, image: np.ndarray, zones: List[Zone]) -> np.ndarray:
        """Visualise les zones détectées"""
        vis = image.copy()
        if len(vis.shape) == 2:
            vis = cv2.cvtColor(vis, cv2.COLOR_GRAY2BGR)
        
        colors = {
            "text": (0, 255, 0),      # Vert
            "table": (255, 0, 0),     # Bleu
            "signature": (0, 0, 255), # Rouge
            "default": (255, 255, 0)  # Cyan
        }
        
        for zone in zones:
            color = colors.get(zone.label, colors["default"])
            cv2.rectangle(vis, (zone.x, zone.y), 
                         (zone.x + zone.width, zone.y + zone.height), 
                         color, 2)
            
            # Ajout du label
            label = zone.label or f"Zone"
            cv2.putText(vis, label, (zone.x, zone.y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return vis