# -*- coding: utf-8 -*-

import os
import sys

# Thiết lập stdout sử dụng mã hóa UTF-8 để hiển thị đúng tiếng Việt và ký hiệu đặc biệt
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Đảm bảo import được các module từ thư mục hiện tại
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.ocr_processor import OCRProcessor
from core.fee_extractor import FeeExtractor

def get_container_id(file_path: str) -> str:
    """
    Trích xuất Container ID trực tiếp từ tên file (bỏ phần mở rộng).
    """
    base_name = os.path.basename(file_path)
    container_id, _ = os.path.splitext(base_name)
    return container_id

def run_test():
    print("=" * 60)
    print("[BAT DAU] KIEM THU SPRINT 1 - LOGIC COT LOI & XU LY OFFLINE")
    print("=" * 60)

    # Khởi tạo các bộ xử lý
    print("[1/3] Đang khởi tạo OCRProcessor (PaddleOCR) & FeeExtractor...")
    ocr = OCRProcessor()
    extractor = FeeExtractor()
    print("-> Khởi tạo thành công!")
    print("-" * 60)

    # Các file mẫu để kiểm thử
    test_files = [
        r"DULIEUTEST/TanTuongKhang/T05 - 2026/BEAU5178688/BEAU5178688.jpg",
        r"DULIEUTEST/TanTuongKhang/T05 - 2026/BEAU5178688/BSIU8110969-BEAU5178688.pdf"
    ]

    for file_rel_path in test_files:
        # Đường dẫn tuyệt đối
        file_path = os.path.abspath(file_rel_path)
        print(f"[TEST] Kiểm thử với file: {file_rel_path}")
        
        if not os.path.exists(file_path):
            print(f"[LOI] Không tìm thấy file: {file_path}. Vui lòng kiểm tra lại đường dẫn!")
            print("-" * 60)
            continue

        # 1. Trích xuất Container ID từ tên file
        cont_id = get_container_id(file_path)
        print(f"[CONTAINER ID] Container ID trích xuất từ tên file: {cont_id}")

        # 2. Nhận diện chữ thô
        print("[OCR] Đang trích xuất văn bản thô...")
        raw_text = ocr.extract_text(file_path)
        
        # In ra 3 dòng đầu tiên của text thô thu được để xác minh
        print("\n--- Van ban tho (mot phan hoac toan bo) ---")
        lines = raw_text.strip().split("\n")
        for line in lines[:10]: # Hiển thị tối đa 10 dòng đầu
            print(f"| {line}")
        if len(lines) > 10:
            print(f"| ... (con tiep {len(lines) - 10} dong)")
        print("------------------------------------------")

        # 3. Trích xuất chi phí
        print("[TRICH XUAT] Đang lọc và trích xuất chi phí...")
        fees = extractor.extract_fees(raw_text)
        
        print("\n[KET QUA] KET QUA TRICH XUAT CHI PHI:")
        if not fees:
            print("   (Khong tim thay chi phi hop le nao)")
        else:
            for idx, fee in enumerate(fees, 1):
                print(f"   [{idx}] Loai phi: {fee['fee_type']:<15} | So tien: {fee['amount']:,} VNĐ")
        
        print("=" * 60)

if __name__ == "__main__":
    run_test()
