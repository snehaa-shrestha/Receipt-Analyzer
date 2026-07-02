import re

supported_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CNY', 'HKD', 'NPR', 'Rs.', 'Rs']
pattern = fr'({"|".join(map(re.escape, supported_currencies))})?\s*(\d[0-9.,]*\d(?:/-)?|\d(?:/-)?)'

text = "Total Rs. 1500.00"
print("Matches for:", text)
for m in re.finditer(pattern, text):
    print(m.groups())

def clean_numeric_value(s: str) -> float:
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

print(clean_numeric_value("1,500.00"))
print(clean_numeric_value("Rs 1500"))
