import cv2
import numpy as np
import io
from PIL import Image

def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Preprocess image for better OCR results.
    Handles low quality images by applying:
    1. Grayscale conversion
    2. Denoising
    3. Adaptive thresholding
    4. Rescaling if too small
    """
    try:
        # Convert bytes to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Could not decode image")

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Check image resolution, upscale if too small (common cause of bad OCR)
        height, width = gray.shape
        if height < 1000 or width < 1000:
            scale_factor = 2
            gray = cv2.resize(gray, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_CUBIC)

        # Apply dilation and erosion to remove noise
        kernel = np.ones((1, 1), np.uint8)
        img = cv2.dilate(gray, kernel, iterations=1)
        img = cv2.erode(img, kernel, iterations=1)

        # Write image filtering (Thresholding) to get black and white
        # Adaptive thresholding is often better for varying lighting conditions
        thresh = cv2.adaptiveThreshold(cv2.medianBlur(gray, 3), 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)

        # Denoise
        # dst = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21) # Can be slow on CPU
        
        # Convert back to PIL Image for pytesseract
        return Image.fromarray(thresh)
    
    except Exception as e:
        print(f"Error in preprocessing: {e}")
        # Fallback to original image if opencv fails
        return Image.open(io.BytesIO(image_bytes))

def sharpen_image(image: Image.Image) -> Image.Image:
    """Apply sharpening filter using PIL"""
    # If needed, can be added here
    return image
