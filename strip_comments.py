import os

def strip_python_comments(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')
    
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith('#'):
            # Keep important ones
            lower = line.lower()
            if 'todo' in lower or 'fixme' in lower or 'important' in lower or 'note:' in lower:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

def strip_js_comments(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.read().split('\n')
        
    new_lines = []
    for line in lines:
        stripped = line.lstrip()
        # Single line JS comment
        if stripped.startswith('//'):
            lower = line.lower()
            if 'todo' in lower or 'fixme' in lower or 'important' in lower or 'note:' in lower:
                new_lines.append(line)
        # Single line JSX comment
        elif stripped.startswith('{/*') and stripped.endswith('*/}'):
            continue
        else:
            new_lines.append(line)
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))

backend_dir = r'd:\ReceiptAnalyzer\backend\app'
frontend_dir = r'd:\ReceiptAnalyzer\frontend\src'

count = 0
for root, _, files in os.walk(backend_dir):
    for f in files:
        if f.endswith('.py'):
            strip_python_comments(os.path.join(root, f))
            count += 1

for root, _, files in os.walk(frontend_dir):
    for f in files:
        if f.endswith(('.js', '.jsx')):
            strip_js_comments(os.path.join(root, f))
            count += 1

print(f"Processed {count} files.")
