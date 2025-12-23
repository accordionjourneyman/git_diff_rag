import pytest
import os
import sqlite3
import sys
from unittest.mock import patch

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts"))
import db_manager

class TestDBManager:
    @pytest.fixture
    def db_path(self, tmp_path):
        path = tmp_path / "test_history.sqlite"
        with patch('db_manager.DB_PATH', str(path)):
            yield str(path)

    def test_init_db(self, db_path):
        db_manager.init_db()
        assert os.path.exists(db_path)
        
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_history'")
        assert c.fetchone() is not None
        conn.close()

    def test_save_and_get_cache(self, db_path):
        db_manager.init_db()
        
        diff_hash = "hash1"
        prompt_hash = "hash2"
        model = "gemini-test"
        response = "Cached Response"
        
        # Save
        db_manager.save_cache(diff_hash, prompt_hash, model, response, 0.0, repo_name="test-repo", summary="Test Summary", tags="tag1,tag2", entry_type="agent_session")
        
        # Get
        cached = db_manager.get_cache(diff_hash, prompt_hash, model)
        assert cached == response

    def test_get_context_prioritization(self, db_path):
        db_manager.init_db()
        repo = "test-repo"
        
        # Save a review
        db_manager.save_cache("h1", "p1", "m1", "Review Resp", 0.0, repo_name=repo, entry_type="review")
        # Save a session (later)
        db_manager.save_cache("h2", "p2", "m2", "Session Resp", 0.0, repo_name=repo, entry_type="agent_session")
        
        ctx = db_manager.get_context(repo, limit=5)
        # Session should be first despite being second in time (or same time) because of prioritization logic
        assert ctx[0]['entry_type'] == 'agent_session'
        assert ctx[0]['response'] == "Session Resp"

    def test_fts_search(self, db_path):
        db_manager.init_db()
        repo = "search-repo"
        
        db_manager.save_cache("h1", "p1", "m1", "R1", 0.0, repo_name=repo, summary="Authentication Logic", tags="auth,security")
        db_manager.save_cache("h2", "p2", "m1", "R2", 0.0, repo_name=repo, summary="Data Pipeline", tags="db,etl")
        
        # Search summary
        ctx = db_manager.get_context(repo, search_query="Authentication")
        assert len(ctx) == 1
        assert "Authentication" in ctx[0]['summary']
        
        # Search tags
        ctx = db_manager.get_context(repo, search_query="etl")
        assert len(ctx) == 1
        assert "Data Pipeline" in ctx[0]['summary']

    def test_cache_miss(self, db_path):
        db_manager.init_db()
        cached = db_manager.get_cache("nonexistent", "hash", "model")
        assert cached is None

    def test_get_latest_cache(self, db_path):
        db_manager.init_db()
        
        diff_hash = "hash1"
        prompt_hash = "hash2"
        model = "gemini-test"
        
        db_manager.save_cache(diff_hash, prompt_hash, model, "Old Response", 0.0)
        import time
        time.sleep(1.1) 
        db_manager.save_cache(diff_hash, prompt_hash, model, "New Response", 0.0)
        
        cached = db_manager.get_cache(diff_hash, prompt_hash, model)
        assert cached == "New Response"
