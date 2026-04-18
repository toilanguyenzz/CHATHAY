import asyncio
from services.ai_summarizer import summarize_text_structured

async def test_bulk_accounts():
    doc_text = """
    DANH SÁCH TÀI KHOẢN HỆ THỐNG TRƯỜNG THPT
    1. Nguyễn Văn A - Tên ĐN: nguyenvana123 - MK: a@123
    2. Trần Tuấn Anh - Tên ĐN: tuananhtran - MK: tuananh@456
    3. Lê Thị B - Tên ĐN: lethib - MK: bb@789
    4. Phạm Văn C - Tên ĐN: pvc_admin - MK: admin!@#
    """
    
    print("1. Thử gửi danh sách...")
    result = await summarize_text_structured(doc_text)
    
    print("==== KẾT QUẢ PHÂN LOẠI ====")
    print("Doc Type:", result.get("document_type"))
    print("Recommended Action:", result.get("recommended_action"))
    
    print("\n2. Thử giả lập user gửi tên để lấy riêng tài khoản...")
    user_name = "Trần Tuấn Anh"
    account_prompt = (
        f"Tài liệu sau là danh sách nhiều thông tin đăng nhập/tài khoản.\\n"
        f"Người dùng tên '{user_name}'.\\n\\n"
        f"Hãy tìm chính xác tài khoản, mật khẩu, và tên hệ thống của người có tên '{user_name}' (hoặc tên gần giống).\\n"
        f"Định dạng như sau:\\n"
        f"Hệ thống: ...\\n"
        f"Tài khoản: ...\\n"
        f"Mật khẩu: ...\\n"
        f"Nếu không tìm thấy ai tên này, hãy thông báo: 'Không tìm thấy thông tin của {user_name} trong danh sách'.\\n"
        f"Trả lời gọn gàng trực tiếp.\\n\\n"
        f"NỘI DUNG TÀI LIỆU:\\n{doc_text[:8000]}"
    )
    
    acct_result = await summarize_text_structured(account_prompt)
    points = acct_result.get("points", [])
    if points:
        print("==== KẾT QUẢ RÚT TRÍCH ====")
        print(points[0].get("detail", ""))
    else:
        print("Overview:", acct_result.get("overview"))

if __name__ == "__main__":
    asyncio.run(test_bulk_accounts())
