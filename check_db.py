import os
from dotenv import load_dotenv
from supabase import create_client

# Tải biến môi trường từ file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Khong tim thay thong tin ket noi Supabase trong file .env!")
    exit(1)

# Kết nối database
print("Dang ket noi Database...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def print_separator():
    print("=" * 60)

def check_users():
    print_separator()
    print(" BAO CAO THONG TIN USER")
    print_separator()

    try:
        # Lấy danh sách user từ bảng user_usage
        response = supabase.table("user_usage").select("*").execute()
        users = response.data
        
        if not users:
            print("Chua co user nao trong he thong.")
            return

        print(f"Tong so ban ghi hoat dong: {len(users)}\n")
        
        # In header giống như bảng
        print(f"{'USER ID':<25} | {'NGAY':<12} | {'LUOT DUNG':<10} | {'SO COIN'}")
        print("-" * 60)
        
        for user in users[:20]: # Chỉ in 20 dòng đầu cho đỡ rối
            uid = str(user.get("user_id", "N/A"))
            date = str(user.get("date", "N/A"))
            count = str(user.get("count", 0))
            coin = str(user.get("coin_balance", 0))
            
            # Rút gọn user_id nếu quá dài
            if len(uid) > 20:
                uid = uid[:10] + "..." + uid[-5:]
                
            print(f"{uid:<25} | {date:<12} | {count:<10} | {coin}")

    except Exception as e:
        print(f"Loi khi lay du lieu user: {e}")

def check_study_sessions():
    print_separator()
    print(" TRANG THAI HOC TAP (Ai dang on thi?)")
    print_separator()

    try:
        # Lấy danh sách phiên học đang diễn ra
        response = supabase.table("study_sessions").select("user_id, mode, doc_id, created_at").execute()
        sessions = response.data
        
        if not sessions:
            print("Hien tai khong co ai dang on tap.")
            return
            
        print(f"Tong so phien hoc dang dien ra: {len(sessions)}\n")
        print(f"{'USER ID':<25} | {'CHE DO':<10} | {'MA TAI LIEU'}")
        print("-" * 60)
        
        for sess in sessions:
            uid = str(sess.get("user_id", "N/A"))
            mode = str(sess.get("mode", "N/A")).upper()
            doc_id = str(sess.get("doc_id", "N/A"))
            
            if len(uid) > 20: uid = uid[:10] + "..." + uid[-5:]
            if len(doc_id) > 15: doc_id = doc_id[:12] + "..."
                
            print(f"{uid:<25} | {mode:<10} | {doc_id}")

    except Exception as e:
        print(f"Loi khi lay du lieu hoc tap: {e}")

if __name__ == "__main__":
    check_users()
    check_study_sessions()
    print_separator()
    print("Hoan tat!")
