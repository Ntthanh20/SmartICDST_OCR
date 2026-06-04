# 🔧 HƯỚNG DẪN CÀI ĐẶT MÔI TRƯỜNG – SmartICDST_OCR v2.0

> **Ngày lập:** 04/06/2026

---

## 1. Yêu cầu hệ thống

| Thành phần | Yêu cầu tối thiểu |
|-----------|-------------------|
| HĐH | Windows 10/11 (64-bit) |
| Python | 3.9 – 3.11 (khuyến nghị 3.10) |
| RAM | >= 4GB |
| Ổ cứng trống | >= 3GB (bao gồm PaddleOCR models) |
| GPU | **KHÔNG cần** – chạy hoàn toàn trên CPU |

---

## 2. Các lệnh cài đặt thư viện

### 2.1. Cài đặt từng thư viện (khuyến nghị để dễ debug)

```bash
# 1. PaddleOCR và PaddlePaddle (Engine OCR offline)
pip install paddlepaddle
pip install paddleocr

# 2. CustomTkinter (GUI hiện đại)
pip install customtkinter

# 3. Pillow (Xử lý và hiển thị ảnh)
pip install Pillow

# 4. Pandas + openpyxl (Xuất file Excel .xlsx)
pip install pandas openpyxl

# 5. PyInstaller (Đóng gói .exe - chỉ cần khi build Sprint 4)
pip install pyinstaller
```

### 2.2. Cài đặt nhanh bằng requirements.txt

```bash
pip install -r requirements.txt
```

Nội dung file `requirements.txt`:
```
paddlepaddle
paddleocr
customtkinter>=5.2.0
Pillow>=10.0.0
pandas>=2.0.0
openpyxl>=3.1.0
pyinstaller>=6.0.0
```

---

## 3. Kiểm tra cài đặt thành công

Chạy lệnh sau trong Terminal/CMD để xác nhận:

```bash
python -c "import paddleocr; print('PaddleOCR OK:', paddleocr.__version__)"
python -c "import customtkinter; print('CustomTkinter OK:', customtkinter.__version__)"
python -c "import pandas; print('Pandas OK:', pandas.__version__)"
python -c "from PIL import Image; print('Pillow OK')"
```

---

## 4. Cấu trúc thư mục dự án hoàn chỉnh

```
D:\SmartICDST_OCR\
│
├── main.py                         # 🚀 Entry point - chạy ứng dụng
├── requirements.txt                # 📦 Danh sách thư viện
├── SmartICDST_OCR.spec             # 🔨 Cấu hình PyInstaller (Sprint 4)
│
├── core/                           # 🧠 Logic nghiệp vụ
│   ├── __init__.py
│   ├── ocr_processor.py            # Gọi PaddleOCR → trả text thô
│   ├── fee_extractor.py            # Regex + Từ điển → trích xuất chi phí
│   └── batch_scanner.py            # Quét thư mục, tổng hợp kết quả
│
├── gui/                            # 🖥️ Giao diện người dùng
│   ├── __init__.py
│   ├── app.py                      # Cửa sổ chính Split-View
│   └── components.py               # Widget bảng, khung hiển thị ảnh
│
├── config/                         # ⚙️ Cấu hình
│   ├── __init__.py
│   └── fee_keywords.py             # Từ điển từ khóa loại chi phí
│
└── DULIEUTEST/                     # 📂 Dữ liệu kiểm thử (đã có sẵn)
    ├── TanTuongKhang/
    │   ├── T01 - 2026/             # Mỗi thư mục con = 1 container
    │   │   ├── BEAU5081511/
    │   │   │   ├── BEAU5081511.jpg  # ← Ảnh hóa đơn (tên = số cont)
    │   │   │   └── *.pdf           # ← Debit Note (tham khảo)
    │   │   └── ...
    │   ├── T02 - 2026/
    │   └── ...
    └── Baocao/
        └── Xaydung/                # Tài liệu xây dựng dự án
```

---

## 5. Lưu ý quan trọng

> [!WARNING]
> **PaddleOCR lần đầu chạy** sẽ tự động tải các model nhận diện (~100MB) về thư mục `~/.paddleocr/`. Đảm bảo có kết nối Internet cho lần chạy đầu tiên. Sau đó, ứng dụng chạy hoàn toàn OFFLINE.

> [!TIP]
> Nếu gặp lỗi khi cài `paddlepaddle` trên Windows, hãy thử:
> ```bash
> pip install paddlepaddle==2.6.2 -f https://www.paddlepaddle.org.cn/whl/windows/cpu-mkl-avx/stable.html
> ```
