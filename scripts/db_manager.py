#!/usr/bin/env python3
import sqlite3
import sys
import os
import json

# Database path: repo_root/data/history.sqlite
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(REPO_ROOT, 'data', 'history.sqlite')

def init_db():
    """Initialize the SQLite database and schema."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  diff_hash TEXT,
                  prompt_hash TEXT,
                  model TEXT,
                  response TEXT,
                  cost REAL,
                  repo_name TEXT)''')
    
    # Check if repo_name column exists (migration)
    c.execute("PRAGMA table_info(analysis_history)")
    columns = [info[1] for info in c.fetchall()]
    if 'repo_name' not in columns:
        print("[DB] Migrating: Adding repo_name column...")
        c.execute("ALTER TABLE analysis_history ADD COLUMN repo_name TEXT")

    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_cache ON analysis_history (diff_hash, prompt_hash, model)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_repo ON analysis_history (repo_name, timestamp)')
    
    conn.commit()
    conn.close()
    # print(f"[DB] Initialized at {DB_PATH}")

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

def get_context(repo_name, limit=3):
    """Retrieve recent analysis history for context."""
    if not os.path.exists(DB_PATH):
        return []
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Get recent successful responses for this repo
    c.execute('''SELECT timestamp, model, response FROM analysis_history 
                 WHERE repo_name=? 
                 ORDER BY timestamp DESC LIMIT ?''',
              (repo_name, limit))
    rows = c.fetchall()
    conn.close()
    
    context = []
    for row in rows:
        context.append({
            "timestamp": row['timestamp'],
            "model": row['model'],
            "response": row['response']
        })
    return context

def save_cache(diff_hash, prompt_hash, model, response, cost=0.0, repo_name=None):
    """Save a new analysis result."""
    init_db() # Ensure DB exists
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO analysis_history (diff_hash, prompt_hash, model, response, cost, repo_name) 
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (diff_hash, prompt_hash, model, response, cost, repo_name))
    conn.commit()
    conn.close()
    print(f"[DB] Saved cache entry for {diff_hash[:8]} (Repo: {repo_name})")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: db_manager.py <init|get|save|get-context> [args...]")
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
            
    elif cmd == 'get-context':
        if len(sys.argv) < 3:
            print("Usage: db_manager.py get-context <repo_name> [limit]")
            sys.exit(1)
        repo = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 3
        ctx = get_context(repo, limit)
        print(json.dumps(ctx))
            
    elif cmd == 'save':
        # Updated signature: save <diff_hash> <prompt_hash> <model> <response_file> <cost> [repo_name]
        if len(sys.argv) < 7:
            print("Usage: db_manager.py save <diff_hash> <prompt_hash> <model> <response_file> <cost> [repo_name]")
            sys.exit(1)
        
        try:
            with open(sys.argv[5], 'r', encoding='utf-8') as f:
                response = f.read()
        except FileNotFoundError:
            print(f"[ERROR] Response file not found: {sys.argv[5]}")
            sys.exit(1)
            
        repo_name = sys.argv[7] if len(sys.argv) > 7 else None
        save_cache(sys.argv[2], sys.argv[3], sys.argv[4], response, float(sys.argv[6]), repo_name)
        
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
