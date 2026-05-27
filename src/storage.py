"""数据存储模块: YAML配置 + SQLite数据库"""

import os
import sqlite3

import yaml

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "live_summary.db")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


class Storage:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS live_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid INTEGER NOT NULL,
                uname TEXT NOT NULL,
                room_id INTEGER NOT NULL,
                title TEXT,
                popularity INTEGER,
                start_time TEXT,
                end_time TEXT,
                duration_min INTEGER,
                danmaku_count INTEGER DEFAULT 0,
                wordcloud_path TEXT,
                summary TEXT,
                date TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS danmaku (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                live_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                send_time TEXT,
                FOREIGN KEY (live_id) REFERENCES live_records(id)
            );
            CREATE INDEX IF NOT EXISTS idx_live_date ON live_records(date);
            CREATE INDEX IF NOT EXISTS idx_live_uid ON live_records(uid);
        """)
        self.conn.commit()

    # --- watch list (YAML) ---

    def get_watch_list(self) -> list[int]:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        uids = config.get("watch_list", [])
        return [u for u in uids if u != 0]

    def add_watch(self, uid: int):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        if uid not in config["watch_list"]:
            config["watch_list"].append(uid)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def remove_watch(self, uid: int):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config["watch_list"] = [u for u in config["watch_list"] if u != uid]
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def sync_watch_list(self, followings: list[dict]):
        uids = [f["uid"] for f in followings]
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        config["watch_list"] = uids
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    # --- live records (SQLite) ---

    def save_live_record(self, live: dict, danmakus: list[str]):
        from datetime import date
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO live_records (uid, uname, room_id, title, popularity,
                start_time, duration_min, danmaku_count, wordcloud_path, summary, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            live.get("uid"), live.get("uname"), live.get("room_id"),
            live.get("title"), live.get("popularity"),
            live.get("start_time"), live.get("duration_min"),
            len(danmakus), live.get("wordcloud_path"), live.get("summary"),
            date.today().isoformat()
        ))
        live_id = cur.lastrowid
        for dm in danmakus:
            cur.execute(
                "INSERT INTO danmaku (live_id, content) VALUES (?, ?)",
                (live_id, dm)
            )
        self.conn.commit()
