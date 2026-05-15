import os, json, traceback
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

doc_id = "5740afa8-6d48-4944-b86e-ee1dc4c192fb"
user_id = "local_dev_user_001"

print("=== Test 1: Select all columns ===")
try:
    result = supabase.table("documents").select("*").eq("id", doc_id).execute()
    if result.data:
        doc = result.data[0]
        print(f"Columns: {list(doc.keys())}")
        print(f"has flashcards: {'flashcards' in doc}")
        print(f"has quiz_questions: {'quiz_questions' in doc}")
    else:
        print("No data found")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

print("\n=== Test 2: Select quiz_questions specifically ===")
try:
    result = supabase.table("documents").select("quiz_questions").eq("id", doc_id).eq("user_id", user_id).execute()
    print(f"Success! Data: {result.data}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()

print("\n=== Test 3: Select flashcards specifically ===")
try:
    result = supabase.table("documents").select("flashcards").eq("id", doc_id).eq("user_id", user_id).execute()
    print(f"Success! Data: {result.data}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
