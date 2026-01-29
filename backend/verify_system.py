import requests
import time
from PIL import Image, ImageDraw
import io

def create_test_image():
    # Create a simple image with text
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    text = "CV\n\nName: Jean Dupont\nEmail: jean.dupont@example.com\nPhone: 06 12 34 56 78\n\nExperience:\n- Developer at Google\n- Manager at Microsoft"
    d.text((10, 10), text, fill='black')
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def verify_api():
    print("Waiting for server to start...")
    # Health check loop
    for i in range(10):
        try:
            r = requests.get('http://localhost:8000/health')
            if r.status_code == 200:
                print("Server is up!")
                break
        except:
            time.sleep(1)
    else:
        print("Server failed to start")
        return

    # Login
    print("Logging in...")
    login_data = {"username": "demo", "password": "demo123"}
    r = requests.post('http://localhost:8000/api/auth/login', json=login_data)
    if r.status_code != 200:
        print(f"Login failed: {r.text}")
        return
    token = r.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}

    # Test OCR
    print("Testing OCR extraction...")
    files = {'file': ('test_cv.png', create_test_image(), 'image/png')}
    r = requests.post('http://localhost:8000/api/ocr/extract', headers=headers, files=files)
    
    if r.status_code == 200:
        data = r.json()
        print("Success!")
        print(f"Document Type Detect: {data.get('document_type')}")
        print(f"Structured Data: {data.get('structured_data')}")
        
        # Validation
        struct = data.get('structured_data', {})
        val_email = struct.get("email")
        if val_email and "example.com" in val_email:
            print("✅ Email extraction verified")
        else:
            print(f"⚠️ Email extraction suboptimal: {val_email}")
            
        if "cv" in data.get('document_type', '').lower():
             print("✅ Document type verified")
        else:
             print(f"❌ Document type failed: {data.get('document_type')}")
             
        print("\n✅ LINK VERIFICATION: Backend received file and returned structured JSON. System is connected.")
    else:
        print(f"OCR Failed: {r.status_code} {r.text}")

if __name__ == "__main__":
    verify_api()
