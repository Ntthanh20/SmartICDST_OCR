# 🔗 SPRINT 3 – ĐẶC TẢ KỸ THUẬT: TÍCH HỢP & XUẤT EXCEL

> **Ngày lập:** 04/06/2026  
> **Mục tiêu Sprint:** Kết nối logic cốt lõi với giao diện, hoàn thiện quét hàng loạt và xuất báo cáo Excel.

---

## 1. Module cần tạo thêm

### 1.1. `core/batch_scanner.py` – Quét thư mục hàng loạt

**Chức năng:** Duyệt toàn bộ thư mục ảnh, gọi OCR + Extractor cho từng file, tổng hợp kết quả.

```python
class BatchScanner:
    def __init__(self):
        """Khởi tạo OCRProcessor và FeeExtractor."""
        pass

    def scan_directory(self, dir_path: str, progress_callback=None) -> list[dict]:
        """
        Quét toàn bộ file .jpg/.jpeg trong thư mục (bao gồm thư mục con).
        
        Args:
            dir_path: Đường dẫn thư mục gốc
            progress_callback: Hàm callback(current, total) để cập nhật progress bar
            
        Returns:
            Danh sách kết quả, VD:
            [
                {
                    "container_id": "BEAU5178688",
                    "image_path": "D:/..../BEAU5178688.jpg",
                    "fee_type": "Nâng hạ",
                    "amount": 1014000,
                    "raw_text": "PHÍ NÂNG HẠ CONTAINER..."
                },
                ...
            ]
        """
        pass
```

**Quy tắc quét:**
1. Duyệt đệ quy (recursive) tìm tất cả file `.jpg` và `.jpeg`
2. Với mỗi file ảnh:
   - Lấy tên file (bỏ extension) → `container_id`
   - Gọi `OCRProcessor.extract_text()` → `raw_text`
   - Gọi `FeeExtractor.extract_fees(raw_text)` → danh sách `{fee_type, amount}`
   - Ghép `container_id` + `image_path` + từng fee → 1 dòng kết quả
3. Gọi `progress_callback` sau mỗi file để cập nhật tiến trình

---

## 2. Tích hợp vào GUI

### 2.1. Nút "Quét thư mục" – Luồng xử lý

```
[Click nút Quét] → [Kiểm tra thư mục hợp lệ]
       │                    │
       │                    ▼
       │           [Hiển thị Progress Bar]
       │                    │
       │                    ▼
       │           [Chạy batch_scanner.scan_directory() 
       │            trên Thread riêng (tránh đông cứng GUI)]
       │                    │
       │                    ▼
       │           [Callback cập nhật progress: "Đang xử lý 15/50..."]
       │                    │
       │                    ▼
       │           [Hoàn tất → Đổ kết quả vào Treeview]
       │                    │
       │                    ▼
       └──────────▶[Ẩn Progress Bar, hiển thị tổng số dòng]
```

> [!IMPORTANT]
> **Threading**: Quá trình OCR tốn thời gian (2-5 giây/ảnh). PHẢI chạy trên thread riêng bằng `threading.Thread` để GUI không bị đông cứng (freeze).

### 2.2. Nút "Xuất Excel" – Luồng xử lý

```python
def export_excel(self, data: list[dict], output_path: str):
    """
    Xuất dữ liệu từ bảng Treeview thành file Excel .xlsx
    
    Cột trong file Excel:
    | STT | Số Container | Loại chi phí | Số tiền (VNĐ) |
    """
    import pandas as pd
    
    df = pd.DataFrame(data)
    df.to_excel(output_path, index=False, sheet_name="Đối soát chi phí")
```

---

## 3. Xử lý sự kiện Click dòng → Hiển thị ảnh

```python
# Khi user click 1 dòng trong Treeview:
# 1. Lấy image_path từ dữ liệu dòng được chọn
# 2. Load ảnh bằng Pillow
# 3. Resize fit khung hiển thị bên phải (giữ tỷ lệ)
# 4. Cập nhật CTkLabel bên phải với ảnh mới
```

---

## 4. Xử lý Double-click → Chỉnh sửa trực tiếp

```
[Double-click ô] → [Popup nhỏ (CTkToplevel)]
       │
       ▼
   ┌──────────────────────┐
   │ Sửa giá trị:         │
   │ [__current_value___]  │
   │ [Lưu]    [Hủy]       │
   └──────────────────────┘
       │
       ▼
[Cập nhật giá trị trong Treeview và data source]
```
