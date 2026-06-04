# -*- coding: utf-8 -*-

import re
from config.fee_keywords import FEE_KEYWORDS

class FeeExtractor:
    def __init__(self):
        """
        Khởi tạo bộ trích xuất chi phí.
        Nạp cấu hình từ điển từ khóa và thiết lập biểu thức chính quy (Regex) cùng ngưỡng giá trị.
        """
        self.keywords = FEE_KEYWORDS
        # Regex tìm các số tiền có dấu phân cách hàng nghìn (chấm hoặc phẩy)
        # Ví dụ: 1.014.000 hoặc 882,000
        self.amount_pattern = re.compile(r'\b(\d{1,3}(?:[.,]\d{3})+)\b')
        # Ngưỡng số tiền hợp lệ: 100.000 VNĐ đến 50.000.000 VNĐ
        self.min_amount = 100000
        self.max_amount = 50000000

    def _is_keyword_in_text(self, kw: str, text: str) -> bool:
        """
        Khớp từ khóa thông minh.
        Đối với từ khóa ngắn (< 4 ký tự), bắt buộc khớp dưới dạng từ độc lập (whole word)
        để tránh khớp nhầm (ví dụ "ha" khớp nhầm trong "hàng", "khang", "thành").
        """
        kw_lower = kw.lower()
        text_lower = text.lower()
        
        if len(kw_lower) >= 4:
            return kw_lower in text_lower
            
        # Regex kiểm tra từ khóa ngắn đứng độc lập, không bị bao quanh bởi ký tự chữ/số tiếng Việt
        pattern = re.compile(rf'(?i)(?:\b|(?<![a-zA-Z0-9à-ỹÀ-Ỹ])){re.escape(kw_lower)}(?:\b|(?![a-zA-Z0-9à-ỹÀ-Ỹ]))')
        return bool(pattern.search(text_lower))

    def _clean_fee_description(self, line: str) -> str:
        """
        Làm sạch dòng chứa từ khóa chi phí để trích xuất được mô tả đầy đủ, chi tiết nhất.
        Ví dụ: "Phương án: NÂNG RỖNG" -> "NÂNG RỖNG"
               "Hạ bãi chờ xuất 40 hàng 1.014.000" -> "Hạ bãi chờ xuất 40 hàng"
        
        Args:
            line: Dòng văn bản chứa chi phí.
            
        Returns:
            Chuỗi mô tả chi tiết đã làm sạch.
        """
        # 1. Loại bỏ các chuỗi tiền mặt (chứa số và dấu phân cách hàng nghìn)
        cleaned = self.amount_pattern.sub("", line)
        
        # 2. Loại bỏ các đơn vị tiền tệ phổ biến ở cuối (VNĐ, VND, đ, usd, USD)
        cleaned = re.sub(r'(?i)\b(?:vnđ|vnd|đ|usd)\b', '', cleaned)
        
        # 3. Loại bỏ các ký tự dấu phân cách hoặc ký hiệu đặc biệt ở đầu/cuối dòng (kèm ký tự phân cách bảng | / \ [ ])
        cleaned = re.sub(r'^[:\-\s\+,\.\*\|\\\/\[\]]+|[:\-\s\+,\.\*\|\\\/\[\]]+$', '', cleaned)
        
        # 4. Loại bỏ các tiền tố giới thiệu phổ biến (chấp nhận cả sai sót OCR như Phudng än, Phuong an...)
        # Ví dụ: "Phương án:", "Phudng än:", "Phuong an:"
        cleaned = re.sub(r'(?i)^ph\w+ng\s+[a-zđãáàảạỹ\w]{2,4}\s*[:\-]*\s*', '', cleaned)
        # Ví dụ: "Dịch vụ:", "Dich vu:"
        cleaned = re.sub(r'(?i)^d[iị]ch\s+v[uụ]\s*[:\-]*\s*', '', cleaned)
        # Ví dụ: "Loại phí:", "Loai phi:", "Tên phí:", "Ten phi:"
        cleaned = re.sub(r'(?i)^(?:loại|loai|tên|ten)\s+ph[ií]\s*[:\-]*\s*', '', cleaned)
        # Ví dụ: "Phí:", "Phi:"
        cleaned = re.sub(r'(?i)^ph[ií]\s*[:\-]*\s*', '', cleaned)
            
        # Strip khoảng trắng thừa ở đầu/cuối
        cleaned = cleaned.strip()
        # Thay thế nhiều khoảng trắng liên tiếp bằng 1 khoảng trắng duy nhất
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned

    def _correct_fee_description(self, desc: str) -> str:
        """
        Chuẩn hóa các cụm từ viết tắt hoặc lỗi nhận diện OCR phổ biến về tiếng Việt chuẩn.
        Ví dụ: "NANG RNG" -> "Nâng rỗng"
        """
        import unicodedata
        
        desc_clean = desc.strip()
        
        # Bỏ dấu tiếng Việt để đối chiếu dễ dàng hơn
        def remove_accents(input_str):
            nfkd_form = unicodedata.normalize('NFKD', input_str)
            return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])
            
        normalized = remove_accents(desc_clean).lower()
        # Loại bỏ khoảng trắng thừa
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # 1. Các trường hợp Nâng Rỗng
        if normalized in ["nang rng", "nang rong", "nang roong", "nang rngo", "nang rngz", "ng rong", "ng rng"]:
            return "Nâng rỗng"
        # 2. Các trường hợp Hạ Rỗng
        if normalized in ["ha rng", "ha rong", "ha roong"]:
            return "Hạ rỗng"
        # 3. Các trường hợp Nâng Bãi
        if normalized in ["nang bai"]:
            return "Nâng bãi"
        # 4. Các trường hợp Hạ Bãi
        if normalized in ["ha bai"]:
            return "Hạ bãi"
        # 5. Vệ sinh vỏ / cont
        if normalized in ["ve sinh cont", "ve sinh vo", "ve sinh container"]:
            return "Vệ sinh container"
            
        # Kiểm tra cụm từ con bên trong
        if "nang rng" in normalized or "nang rong" in normalized or "ng rong" in normalized or "ng rng" in normalized:
            return "Nâng rỗng"
        if "ha rng" in normalized or "ha rong" in normalized:
            return "Hạ rỗng"
            
        return desc_clean

    def extract_fees(self, raw_text: str) -> list[dict]:
        """
        Phân tích chuỗi text thô theo cơ chế "Định vị theo dòng và Khử nhiễu" (Line-by-Line Anchor & Noise Filtering).
        Trích xuất và làm sạch mô tả chi phí chi tiết thay vì viết vắn tắt.
        Hỗ trợ tìm kiếm số tiền lân cận ở cả dòng trên và dòng dưới (Proximity Fallback).
        
        Args:
            raw_text: Chuỗi văn bản thô phân tách bởi "\n".
            
        Returns:
            Danh sách các dict chứa cặp [Loại chi phí đầy đủ - Số tiền] hợp lệ.
            Ví dụ: [{"fee_type": "Hạ bãi chờ xuất 40 hàng", "amount": 1014000}]
        """
        if not raw_text:
            return []

        # Tách raw_text thành các dòng riêng biệt
        lines = raw_text.split('\n')
        extracted_results = []
        
        # Bước A: Danh sách đen từ khóa nhiễu (Blacklist) để loại bỏ dòng tổng cộng / VAT / mã thuế
        blacklist = ["tổng cộng", "cộng tiền hàng", "tiền thuế", "thuế suất", "mã số thuế", "thành tiền tổng"]
        
        i = 0
        n = len(lines)
        while i < n:
            line_raw = lines[i]
            line = line_raw.strip()
            if not line:
                i += 1
                continue
            
            # Kiểm tra xem dòng hiện tại có chứa từ khóa nhiễu thuộc blacklist hay không
            is_blacklisted = False
            line_lower = line.lower()
            for black_kw in blacklist:
                if black_kw in line_lower:
                    is_blacklisted = True
                    break
            
            if is_blacklisted:
                i += 1
                continue
            
            # Bước C: Duyệt tìm từ khóa chi phí trên dòng hiện tại
            fee_category = self._classify_text(line)
            if fee_category:
                # Trích xuất và làm sạch mô tả đầy đủ từ dòng chứa từ khóa chi phí
                desc = self._clean_fee_description(line)
                if not desc:
                    desc = fee_category
                else:
                    # Chuẩn hóa từ viết tắt hoặc lỗi chính tả OCR
                    desc = self._correct_fee_description(desc)
                
                # Tìm các chuỗi số tiền trên chính dòng đó
                matches = self.amount_pattern.findall(line)
                valid_amounts = []
                
                for match in matches:
                    clean_num = match.replace(".", "").replace(",", "")
                    try:
                        amount_val = int(clean_num)
                        # Lọc theo ngưỡng giá trị hợp lệ [100.000, 50.000.000]
                        if self.min_amount <= amount_val <= self.max_amount:
                            valid_amounts.append(amount_val)
                    except ValueError:
                        continue
                
                if valid_amounts:
                    # Ưu tiên lấy số tiền đầu tiên xuất hiện trên dòng (thường là đơn giá / tiền trước thuế)
                    extracted_results.append({
                        "fee_type": desc,
                        "amount": valid_amounts[0]
                    })
                else:
                    # Bước D: Cơ chế dự phòng lân cận (Proximity Fallback)
                    # Nếu dòng chi phí không có số tiền (lệch cột khi cào PDF/ảnh), 
                    # ta tiến hành kiểm tra dòng ngay dưới (i + 1) và dòng ngay trên (i - 1)
                    found_amount = None
                    
                    # 1. Kiểm tra dòng ngay dưới (i + 1)
                    if i + 1 < n:
                        next_line = lines[i + 1].strip()
                        # Dòng dưới không chứa từ khóa chi phí nào khác
                        next_fee_type = self._classify_text(next_line)
                        if not next_fee_type:
                            next_line_blacklisted = False
                            next_line_lower = next_line.lower()
                            for black_kw in blacklist:
                                if black_kw in next_line_lower:
                                    next_line_blacklisted = True
                                    break
                            
                            if not next_line_blacklisted:
                                next_matches = self.amount_pattern.findall(next_line)
                                for match in next_matches:
                                    clean_num = match.replace(".", "").replace(",", "")
                                    try:
                                        amount_val = int(clean_num)
                                        if self.min_amount <= amount_val <= self.max_amount:
                                            found_amount = amount_val
                                            break
                                    except ValueError:
                                        continue
                    
                    # 2. Nếu dòng dưới không có, kiểm tra dòng ngay trên (i - 1)
                    if found_amount is None and i - 1 >= 0:
                        prev_line = lines[i - 1].strip()
                        # Dòng trên không chứa từ khóa chi phí nào khác
                        prev_fee_type = self._classify_text(prev_line)
                        if not prev_fee_type:
                            prev_line_blacklisted = False
                            prev_line_lower = prev_line.lower()
                            for black_kw in blacklist:
                                if black_kw in prev_line_lower:
                                    prev_line_blacklisted = True
                                    break
                            
                            if not prev_line_blacklisted:
                                prev_matches = self.amount_pattern.findall(prev_line)
                                for match in prev_matches:
                                    clean_num = match.replace(".", "").replace(",", "")
                                    try:
                                        amount_val = int(clean_num)
                                        if self.min_amount <= amount_val <= self.max_amount:
                                            found_amount = amount_val
                                            break
                                    except ValueError:
                                        continue
                                        
                    if found_amount is not None:
                        extracted_results.append({
                            "fee_type": desc,
                            "amount": found_amount
                        })
            
            i += 1

        return extracted_results

    def _classify_text(self, text: str) -> str:
        """
        Xác định loại chi phí dựa trên từ điển từ khóa.
        
        Args:
            text: Văn bản dòng cần phân loại.
            
        Returns:
            Tên chi phí nếu tìm thấy từ khóa hợp lệ, ngược lại trả về None.
        """
        for category, keywords in self.keywords.items():
            for kw in keywords:
                if self._is_keyword_in_text(kw, text):
                    return category
        return None
