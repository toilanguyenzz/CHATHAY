#!/usr/bin/env python3
"""
Quick test for Mode Detection (Giai đoạn 1 validation)
Tests 6 samples: 3 STUDY_MATERIAL + 3 BUSINESS_DOC
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.mode_detector import detect_mode


# =====================================================
# TEST DATA: Replace these with real file content
# =====================================================

# Sample 1: Đề thi Toán THPT (STUDY_MATERIAL)
DE_THI_TOAN = """
ĐỀ THI THPT QUỐC GIA 2025
Môn: Toán
Thời gian: 90 phút

Câu 1: Giá trị của biểu thức √(4) là:
A. 2
B. -2
C. ±2
D. 0

Câu 2: Phương trình x² - 5x + 6 = 0 có nghiệm là:
A. x₁=1, x₂=6
B. x₁=2, x₂=3
C. x₁=-2, x₂=-3
D. x₁=3, x₂=2

[更多 câu hỏi...]
""".strip()

# Sample 2: Bài giảng Lý (STUDY_MATERIAL)
BAI_GIANG_LY = """
BÀI GIẢNG VẬT LÝ 12
Chương 3: Điện xoay chiều

3.1. Công thức điện áp: u = Uₘ sin(ωt + φ₀)
3.2. Động điện xoay chiều:
   - Từ trường: B = Bₘ sin(ωt)
   - Đòng điện: i = Iₘ sin(ωt + φ)
3.3. Công suất: P = UIcosφ
3.4. Hệ số công suất cosφ

Ví dụ: Tính công suất của động cơ có U=220V, I=5A, cosφ=0.8
P = 220 × 5 × 0.8 = 880W
""".strip()

# Sample 3: Slide Sử (STUDY_MATERIAL)
SLIDE_SU = """
KHÁNG CHIẾN CHỐNG MỸ 1954-1975

1. Kháng chiến toàn quốc 1946-1954
   - Chiến thắng Điện Biên Phủ 7/5/1954
   - Hiệp định Genève 21/7/1954

2. Kháng chiến chống Mỹ 1954-1975
   - Sự kiện 30/4/1975: Giải phóng miền Nam
   - Trận Điện Biên Phủ trên không (1972)
   - Chiến dịch Tây Nguyên (1975)

[Thêm nội dung...]
""".strip()

# Sample 4: Thông báo hành chính (BUSINESS_DOC)
THONG_BAO_NGHI_LE = """
CÔNG TY ABC
Số: 123/TB-2025
V/v: Thông báo nghỉ lễ 30/4 - 1/5/2025

Kính gửi: Toàn thể nhân viên

Công ty thông báo nghỉ lễ 30/4 và 1/5/2025 theo quy định.
Thời gian nghỉ: 2 ngày (30/4 và 1/5).
Nhân viên vui lòng hoàn thành công việc trước 17h ngày 29/4/2025.

Nếu cần làm việc urgent, liên hệ quản lý trực tiếp.

TP.HCM, ngày 25 tháng 4 năm 2025
GIÁM ĐỐC
(Ký tên, đóng dấu)
""".strip()

# Sample 5: Hóa đơn điện (BUSINESS_DOC)
HOA_DON_DIEN = """
HÓA ĐƠN TIỀN ĐIỆN
Số: HD-2025-04-001234
Kỳ: tháng 04/2025

Họ tên: Nguyễn Văn A
Địa chỉ: 123 Đường Lê Lợi, P.Bến Thành, Q.1
Số hồ sơ: 123456789

CHI TIÊT SỬ DỤNG:
- Điện năng: 250 kWh
- Đơn giá: 3,500 VNĐ/kWh
- Tiền điện: 875,000 VNĐ
- Phí bảo vì môi trường: 10,000 VNĐ
- VAT (10%): 88,500 VNĐ

TỔNG CỘNG: 973,500 VNĐ (Chín trăm bảy mươi ba nghìn năm trăm đồng)

