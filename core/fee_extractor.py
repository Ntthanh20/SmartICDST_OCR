# -*- coding: utf-8 -*-

import re
from config.fee_keywords import FEE_KEYWORDS

class FeeExtractor:
    def __init__(self):
        """
        Khởi tạo extractor.
        Nạp cấu hình từ điển từ khóa và thiết lập regex cùng ngưỡng giá trị hợp lệ.
        """
        self.keywords = FEE_KEYWORDS
        # Regex tìm số tiền có dấu phân cách hàng nghìn (chấm hoặc phẩy)
        # Ví dụ: 1.014.000 hoặc 882,000
        self.amount_pattern = re.compile(r'\b(\d{1,3}(?:[.,]\d{3})+)\b')
        # Ngưỡng số tiền hợp lệ: 100.000 VNĐ đến 50.000.000 VNĐ
        self.min_amount = 100000
        self.max_amount = 50000000

    def extract_fees(self, raw_text: str) -> list[dict]:
        """
        Phân tích chuỗi text thô thu được từ OCR/PDF để trích xuất các cặp (loại phí, số tiền) hợp lệ.
        
        Args:
            raw_text: Chuỗi văn bản thô.
            
        Returns:
            Danh sách các dict chứa thông tin chi phí trích xuất được.
            Ví dụ: [{"fee_type": "Hạ", "amount": 1014000}]
        """
        if not raw_text:
            return []

        lines = raw_text.splitlines()
        extracted_results = []

        for idx, line in enumerate(lines):
            line_cleaned = line.strip()
            if not line_cleaned:
                continue

            # Tìm tất cả các chuỗi số tiền trên dòng này
            matches = self.amount_pattern.findall(line_cleaned)
            if not matches:
                continue

            # Loại bỏ các chuỗi trùng lặp trên cùng một dòng (tránh trường hợp đơn giá trùng với thành tiền)
            unique_matches = list(dict.fromkeys(matches))

            for match in unique_matches:
                # Chuyển chuỗi số tiền thành số nguyên bằng cách bỏ dấu phân cách hàng nghìn
                clean_num = match.replace(".", "").replace(",", "")
                try:
                    amount = int(clean_num)
                except ValueError:
                    continue

                # Chỉ xử lý số tiền nằm trong ngưỡng hợp lệ [100.000, 50.000.000] VNĐ
                if not (self.min_amount <= amount <= self.max_amount):
                    continue

                # Bắt đầu phân loại chi phí cho số tiền này
                # Ưu tiên 1: Tìm từ khóa trên chính dòng hiện tại
                fee_type = self._classify_text(line_cleaned)

                # Ưu tiên 2: Nếu chưa phân loại, tìm ở dòng ngay phía trước
                if fee_type == "Chưa phân loại" and idx > 0:
                    fee_type = self._classify_text(lines[idx - 1])

                # Ưu tiên 3: Nếu vẫn chưa phân loại, tìm ở dòng ngay phía sau
                if fee_type == "Chưa phân loại" and idx < len(lines) - 1:
                    fee_type = self._classify_text(lines[idx + 1])

                extracted_results.append({
                    "fee_type": fee_type,
                    "amount": amount
                })

        return extracted_results

    def _classify_text(self, text: str) -> str:
        """
        Xác định loại chi phí dựa trên so khớp từ khóa từ điển trong văn bản.
        
        Args:
            text: Chuỗi văn bản cần phân tích.
            
        Returns:
            Tên loại chi phí tìm thấy hoặc "Chưa phân loại".
        """
        text_lower = text.lower()
        for category, keywords in self.keywords.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return category
        return "Chưa phân loại"
