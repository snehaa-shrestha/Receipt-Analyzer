import easyocr
import cv2
import numpy as np
import re
from datetime import datetime
import os
import sys

# Initialize EasyOCR Reader once (at module level)
# Try GPU=True for speed, it will fallback to CPU if CUDA not found
print("Initializing EasyOCR Model...")
reader = easyocr.Reader(['en'], gpu=True) 
print("EasyOCR Model Initialized.")

def clean_ocr_number(s):
    """
    Cleans OCR'd numbers with regex-based post-processing.
    Smart handling for comma/dot confusion and OCR character errors.
    """
    if not s: return 0.0
    
    # First pass: Remove currency symbols and common OCR artifacts
    s = re.sub(r'[₹$€£¥Rs]', '', s)  # Remove currency symbols
    s = s.strip()
    
    # Map common alpha chars to digits (OCR character confusion)
    corrections = {
        'O': '0', 'D': '0', 'Q': '0', 'U': '0', 'G': '0',
        'I': '1', 'l': '1', '|': '1', 'L': '1', '!': '1',
        'Z': '2', 'z': '2',
        'A': '4', 
        'S': '5', '$': '5', 's': '5',
        'b': '6', 
        'T': '7', 
        'B': '8', 
        'g': '9', 'q': '9'
    }
    
    # Pre-clean: uppercase, remove spaces, handle corrections
    s_clean = list(s.upper().replace(' ', ''))
    for i, char in enumerate(s_clean):
        if char in corrections:
            s_clean[i] = corrections[char]
    s = "".join(s_clean)

    # Smart Comma/Dot Logic
    # Find position of last separator (dot or comma)
    last_sep_idx = -1
    last_sep_char = ''
    
    for i in range(len(s) - 1, -1, -1):
        if s[i] in [',', '.']:
            last_sep_idx = i
            last_sep_char = s[i]
            break
            
    if last_sep_idx != -1:
        # Check how many digits after separator
        digits_after = 0
        for i in range(last_sep_idx + 1, len(s)):
            if s[i].isdigit(): digits_after += 1
            
        if last_sep_char == ',':
            if digits_after == 2:
                # Likely a decimal misread as comma (945,00)
                # Replace this comma with dot, remove other non-digits
                s = s[:last_sep_idx] + '.' + s[last_sep_idx+1:]
            else:
                # Likely thousands separator (1,000) or just noise
                pass
    
    # Final cleanup: remove everything except digits and the one dot
    final_chars = []
    has_dot = False
    for char in s:
        if char.isdigit():
            final_chars.append(char)
        elif char == '.':
            if not has_dot:
                final_chars.append('.')
                has_dot = True
                
    result_str = "".join(final_chars)
    if not result_str: return 0.0
    if result_str == '.': return 0.0
    
    try:
        return float(result_str)
    except:
        return 0.0

def group_blocks_into_lines(results, threshold=10):
    """
    EasyOCR returns list of (bbox, text, prob).
    Group by Y-center to reconstruct physical lines.
    """
    # Sort by Top-Left Y
    sorted_results = sorted(results, key=lambda x: x[0][0][1])
    
    lines = []
    current_line = []
    
    for item in sorted_results:
        box, text, prob = item
        # Calculate Y-center of the box
        y_center = (box[0][1] + box[2][1]) / 2
        
        if not current_line:
            current_line.append(item)
            continue
            
        last_item = current_line[-1]
        last_y_center = (last_item[0][0][1] + last_item[0][2][1]) / 2
        
        # If y-centers are close, same line
        if abs(y_center - last_y_center) < threshold:
            current_line.append(item)
        else:
            lines.append(current_line)
            current_line = [item]
            
    if current_line:
        lines.append(current_line)
        
    final_text_lines = []
    for line in lines:
        # Sort by X-coord (Left to Right)
        line.sort(key=lambda x: x[0][0][0])
        line_text = " ".join([item[1] for item in line])
        final_text_lines.append(line_text)
        
    return "\n".join(final_text_lines)

