# -*- coding: utf-8 -*-

import os
from core.ocr_processor import OCRProcessor
from core.fee_extractor import FeeExtractor

class BatchScanner:
    def __init__(self):
        """
        Khởi tạo BatchScanner.
        Khởi tạo sẵn các instance của OCRProcessor và FeeExtractor để dùng lại.
        """
        self.ocr = OCRProcessor()
        self.extractor = FeeExtractor()

    def scan_directory(self, dir_path: str, progress_callback=None) -> list[dict]:
        """
        Quét đệ quy toàn bộ các file ảnh (.jpg, .jpeg, .png) và file tài liệu (.pdf) trong thư mục.
        Gọi OCRProcessor và FeeExtractor để trích xuất phí của từng file.
        
        Args:
            dir_path: Đường dẫn thư mục gốc cần quét.
            progress_callback: Hàm callback(current, total, file_name) để cập nhật tiến trình trên giao diện.
            
        Returns:
            Danh sách kết quả trích xuất dạng:
            [
                {
                    "container_id": "WHSU6940626",
                    "file_path": "D:/...",
                    "fee_type": "Hạ",
                    "amount": 1014000,
                    "raw_text": "..."
                },
                ...
            ]
        """
        if not os.path.exists(dir_path):
            print(f"[ERROR] Thư mục không tồn tại: {dir_path}")
            return []

        # 1. Tìm tất cả các file hợp lệ đệ quy
        supported_extensions = ('.jpg', '.jpeg', '.png', '.pdf')
        all_files = []
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.lower().endswith(supported_extensions):
                    # Bỏ qua các file desktop.ini hoặc file tạm hệ thống
                    if file.startswith("~$") or file.startswith("."):
                        continue
                    all_files.append(os.path.join(root, file))

        total_files = len(all_files)
        print(f"[INFO] Tìm thấy {total_files} file cần xử lý trong {dir_path}")
        
        results = []
        if total_files == 0:
            return results

        # 2. Xử lý từng file
        for idx, file_path in enumerate(all_files, 1):
            file_name = os.path.basename(file_path)
            
            # Cập nhật progress callback nếu có
            if progress_callback:
                progress_callback(idx, total_files, file_name)
                
            print(f"[SCAN] [{idx}/{total_files}] Đang xử lý: {file_name}")

            # Lấy Container ID là tên file (loại bỏ phần mở rộng)
            container_id, _ = os.path.splitext(file_name)
            
            try:
                # Chạy OCR / PDF Trích xuất văn bản thô
                raw_text = self.ocr.extract_text(file_path)
                
                # Trích xuất chi phí
                fees = self.extractor.extract_fees(raw_text)
                
                # Nếu tìm thấy các chi phí hợp lệ
                if fees:
                    for fee in fees:
                        results.append({
                            "container_id": container_id,
                            "file_path": file_path,
                            "fee_type": fee["fee_type"],
                            "amount": fee["amount"],
                            "raw_text": raw_text
                        })
                else:
                    # Nếu không tìm thấy phí nào, vẫn lưu một dòng "Chưa phân loại" với số tiền 0
                    # để người dùng biết file này đã được quét và có thể tự điền tay
                    results.append({
                        "container_id": container_id,
                        "file_path": file_path,
                        "fee_type": "Chưa phân loại",
                        "amount": 0,
                        "raw_text": raw_text
                    })
            except Exception as e:
                print(f"[ERROR] Lỗi khi quét file {file_name}: {str(e)}")
                results.append({
                    "container_id": container_id,
                    "file_path": file_path,
                    "fee_type": "Lỗi xử lý",
                    "amount": 0,
                    "raw_text": ""
                })

        return results
