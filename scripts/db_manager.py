#!/usr/bin/env python3
import sqlite3
import sys
import os
import json
import argparse
from typing import Optional, List, Dict, Any

# Database path: repo_root/data/history.sqlite
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(REPO_ROOT, 'data', 'history.sqlite')

def get_db_connection():
    """Establishes a database connection."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the SQLite database and schema with versioning."""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create schema version table
    c.execute('''CREATE TABLE IF NOT EXISTS schema_version
                 (version INTEGER PRIMARY KEY,
                  applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  description TEXT)''')
    
    # Get current schema version
    c.execute('SELECT MAX(version) FROM schema_version')
    current_version = c.fetchone()[0] or 0
    
    # Apply migrations incrementally
    if current_version < 1:
        _apply_migration_v1(c)
        c.execute('INSERT INTO schema_version (version, description) VALUES (?, ?)', 
                 (1, 'Initial schema with analysis_history table'))
    
    if current_version < 2:
        _apply_migration_v2(c)
        c.execute('INSERT INTO schema_version (version, description) VALUES (?, ?)', 
                 (2, 'Add config_snapshot and enhanced columns'))
    
    conn.commit()
    conn.close()

def _apply_migration_v1(c):
    """Apply version 1: Initial schema."""
    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  diff_hash TEXT,
                  prompt_hash TEXT,
                  model TEXT,
                  response TEXT,
                  cost REAL,
                  repo_name TEXT,
                  summary TEXT,
                  tags TEXT,
                  entry_type TEXT DEFAULT 'review')''')
    
    # Create FTS5 Virtual Table for semantic search
    try:
        c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS analysis_history_fts 
                     USING fts5(id UNINDEXED, summary, tags, entry_type, content='analysis_history', content_rowid='id')''')
        
        # Triggers to keep FTS in sync
        c.execute('''CREATE TRIGGER IF NOT EXISTS history_ai AFTER INSERT ON analysis_history BEGIN
                     INSERT INTO analysis_history_fts(rowid, id, summary, tags, entry_type) VALUES (new.id, new.id, new.summary, new.tags, new.entry_type);
                     END''')
        c.execute('''CREATE TRIGGER IF NOT EXISTS history_ad AFTER DELETE ON analysis_history BEGIN
                     INSERT INTO analysis_history_fts(analysis_history_fts, rowid, id, summary, tags, entry_type) 
                     VALUES('delete', old.id, old.id, old.summary, old.tags, old.entry_type);
                     END''')
        c.execute('''CREATE TRIGGER IF NOT EXISTS history_au AFTER UPDATE ON analysis_history BEGIN
                     INSERT INTO analysis_history_fts(analysis_history_fts, rowid, id, summary, tags, entry_type) 
                     VALUES('delete', old.id, old.id, old.summary, old.tags, old.entry_type);
                     INSERT INTO analysis_history_fts(rowid, id, summary, tags, entry_type) 
                     VALUES (new.id, new.id, new.summary, new.tags, new.entry_type);
                     END''')
    except sqlite3.OperationalError as e:
        print(f"[DB] [WARN] FTS5 not supported or error: {e}")

    # Index for fast lookups
    c.execute('CREATE INDEX IF NOT EXISTS idx_cache ON analysis_history (diff_hash, prompt_hash, model)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_repo ON analysis_history (repo_name, timestamp)')

