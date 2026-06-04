# 📊 SmartICDST_OCR v2.0 – Hệ Thống Đối Soát Hóa Đơn Logistics Tự Động Offline

## 📌 Giới thiệu dự án
**SmartICDST_OCR v2.0** là ứng dụng Windows Desktop (.exe) chạy **hoàn toàn OFFLINE**, được phát triển nhằm tự động hóa quy trình đối soát hóa đơn nâng hạ và chi phí logistics tại ICD. 

Để đảm bảo độ chính xác dữ liệu là **chính xác tuyệt đối (100%)**, dự án **NÓI KHÔNG với Generative AI / LLM** nhằm loại bỏ hoàn toàn các lỗi ảo giác (hallucination) dữ liệu tài chính. Thay vào đó, hệ thống sử dụng sự kết hợp chặt chẽ giữa thuật toán OCR offline, trích xuất văn bản số học (digital scraping), biểu thức chính quy (Regex) và đối khớp từ điển (Dictionary Matching).

---

## ⚙️ Kiến trúc Thuật toán & Quy tắc Cốt lõi

1.  **Nguyên tắc Container ID:**
    *   Lấy trực tiếp tên file ảnh/PDF đầu vào (loại bỏ phần mở rộng) làm số Container (ví dụ: file `WHSU6940626.jpg` hoặc `WHSU6940626.pdf` $\rightarrow$ Container ID là `WHSU6940626`).
    *   *Tuyệt đối không dùng OCR để nhận diện số container* trên mặt hóa đơn để triệt tiêu hoàn toàn lỗi nhầm lẫn ký tự phổ biến (chữ `O` và số `0`, chữ `I` và số `1`).
2.  **Cơ chế Trích xuất Văn bản (OCR & PDF Scraping):**
    *   **PDF văn bản kỹ thuật số (Searchable PDF):** Sử dụng `pdfplumber` để cào trực tiếp văn bản từ file PDF gốc, tốc độ xử lý nhanh dưới 1 giây và chính xác 100%.
    *   **PDF quét (Scanned PDF):** Sử dụng `PyMuPDF` (`fitz`) để render trang PDF thành hình ảnh chất lượng cao, sau đó chạy qua bộ nhận dạng chữ viết tiếng Việt.
    *   **Hình ảnh hóa đơn (.jpg/.png...):** Sử dụng `PaddleOCR` (lang='vi', use_gpu=False) chạy trên CPU ngoại tuyến.
3.  **Thuật toán Lọc tiền & Phân loại Chi phí:**
    *   **Lọc số tiền:** Áp dụng Regular Expression chuẩn hóa: `r'\b(\d{1,3}(?:[.,]\d{3})+)\b'`. Chỉ chấp nhận số tiền nằm trong khoảng giá trị hợp lệ từ **100.000 VNĐ** đến **50.000.000 VNĐ**.
    *   **Phân loại chi phí:** Dò tìm từ khóa (Dictionary Matching) thông qua file cấu hình `config/fee_keywords.py` để phân loại chi phí thành 6 nhóm chuẩn: **Nâng, Hạ, Vệ sinh, Lưu cont, Cân, Phụ phí**.
    *   *Thứ tự ưu tiên dò từ khóa:* Dòng hiện tại chứa số tiền $\rightarrow$ Dòng ngay trước $\rightarrow$ Dòng ngay sau.

---

## 📂 Cấu trúc Thư mục Dự án

```text
D:\SmartICDST_OCR\
│
├── main.py                         # 🚀 Entry point khởi chạy ứng dụng (Sprint 4)
├── requirements.txt                # 📦 Danh sách thư viện cần cài đặt
├── README.md                       # 📖 Hướng dẫn chi tiết dự án
├── .gitignore                      # 🛡️ Cấu hình bỏ qua các file rác/dữ liệu test khi push Git
│
├── core/                           # 🧠 Logic nghiệp vụ xử lý dữ liệu
│   ├── __init__.py
│   ├── ocr_processor.py            # Nhận dạng văn bản từ Ảnh và PDF (Scanned/Digital)
│   ├── fee_extractor.py            # Trích xuất số tiền (Regex) & phân loại phí (Từ điển)
│   └── batch_scanner.py            # Quét hàng loạt thư mục, tổng hợp kết quả (Sprint 3)
│
├── gui/                            # 🖥️ Giao diện người dùng
│   ├── __init__.py
│   ├── app.py                      # Khung giao diện chính dạng Split-View (Sprint 2)
│   └── components.py               # Các widget tùy chỉnh (Bảng kết quả, Preview ảnh)
│
├── config/                         # ⚙️ Cấu hình hệ thống
│   ├── __init__.py
│   └── fee_keywords.py             # Định nghĩa danh sách từ khóa có dấu & không dấu
│
└── DULIEUTEST/                     # 📂 Thư mục dữ liệu kiểm thử (Chỉ đồng bộ thư mục Baocao lên GitHub)
    └── Baocao/
        └── Xaydung/                # Tài liệu kỹ thuật chi tiết của 4 Sprints
```

---

## 🛠️ Hướng dẫn Cài đặt & Chạy thử nghiệm

### 1. Cài đặt các thư viện phụ thuộc
Hệ thống sử dụng các thư viện Python chuyên dụng được ghim phiên bản ổn định để chạy offline trên CPU Windows:

```bash
pip install -r requirements.txt
```

*Danh sách thư viện chi tiết trong `requirements.txt`:*
*   `paddlepaddle==2.6.2` (Engine học sâu của Baidu)
*   `paddleocr==2.8.1` (Công cụ OCR offline tốt nhất cho tiếng Việt)
*   `customtkinter>=5.2.0` (GUI hiện đại, hỗ trợ Dark/Light mode)
*   `Pillow>=10.0.0` (Xử lý và hiển thị hình ảnh hóa đơn)
*   `pandas>=2.0.0` & `openpyxl>=3.1.0` (Đọc/ghi và xuất báo cáo Excel)
*   `pdfplumber>=0.10.0` (Cào chữ trực tiếp từ PDF văn bản)
*   `pymupdf>=1.22.0` (Render nhanh các trang PDF thành ảnh)
*   `pyinstaller>=6.0.0` (Đóng gói ứng dụng thành file .exe chạy độc lập)

### 2. Kiểm thử độc lập Logic Cốt lõi (Sprint 1)
Chạy script kiểm thử để kiểm tra khả năng đọc và trích xuất chi phí từ hình ảnh hóa đơn `.jpg` và tài liệu `.pdf`:

```bash
python test_sprint1.py
```

---

## 🗺️ Lộ trình Phát triển 4 Sprints

| Giai đoạn | Mục tiêu | Trạng thái | Các file triển khai |
|-----------|----------|------------|---------------------|
| **Sprint 1** | Logic cốt lõi: OCR, PDF, Regex & Lọc từ điển | **Hoàn thành** | `core/ocr_processor.py`, `core/fee_extractor.py`, `config/fee_keywords.py`, `test_sprint1.py` |
| **Sprint 2** | Giao diện người dùng Split-View (Bảng | Ảnh gốc) | *Chờ kích hoạt* | `gui/app.py`, `gui/components.py` |
| **Sprint 3** | Quét thư mục hàng loạt, Tích hợp luồng & Xuất Excel | *Chờ kích hoạt* | `core/batch_scanner.py` |
| **Sprint 4** | Đóng gói .exe độc lập chạy hoàn toàn offline | *Chờ kích hoạt* | `main.py`, `SmartICDST_OCR.spec` |
