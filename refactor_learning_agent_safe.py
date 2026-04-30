import os
import ast

filepath = '/Users/ajayyy/Desktop/GenAI Academy APAC/Saarthi-AI/agents/learning_agent.py'
with open(filepath, 'r') as f:
    content = f.read()

# To do this safely, we replace specific patterns or do it line by line exactly matching `return json.dumps(...)` if it's on the same line, or we can use a more precise string replacement.

lines = content.split('\n')
for i in range(len(lines)):
    line = lines[i]
    if 'return json.dumps(' in line:
        if 'default=str)' in line:
            new_line = line.replace('return json.dumps(', 'return ').replace(', default=str)', '')
        else:
            # this assumes the ending ) is at the end of the line
            new_line = line.replace('return json.dumps(', 'return ')
            if new_line.endswith(')'):
                new_line = new_line[:-1]
        lines[i] = new_line

content = '\n'.join(lines)

with open(filepath, 'w') as f:
    f.write(content)
print("Done")
