with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check that the drag handle is removed
if 'id="bar-handle"' not in content:
    print("SUCCESS: drag handle removed")
else:
    print("ERROR: drag handle still exists")

# Check that tab-layer pill is removed
if 'id="tab-layer"' not in content:
    print("SUCCESS: tab-layer removed")
else:
    print("ERROR: tab-layer still exists")

# Check right panel properties exist
if 'id="rp-panel-viewer"' in content and 'id="rp-opacity"' in content:
    print("SUCCESS: Right panel properties exist")
else:
    print("ERROR: Right panel properties missing")

# Check that #element-action-bar was NOT added
if 'id="element-action-bar"' not in content:
    print("SUCCESS: element-action-bar correctly avoided")
else:
    print("ERROR: element-action-bar was added")
