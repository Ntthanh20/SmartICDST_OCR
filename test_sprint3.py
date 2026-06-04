# -*- coding: utf-8 -*-

import os
import sys
import pandas as pd

# Thiết lập stdout sử dụng mã hóa UTF-8 để hiển thị đúng tiếng Việt
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Đảm bảo import được các module từ thư mục hiện tại
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.batch_scanner import BatchScanner

def run_test():
    print("=" * 60)
    print("[BAT DAU] KIEM THU SPRINT 3 - QUET HANG LOAT & XUAT EXCEL")
    print("=" * 60)

    # 1. Khởi tạo BatchScanner
    print("[1/3] Đang khởi tạo BatchScanner...")
    scanner = BatchScanner()
    print("-> Khởi tạo thành công!")

    # 2. Thực hiện quét thử nghiệm thư mục chứa container BEAU5178688
    target_dir = os.path.abspath("DULIEUTEST/TanTuongKhang/T05 - 2026/BEAU5178688")
    print(f"[2/3] Đang quét thư mục: {target_dir}")
    
    if not os.path.exists(target_dir):
        print(f"[LOI] Không tìm thấy thư mục kiểm thử: {target_dir}")
        return

    results = scanner.scan_directory(target_dir)
    print(f"-> Quét hoàn tất! Tìm thấy {len(results)} bản ghi chi phí.")

    # In kết quả quét ra màn hình
    print("\n--- Danh sách chi phí trích xuất được ---")
    for idx, r in enumerate(results, 1):
        print(f"[{idx}] Cont: {r['container_id']:<25} | Phí: {r['fee_type']:<15} | Tiền: {r['amount']:,} VNĐ | File: {os.path.basename(r['file_path'])}")
    print("-" * 60)

    # 3. Thử nghiệm kết xuất Pandas sang file Excel
    excel_path = os.path.abspath("DULIEUTEST/test_sprint3_output.xlsx")
    print(f"[3/3] Đang xuất kết quả sang Excel tại: {excel_path}")

    # Chuẩn bị cấu trúc dữ liệu xuất báo cáo
    data_list = []
    for idx, res in enumerate(results, 1):
        data_list.append({
            "STT": idx,
            "Số Container": res["container_id"],
            "Loại chi phí": res["fee_type"],
            "Số tiền (VNĐ)": res["amount"]
        })

    # Chuyển đổi DataFrame
    df = pd.DataFrame(data_list)
    
    try:
        # Xuất file xlsx
        df.to_excel(excel_path, index=False, sheet_name="Đối soát chi phí")
        print("-> Xuất Excel thành công!")
        
        # Xác minh file có tồn tại và kích thước lớn hơn 0
        if os.path.exists(excel_path) and os.path.getsize(excel_path) > 0:
            print("[OK] KIỂM THỬ THÀNH CÔNG! File Excel hợp lệ.")
        else:
            print("[LOI] Lỗi: File Excel được tạo ra nhưng rỗng hoặc không tồn tại.")
    except Exception as e:
        print(f"[LOI] Lỗi khi xuất Excel: {str(e)}")

    print("=" * 60)

if __name__ == "__main__":
    run_test()