def preprocess_image_for_ocr(img):
    """
    Optimized preprocessing for EasyOCR - proven to work with receipts.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply bilateral filter - removes noise while keeping edges sharp
    filtered = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # CLAHE for contrast enhancement (critical for faded receipts)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(filtered)
    
    # Adaptive thresholding - creates clean binary image
    binary = cv2.adaptiveThreshold(
        enhanced, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )
    
    # Denoise the binary image
    denoised = cv2.fastNlMeansDenoising(binary, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    return denoised

def extract_text(image_bytes):
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
             raise ValueError("Could not decode image")
             
        # Resize for optimal OCR (300 DPI equivalent)
        height, width = img.shape[:2]
        
        # Upscaling helps OCR - aim for 1200-1500px width (equivalent to 300 DPI)
        target_width = 1500
        
        if width > target_width:
            scale = target_width / width
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        elif width < 1000:
            # Upscale small images (CRITICAL for accuracy)
            scale = 1200 / width
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Apply optimized preprocessing
        processed_img = preprocess_image_for_ocr(img)
            
        # Run EasyOCR with optimal parameters for receipts
        results = reader.readtext(
            processed_img, 
            paragraph=False,
            detail=1,
            batch_size=1,
            workers=0,
            allowlist=None,
            blocklist=None,
            decoder='greedy',  # Greedy is actually faster and often better for receipts
            min_size=10,
            text_threshold=0.6,  # Slightly lower to catch more text
            low_text=0.3,
            link_threshold=0.3,
            canvas_size=2560,
            mag_ratio=1.5
        )
        
        # Reconstruct lines from bounding boxes
        text = group_blocks_into_lines(results, threshold=15)
        
        print("----- EASYOCR RAW OUTPUT -----")
        print(text)
        print("----- END EASYOCR OUTPUT -----")
        
        return text
    except Exception as e:
        print(f"CRITICAL EASYOCR FAILURE: {e}")
        import traceback
        traceback.print_exc()
        return ""

def parse_receipt(text):
    data = {
        "merchant_name": "Unknown",
        "total_amount": 0.0,
        "date_extracted": None,
        "items": [],
        "raw_text": text
    }
    
    if not text:
        return data

    lines = text.split('\n')
    # Filter very short lines
    clean_lines = [line.strip() for line in lines if len(line.strip()) > 2]
    
    date_pattern = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')

    # 3. Enhanced Merchant Detection
    # Strategy: Check for "Issued By:" pattern first, then top lines, then bottom lines
    skip_keywords = ["RECEIPT", "INVOICE", "CASH", "CREDIT", "SALE", "TOTAL", "AMOUNT", "DATE", "TIME", "ESTIMATE", "KSTIMATE", "VAT", "PAN", "BILL", "TAX", "PHONE", "TEL", "ADDRESS", "THANK", "VISIT", "NOTE", "PLEASE"]
    
    # First, look for "Issued By:" pattern (common in restaurant receipts)
    for line in clean_lines:
        if "ISSUED BY" in line.upper() or "ISSUED_BY" in line.upper():
            # Extract text after "Issued By:"
            parts = re.split(r'issued\s*by\s*:?\s*', line, flags=re.IGNORECASE)
            if len(parts) > 1 and parts[1].strip():
                merchant = parts[1].strip()
                # Clean up common OCR artifacts
                merchant = re.sub(r'[_\-:]+$', '', merchant)  # Remove trailing punctuation
                if len(merchant) >= 3:
                    data["merchant_name"] = merchant
                    break
    
    # If not found, try first 5 lines (merchant usually at top)
    if data["merchant_name"] == "Unknown":
        for line in clean_lines[:5]:
            is_skip = any(k in line.upper() for k in skip_keywords)
            is_garbage = re.match(r'^[\W\d_]+$', line)
            has_date = date_pattern.search(line)
            has_letters = sum(c.isalpha() for c in line) >= 3
            
            if not is_skip and not is_garbage and not has_date and has_letters and len(line) >= 3:
                data["merchant_name"] = line.strip()
                break
    
    # If still not found, try last 5 lines (sometimes merchant is at bottom)
    if data["merchant_name"] == "Unknown":
        for line in reversed(clean_lines[-5:]):
            is_skip = any(k in line.upper() for k in skip_keywords)
            is_garbage = re.match(r'^[\W\d_]+$', line)
            has_letters = sum(c.isalpha() for c in line) >= 3
            
            # Skip lines that look like scanner watermarks
            if "SCANNED" in line.upper() or "CAMSCANNER" in line.upper():
                continue
            
            if not is_skip and not is_garbage and has_letters and len(line) >= 3:
                data["merchant_name"] = line.strip()
                break

    # 1. Enhanced Total Detection (Fuzzy matching + Space handling)
    candidates = []
    
    for line in reversed(clean_lines):
        line_upper = line.upper()
        
        # Check for Total-like keywords
        is_total_line = False
        if re.search(r'(?:N[ET].?T|GR[AO].?ND|GR[OA].?SS)\s*(?:AM|TO|AN)', line_upper) or "TOTAL" in line_upper:
             is_total_line = True
        elif "TENDER" in line_upper:
             is_total_line = True
        
        if is_total_line:
            # Approach 1: Regex for space-separated numbers (handles "4 370.00")
            regex_matches = re.findall(r'(\d+(?:[ .,]\d+)*\.\d{2})', line)
            for m in regex_matches:
                 try:
                     val = float(m.replace(' ', '').replace(',', ''))
                     candidates.append(val)
                 except: pass

            # Approach 2: Token cleaning
            parts = line.split()
            for p in parts:
                if sum(c.isdigit() for c in p) > 1: 
                    val = clean_ocr_number(p)
                    if val > 0: candidates.append(val)
                    
    if candidates:
        data["total_amount"] = max(candidates)
        
    # Fallback: Scanned whole text for largest number
    if data["total_amount"] == 0.0:
        all_vals = []
        for line in clean_lines:
             regex_matches = re.findall(r'(\d+(?:[ .,]\d+)*\.\d{2})', line)
             for m in regex_matches:
                 try:
                     val = float(m.replace(' ', '').replace(',', ''))
                     if val > 10: all_vals.append(val)
                 except: pass
                 
             parts = line.split()
             for p in parts:
                 if re.search(r'\d', p):
                     v = clean_ocr_number(p)
                     if v > 10.0: all_vals.append(v)
                     
        if all_vals:
            data["total_amount"] = max(all_vals)

    # 3. Item Extraction
    # Strategy: Iterate lines. If line has text + float, candidate.
    # STOP if we hit the "Total" block to avoid parsing footer numbers (Phone, Tax ID) as items.
    
    item_pattern = re.compile(r'([a-zA-Z\s\(\)\:\-\.]+)\s+(\d+\.\d{2})')
    parsing_items = True
    
    for i, line in enumerate(clean_lines):
        # Check if this line marks the start of the Totals section
        # If so, STOP parsing items to prevent footer noise (like Phone numbers) being read as prices
        if re.search(r'(?:TOTAL|GROSS|NET|SUBTOTAL|TAX|VAT|TENDER|CHANGE|DUE|CASH|CREDIT)', line, re.IGNORECASE):
            parsing_items = False
            continue
            
        if not parsing_items:
            continue

        # Ignore lines that look like metadata or phone numbers
        if re.search(r'(?:Tel|Ph|Phone|Call|Bill|Invoice|Date|Pan|Vat)', line, re.IGNORECASE):
            continue

        match = item_pattern.search(line)
        if match:
            desc = match.group(1).strip()
            price_str = match.group(2)
            
            # Filter out likely garbage
            if len(desc) < 3: continue
            if "TOTAL" in desc.upper(): continue
            
            try:
                price = float(price_str)
                
                # SANITY CHECK: Ignore items with absurd prices (likely phone numbers or IDs misread)
                # Unless it matches the detected total exactly, it's probably garbage if > 100,000
                if price > 100000:
                    continue
                
                data["items"].append({
                    "description": desc,
                    "amount": price
                })
            except:
                pass
            parsing_items = False
            continue
            
        if not parsing_items:
            continue

        # Ignore lines that look like metadata or phone numbers
        if re.search(r'(?:Tel|Ph|Phone|Call|Bill|Invoice|Date|Pan|Vat)', line, re.IGNORECASE):
            continue

        match = item_pattern.search(line)
        if match:
            desc = match.group(1).strip()
            price_str = match.group(2)
            
            # Filter out likely garbage
            if len(desc) < 3: continue
            if "TOTAL" in desc.upper(): continue
            
            try:
                price = float(price_str)
                # Safety valve: Single item shouldn't be massive compared to total (if we had one)
                # But since we determine total later, we'll just cap it to reasonable sanity
                # or assume the footer guard catches the big phone numbers.
                
                data["items"].append({
                    "description": desc,
                    "amount": price
                })
            except:
                pass

    # 4. Merchant Name Cleanup
    # Apply corrections for known OCR failures
    data["merchant_name"] = correct_merchant_name(data["merchant_name"])

    # 5. Enhanced Date Extraction
    # Strategy: Look for specific date patterns, prioritizing lines with "Date" keyword.
    
    # Regex patterns for common formats
    # 1. DD/MM/YYYY or MM/DD/YYYY or YYYY/MM/DD (with / or - or .)
    # Also handles spaces often introduced by OCR: "13 / 07 / 2026"
    date_patterns = [
        re.compile(r'(\d{4}[\.\-\/]\s*\d{1,2}[\.\-\/]\s*\d{1,2})'),       # YYYY-MM-DD
        re.compile(r'(\d{1,2}[\.\-\/]\s*\d{1,2}[\.\-\/]\s*\d{2,4})'),     # DD/MM/YYYY with optional spaces
        re.compile(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\.\-\/]+\d{1,2}[,\s\.\-\/]+\d{4})', re.IGNORECASE), # Mon DD, YYYY or Mon/DD/YYYY
        re.compile(r'(\d{1,2}[\s\.\-\/]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\.\-\/]+\d{4})', re.IGNORECASE)  # DD Mon YYYY or DD/Mon/YYYY
    ]
    
    extracted_date = None
    
    # Pre-process lines for date extraction to fix common OCR typos in dates (O->0, l->1, etc.)
    # But only apply this temporary fix for date searching to avoid messing up text
    
    def clean_date_line(l):
        # Replace O/o with 0, I/l with 1 inside probable numeric sequences
        # Simple approach: just replace globally for the check
        return l.replace('O', '0').replace('o', '0').replace('l', '1').replace('I', '1').replace('g', '9')

    # Pass 1: Look for "Date" keyword lines first (High Confidence)
    for line in clean_lines:
        if "DATE" in line.upper():
            # Clean OCR noise from line to help regex (e.g. "Date: 12/01/2026" -> "Date 12/01/2026")
            clean_line = line.replace(':', ' ').replace('.', ' ')
            clean_line = clean_date_line(clean_line)
            
            for pattern in date_patterns:
                match = pattern.search(clean_line) or pattern.search(line)
                if match:
                    date_str = match.group(1)
                    extracted_date = parse_date_string(date_str)
                    if extracted_date: break
        if extracted_date: break
        
    # Pass 2: If no date found near "Date" keyword, scan all lines
    if not extracted_date:
        for line in clean_lines:
            clean_line = clean_date_line(line)
            for pattern in date_patterns:
                match = pattern.search(clean_line)
                if match:
                    date_str = match.group(1)
                    extracted_date = parse_date_string(date_str)
                    if extracted_date: break
            if extracted_date: break
            
    data["date_extracted"] = extracted_date or None
            
    return data

def correct_merchant_name(name):
    """
    Fixes common OCR misreads for merchant names using fuzzy logic or direct mapping.
    """
    if not name: return "Unknown"
    
    name_upper = name.upper()
    
    # Direct mappings for known errors
    corrections = {
        "DIG HART": "Big Mart",
        "DIG MART": "Big Mart",
        "BIG HART": "Big Mart",
        "DLG HART": "Big Mart",
        "BHAT BHATENI": "Bhat Bhateni",
        "BHAT BHATEN": "Bhat Bhateni",
        "BHAT-BHATENI": "Bhat Bhateni"
    }
    
    # Check for partial matches
    if "BHAT" in name_upper and "BHATENI" in name_upper:
        return "Bhat Bhateni"
    if "BIG" in name_upper and "MART" in name_upper:
        return "Big Mart"
    if "DIG" in name_upper and "HART" in name_upper:
        return "Big Mart"
        
    return corrections.get(name_upper, name)

def parse_date_string(date_str):
    """Helper to try multiple formats and handle Vikram Samvat conversion"""
    # Normalize separators
    date_str = date_str.replace(' ', '').replace('.', '/').replace('-', '/')
    
    formats = [
        "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%y",
        "%Y-%m-%d", "%d-%m-%Y", 
        "%b%d,%Y", "%d%b%Y" # Compressed due to space removal above
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            
            # Vikram Samvat (Nepal) Detection & Conversion
            # VS years are typically 2000-2100 (56-57 years ahead of Gregorian)
            if dt.year > 2028 and dt.year < 2150:
                # This is likely Vikram Samvat - convert to Gregorian
                # VS is approximately 56.7 years ahead of Gregorian
                # More accurate: VS 2082 = AD 2025/2026 (varies by month)
                
                # Approximate conversion (good enough for budget tracking)
                gregorian_year = dt.year - 57
                
                # Adjust month if needed (VS calendar months don't align perfectly)
                # For simplicity, we'll use the same month/day
                try:
                    converted_dt = datetime(gregorian_year, dt.month, dt.day)
                    print(f"Converted VS date {dt} to Gregorian {converted_dt}")
                    return converted_dt
                except ValueError:
                    # If day doesn't exist in that month, use last day of month
                    import calendar
                    last_day = calendar.monthrange(gregorian_year, dt.month)[1]
                    converted_dt = datetime(gregorian_year, dt.month, min(dt.day, last_day))
                    print(f"Converted VS date {dt} to Gregorian {converted_dt} (adjusted day)")
                    return converted_dt
            
            # Normal Gregorian date
            return dt
        except:
            continue
    return None
            
    return data
