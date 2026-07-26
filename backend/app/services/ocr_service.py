import cv2
import numpy as np
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import tempfile
import os
import json
import google.generativeai as genai

import torch
import logging

model = None
logger = logging.getLogger(__name__)


def log_to_file(msg):
    try:
        with open("D:/ReceiptAnalyzer/backend/ocr_debug.log", "a") as f:
            f.write(f"{datetime.now()} - {msg}\n")
    except:
        pass


def log_error(message, error=None):
    if error:
        logger.exception(message)
        log_to_file(f"ERROR: {message} - {str(error)}")
    else:
        logger.error(message)
        log_to_file(f"ERROR: {message}")


def get_model():
    global model
    if model is None:
        log_to_file("Starting model initialization...")
        try:
            device = torch.device("cpu")
            from doctr.models import ocr_predictor
            model = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True).to(device)
            log_to_file("Model initialization successful!")
        except Exception as e:
            msg = f"Failed to initialize Doctr model: {str(e)}"
            log_to_file(msg)
            raise
    return model


def deskew(image):
    """
    Detects the skew angle of the text and rotates the image to straighten it.
    """
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        coords = np.column_stack(np.where(thresh > 0))
        if len(coords) < 10:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) > 30:
            return image

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

        height, width = image.shape[:2]
        target_height = 1800
        scale = target_height / height
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        image = deskew(image)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        denoised = cv2.bilateralFilter(enhanced, 7, 50, 50)

        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        sharpened = cv2.filter2D(denoised, -1, kernel)

        return sharpened
    except Exception as e:
        log_error("Preprocessing failed", e)
        return None


