import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple, Optional
import pytesseract
from pdf2image import convert_from_bytes
import tempfile
import os

class ImagePreprocessor:
    """Classe pour le prétraitement des images"""
    
    def __init__(self):
        self.min_width = 500
        self.min_height = 500
        
    def load_image(self, file_bytes: bytes, filename: str) -> Optional[np.ndarray]:
        """Charge une image depuis des bytes"""
        try:
            if filename.lower().endswith('.pdf'):
                # Conversion PDF en image
                images = convert_from_bytes(file_bytes)
                if images:
                    # Prendre la première page
                    img_array = np.array(images[0])
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                    return img_array
                return None
            else:
                # Lecture d'image standard
                nparr = np.frombuffer(file_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                return img
        except Exception as e:
            print(f"Erreur de chargement d'image: {e}")
            return None
    
    def resize_image(self, image: np.ndarray, max_size: Tuple[int, int] = (2000, 2000)) -> np.ndarray:
        """Redimensionne l'image tout en conservant le ratio"""
        height, width = image.shape[:2]
        
        if height > max_size[0] or width > max_size[1]:
            ratio = min(max_size[0] / height, max_size[1] / width)
            new_height = int(height * ratio)
            new_width = int(width * ratio)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        return image
    
    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convertit l'image en niveaux de gris"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    
    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        """Réduction du bruit"""
        return cv2.medianBlur(image, 3)
    
    def thresholding(self, image: np.ndarray) -> np.ndarray:
        """Binarisation de l'image"""
        # Utilisation d'Otsu pour le seuillage automatique
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    
    def deskew(self, image: np.ndarray) -> np.ndarray:
        """Redressement de l'image"""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), 
                                flags=cv2.INTER_CUBIC, 
                                borderMode=cv2.BORDER_REPLICATE)
        return rotated
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Amélioration du contraste"""
        # CLAHE (Contrast Limited Adaptive Histogram Equalization)
        if len(image.shape) == 2:  # Grayscale
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            return clahe.apply(image)
        else:  # Couleur
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    def detect_edges(self, image: np.ndarray) -> np.ndarray:
        """Détection des contours"""
        edges = cv2.Canny(image, 50, 150)
        return edges
    
    def preprocess(self, image: np.ndarray, 
                   grayscale: bool = True,
                   denoise: bool = True,
                   threshold: bool = True,
                   deskew_img: bool = True,
                   enhance: bool = True) -> np.ndarray:
        """Pipeline complet de prétraitement"""
        processed = image.copy()
        
        # Redimensionnement
        processed = self.resize_image(processed)
        
        if grayscale:
            processed = self.convert_to_grayscale(processed)
        
        if denoise and grayscale:
            processed = self.remove_noise(processed)
        
        if enhance and grayscale:
            processed = self.enhance_contrast(processed)
        
        if deskew_img and grayscale:
            processed = self.deskew(processed)
        
        if threshold and grayscale:
            processed = self.thresholding(processed)
        
        return processed
    
    def save_preview(self, image: np.ndarray, filename: str) -> str:
        """Sauvegarde un aperçu de l'image traitée"""
        import uuid
        from app.config import settings
        
        preview_dir = os.path.join(settings.STATIC_DIR, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        
        preview_filename = f"{uuid.uuid4()}_{filename}"
        preview_path = os.path.join(preview_dir, preview_filename)
        
        cv2.imwrite(preview_path, image)
        return f"/static/previews/{preview_filename}"