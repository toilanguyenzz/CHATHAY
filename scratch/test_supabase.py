import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if url and key:
    supabase = create_client(url, key)
    try:
        # Fetch an existing table or something to test connection
        res = supabase.table("user_usage").select("*").limit(1).execute()
        print("Connected! user_usage data:", res.data)
    except Exception as e:
        print("Error connecting:", e)
else:
    print("No supabase credentials!")
