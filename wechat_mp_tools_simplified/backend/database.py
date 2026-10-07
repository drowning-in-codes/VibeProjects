import sqlite3
from pathlib import Path
from typing import Iterable

from .models import Account


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    fakeid TEXT PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    alias TEXT NOT NULL DEFAULT '',
                    avatar TEXT NOT NULL DEFAULT '',
                    signature TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS follows (
                    fakeid TEXT PRIMARY KEY REFERENCES accounts(fakeid) ON DELETE CASCADE,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert_accounts(self, accounts: Iterable[Account]) -> None:
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO accounts (fakeid, nickname, alias, avatar, signature)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(fakeid) DO UPDATE SET
                    nickname = excluded.nickname,
                    alias = excluded.alias,
                    avatar = excluded.avatar,
                    signature = excluded.signature,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (item.fakeid, item.nickname, item.alias, item.avatar, item.signature)
                    for item in accounts
                ],
            )

    def list_followed(self) -> list[dict]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT a.fakeid, a.nickname, a.alias, a.avatar, a.signature
                FROM follows f
                JOIN accounts a ON a.fakeid = f.fakeid
                ORDER BY f.created_at DESC, a.nickname COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def set_followed(self, account: Account, followed: bool) -> list[dict]:
        self.upsert_accounts([account])
        with self.connect() as connection:
            if followed:
                connection.execute(
                    "INSERT OR IGNORE INTO follows (fakeid) VALUES (?)",
                    (account.fakeid,),
                )
            else:
                connection.execute("DELETE FROM follows WHERE fakeid = ?", (account.fakeid,))
        return self.list_followed()
