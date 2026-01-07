import os
import sys

# Add the current directory to sys.path so 'app' can be found
sys.path.append(os.getcwd())

from app.services.ocr_service import extract_text
import glob

def test_ocr():
    uploads = glob.glob("uploads/*.jpg") + glob.glob("uploads/*.png")
    print(f"Found {len(uploads)} uploads.")
    
    for img_path in uploads[:5]: # Test first 5
        print(f"\n--- Testing: {img_path} ---")
        try:
            with open(img_path, "rb") as f:
                content = f.read()
            result = extract_text(content)
            print(f"Merchant: {result.get('merchant_name')}")
            print(f"Amount: {result.get('total_amount')}")
            print(f"Date: {result.get('date_extracted')}")
        except Exception as e:
            print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_ocr()
