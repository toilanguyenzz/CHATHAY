import asyncio
import os
from unittest.mock import patch, MagicMock

# Mock các hàm gửi tin nhắn ra Zalo để nó in ra màn hình thay vì gọi API Zalo
async def mock_send_text_message(user_id, text):
    print(f"\n🤖 [BOT GỬI]:\n{text}\n")

async def mock_send_long_text_message(user_id, text, buttons=None):
    print(f"\n🤖 [BOT GỬI]:\n{text}")
    if buttons:
        print("\n👇 [NÚT BẤM KÈM THEO]:")
        for btn in buttons:
            title = btn.get('title', '')
            payload = btn.get('payload', '')
            print(f"  🔘 {title} -> (Payload: {payload})")
    print("\n")

async def mock_send_text_with_buttons(user_id, text, buttons):
    await mock_send_long_text_message(user_id, text, buttons)

async def test_cli():
    # Import zalo_webhook
    import zalo_webhook
    
    # Gắn mock vào các hàm của zalo_webhook
    zalo_webhook.send_text_message = mock_send_text_message
    zalo_webhook.send_long_text_message = mock_send_long_text_message
    zalo_webhook.send_text_with_buttons = mock_send_text_with_buttons
    
    print("=" * 60)
    print("🚀 CÔNG CỤ TEST LOCAL KHÔNG CẦN ZALO 🚀")
    print("=" * 60)
    print("• Gõ văn bản bình thường để test chat/hỏi đáp.")
    print("• Dán đường dẫn tuyệt đối của file (VD: C:\\tai-lieu.pdf hoặc D:\\anh.jpg) để test đọc file/ảnh.")
    print("• Gõ 'exit' hoặc 'quit' để thoát.\n")
    
    user_id = "test_local_user_123"
    
    while True:
        try:
            msg = input("👤 Bạn: ").strip()
            if msg.lower() in ['exit', 'quit']:
                break
            if not msg:
                continue
            
            # Kiểm tra nếu msg là 1 đường dẫn file hợp lệ
            if os.path.exists(msg) and os.path.isfile(msg):
                print(f"\n⏳ [HỆ THỐNG]: Đang xử lý file {os.path.basename(msg)}...")
                file_name = os.path.basename(msg)
                file_size = os.path.getsize(msg)
                file_type = zalo_webhook.get_file_type(file_name)
                
                # Mock hàm download để copy file local vào thư mục temp thay vì tải từ internet
                async def fake_download(url, dest):
                    import shutil
                    shutil.copy2(msg, dest)
                    return True
                
                zalo_webhook.download_zalo_file = fake_download
                
                if file_type == "image":
                    # Patch httpx cho nhánh xử lý ảnh
                    class MockResponse:
                        status_code = 200
                        @property
                        def content(self):
                            with open(msg, "rb") as f:
                                return f.read()
                    
                    class MockClient:
                        async def __aenter__(self):
                            return self
                        async def __aexit__(self, exc_type, exc_val, exc_tb):
                            pass
                        async def get(self, url):
                            return MockResponse()

                    with patch('httpx.AsyncClient', return_value=MockClient()):
                        await zalo_webhook.handle_zalo_image(user_id, "fake_image_url")
                else:
                    await zalo_webhook.handle_zalo_file(user_id, "fake_url", file_name, file_size)
            else:
                # Xử lý text bình thường
                await zalo_webhook.handle_zalo_text(user_id, msg)
                
        except Exception as e:
            print(f"\n❌ [LỖI]: {e}\n")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cli())
