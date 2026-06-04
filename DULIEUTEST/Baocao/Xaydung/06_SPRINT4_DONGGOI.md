# 📦 SPRINT 4 – ĐẶC TẢ KỸ THUẬT: ĐÓNG GÓI .EXE

> **Ngày lập:** 04/06/2026  
> **Mục tiêu Sprint:** Build ứng dụng thành file .exe chạy trên Windows không cần Python.

---

## 1. Công cụ sử dụng

| Công cụ | Phiên bản | Vai trò |
|---------|-----------|---------|
| PyInstaller | >= 6.0 | Đóng gói Python → .exe |
| Chế độ build | `--onedir` | Thư mục chứa exe + dependencies (ổn định hơn `--onefile`) |

---

## 2. Thách thức kỹ thuật khi đóng gói

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| PaddleOCR models | Cần file model (~100MB) nằm ngoài package | Copy thủ công vào thư mục dist hoặc dùng `--add-data` |
| PaddlePaddle DLLs | Cần các file .dll/.pyd đặc biệt | Liệt kê trong `hiddenimports` và `binaries` |
| CustomTkinter assets | CTk có thư mục theme/assets riêng | Dùng `--add-data` chỉ đường dẫn |
| Kích thước lớn | PaddlePaddle + models = 500MB+ | Chấp nhận hoặc dùng UPX compress |

---

## 3. Cấu hình PyInstaller (.spec file)

```python
# SmartICDST_OCR.spec (pseudo-code)
a = Analysis(
    ['main.py'],
    pathex=['D:\\SmartICDST_OCR'],
    hiddenimports=[
        'paddleocr',
        'paddlepaddle',
        'customtkinter',
        'PIL',
        'pandas',
        'openpyxl',
        # ... các module ẩn khác
    ],
    datas=[
        # CustomTkinter theme assets
        ('path/to/customtkinter', 'customtkinter'),
        # PaddleOCR models (nếu bundle)
        ('~/.paddleocr/whl', 'paddleocr_models'),
    ],
)
```

---

## 4. Quy trình build

```bash
# Bước 1: Chạy PyInstaller
pyinstaller SmartICDST_OCR.spec

# Bước 2: Copy PaddleOCR models vào thư mục dist (nếu cần)
xcopy "%USERPROFILE%\.paddleocr" "dist\SmartICDST_OCR\paddleocr_models" /E /I

# Bước 3: Test chạy
dist\SmartICDST_OCR\SmartICDST_OCR.exe
```

---

## 5. Cấu trúc thư mục sau khi build

```
dist/
└── SmartICDST_OCR/
    ├── SmartICDST_OCR.exe       # ← File chạy chính
    ├── _internal/               # Dependencies (auto-generated)
    │   ├── paddleocr/
    │   ├── customtkinter/
    │   └── ...
    └── paddleocr_models/        # PaddleOCR models (copy thủ công)
        ├── whl/
        │   ├── det/
        │   ├── rec/
        │   └── cls/
        └── ...
```

---

## 6. Checklist kiểm tra sau build

- [ ] File .exe chạy được trên máy KHÔNG cài Python
- [ ] GUI hiển thị đúng, không bị lỗi theme
- [ ] Chọn thư mục ảnh và quét thành công
- [ ] OCR đọc được chữ tiếng Việt
- [ ] Xuất file Excel thành công
- [ ] Hiển thị ảnh khi click dòng trong bảng
- [ ] Kích thước tổng thể chấp nhận được (< 1GB)
