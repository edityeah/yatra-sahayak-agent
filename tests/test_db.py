import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import db


def test_get_pool_none_when_db_disabled(monkeypatch):
    from agent.config import get_settings
    get_settings.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    pool = asyncio.run(db.get_pool())
    assert pool is None


def test_sanitize_pg_url_strips_pgbouncer():
    out = db._sanitize_pg_url("postgresql://u:p@host:6543/db?pgbouncer=true&sslmode=require")
    assert "pgbouncer" not in out
    assert "sslmode=require" in out