class ReceiptAnalyzer:
    """
    Advanced analysis logic with regex fallback for when Gemini is unavailable.
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
            'confidence_score': 0.0, 'items': [], 'suggested_category': None
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
        extracted_data['suggested_category'] = self._guess_category(text_blocks)
        extracted_data['confidence_score'] = self._calculate_confidence(extracted_data)

        MAX_REASONABLE_AMOUNT = 100000
        total_amount = float(extracted_data['amount']) if extracted_data['amount'] else None

        if total_amount and total_amount > MAX_REASONABLE_AMOUNT:
            log_to_file(f"WARNING: Extracted amount ${total_amount:,.2f} exceeds maximum. Setting to None.")
            total_amount = None

        return {
            "merchant_name": extracted_data['merchant_name'] or "Unknown",
            "date_extracted": extracted_data['bill_date'],
            "total_amount": total_amount,
            "currency": extracted_data['currency'],
            "items": extracted_data['items'],
            "suggested_category": extracted_data['suggested_category'],
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
        nepali_to_english = {
            '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
            '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'
        }
        for np_char, en_char in nepali_to_english.items():
            text = text.replace(np_char, en_char)

        text = text.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1').replace('S', '5')

        date_patterns = [
            r'\d{1,2}[-/.\s]+[a-zA-Z]{3,9}[-/.\s]+\d{2,4}',
            r'\d{4}[-/.\s]+[a-zA-Z]{3,9}[-/.\s]+\d{1,2}',
            r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}',
            r'\d{4}[年]\d{1,2}[月]\d{1,2}',
            r'\d{1,2}[-/.]\d{1,2}[-/.]\d{4}',
            r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2}'
        ]

        for pattern in date_patterns:
            if match := re.search(pattern, text):
                try:
                    parsed_dt = self._normalize_date(match.group(0))
                    if parsed_dt:
                        return parsed_dt
                except:
                    continue
        return None

    def _normalize_date(self, date_str: str) -> Optional[datetime]:
        date_str = re.sub(r'[-/.\s年]', '/', date_str).replace('月', '/').replace('日', '')
        parts = [p for p in date_str.split('/') if p]
        if len(parts) != 3:
            return None

        month_map = {
            'jan': '1', 'feb': '2', 'mar': '3', 'apr': '4', 'may': '5', 'jun': '6',
            'jul': '7', 'aug': '8', 'sep': '9', 'oct': '10', 'nov': '11', 'dec': '12',
            'january': '1', 'february': '2', 'march': '3', 'april': '4', 'june': '6',
            'july': '7', 'august': '8', 'september': '9', 'october': '10', 'november': '11', 'december': '12'
        }

        exact_month_index = None
        for i in range(len(parts)):
            clean_part = parts[i].lower()
            if clean_part in month_map:
                parts[i] = month_map[clean_part]
                exact_month_index = i

        p0, p1, p2 = parts[0], parts[1], parts[2]
        if not (p0.isdigit() and p1.isdigit() and p2.isdigit()):
            return None

        val0, val1, val2 = int(p0), int(p1), int(p2)
        year, month, day = None, None, None

        if len(p0) == 4:
            year = val0
            if exact_month_index == 1:
                month, day = val1, val2
            elif exact_month_index == 2:
                month, day = val2, val1
            else:
                if 1 <= val1 <= 12 and 1 <= val2 <= 32:
                    month, day = val1, val2
                elif 1 <= val2 <= 12 and 1 <= val1 <= 32:
                    month, day = val2, val1

        elif len(p2) == 4:
            year = val2
            if exact_month_index == 0:
                month, day = val0, val1
            elif exact_month_index == 1:
                month, day = val1, val0
            else:
                if year > 2028:
                    if 1 <= val1 <= 12 and 1 <= val0 <= 32:
                        month, day = val1, val0

                if not month:
                    if 1 <= val0 <= 12 and 1 <= val1 <= 32:
                        month, day = val0, val1
                    elif 1 <= val1 <= 12 and 1 <= val0 <= 32:
                        month, day = val1, val0

        else:
            if 70 <= val0 <= 99:
                year = val0 + 2000
                if exact_month_index == 1:
                    month, day = val1, val2
                elif exact_month_index == 2:
                    month, day = val2, val1
                else:
                    if 1 <= val1 <= 12 and 1 <= val2 <= 32:
                        month, day = val1, val2
            elif 70 <= val2 <= 99:
                year = val2 + 2000
                if exact_month_index == 0:
                    month, day = val0, val1
                elif exact_month_index == 1:
                    month, day = val1, val0
                else:
                    if 1 <= val1 <= 12 and 1 <= val0 <= 32:
                        month, day = val1, val0
            else:
                year = val2 + 2000
                if exact_month_index == 0:
                    month, day = val0, val1
                elif exact_month_index == 1:
                    month, day = val1, val0
                else:
                    if 1 <= val0 <= 12 and 1 <= val1 <= 32:
                        month, day = val0, val1
                    elif 1 <= val1 <= 12 and 1 <= val0 <= 32:
                        month, day = val1, val0

        if not year or not month or not day:
            return None

        if 2028 <= year <= 2100:
            try:
                import nepali_datetime
                bs_date = nepali_datetime.date(year, month, day)
                ad_date = bs_date.to_datetime_date()
                return datetime(ad_date.year, ad_date.month, ad_date.day)
            except Exception as e:
                year_ad = year - 57
                try:
                    return datetime(year_ad, month, day)
                except:
                    import calendar
                    last = calendar.monthrange(year_ad, month)[1]
                    return datetime(year_ad, month, min(day, last))
        else:
            if not (1900 <= year <= 2200):
                return None
            try:
                return datetime(year, month, day)
            except:
                return None

    def _extract_amounts(self, text_blocks: List[str], detected_currency: Optional[str] = None) -> Dict:
        amounts = {'amount': None, 'currency': detected_currency}

        strong_total_indicators = ['net amount', 'grand total', 'net payable', 'total due', 'amount due', 'total payable', 'net total', 'final total']
        total_indicators = ['total', 'amount', 'sum', 'due', 'pay', 'balance', 'net']
        exclude_keywords = ['qty', 'quantity', 'items', 'count', 'change', 'tender', 'tendered', 'cash', 'received', 'discount', 'gross', 'subtotal', 'sub total', 'dis ', 'taxable']

        amount_pattern = self._get_amount_pattern()
        all_candidates = []

        for i in range(len(text_blocks)):
            text = text_blocks[i]
            text_lower = text.lower()

            if any(k in text_lower for k in exclude_keywords):
                continue

            confidence = 0.4
            if any(k in text_lower for k in strong_total_indicators):
                confidence = 1.2
            elif any(k in text_lower for k in total_indicators):
                confidence = 1.0

            search_text = text
            if confidence >= 1.0:
                for j in range(1, 4):
                    if i + j < len(text_blocks):
                        search_text += " " + text_blocks[i+j]

            for match in re.finditer(amount_pattern, search_text):
                val = self._clean_numeric_value(match.group(2))
                if 0 < val < 100000:
                    all_candidates.append((val, match.group(1) or detected_currency, confidence))

        if not all_candidates:
            for text in text_blocks:
                for match in re.finditer(amount_pattern, text):
                    val = self._clean_numeric_value(match.group(2))
                    if 0 < val < 100000:
                        all_candidates.append((val, match.group(1) or detected_currency, 0.2))

        if all_candidates:
            unique_candidates = {}
            for val, curr, conf in all_candidates:
                if val not in unique_candidates or conf > unique_candidates[val][1]:
                    unique_candidates[val] = (curr, conf)

            candidates_list = [(val, curr, conf) for val, (curr, conf) in unique_candidates.items()]
            candidates_list.sort(key=lambda x: (x[2], x[0]), reverse=True)

            if candidates_list[0][2] <= 0.4:
                candidates_list.sort(key=lambda x: x[0], reverse=True)

            amounts['amount'], amounts['currency'] = str(candidates_list[0][0]), candidates_list[0][1]

        return amounts

    def _clean_numeric_value(self, s: str) -> float:
        s = s.upper().replace('O', '0').replace('D', '0').replace('Q', '0').replace('G', '9')
        s = s.replace('S', '5').replace('Z', '2').replace('T', '7').replace('B', '8')
        s = s.replace('I', '1').replace('L', '1').replace('|', '1')
        s = s.replace('/-', '').replace('/=', '')
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
        noise_words = ['total', 'subtotal', 'tax', 'date', 'amount', 'due', 'thank', 'visit',
                       'hscode', 'gst', 'vat', 'net', 'change', 'cash', 'card', 'table', 'token', 'bill no', 'receipt no']

        # FIX: accept whole numbers (e.g. 945) AND decimals (945.00 / 945,50)
        pattern = fr'(.*?)\s*({"| ".join(map(re.escape, self.supported_currencies))})?\s*(\d+(?:[.,]\d+)?)\s*$'

        for text in text_blocks:
            if any(k in text.lower() for k in noise_words): continue

            if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', text): continue

            if match := re.search(pattern, text):
                val = self._clean_numeric_value(match.group(3))
                desc = match.group(1).strip()

                desc = re.sub(r'^[\d]+\s*[).]*\s*', '', desc)
                desc = re.sub(r'^[^\w\s]+', '', desc).strip()

                MAX_ITEM_PRICE = 10000
                if val > 0 and val <= MAX_ITEM_PRICE and len(desc) > 2:
                    items.append({'item_name': desc, 'price': float(val)})

        return items

    def _guess_category(self, text_blocks: List[str]) -> str:
        """Keyword-based category guess — used as fallback when Gemini is unavailable."""
        text = ' '.join(text_blocks).lower()
        categories = {
            'Food': ['restaurant', 'cafe', 'hotel', 'bhansa', 'kitchen', 'eatery', 'dining',
                     'coffee', 'tea', 'bakery', 'pizza', 'burger', 'momo', 'thali', 'cafe'],
            # 'Groceries': ['mart', 'supermarket', 'bhatbhateni', 'bigmart', 'grocery', 'kirana',
            #               'food', 'meal', 'drink', 'rice', 'dal', 'bread', 'chicken', 'dairy'],
            'Shopping': ['store', 'shop', 'market', 'retail', 'clothing', 'fashion', 'shoes', 'electronics', 'boutique', 'mall','mart', 'supermarket', 'bhatbhateni', 'bigmart', 'grocery', 'kirana',
                    'food', 'meal', 'drink', 'rice', 'dal', 'bread', 'chicken', 'dairy'],
            'Transport': ['taxi', 'bus', 'fuel', 'petrol', 'diesel', 'fare', 'parking',
                          'vehicle', 'travel', 'airline', 'flight', 'cab', 'ride'],
            'Health': ['pharmacy', 'hospital', 'clinic', 'doctor', 'medicine', 'medical',
                       'dental', 'health', 'lab', 'diagnostic'],
            'Utilities': ['electricity', 'water', 'internet', 'telephone', 'gas', 'utility',
                          'broadband', 'mobile', 'recharge'],
            'Entertainment': ['cinema', 'movie', 'game', 'park', 'ticket', 'concert', 'fun', 'amusement'],
        }
        scores = {cat: sum(1 for kw in kws if kw in text) for cat, kws in categories.items()}
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'Other'

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
        return fr'({"| ".join(map(re.escape, self.supported_currencies))})?\s*(\d[0-9.,]*\d(?:/-)?|\d(?:/-)?)'


analyzer = ReceiptAnalyzer()


def _extract_text_blocks_from_doctr(result) -> List[str]:
    """
    Extracts text blocks from Doctr OCR result.
    Processes hierarchically: page -> block -> line -> word
    """
    text_blocks = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                text = ' '.join(word.value for word in line.words)
                if text.strip():
                    text_blocks.append(text.strip())
    return text_blocks


def _parse_text_with_gemini(raw_text: str) -> Optional[Dict]:
    """
    Send raw OCR text to Gemini for fast structured parsing (text-only = fast).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = f"""You are a receipt data extractor. Parse the following raw OCR text from a receipt and return ONLY a JSON object.

Raw OCR text:
---
{raw_text}
---

Instructions:
- Extract EVERY product/service line item you can identify from the receipt, including its name and price.
- DO NOT include metadata like "Table No", "Bill No", "Receipt No", "VAT", "Tax", "Token No", "Customer Name" as items. Only include actual products or services purchased.
- Choose a category from: Food, Groceries, Transport, Shopping, Entertainment, Utilities, Health, Other
- CRITICAL CATEGORY RULES — base the overall receipt category on the PREDOMINANT ITEMS purchased, not the merchant/store type.
  - "Food" → If the majority of items or the highest value items are ready-to-eat food, meals, snacks, or drinks.
  - "Groceries" → If the majority of items are raw ingredients, produce, household staples, or packaged food meant for home use.
  - "Shopping" → If the items are clothing, electronics, accessories, or other non-grocery retail items.
  - Evaluate the actual items in the receipt to make this decision.
- Return ONLY this JSON (no extra text, no markdown code fences):
{{
  "merchant_name": "string",
  "date_extracted": "YYYY-MM-DD or null",
  "total_amount": number or null,
  "currency": "NPR or USD or EUR etc",
  "suggested_category": "one of: Food, Groceries, Transport, Shopping, Entertainment, Utilities, Health, Other",
  "items": [
    {{"item_name": "descriptive item name", "price": number}}
  ],
  "confidence": number between 0 and 1
}}"""

        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)

        if data.get("date_extracted"):
            try:
                data["date_extracted"] = datetime.strptime(data["date_extracted"], "%Y-%m-%d")
            except:
                data["date_extracted"] = None

        return data
    except Exception as e:
        log_error("Gemini text parse failed", e)
        return None


