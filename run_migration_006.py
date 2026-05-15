"""Run migration 006 using Supabase REST API."""
import os
import sys
import requests
from pathlib import Path

# Fix encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

SUPABASE_URL = "https://zylckskdbbhiohbacxkd.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp5bGNrc2tkYmJoaW9oYmFjeGtkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Njg0MjE0NiwiZXhwIjoyMDkyNDE4MTQ2fQ.P5mNuHcxa8hxnbHgW16okSbabTHC7we75ojsAfPMyXw"

def main():
    migration_path = Path(__file__).parent / "migrations" / "006_shared_quiz.sql"
    sql = migration_path.read_text(encoding="utf-8")

    print("=" * 60)
    print("DATABASE MIGRATION: 006_shared_quiz.sql")
    print("=" * 60)
    print()
    print("Tables to create:")
    print("  - user_profiles (Store real Zalo info: display_name, avatar_url)")
    print("  - shared_quizzes (Public quizzes created by teachers)")
    print("  - quiz_attempts (Student quiz results)")
    print("  - user_quiz_bookmarks (Bookmarked questions)")
    print("  - user_flashcard_notes (Highlights, notes)")
    print("  - flashcard_progress (SM-2 spaced repetition)")
    print()
    print("=" * 60)
    print()
    print("HOW TO RUN MIGRATION:")
    print()
    print("1. Open Supabase Dashboard:")
    print(f"   {SUPABASE_URL}/studio")
    print()
    print("2. Go to SQL Editor (left menu)")
    print()
    print("3. Copy entire content of file:")
    print(f"   {migration_path}")
    print()
    print("4. Paste into SQL Editor and press 'Run'")
    print()
    print("Or run directly with psql:")
    db_url = os.getenv('DATABASE_URL', 'YOUR_DATABASE_URL')
    print(f"   psql {db_url} < migrations/006_shared_quiz.sql")
    print()
    print("=" * 60)
    print()
    print("After migration completes:")
    print("  - Teacher uploads file -> AI generates quiz ONCE")
    print("  - Teacher creates share link -> sends to 100 students")
    print("  - Students take quiz -> NO AI token cost")
    print("  - Teacher sees dashboard -> real Zalo names shown")
    print()

if __name__ == "__main__":
    main()