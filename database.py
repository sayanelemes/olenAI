"""
database.py
Async SQLite database manager with WAL (Write-Ahead Logging) mode,
synchronous=NORMAL, and busy_timeout=5000 for high-concurrency order tracking.
All queries are strictly parameterized with ? placeholders.
"""

import logging
from typing import Any
import aiosqlite

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Thread-safe and async-safe SQLite manager using aiosqlite in WAL mode.
    Guarantees concurrency isolation across multiple workers without 'database is locked' errors.
    """

    def __init__(self, db_path: str = "bot_orders.db") -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init_db(self) -> None:
        """
        Initialize persistent connection, set concurrency PRAGMAs and create schema.
        """
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row

        # Concurrency & Performance PRAGMAs
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA synchronous=NORMAL;")
        await self._conn.execute("PRAGMA busy_timeout=5000;")
        await self._conn.commit()

        await self._create_tables()
        logger.info("DatabaseManager initialized at '%s' with WAL mode.", self.db_path)

    async def _create_tables(self) -> None:
        """
        Create 'orders' table if it does not already exist.
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS orders (
            charge_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            prompt TEXT,
            tags TEXT,
            status TEXT DEFAULT 'PENDING',
            audio_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await self._conn.execute(create_sql)
        await self._conn.commit()

    async def create_order(
        self,
        charge_id: str,
        user_id: int,
        prompt: str,
        tags: str,
        status: str = "PAID",
    ) -> None:
        """
        Insert a new order or update existing order on conflict using parameterized SQL.
        """
        sql = """
        INSERT INTO orders (charge_id, user_id, prompt, tags, status)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(charge_id) DO UPDATE SET
            user_id = excluded.user_id,
            prompt = excluded.prompt,
            tags = excluded.tags,
            status = excluded.status;
        """
        await self._conn.execute(sql, (charge_id, user_id, prompt, tags, status))
        await self._conn.commit()
        logger.info("Saved order %s (user_id=%d, status=%s) to database.", charge_id, user_id, status)

    async def update_status(
        self,
        charge_id: str,
        status: str,
        audio_url: str | None = None,
    ) -> None:
        """
        Update order processing status and optional audio_url.
        """
        if audio_url is not None:
            sql = "UPDATE orders SET status = ?, audio_url = ? WHERE charge_id = ?;"
            params = (status, audio_url, charge_id)
        else:
            sql = "UPDATE orders SET status = ? WHERE charge_id = ?;"
            params = (status, charge_id)

        await self._conn.execute(sql, params)
        await self._conn.commit()
        logger.info("Updated order %s status to '%s'.", charge_id, status)

    async def get_order(self, charge_id: str) -> dict[str, Any] | None:
        """
        Retrieve order by its charge_id.
        """
        sql = "SELECT * FROM orders WHERE charge_id = ?;"
        async with self._conn.execute(sql, (charge_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def close(self) -> None:
        """
        Close active database connection.
        """
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed.")
