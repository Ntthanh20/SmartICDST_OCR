# -*- coding: utf-8 -*-

import os
from core.ocr_processor import OCRProcessor
from core.fee_extractor import FeeExtractor

class BatchScanner:
    def __init__(self, ocr_processor=None):
        """
        Khởi tạo BatchScanner.
        Nhận vào ocr_processor tùy chọn để tái sử dụng, giúp tối ưu bộ nhớ và thời gian nạp.
        """
        self.ocr = ocr_processor if ocr_processor is not None else OCRProcessor()
        self.extractor = FeeExtractor()

    def is_valid_container(self, c_str: str) -> bool:
        """
        Kiểm tra tính hợp lệ của số container theo tiêu chuẩn ISO 6346 (Check Digit).
        """
        if not c_str or len(c_str) != 11:
            return False
        c_str = c_str.upper()
        if not c_str[:4].isalpha() or not c_str[4:].isdigit():
            return False
            
        alphabet = '0123456789A BCDEFGHIJK LMNOPQRSTU VWXYZ'
        try:
            total = sum(alphabet.index(char) * (2 ** i) for i, char in enumerate(c_str[:10]))
            # Modulo 11, sau đó Modulo 10
            return (total % 11) % 10 == int(c_str[10])
        except Exception:
            return False

    def _get_folder_container(self, file_path: str, scan_root: str) -> str:
        """
        Duyệt ngược từ file_path lên scan_root để tìm tên thư mục con đầu tiên
        khớp hoàn toàn với định dạng container (4 chữ cái + 7 chữ số).
        """
        import re
        container_pattern = re.compile(r'^[A-Za-z]{4}\d{7}$')
        
        # Chuẩn hóa đường dẫn
        curr = os.path.dirname(os.path.abspath(file_path))
        root_abs = os.path.abspath(scan_root)
        
        while curr:
            base = os.path.basename(curr)
            if not base:
                break
            if container_pattern.match(base):
                return base.upper()
            if curr == root_abs:
                break
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
        return ""

    def extract_document_key(self, text: str) -> str:
        """
        Trích xuất mã tài liệu duy nhất (Mã lô hoặc Số hóa đơn hoặc Mã giao dịch)
        từ nội dung văn bản để làm key phân loại tránh trùng lặp.
        """
        if not text:
            return ""
            
        import re
        # 1. Tìm Mã lô (ưu tiên số 1 cho Biên nhận nợ)
        ma_lo_match = re.search(r'(?i)m[aã]\s+l[oô]\s*[:\s\-]+([0-9]+)', text)
        if ma_lo_match:
            return f"LO_{ma_lo_match.group(1)}"
            
        # 2. Tìm Số hóa đơn (Số No., Số hóa đơn, Số)
        # Ví dụ: "Số hóa đơn: 0019276", "Số (No.): 113023", "Số (No.): 18248", "S hoadon0o31242"
        so_hd_match = re.search(r'(?i)(?:s[oố]\s+h[oó]a\s+[dđ]on|s[oố]\s*\(no\.?\)|s\s+hoadon)\s*[:\s\-]*([a-zA-Z0-9]+)', text)
        if so_hd_match:
            return f"HD_{so_hd_match.group(1)}"
            
        # Thử tìm Số: ở đầu dòng hoặc sau ngày tháng (bắt buộc có dấu hai chấm hoặc gạch ngang để tránh trùng địa chỉ đường)
        so_generic_match = re.search(r'(?i)\bs[oố]\s*[:\-]+([0-9]+)', text)
        if so_generic_match:
            val = so_generic_match.group(1)
            if len(val) <= 10 and val.isdigit():
                return f"HD_{val}"
                
        # 3. Tìm Mã giao dịch
        ma_gd_match = re.search(r'(?i)m[aã]\s+giao\s+d[iị]ch\s*[:\s\-]+([a-zA-Z0-9]+)', text)
        if ma_gd_match:
            return f"GD_{ma_gd_match.group(1)}"
            
        return ""

    def scan_directory(self, dir_path: str, progress_callback=None) -> list[dict]:
        """
        Quét đệ quy toàn bộ các file ảnh (.jpg, .jpeg, .png) và file tài liệu (.pdf) trong thư mục.
        Gọi OCRProcessor và FeeExtractor để trích xuất phí của từng file.
        
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

        # Sắp xếp danh sách file cần quét: file PDF trước (độ chính xác/tốc độ cao hơn), file ảnh sau
        all_files.sort(key=lambda x: (0 if x.lower().endswith('.pdf') else 1, x.lower()))

        # Set lưu các chi phí đã thêm để loại trừ trùng lặp: (container_id, fee_type, effective_doc_key)
        seen_records = set()

        # 2. Xử lý từng file
        for idx, file_path in enumerate(all_files, 1):
            file_name = os.path.basename(file_path)
            
            # Cập nhật progress callback nếu có
            if progress_callback:
                progress_callback(idx, total_files, file_name)
                
            print(f"[SCAN] [{idx}/{total_files}] Đang xử lý: {file_name}")

            import re
            container_pattern = re.compile(r'([A-Za-z]{4}\d{7})')
            
            # 1. Tìm container từ thư mục cha trong cây thư mục
            folder_container = self._get_folder_container(file_path, dir_path)
            
            # 2. Tìm container từ tên file (chỉ lấy các container hợp lệ theo check digit)
            file_containers = [c.upper() for c in container_pattern.findall(file_name) if self.is_valid_container(c)]
            
            # 3. Xây dựng danh sách default_containers
            default_containers = []
            if folder_container:
                default_containers.append(folder_container)
            for fc in file_containers:
                if fc not in default_containers:
                    default_containers.append(fc)
                    
            if not default_containers:
                default_name, _ = os.path.splitext(file_name)
                default_containers = [default_name]

            try:
                # Trích xuất văn bản theo từng trang
                pages_text = self.ocr.extract_text_by_pages(file_path)
                
                for page_idx, page_text in enumerate(pages_text):
                    # Trích xuất mã tài liệu duy nhất (Mã lô / Số hóa đơn)
                    doc_key = self.extract_document_key(page_text)
                    effective_doc_key = doc_key if doc_key else file_path

                    # Tìm Container ID trong nội dung trang và chỉ lọc các container hợp lệ theo check digit
                    found_containers = container_pattern.findall(page_text)
                    valid_found = []
                    seen_page = set()
                    for c in found_containers:
                        c_upper = c.upper()
                        if self.is_valid_container(c_upper) and c_upper not in seen_page:
                            seen_page.add(c_upper)
                            valid_found.append(c_upper)
                    
                    # Nếu tên thư mục chứa là một container hợp lệ và chưa có trong danh sách, bắt buộc thêm vào
                    if folder_container and folder_container not in seen_page:
                        seen_page.add(folder_container)
                        valid_found.append(folder_container)
                        
                    if valid_found:
                        page_container_ids = valid_found
                    else:
                        page_container_ids = default_containers
                    
                    # Trích xuất chi phí của trang này
                    fees = self.extractor.extract_fees(page_text)
                    
                    if fees:
                        for page_container_id in page_container_ids:
                            for fee in fees:
                                uniq_key = (page_container_id, fee["fee_type"], effective_doc_key)
                                if uniq_key not in seen_records:
                                    seen_records.add(uniq_key)
                                    results.append({
                                        "container_id": page_container_id,
                                        "file_path": file_path,
                                        "fee_type": fee["fee_type"],
                                        "amount": fee["amount"],
                                        "raw_text": page_text,
                                        "document_key": doc_key
                                    })
                                else:
                                    print(f"[DUP SKIP] Bỏ qua chi phí trùng: Cont={page_container_id}, Phí={fee['fee_type']}, Key={effective_doc_key}")
                    else:
                        # Nếu không tìm thấy phí nào, vẫn lưu một dòng "Chưa phân loại" với số tiền 0
                        # để người dùng biết file này đã được quét và có thể tự điền tay
                        for page_container_id in page_container_ids:
                            uniq_key = (page_container_id, "Chưa phân loại", effective_doc_key)
                            if uniq_key not in seen_records:
                                seen_records.add(uniq_key)
                                results.append({
                                    "container_id": page_container_id,
                                    "file_path": file_path,
                                    "fee_type": "Chưa phân loại",
                                    "amount": 0,
                                    "raw_text": page_text,
                                    "document_key": doc_key
                                })
            except Exception as e:
                print(f"[ERROR] Lỗi khi quét file {file_name}: {str(e)}")
                fallback_id = default_containers[0] if default_containers else "Lỗi"
                results.append({
                    "container_id": fallback_id,
                    "file_path": file_path,
                    "fee_type": "Lỗi xử lý",
                    "amount": 0,
                    "raw_text": "",
                    "document_key": ""
                })

        # 3. Lọc bỏ các dòng "Chưa phân loại" nếu container đó đã có chi phí hợp lệ khác
        containers_with_fees = {
            r["container_id"] for r in results 
            if r["fee_type"] != "Chưa phân loại" and r["fee_type"] != "Lỗi xử lý" and r["amount"] > 0
        }
        
        filtered_results = []
        for r in results:
            if r["fee_type"] == "Chưa phân loại" and r["container_id"] in containers_with_fees:
                # Bỏ qua dòng Chưa phân loại nếu đã có chi phí thực tế
                continue
            filtered_results.append(r)
            
        return filtered_results
