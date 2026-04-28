"""Debug: run schema SQL statement by statement using sqlite3 directly."""
import sqlite3
import tempfile
import os

db_path = os.path.join(tempfile.mkdtemp(), 'test.db')

# Read the database.py file
db_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'djen', 'api', 'database.py')
with open(db_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Extract the executescript SQL between the triple quotes
marker = 'conn.executescript("""'
start = content.find(marker)
if start == -1:
    print("Could not find executescript")
    exit(1)
start += len(marker)

# Find the closing """) - need to find the FIRST one after start
end = content.find('""")', start)
if end == -1:
    print("Could not find end of executescript")
    exit(1)

sql = content[start:end]

# Now try executescript on a fresh DB
conn = sqlite3.connect(db_path)
try:
    conn.executescript(sql)
    print("SUCCESS: All schema statements executed")
except sqlite3.OperationalError as e:
    print(f"EXECUTESCRIPT ERROR: {e}")
    print()
    # Now try to find which statement fails by running them one at a time
    # Use a proper SQL statement splitter
    print("Running statements individually to find the culprit...")
    conn2 = sqlite3.connect(os.path.join(tempfile.mkdtemp(), 'test2.db'))
    
    # Simple state machine to split SQL respecting comments and strings
    stmts = []
    current = []
    in_string = False
    string_char = None
    i = 0
    while i < len(sql):
        ch = sql[i]
        
        if in_string:
            current.append(ch)
            if ch == string_char:
                in_string = False
            i += 1
            continue
        
        # Check for line comment
        if ch == '-' and i + 1 < len(sql) and sql[i+1] == '-':
            # Skip to end of line
            nl = sql.find('\n', i)
            if nl == -1:
                break
            i = nl + 1
            continue
        
        # Check for string start
        if ch in ("'", '"'):
            in_string = True
            string_char = ch
            current.append(ch)
            i += 1
            continue
        
        if ch == ';':
            stmt = ''.join(current).strip()
            if stmt:
                stmts.append(stmt)
            current = []
            i += 1
            continue
        
        current.append(ch)
        i += 1
    
    # Last statement
    last = ''.join(current).strip()
    if last:
        stmts.append(last)
    
    print(f"Found {len(stmts)} statements")
    for idx, stmt in enumerate(stmts):
        try:
            conn2.execute(stmt)
            conn2.commit()
        except Exception as ex:
            first_line = stmt.split('\n')[0].strip()
            print(f"\nFAIL #{idx}: {ex}")
            print(f"  First line: {first_line}")
            print(f"  Full stmt ({len(stmt)} chars):")
            for line in stmt.split('\n')[:5]:
                print(f"    {line.rstrip()}")
            if len(stmt.split('\n')) > 5:
                print(f"    ... ({len(stmt.split(chr(10)))} lines total)")
    
    conn2.close()

conn.close()
