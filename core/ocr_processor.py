# -*- coding: utf-8 -*-

import os
import tempfile
import logging
from paddleocr import PaddleOCR
import pdfplumber
import fitz  # PyMuPDF

# Tắt các thông điệp cảnh báo thừa từ Paddle và PyMuPDF
logging.getLogger("ppocr").setLevel(logging.ERROR)

class OCRProcessor:
    def __init__(self):
        """
        Khởi tạo công cụ OCR.
        Tự động kiểm tra xem có thư mục chứa các file model offline (weights) ở bên cạnh 
        thư mục chạy / file thực thi .exe hay không. Nếu có thì nạp trực tiếp, ngược lại 
        sẽ nạp từ thư mục mặc định người dùng (~/.paddleocr/).
        """
        import sys
        
        # Xác định thư mục cơ sở
        if getattr(sys, 'frozen', False):
            # Nếu chạy từ file .exe được đóng gói
            base_dir = os.path.dirname(sys.executable)
        else:
            # Nếu chạy script Python bình thường
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        model_base = os.path.join(base_dir, "paddleocr_models")
        det_dir = os.path.join(model_base, "det", "en", "en_PP-OCRv3_det_infer")
        rec_dir = os.path.join(model_base, "rec", "latin", "latin_PP-OCRv3_rec_infer")
        cls_dir = os.path.join(model_base, "cls", "ch_ppocr_mobile_v2.0_cls_infer")

        # Nếu tồn tại các thư mục mô hình offline
        if os.path.exists(det_dir) and os.path.exists(rec_dir):
            print(f"[OCR] Nạp mô hình offline từ: {model_base}")
            self.ocr = PaddleOCR(
                lang='vi',
                use_gpu=False,
                show_log=False,
                det_model_dir=det_dir,
                rec_model_dir=rec_dir,
                cls_model_dir=cls_dir
            )
        else:
            print("[OCR] Khởi tạo mô hình mặc định từ thư mục người dùng (~/.paddleocr/)")
            self.ocr = PaddleOCR(lang='vi', use_gpu=False, show_log=False)

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Nhận diện chữ từ file ảnh (JPG, JPEG, PNG,...) sử dụng PaddleOCR.
        
        Args:
            image_path: Đường dẫn tuyệt đối đến file ảnh.
            
        Returns:
            Chuỗi văn bản thô đã ghép nối từ tất cả các khối chữ tìm thấy.
        """
        try:
            # Gọi ocr nhận diện ảnh
            result = self.ocr.ocr(image_path, cls=False)
            if not result:
                return ""
            
            lines = []
            for line in result:
                if line is None:
                    continue
                for word_info in line:
                    # word_info: [ [box], (text, confidence) ]
                    text = word_info[1][0]
                    lines.append(text)
            
            return "\n".join(lines)
        except Exception as e:
            print(f"[ERROR] Lỗi khi nhận diện OCR ảnh {image_path}: {str(e)}")
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Trích xuất văn bản từ file PDF.
        Thử cào chữ trực tiếp trước bằng pdfplumber (cho PDF văn bản kỹ thuật số).
        Nếu không lấy được chữ (PDF quét), sử dụng PyMuPDF render trang thành ảnh và chạy OCR.
        
        Args:
            pdf_path: Đường dẫn tuyệt đối đến file PDF.
            
        Returns:
            Chuỗi văn bản thô thu được từ PDF.
        """
        text = ""
        try:
            # Bước 1: Thử cào chữ trực tiếp dùng pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Loại bỏ khoảng trắng thừa để kiểm tra độ dài thực tế
            cleaned_text = text.strip()
            
            # Nếu cào được chữ trực tiếp và có độ dài hợp lý (không phải PDF rỗng hoặc PDF quét)
            if len(cleaned_text) > 20:
                # Trả về văn bản đã cào trực tiếp
                return cleaned_text

        except Exception as e:
            print(f"[WARNING] Không thể cào chữ trực tiếp từ PDF {pdf_path}: {str(e)}. Thử nghiệm phương pháp render ảnh OCR.")
        
        # Bước 2: PDF quét - Render từng trang thành ảnh bằng PyMuPDF (fitz) rồi OCR
        print(f"[INFO] File {os.path.basename(pdf_path)} được nhận diện là PDF quét. Bắt đầu render ảnh và chạy OCR...")
        ocr_text_list = []
        doc = None
        try:
            doc = fitz.open(pdf_path)
            for page_idx, page in enumerate(doc):
                # Render với độ phân giải tăng 2 lần để OCR chính xác hơn
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Tạo file ảnh tạm
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                    temp_filename = temp_file.name
                
                try:
                    pix.save(temp_filename)
                    # Chạy OCR trên file ảnh tạm này
                    page_ocr_text = self.extract_text_from_image(temp_filename)
                    if page_ocr_text:
                        ocr_text_list.append(page_ocr_text)
                finally:
                    # Đảm bảo xóa file tạm sau khi chạy xong
                    if os.path.exists(temp_filename):
                        os.remove(temp_filename)
                        
            return "\n".join(ocr_text_list)
        except Exception as e:
            print(f"[ERROR] Lỗi khi xử lý PDF quét {pdf_path}: {str(e)}")
            return ""
        finally:
            if doc:
                doc.close()

    def extract_text(self, file_path: str) -> str:
        """
        Hàm chính: Nhận diện đường dẫn file, tự động phân loại xử lý ảnh hay PDF.
        
        Args:
            file_path: Đường dẫn tuyệt đối đến file cần trích xuất text.
            
        Returns:
            Chuỗi văn bản thô thu được.
        """
        if not os.path.exists(file_path):
            print(f"[ERROR] File không tồn tại: {file_path}")
            return ""
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".pdf"]:
            return self.extract_text_from_pdf(file_path)
        elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
            return self.extract_text_from_image(file_path)
        else:
            print(f"[WARNING] Định dạng file không được hỗ trợ: {ext}")
            return ""