def _apply_migration_v2(c):
    """Apply version 2: Enhanced columns for auditability."""
    # Migration: Check for new columns
    c.execute("PRAGMA table_info(analysis_history)")
    existing_columns = {info[1] for info in c.fetchall()}
    
    required_columns = {
        'config_snapshot': 'TEXT'  # JSON snapshot of WorkflowConfig for auditability
    }
    
    for col, col_def in required_columns.items():
        if col not in existing_columns:
            print(f"[DB] Migrating: Adding {col} column...")
            try:
                c.execute(f"ALTER TABLE analysis_history ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError as e:
                print(f"[DB] Migration warning for {col}: {e}")

def get_cache(diff_hash: str, prompt_hash: str, model: str) -> Optional[str]:
    """Retrieve cached response if exists."""
    if not os.path.exists(DB_PATH):
        return None
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT response FROM analysis_history 
                 WHERE diff_hash=? AND prompt_hash=? AND model=? 
                 ORDER BY timestamp DESC LIMIT 1''',
              (diff_hash, prompt_hash, model))
    row = c.fetchone()
    conn.close()
    return row['response'] if row else None

def get_context(repo_name: str, limit: int = 3, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent analysis history for context, optionally filtered by search."""
    if not os.path.exists(DB_PATH):
        return [{"status": "no_history", "message": "<!-- No relevant historical reviews found (DB missing) -->"}]
        
    conn = get_db_connection()
    c = conn.cursor()
    
    query_base = "SELECT id, timestamp, model, response, summary, tags, entry_type FROM analysis_history"
    
    if search_query:
        # Search using FTS5
        try:
            c.execute('''SELECT h.id, h.timestamp, h.model, h.response, h.summary, h.tags, h.entry_type 
                         FROM analysis_history h
                         JOIN analysis_history_fts f ON h.id = f.rowid
                         WHERE h.repo_name=? AND analysis_history_fts MATCH ?
                         ORDER BY (h.entry_type = 'agent_session') DESC, rank LIMIT ?''',
                      (repo_name, search_query, limit))
        except sqlite3.OperationalError:
            # Fallback
            c.execute(f'''{query_base} 
                         WHERE repo_name=? AND (summary LIKE ? OR tags LIKE ?)
                         ORDER BY (entry_type = 'agent_session') DESC, timestamp DESC LIMIT ?''',
                      (repo_name, f'%{search_query}%', f'%{search_query}%', limit))
    else:
        c.execute(f'''{query_base} 
                     WHERE repo_name=? 
                     ORDER BY (entry_type = 'agent_session') DESC, timestamp DESC LIMIT ?''',
                  (repo_name, limit))
    
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        return [{"status": "no_history", "message": "<!-- No relevant historical reviews found -->"}]
        
    context = []
    for row in rows:
        context.append({
            "id": row['id'],
            "timestamp": row['timestamp'],
            "model": row['model'],
            "summary": row['summary'] or "No summary available",
            "tags": row['tags'] or "",
            "entry_type": row['entry_type'],
            "response": row['response']
        })
    return context


def get_analysis_with_config(entry_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve a specific analysis with its config snapshot for replay.
    
    Args:
        entry_id: Database ID of the analysis entry
        
    Returns:
        Dictionary with 'response', 'config_snapshot' (JSON string), and metadata,
        or None if not found.
    """
    if not os.path.exists(DB_PATH):
        return None
        
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''SELECT id, timestamp, diff_hash, prompt_hash, model, response, 
                        repo_name, summary, tags, entry_type, config_snapshot 
                 FROM analysis_history WHERE id=?''', (entry_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
        
    return {
        'id': row['id'],
        'timestamp': row['timestamp'],
        'diff_hash': row['diff_hash'],
        'prompt_hash': row['prompt_hash'],
        'model': row['model'],
        'response': row['response'],
        'repo_name': row['repo_name'],
        'summary': row['summary'],
        'tags': row['tags'],
        'entry_type': row['entry_type'],
        'config_snapshot': row['config_snapshot']  # JSON string of WorkflowConfig
    }

def save_cache(diff_hash: str, prompt_hash: str, model: str, response: str, 
               cost: float = 0.0, repo_name: str = None, summary: str = None, 
               tags: str = None, entry_type: str = 'review', config_snapshot: str = None):
    """Save a new analysis result with optional config snapshot for auditability.
    
    Args:
        diff_hash: SHA256 hash of the diff content
        prompt_hash: SHA256 hash of the base prompt
        model: LLM model name
        response: LLM response text
        cost: API cost (if tracked)
        repo_name: Repository name
        summary: Brief summary for context
        tags: Comma-separated tags
        entry_type: 'review' or 'agent_session'
        config_snapshot: JSON string of WorkflowConfig for reproducibility
    """
    init_db() # Ensure DB exists
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO analysis_history 
                 (diff_hash, prompt_hash, model, response, cost, repo_name, summary, tags, entry_type, config_snapshot) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (diff_hash, prompt_hash, model, response, cost, repo_name, summary, tags, entry_type, config_snapshot))
    conn.commit()
    conn.close()
    print(f"[DB] Saved {entry_type} entry for {diff_hash[:8]} (Repo: {repo_name}, Tags: {tags})")

def update_tags(entry_id: int, add_tags: str = None, remove_tags: str = None):
    """Manually update tags for a specific entry."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT tags FROM analysis_history WHERE id=?", (entry_id,))
    row = c.fetchone()
    if not row:
        print(f"[ERROR] Entry ID {entry_id} not found.")
        conn.close()
        return False
        
    current_tags = set(row['tags'].split(',') if row['tags'] else [])
    if add_tags:
        current_tags.update([t.strip() for t in add_tags.split(',')])
    if remove_tags:
        for t in remove_tags.split(','):
            current_tags.discard(t.strip())
            
    new_tags_str = ','.join(sorted(filter(None, current_tags)))
    c.execute("UPDATE analysis_history SET tags=? WHERE id=?", (new_tags_str, entry_id))
    conn.commit()
    conn.close()
    print(f"[DB] Updated tags for ID {entry_id}: {new_tags_str}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Manage the analysis history database.")
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Init command
    subparsers.add_parser('init', help='Initialize the database')

    # Get command
    get_parser = subparsers.add_parser('get', help='Get cached response')
    get_parser.add_argument('diff_hash', help='Hash of the diff')
    get_parser.add_argument('prompt_hash', help='Hash of the prompt')
    get_parser.add_argument('model', help='Model name')

    # Save command
    save_parser = subparsers.add_parser('save', help='Save analysis result')
    save_parser.add_argument('--diff-hash', required=True)
    save_parser.add_argument('--prompt-hash', required=True)
    save_parser.add_argument('--model', required=True)
    save_parser.add_argument('--response', required=True)
    save_parser.add_argument('--cost', type=float, default=0.0)
    save_parser.add_argument('--repo-name')
    save_parser.add_argument('--summary')
    save_parser.add_argument('--tags')
    save_parser.add_argument('--entry-type', default='review')

    # Get Context command
    context_parser = subparsers.add_parser('get-context', help='Get context for a repo')
    context_parser.add_argument('repo_name')
    context_parser.add_argument('--limit', type=int, default=3)
    context_parser.add_argument('--search')

    # Tag command
    tag_parser = subparsers.add_parser('tag', help='Update tags')
    tag_parser.add_argument('entry_id', type=int)
    tag_parser.add_argument('--add')
    tag_parser.add_argument('--remove')

    # Search command (new, exposed from get_context logic)
    search_parser = subparsers.add_parser('search', help='Search history')
    search_parser.add_argument('repo_name')
    search_parser.add_argument('query')
    search_parser.add_argument('--limit', type=int, default=5)

    args = parser.parse_args()

    if args.command == 'init':
        init_db()
    elif args.command == 'get':
        res = get_cache(args.diff_hash, args.prompt_hash, args.model)
        if res:
            print(res)
        else:
            sys.exit(1)
    elif args.command == 'save':
        response_content = args.response
        # Try to read as file if it looks like a path
        try:
            if os.path.exists(args.response):
                with open(args.response, 'r', encoding='utf-8') as f:
                    response_content = f.read()
        except OSError:
            pass
            
        save_cache(args.diff_hash, args.prompt_hash, args.model, response_content, 
                   args.cost, args.repo_name, args.summary, args.tags, args.entry_type)
    elif args.command == 'get-context':
        ctx = get_context(args.repo_name, args.limit, args.search)
        print(json.dumps(ctx, indent=2))
    elif args.command == 'tag':
        update_tags(args.entry_id, args.add, args.remove)
    elif args.command == 'search':
        ctx = get_context(args.repo_name, args.limit, args.query)
        print(json.dumps(ctx, indent=2))
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
