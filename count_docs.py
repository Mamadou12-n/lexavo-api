"""Count JSON docs and write to file."""
import os

base = r'C:\Users\bahma\Downloads\base-juridique-app\output'
count = 0
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith('.json') and not f.startswith('.'):
            count += 1

out = r'C:\Users\bahma\Downloads\base-juridique-app\logs\_count.txt'
with open(out, 'w') as f:
    f.write(str(count) + '\n')
print(count)
