import cv2
import numpy as np
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import tempfile
import os

import torch
# device = torch.device("cpu") # Move inside function

# Global model variable
model = None

def log_to_file(msg):
    try:
        with open("D:/ReceiptAnalyzer/backend/ocr_debug.log", "a") as f:
            f.write(f"{datetime.now()} - {msg}\n")
    except:
        pass

def get_model():
    global model
    if model is None:
        log_to_file("Starting model initialization...")
        try:
            device = torch.device("cpu")
            from doctr.models import ocr_predictor
            # Lazy load model only when actual OCR is requested
            model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True).to(device)
            log_to_file("Model initialization successful!")
        except Exception as e:
            msg = f"Failed to initialize Doctr model: {str(e)}"
            log_to_file(msg)
            raise
    return model

import logging
logger = logging.getLogger(__name__)

def log_error(message, error=None):
    if error:
        logger.exception(message)
    else:
        logger.error(message)

def deskew(image):
    """
    Detects the skew angle of the text and rotates the image to straighten it.
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Find all non-zero pixels
        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 10: # Not enough points to determine angle
            return image
            
        angle = cv2.minAreaRect(coords)[-1]
        
        # cv2.minAreaRect returns angle in range [-90, 0)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        # Limit rotation to reasonable receipt angles (-30 to 30 degrees)
        if abs(angle) > 30:
            return image

        # Rotate the image
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    except Exception as e:
        log_error("Deskew failed", e)
        return image

def preprocess_image_for_ocr(image_content):
    """
    High-accuracy preprocessing for receipts.
    """
    try:
        nparr = np.frombuffer(image_content, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            log_error("Failed to decode image")
            return None

        # Resize for consistency
        height, width = image.shape[:2]
        target_height = 1800
        scale = target_height / height
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Deskew
        image = deskew(image)

        # Grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Denoising
        denoised = cv2.bilateralFilter(enhanced, 7, 50, 50)

        # Sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)

        return sharpened
    except Exception as e:
        log_error("Preprocessing failed", e)
        return None

class ReceiptAnalyzer:
    """
    Advanced analysis logic - ported from GitHub repo with enhancements.
    """
    def __init__(self):
        self.receipt_types = {
            'invoice': ['invoice', 'bill to', 'payment due', 'invoice no'],
            'receipt': ['receipt', 'thank you', 'served by', 'cashier'],
            'order': ['order', 'delivery', 'purchase order', 'shipping']
        }
        self.currency_patterns = {
            'HKD': [r'HK\$', r'HKD', r'港币', r'港幣'],
            'CNY': [r'¥', r'CNY', r'RMB', r'元', r'CHY', r'人民币'],
            'USD': [r'USD', r'US\$', r'\$(?!HK)'],
            'EUR': [r'€', r'EUR'],
            'GBP': [r'£', r'GBP'],
            'JPY': [r'JPY', r'円', r'¥'],
            'NPR': [r'Rs\.?', r'NPR', r'रू', r'NRs'] 
        }
        self.supported_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'HKD', 'NPR']

    def analyze_text(self, text_blocks: List[str]) -> Dict:
        extracted_data = {
            'merchant_name': None, 'bill_date': None, 'amount': None,
            'description': None, 'type': None, 'currency': None,
            'confidence_score': 0.0, 'items': []
        }
        
        currency, _ = self._detect_currency(text_blocks)
        extracted_data['currency'] = currency
        extracted_data['bill_date'] = self._find_date(text_blocks)
        extracted_data['merchant_name'], _ = self._find_merchant(text_blocks)
        amounts = self._extract_amounts(text_blocks, currency)
        extracted_data.update(amounts)
        extracted_data['items'] = self._extract_items(text_blocks)
        extracted_data['description'] = self._get_description(text_blocks)
        extracted_data['type'] = self._classify_receipt_type(text_blocks)
        extracted_data['confidence_score'] = self._calculate_confidence(extracted_data)
        
        # Validate and cap the total amount to prevent OCR errors
        MAX_REASONABLE_AMOUNT = 100000  # $100,000 max for receipts
        total_amount = float(extracted_data['amount']) if extracted_data['amount'] else None
        
        if total_amount and total_amount > MAX_REASONABLE_AMOUNT:
            log_to_file(f"WARNING: Extracted amount ${total_amount:,.2f} exceeds maximum. Capping at ${MAX_REASONABLE_AMOUNT:,.2f}")
            total_amount = None  # Set to None if unrealistic, will be handled by receipt upload logic
        
        return {
            "merchant_name": extracted_data['merchant_name'] or "Unknown",
            "date_extracted": extracted_data['bill_date'],
            "total_amount": total_amount,
            "currency": extracted_data['currency'],
            "items": extracted_data['items'],
            "confidence": extracted_data['confidence_score'],
            "raw_text": "\n".join(text_blocks)
        }

    def _find_date(self, text_blocks: List[str]) -> Optional[datetime]:
        date_keywords = ['date:', 'dated:', 'bill date:', 'invoice date:', 'printed on:']
        for text in text_blocks:
            if any(k in text.lower() for k in date_keywords):
                if match := self._extract_date_from_text(text): return match
        for text in text_blocks:
            if match := self._extract_date_from_text(text): return match
        return None

    def _extract_date_from_text(self, text: str) -> Optional[datetime]:
        text = text.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1').replace('S', '5')
        
        date_patterns = [
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}', 
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
            r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}', 
            r'\d{4}/\d{1,2}/\d{1,2}'
        ]
        
        for pattern in date_patterns:
            if match := re.search(pattern, text):
                try: return self._normalize_date(match.group(0))
                except: continue
        return None

    def _normalize_date(self, date_str: str) -> Optional[datetime]:
        date_str = date_str.replace('.', '/').replace('-', '/').replace(' ', '').replace('年', '-').replace('月', '-').replace('日', '')
        # Prioritize Month/Day/Year (US format) before Day/Month/Year for accurate parsing
        date_formats = ['%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%m-%d-%Y', '%d-%m-%Y', '%d%b%Y']
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                if 2028 < dt.year < 2150:
                    year = dt.year - 57
                    try: dt = datetime(year, dt.month, dt.day)
                    except: 
                        import calendar
                        last = calendar.monthrange(year, dt.month)[1]
                        dt = datetime(year, dt.month, min(dt.day, last))
                return dt
            except: continue
        return None

    def _extract_amounts(self, text_blocks: List[str], detected_currency: Optional[str] = None) -> Dict:
        amounts = {'amount': None, 'currency': detected_currency}
        total_indicators = ['total', 'amount', 'sum', 'due', 'pay', 'balance', 'grand total', 'net']
        amount_pattern = self._get_amount_pattern()
        all_candidates = []

        for text in reversed(text_blocks):
            if any(i in text.lower() for i in total_indicators):
                for match in re.finditer(amount_pattern, text):
                    val = self._clean_numeric_value(match.group(2))
                    if val > 0: all_candidates.append((val, match.group(1) or detected_currency, 1.0))

        if not all_candidates:
            for text in text_blocks[int(len(text_blocks)*0.6):]:
                for match in re.finditer(amount_pattern, text):
                    val = self._clean_numeric_value(match.group(2))
                    if val > 0: all_candidates.append((val, match.group(1) or detected_currency, 0.7))

        if all_candidates:
            all_candidates.sort(key=lambda x: (x[2], x[0]), reverse=True)
            amounts['amount'], amounts['currency'] = str(all_candidates[0][0]), all_candidates[0][1]
            
        return amounts

    def _clean_numeric_value(self, s: str) -> float:
        s = s.upper().replace('O', '0').replace('D', '0').replace('Q', '0').replace('G', '9')
        s = s.replace('S', '5').replace('Z', '2').replace('T', '7').replace('B', '8')
        s = s.replace('I', '1').replace('L', '1').replace('|', '1')
        s = s.replace(',', '.')
        digits_only = "".join([c for c in s if c.isdigit() or c == '.'])
        
        if not digits_only:
            return 0.0
            
        try:
            if digits_only.count('.') > 1:
                parts = digits_only.split('.')
                digits_only = "".join(parts[:-1]) + "." + parts[-1]
            return float(digits_only)
        except:
            return 0.0

    def _find_merchant(self, text_blocks: List[str]) -> Tuple[Optional[str], float]:
        merchant_indicators = ['ltd', 'limited', 'inc', 'corp', 'co', 'company', 'store', 'restaurant', 'shop', 'cafe', 'hotel', 'mall', 'market', 'pvt', 'kitchen', 'pasal']
        
        for text in text_blocks:
            if "ISSUED BY" in text.upper():
                parts = re.split(r'issued\s*by\s*:?\s*', text, flags=re.IGNORECASE)
                if len(parts) > 1 and len(parts[1].strip()) > 2:
                    return self._correct_merchant_name(parts[1].strip()), 1.0

        for text in text_blocks[:5]:
            cleaned = self._preprocess_text(text)
            if len(text.strip()) < 3 or self._is_unwanted_merchant_line(cleaned): continue
            
            if any(i in cleaned for i in merchant_indicators): 
                return self._correct_merchant_name(text.strip()), 0.95
            
            if text.isupper() and len(text.split()) > 1: 
                return self._correct_merchant_name(text.strip()), 0.85

        for text in text_blocks[:3]:
            if len(text.strip()) > 3 and not any(c.isdigit() for c in text): 
                return self._correct_merchant_name(text.strip()), 0.7
        
        return None, 0.0

    def _correct_merchant_name(self, name: str) -> str:
        corrections = {
            'BIG MART': ['BlG MART', 'DIG MART', 'BIG HART'],
            'BHAT BHATENI': ['BHAT BHATENI', 'BHAT-BHATENI', 'B HAT BHAT ENI'],
        }
        name_upper = name.upper()
        for correct, wrongs in corrections.items():
            if any(w in name_upper for w in wrongs):
                return correct
        return name

    def _extract_items(self, text_blocks: List[str]) -> List[Dict]:
        items = []
        # Exclude internal headers/footers
        noise_words = ['total', 'subtotal', 'tax', 'date', 'amount', 'due', 'thank', 'visit', 'hscode', 'gst', 'vat', 'net', 'change', 'cash', 'card']
        
        # Regex to capture: Description ... Price
        # Improved to be less greedy and capture clean prices at end of line
        pattern = fr'(.*?)\s*({"|".join(map(re.escape, self.supported_currencies))})?\s*(\d+[.,]\d{{2}})$'
        
        for text in text_blocks:
            # Filter out noise lines
            if any(k in text.lower() for k in noise_words): continue
            
            # Additional check: skip lines that are just dates
            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text): continue

            if match := re.search(pattern, text):
                val = self._clean_numeric_value(match.group(3))
                desc = match.group(1).strip()
                
                # Clean description (remove leading "1).", "1.", "*", etc)
                desc = re.sub(r'^[\d]+\s*[).]*\s*', '', desc)
                desc = re.sub(r'^[^\w\s]+', '', desc).strip()

                # Validate item price - cap at $10,000 to prevent OCR errors
                MAX_ITEM_PRICE = 10000
                if val > 0 and val <= MAX_ITEM_PRICE and len(desc) > 2:
                    items.append({'item_name': desc, 'price': float(val)})
                    
        return items

    def _get_description(self, text_blocks: List[str]) -> Optional[str]:
        items = self._extract_items(text_blocks)
        return f"Receipt from {items[0]['item_name']}..." if items else "Receipt"

    def _classify_receipt_type(self, text_blocks: List[str]) -> str:
        text_content = ' '.join(text_blocks).lower()
        scores = {t: sum(k in text_content for k in ks) for t, ks in self.receipt_types.items()}
        return max(scores.items(), key=lambda x: x[1])[0] if scores and max(scores.values()) > 0 else 'general'

    def _detect_currency(self, text_blocks: List[str]) -> Tuple[Optional[str], float]:
        counts = {}
        for cur, pats in self.currency_patterns.items():
            for text in text_blocks:
                if re.search('|'.join(pats), text, re.IGNORECASE): counts[cur] = counts.get(cur, 0) + 1
        return (max(counts.items(), key=lambda x: x[1])[0], 0.5) if counts else ('NPR', 0.0)

    def _calculate_confidence(self, data: Dict) -> float:
        return round(min(sum(w for f, w in {'bill_date': 0.25, 'amount': 0.3, 'merchant_name': 0.25, 'currency': 0.2}.items() if data.get(f)), 1.0), 2)

    def _is_unwanted_merchant_line(self, text: str) -> bool:
        noise_keywords = [
            'total', 'tax', 'date', 'tel', 'receipt', 'cash', 'card', 'change', 
            'balance', 'due', 'paid', 'amount', 'time', 'estimate',
            'ksmai', 'kstimate', 'invoice', 'memo', 'served', 'order', 'table',
            'phone', 'pan', 'vat', 'bill', 'id', 'user', 'stimate',
            'sale', 'copy', 'customer', 'duplicate', 'terminal', 'auth'
        ]
        return any(word in text.lower() for word in noise_keywords)

    def _preprocess_text(self, text: str) -> str:
        return re.sub(r'[^\w\s]', '', re.sub(r'\s+', ' ', text.lower().strip()))

    def _get_amount_pattern(self) -> str:
        return fr'({"|".join(map(re.escape, self.supported_currencies))})?\s*(\d+[.,]\d{{2}})'


# Initialize global analyzer
analyzer = ReceiptAnalyzer()

def _extract_text_blocks_from_doctr(result) -> List[str]:
    """
    Extracts text blocks from Doctr OCR result.
    Processes hierarchically: page → block → line → word
    """
    text_blocks = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                text = ' '.join(word.value for word in line.words)
                if text.strip():
                    text_blocks.append(text.strip())
    return text_blocks

def extract_text(image_content):
    """
    Main OCR extraction using Doctr (from GitHub repo).
    """
    try:
        # 1. Preprocess and save to temp file (Doctr requires file path)
        processed_image = preprocess_image_for_ocr(image_content)
        if processed_image is None: 
            return {}
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            cv2.imwrite(tmp.name, processed_image)
            tmp_path = tmp.name
        
        try:
            # 2. Run Doctr OCR
            model_instance = get_model()
            doc = DocumentFile.from_images(tmp_path)
            result = model_instance(doc)
            
            # 3. Extract text blocks
            text_blocks = _extract_text_blocks_from_doctr(result)
            
            print("----- DOCTR OCR OUTPUT -----")
            for l in text_blocks: print(l)
            print("----------------------------")
            
            # 4. Analyze with ReceiptAnalyzer
            return analyzer.analyze_text(text_blocks)
        except Exception as e:
            log_error("Doctr OCR Model failure", e)
            return {"raw_text": "Error during OCR processing. Check logs."}
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except Exception as e:
        log_error("Top-level OCR FAILED", e)
        return {}
