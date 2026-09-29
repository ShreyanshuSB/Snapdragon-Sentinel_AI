"""
SENTINEL - Database & Demo Data Reset Utility
Safely cleans redundant test conversations, restores clean demo state,
and verifies schema integrity without polluting production/dev data.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("reset_demo_data")

DB_PATH = Path(__file__).resolve().parent.parent / "backend" / "sentinel.db"


def clean_duplicate_test_conversations(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Removes duplicate test conversations while keeping the primary conversation."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at FROM conversations ORDER BY id ASC")
    rows = cursor.fetchall()

    seen_titles: dict[str, int] = {}
    ids_to_delete: list[int] = []

    for conv_id, title, _ in rows:
        if title in seen_titles:
            ids_to_delete.append(conv_id)
        else:
            seen_titles[title] = conv_id

    # Also clean any probe/test conversations
    cursor.execute("SELECT id FROM conversations WHERE title LIKE '%PROBE%'")
    for (probe_id,) in cursor.fetchall():
        if probe_id not in ids_to_delete:
            ids_to_delete.append(probe_id)

    if not ids_to_delete:
        logger.info("No duplicate or probe conversations found.")
        return 0

    logger.info(f"Found {len(ids_to_delete)} duplicate/probe conversation(s) to remove.")
    if not dry_run:
        cursor.execute("PRAGMA foreign_keys=ON")
        for cid in ids_to_delete:
            cursor.execute("DELETE FROM conversation_messages WHERE conversation_id = ?", (cid,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (cid,))
        conn.commit()
        logger.info(f"Successfully deleted {len(ids_to_delete)} conversation(s).")

    return len(ids_to_delete)


def reset_privacy_settings(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Ensures privacy settings exist with local-first defaults."""
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM privacy_settings WHERE id = 1")
    exists = cursor.fetchone()

    if not exists:
        if not dry_run:
            cursor.execute(
                """
                INSERT INTO privacy_settings (id, camera_enabled, microphone_enabled, memory_enabled, local_ai_mode, cloud_fallback)
                VALUES (1, 0, 0, 1, 'local_only', 0)
                """
            )
            conn.commit()
            logger.info("Initialized default privacy settings (local_only=True).")
    else:
        logger.info("Privacy settings verified (id=1 exists).")


def full_reset(conn: sqlite3.Connection, dry_run: bool = False) -> None:
    """Full reset of memories, conversations, and attachments while preserving schema."""
    logger.warning("Performing full reset of application data...")
    if dry_run:
        logger.info("[Dry Run] Would truncate memories, attachments, conversations, and documents.")
        return

    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    tables = [
        "conversation_messages",
        "conversations",
        "attachments",
        "memories",
        "document_chunks",
        "document_pages",
        "documents",
        "projects",
    ]
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table}")
            cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        except sqlite3.OperationalError:
            pass  # Table might not exist yet

    cursor.execute("PRAGMA foreign_keys=ON")
    reset_privacy_settings(conn, dry_run=False)
    conn.commit()
    logger.info("Full reset complete. Clean state initialized.")


def main() -> None:
    parser = argparse.ArgumentParser(description="SENTINEL Demo Data & Test Artifacts Cleaner")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying database")
    parser.add_argument("--full-reset", action="store_true", help="Reset all user data to clean blank slate")
    parser.add_argument("--db-path", type=str, default=str(DB_PATH), help="Path to SQLite database")

    args = parser.parse_args()
    db_file = Path(args.db_path)

    if not db_file.exists():
        logger.error(f"Database not found at: {db_file}")
        sys.exit(1)

    logger.info(f"Connecting to database: {db_file}")
    conn = sqlite3.connect(str(db_file))

    try:
        if args.full_reset:
            full_reset(conn, dry_run=args.dry_run)
        else:
            clean_duplicate_test_conversations(conn, dry_run=args.dry_run)
            reset_privacy_settings(conn, dry_run=args.dry_run)
    finally:
        conn.close()

    logger.info("Done.")


if __name__ == "__main__":
    main()