Hạn thanh toán: 25/04/2025
""".strip()

# Sample 6: Quyết định (BUSINESS_DOC)
QUYET_DINH_PHE_DUYET = """
ỦY BAN NHÂN DÂN
TP. HÀ NỘI

QUYẾT ĐỊNH
Số: 1234/QĐ-UBND
V/v: Phê duyệt dự án đầu tư xây dựng...

THEO ĐỀ NGHỊ của Giám đốc Sở Kế hoạch và Đầu tư (tại Tờ trình số 456/TT-SKHĐT ngày 10/4/2025);

ỦY BAN NHÂN DÂN THÀNH PHỐ HÀ NỘI QUYẾT ĐỊNH:

Điều 1. Phê duyệt dự án đầu tư xây dựng... với các nội dung chính:
1. Tên dự án: ...
2. Địa điểm: ...
3. Quy mô: ...
4. Vốn đầu tư: 500 tỷ đồng.

Điều 2. Các cơ quan liên quan có trách nhiệm thi hành.

Nơi nhận:
- Như Điều 1;
- Lưu: VT, KHĐT.

TM. ỦY BAN NHÂN DÂN
CHỦ TỊCH
(Ký tên, đóng dấu)
""".strip()


# =====================================================
# TEST SUITES
# =====================================================

TEST_CASES = [
    {
        "name": "Đề thi Toán THPT",
        "text": DE_THI_TOAN,
        "expected_mode": "STUDY_MATERIAL",
        "confidence_min": 0.8
    },
    {
        "name": "Bài giảng Lý 12",
        "text": BAI_GIANG_LY,
        "expected_mode": "STUDY_MATERIAL",
        "confidence_min": 0.8
    },
    {
        "name": "Slide Sử lớp 12",
        "text": SLIDE_SU,
        "expected_mode": "STUDY_MATERIAL",
        "confidence_min": 0.8
    },
    {
        "name": "Thông báo nghỉ lễ",
        "text": THONG_BAO_NGHI_LE,
        "expected_mode": "BUSINESS_DOC",
        "confidence_min": 0.8
    },
    {
        "name": "Hóa đơn điện",
        "text": HOA_DON_DIEN,
        "expected_mode": "BUSINESS_DOC",
        "confidence_min": 0.8
    },
    {
        "name": "Quyết định phê duyệt",
        "text": QUYET_DINH_PHE_DUYET,
        "expected_mode": "BUSINESS_DOC",
        "confidence_min": 0.8
    }
]


async def run_tests():
    """Run all test cases"""
    print("=" * 60)
    print("MODE DETECTION TEST — Giai đoạn 1 validation")
    print("=" * 60)
    print()

    passed = 0
    failed = 0

    for i, test in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{len(TEST_CASES)}: {test['name']}")
        print(f"Expected mode: {test['expected_mode']}")

        try:
            result = await detect_mode(test['text'])
            detected_mode = result.get("mode")
            confidence = result.get("confidence", 0)
            reason = result.get("reason", "")

            print(f"Detected: {detected_mode} (confidence: {confidence:.2f})")
            print(f"Reason: {reason}")

            # Check
            if detected_mode == test['expected_mode'] and confidence >= test['confidence_min']:
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL")
                failed += 1
                print(f"   Expected: {test['expected_mode']}, Got: {detected_mode}")
                print(f"   Confidence: {confidence:.2f} (min {test['confidence_min']})")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

        print("-" * 60)

    # Summary
    print()
    print("=" * 60)
    print(f"SUMMARY: {passed}/{len(TEST_CASES)} passed")
    print(f"Accuracy: {passed/len(TEST_CASES)*100:.1f}%")
    print("=" * 60)

    if passed == len(TEST_CASES):
        print("🎉 All tests passed! Mode detection is ready.")
        return 0
    else:
        print("⚠️ Some tests failed. Need to improve prompt.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)
