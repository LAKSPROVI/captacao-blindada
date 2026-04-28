"""Debug script to find the exact failing SQL statement in the schema."""
import sqlite3
import tempfile
import os

db_path = os.path.join(tempfile.mkdtemp(), 'test.db')
conn = sqlite3.connect(db_path)

db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'djen', 'api', 'database.py')
with open(db_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the executescript block
start_marker = 'conn.executescript("""'
end_marker = '""")'

start_idx = content.find(start_marker)
if start_idx == -1:
    print("Could not find executescript start")
    exit(1)

start_idx += len(start_marker)
end_idx = content.find(end_marker, start_idx)
if end_idx == -1:
    print("Could not find executescript end")
    exit(1)

schema = content[start_idx:end_idx]

# Split into individual statements and run each one
statements = [s.strip() for s in schema.split(';') if s.strip() and not s.strip().startswith('--')]

for i, stmt in enumerate(statements):
    # Skip pure comment lines
    lines = [l for l in stmt.split('\n') if l.strip() and not l.strip().startswith('--')]
    clean = '\n'.join(lines).strip()
    if not clean:
        continue
    try:
        conn.execute(clean)
        conn.commit()
    except Exception as e:
        print(f"FAIL at statement {i}: {e}")
        print(f"Statement:\n{clean[:300]}")
        print()
        # Don't break - show all failures
        
print("Done checking all statements")
conn.close()
os.unlink(db_path)
