# 🎯 SPRINT 1 – ĐẶC TẢ KỸ THUẬT: LOGIC CỐT LÕI

> **Ngày lập:** 04/06/2026  
> **Mục tiêu Sprint:** Xây dựng 3 module logic xử lý cốt lõi hoàn chỉnh và kiểm thử độc lập.

---

## 1. Tổng quan các file cần tạo

| File | Vai trò | Phụ thuộc |
|------|---------|-----------|
| `config/fee_keywords.py` | Từ điển từ khóa phân loại chi phí | Không |
| `core/ocr_processor.py` | Gọi PaddleOCR, trả về text thô | PaddleOCR |
| `core/fee_extractor.py` | Regex trích số tiền + từ điển gán loại phí | `config/fee_keywords.py` |

---

## 2. Chi tiết thiết kế từng Module

### 2.1. `config/fee_keywords.py` – Từ điển từ khóa

Bộ từ khóa được nhóm theo **loại chi phí**. Khi OCR trả về text thô, hệ thống sẽ dò từ trên xuống dưới theo thứ tự ưu tiên.

```python
# Cấu trúc dữ liệu:
FEE_KEYWORDS = {
    "Loại phí 1": ["từ khóa 1", "từ khóa 2", ...],
    "Loại phí 2": ["từ khóa 3", "từ khóa 4", ...],
}
```

**Danh sách loại chi phí dự kiến:**

| Loại chi phí | Từ khóa mẫu |
|-------------|-------------|
| Nâng | nâng, lifting, lift on |
| Hạ | hạ, hạ bãi, lift off |
| Vệ sinh | vệ sinh, cleaning, wash |
| Lưu cont | lưu container, detention, demurrage |
| Phụ phí | phụ phí, surcharge, phí |
| Cân | cân, weighing, VGM |

> [!NOTE]
> Từ điển sẽ được mở rộng dần dựa trên dữ liệu thực tế. Thiết kế tách riêng file `fee_keywords.py` giúp dễ chỉnh sửa mà không cần thay đổi logic code.

---

### 2.2. `core/ocr_processor.py` – Module OCR

**Chức năng:** Nhận đường dẫn ảnh → Trả về chuỗi text thô.

**Thiết kế API:**

```python
class OCRProcessor:
    def __init__(self):
        """Khởi tạo PaddleOCR một lần duy nhất (tối ưu bộ nhớ)."""
        pass

    def extract_text(self, image_path: str) -> str:
        """
        Đọc ảnh bằng PaddleOCR, ghép tất cả dòng text thành 1 chuỗi.
        
        Args:
            image_path: Đường dẫn tuyệt đối đến file ảnh .jpg/.jpeg
            
        Returns:
            Chuỗi text thô đã ghép nối (VD: "Hạ bãi 1.014.000 Nâng rỗng 882.000")
        """
        pass
```

**Quy tắc xử lý:**
1. Khởi tạo PaddleOCR với `lang='vi'`, `use_gpu=False`, `show_log=False`
2. Gọi `ocr.ocr(image_path)` lấy kết quả
3. Ghép tất cả các text block thành một chuỗi duy nhất (nối bằng dấu cách)
4. Trả về chuỗi text thô (không xử lý gì thêm)

---

### 2.3. `core/fee_extractor.py` – Module trích xuất chi phí

**Chức năng:** Nhận text thô → Trả về danh sách `[{loại_phí, số_tiền}]`.

**Thiết kế API:**

```python
class FeeExtractor:
    def __init__(self):
        """Nạp từ điển từ khóa từ config/fee_keywords.py."""
        pass

    def extract_fees(self, raw_text: str) -> list[dict]:
        """
        Phân tích text thô để trích xuất các cặp (loại phí, số tiền).
        
        Args:
            raw_text: Chuỗi text thô từ OCR
            
        Returns:
            Danh sách dict, VD:
            [
                {"fee_type": "Hạ bãi", "amount": 1014000},
                {"fee_type": "Nâng rỗng", "amount": 882000}
            ]
        """
        pass

    def _find_amounts(self, text: str) -> list[int]:
        """Dùng Regex tìm tất cả số tiền trong text."""
        pass

    def _classify_fee_type(self, text: str) -> str:
        """Dùng từ điển từ khóa xác định loại chi phí."""
        pass
```

**Chi tiết Regex trích xuất số tiền:**

```python
# Pattern: Tìm số có dấu chấm hoặc phẩy ngăn cách hàng nghìn
# VD: 1.014.000 | 882,000 | 1,500,000 | 370.000
import re
pattern = r'\b(\d{1,3}(?:[.,]\d{3})+)\b'
```

**Quy trình xử lý:**
1. Dùng Regex tìm tất cả chuỗi có format số tiền
2. Chuyển đổi thành số nguyên (bỏ dấu `.` và `,`)
3. Lọc: chỉ giữ số tiền trong khoảng hợp lệ (100.000 – 50.000.000)
4. Dò từ điển từ khóa → gán loại phí tương ứng
5. Trả về danh sách kết quả

---

## 3. Luồng xử lý tổng thể Sprint 1

```
Ảnh (.jpg) ─────┐
                 │
                 ▼
         ┌───────────────┐
         │ OCRProcessor  │
         │ extract_text()│──── text thô: "PHÍ NÂNG HẠ CONTAINER ... 1.014.000 ..."
         └───────────────┘
                 │
                 ▼
         ┌───────────────┐
         │ FeeExtractor  │
         │ extract_fees()│──── [{"fee_type": "Nâng hạ", "amount": 1014000}]
         └───────────────┘
```

---

## 4. Test Script (kiểm thử độc lập)

Sau khi hoàn thành Sprint 1, sẽ tạo file `test_sprint1.py` để kiểm tra:

```python
# Pseudo-code test
from core.ocr_processor import OCRProcessor
from core.fee_extractor import FeeExtractor

ocr = OCRProcessor()
extractor = FeeExtractor()

# Test với 1 ảnh mẫu
text = ocr.extract_text("DULIEUTEST/TanTuongKhang/T05 - 2026/BEAU5178688/BEAU5178688.jpg")
print("OCR Text:", text)

fees = extractor.extract_fees(text)
print("Extracted Fees:", fees)
```
