import sys

with open('/Applications/javaclas/ml/regenerate_chapters.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

output_lines = []
for i, line in enumerate(lines):
    output_lines.append(line)
    if i + 1 == 1177:
        break

while output_lines and output_lines[-1].strip() == '':
    output_lines.pop()

if not output_lines[-1].endswith('\n'):
    output_lines[-1] += '\n'

with open('/Applications/javaclas/ml/regenerate_chapters.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print(f'Truncated to {len(output_lines)} lines')

with open('/Applications/javaclas/ml/regenerate_chapters.py', 'r', encoding='utf-8') as f:
    content = f.read()
last_lines = content.split('\n')[-4:]
for line in last_lines:
    if line.strip():
        print(repr(line))