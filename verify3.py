with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's double check Fix 1 is applied correctly
if '<label id="stroke-label">Stroke</label>' in content:
    print("Fix 1 is applied")
else:
    print("Fix 1 NOT applied")
