#!/usr/bin/env python3
import sqlite3
import sys
import os

# Database path: repo_root/data/history.sqlite
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(REPO_ROOT, 'data', 'history.sqlite')

def init_db():
    """Initialize the SQLite database and schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  diff_hash TEXT,
                  prompt_hash TEXT,
                  model TEXT,
                  response TEXT,
                  cost REAL)''')
    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_cache ON analysis_history (diff_hash, prompt_hash, model)')
    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")

def get_cache(diff_hash, prompt_hash, model):
    """Retrieve cached response if exists."""
    if not os.path.exists(DB_PATH):
        return None
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''SELECT response FROM analysis_history 
                 WHERE diff_hash=? AND prompt_hash=? AND model=? 
                 ORDER BY timestamp DESC LIMIT 1''',
              (diff_hash, prompt_hash, model))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_cache(diff_hash, prompt_hash, model, response, cost=0.0):
    """Save a new analysis result."""
    init_db() # Ensure DB exists
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO analysis_history (diff_hash, prompt_hash, model, response, cost) 
                 VALUES (?, ?, ?, ?, ?)''',
              (diff_hash, prompt_hash, model, response, cost))
    conn.commit()
    conn.close()
    print(f"[DB] Saved cache entry for {diff_hash[:8]}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: db_manager.py <init|get|save> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]
    
    if cmd == 'init':
        init_db()
        
    elif cmd == 'get':
        if len(sys.argv) < 5:
            print("Usage: db_manager.py get <diff_hash> <prompt_hash> <model>")
            sys.exit(1)
        res = get_cache(sys.argv[2], sys.argv[3], sys.argv[4])
        if res:
            print(res)
            sys.exit(0) # Success
        else:
            sys.exit(1) # Not found
            
    elif cmd == 'save':
        if len(sys.argv) < 7:
            print("Usage: db_manager.py save <diff_hash> <prompt_hash> <model> <response_file> <cost>")
            sys.exit(1)
        
        try:
            with open(sys.argv[5], 'r', encoding='utf-8') as f:
                response = f.read()
        except FileNotFoundError:
            print(f"[ERROR] Response file not found: {sys.argv[5]}")
            sys.exit(1)
            
        save_cache(sys.argv[2], sys.argv[3], sys.argv[4], response, float(sys.argv[6]))
        
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