def _parse_image_with_gemini(image_content: bytes) -> Optional[Dict]:
    """
    Send the raw image DIRECTLY to Gemini Vision as a last resort.
    Used when Doctr text is too garbled for text-based parsing.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = """You are an expert receipt scanner. Look at this receipt image carefully and extract ALL information.
Return ONLY a JSON object:
{
  "merchant_name": "store name",
  "date_extracted": "YYYY-MM-DD or null",
  "total_amount": number or null,
  "currency": "NPR or USD etc",
  "suggested_category": "one of: Food, Groceries, Transport, Shopping, Entertainment, Utilities, Health, Other",
  "items": [
    {"item_name": "item description", "price": number}
  ],
  "confidence": 0.95
}
List EVERY product/service line item visible on the receipt with its price. Do not skip any items.
DO NOT include metadata like "Table No", "Bill No", "Receipt No", "VAT", "Tax", "Token No" as items. Only include actual products or services purchased.
CRITICAL CATEGORY RULES — base the overall receipt category on the PREDOMINANT ITEMS purchased, not the merchant/store type:
- "Food" → If the majority of items or the highest value items are ready-to-eat food, meals, snacks, or drinks.
- "Groceries" → If the majority of items are raw ingredients, produce, household staples, or packaged food meant for home use.
- "Shopping" → If the items are clothing, electronics, accessories, or other non-grocery retail items.
- Evaluate the actual items in the receipt to make this decision."""

        import base64
        b64 = base64.standard_b64encode(image_content).decode("utf-8")
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": b64}
        ])

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)

        if data.get("date_extracted"):
            try:
                data["date_extracted"] = datetime.strptime(data["date_extracted"], "%Y-%m-%d")
            except:
                data["date_extracted"] = None

        return data
    except Exception as e:
        log_error("Gemini Vision fallback failed", e)
        return None


def _fix_category(result: dict) -> dict:
    """
    Deterministic category correction layer based on item contents.
    The items are the ground truth — not the merchant name.
    """
    items = result.get("items", [])
    if not items:
        return result
        
    category_counts = {}
    
    # Helper classification purely for this heuristic check
    def _classify_item(text: str) -> str:
        text = text.lower()
        if any(x in text for x in ['burger', 'pizza', 'momo', 'chicken', 'fries', 'meal', 'lunch', 'dinner', 'coffee', 'tea', 'cafe', 'restaurant', 'coke', 'pepsi', 'drink']):
            return "Food"
        if any(x in text for x in ['shirt', 'pant', 'shoe', 'cable', 'charger', 'phone', 'tv', 'electronics', 'clothing','milk', 'bread', 'egg', 'rice', 'dal', 'flour', 'sugar', 'salt', 'oil', 'apple', 'banana', 'vegetable', 'fruit', 'soap', 'shampoo', 'detergent', 'mart', 'grocery']):
            return "Shopping"
        if any(x in text for x in ['uber', 'taxi', 'bus', 'fuel', 'petrol', 'diesel']):
            return "Transport"
        return "Other"

    # Count categories based on item names
    for item in items:
        item_name = item.get("item_name", "")
        if not item_name:
            continue
        cat = _classify_item(item_name)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Find the most frequent category
    if category_counts:
        best_cat = max(category_counts.items(), key=lambda x: x[1])[0]
        if best_cat != "Other":
            result["suggested_category"] = best_cat
            log_to_file(f"[_fix_category] Derived category → {best_cat} based on items: {category_counts}")

    return result


def extract_text(image_content):
    """
    Three-tier pipeline — guarantees items are always extracted:

      Tier 1 (FAST):   Doctr OCR → raw text → Gemini text-only parse
                        Local model + tiny text payload = fastest path.

      Tier 2 (ROBUST): If Tier 1 yields no items, send the original image
                        directly to Gemini Vision. Handles blurry/skewed receipts
                        that Doctr mangles.

      Tier 3 (FALLBACK): Regex analyzer if Gemini is unavailable entirely.
    """
    raw_text = ""
    text_blocks = []

    # ── Tier 1: Doctr + Gemini text parse ─────────────────────────────────
    try:
        processed_image = preprocess_image_for_ocr(image_content)
        if processed_image is not None:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                cv2.imwrite(tmp.name, processed_image)
                tmp_path = tmp.name

            try:
                model_instance = get_model()
                doc = DocumentFile.from_images(tmp_path)
                result = model_instance(doc)
                text_blocks = _extract_text_blocks_from_doctr(result)
                raw_text = "\n".join(text_blocks)
                log_to_file(f"Doctr extracted {len(text_blocks)} lines.")
                print("----- DOCTR OCR OUTPUT -----")
                for l in text_blocks: print(l)
                print("----------------------------")
            except Exception as e:
                log_error("Doctr OCR failed (continuing to Tier 2)", e)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
    except Exception as e:
        log_error("Image preprocessing failed (continuing to Tier 2)", e)

    # Try Gemini text parse if we have text
    if raw_text.strip():
        gemini_result = _parse_text_with_gemini(raw_text)
        if gemini_result is not None:
            items = gemini_result.get("items", [])
            if items:
                log_to_file(f"Tier 1 success: {len(items)} items extracted via Doctr+Gemini text.")
                gemini_result["raw_text"] = raw_text
                return _fix_category(gemini_result)
            else:
                log_to_file("Tier 1: Gemini text parse returned 0 items. Escalating to Tier 2 (Vision).")

    # ── Tier 2: Gemini Vision (direct image) ──────────────────────────────
    log_to_file("Tier 2: Sending image directly to Gemini Vision...")
    vision_result = _parse_image_with_gemini(image_content)
    if vision_result is not None:
        items = vision_result.get("items", [])
        if items:
            log_to_file(f"Tier 2 success: {len(items)} items extracted via Gemini Vision.")
            vision_result.setdefault("raw_text", raw_text)
            return _fix_category(vision_result)
        else:
            log_to_file("Tier 2: Vision also returned 0 items. Falling back to regex.")

    # ── Tier 3: Legacy regex analyzer ─────────────────────────────────────
    log_to_file("Tier 3: Using regex analyzer fallback.")
    if text_blocks:
        return _fix_category(analyzer.analyze_text(text_blocks))

    return {"raw_text": raw_text or "", "items": [], "merchant_name": "Unknown"}
