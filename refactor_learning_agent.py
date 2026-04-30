import re
import os

filepath = '/Users/ajayyy/Desktop/GenAI Academy APAC/Saarthi-AI/agents/learning_agent.py'
with open(filepath, 'r') as f:
    content = f.read()

# Replace json.dumps({ ... }, default=str) with { ... }
content = re.sub(r'json\.dumps\((.*?)(?:,\s*default=str)?\)', r'\1', content, flags=re.DOTALL)

with open(filepath, 'w') as f:
    f.write(content)

print(f"Refactored {filepath}")
