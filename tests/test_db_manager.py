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
        db_manager.save_cache(diff_hash, prompt_hash, model, response, 0.0)
        
        # Get
        cached = db_manager.get_cache(diff_hash, prompt_hash, model)
        assert cached == response

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
        time.sleep(1.1) # Ensure timestamp difference (sqlite default is seconds resolution usually, but let's be safe)
        db_manager.save_cache(diff_hash, prompt_hash, model, "New Response", 0.0)
        
        cached = db_manager.get_cache(diff_hash, prompt_hash, model)
        assert cached == "New Response"
