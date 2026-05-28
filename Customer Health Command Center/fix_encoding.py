path = r'c:\Users\nickr\OneDrive\Desktop\Project Folder\Customer Health Command Center\intervention_queue.html'

with open(path, 'rb') as f:
    raw = f.read()

# Undo the previous bad replacement of 0x3f -> &#x1F534;
raw = raw.replace(b'&#x1F534;', b'?')  # revert the 43 bad replacements first

# Now fix the actual mangled red circle bytes
bad_red = b'\xc3\xb0\xc5\xb8\xe2\x80\x9d\xc2\xb4'
count = raw.count(bad_red)
raw = raw.replace(bad_red, b'&#x1F534;')
print(f"Fixed {count}x red circle")

with open(path, 'wb') as f:
    f.write(raw)

# Verify
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()
idx = html.find('URGENT SAVE-PLAY')
print("Context:", html[max(0,idx-30):idx+20])
print("Done")
