"""Debug script to check if admin user gets created in test DB."""
import os
import tempfile

os.environ['JWT_SECRET_KEY'] = 'test-secret-key-for-testing-only-32chars!!'
os.environ['IS_PRODUCTION'] = 'false'
os.environ['ENCRYPTION_KEY'] = 'test-encryption-key-for-testing-32!'
os.environ['ADMIN_USERNAME'] = 'admin'
os.environ['ADMIN_PASSWORD'] = 'admin'

from unittest.mock import patch
import djen.api.database as db_mod

tmp = tempfile.mkdtemp()
db_path = os.path.join(tmp, 'test.db')
test_db = db_mod.Database(db_path=db_path)
db_mod._db_instance = test_db

def get_test_db():
    return test_db

with patch.object(db_mod, 'get_database', get_test_db), \
     patch('djen.api.app.get_database', get_test_db), \
     patch('djen.api.auth.get_database', get_test_db), \
     patch('djen.api.app.start_scheduler'):
    from djen.api.app import app

# Check tables
tables = test_db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Tables: {[t[0] for t in tables]}")

# Check if users table has data
try:
    rows = test_db.conn.execute('SELECT * FROM users').fetchall()
    print(f"Users in DB: {len(rows)}")
    for r in rows:
        print(dict(r))
except Exception as e:
    print(f"Error querying users: {e}")

# Try to authenticate
from djen.api.auth import authenticate_user, _get_db
print(f"\n_get_db() returns: {_get_db()}")
print(f"test_db is: {test_db}")
print(f"Same object? {_get_db() is test_db}")

user = authenticate_user("admin", "admin")
print(f"\nauthenticate_user result: {user}")
