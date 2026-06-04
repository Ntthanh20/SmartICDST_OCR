# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import logging
import cv2
import numpy as np
from PIL import Image
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
        Thiết lập use_angle_cls=True để nạp thêm mô hình phân loại góc chữ.
        """
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
                use_angle_cls=True,  # Bắt buộc bật để chạy mô hình nhận dạng góc nghiêng/ngược
                det_model_dir=det_dir,
                rec_model_dir=rec_dir,
                cls_model_dir=cls_dir
            )
        else:
            print("[OCR] Khởi tạo mô hình mặc định từ thư mục người dùng (~/.paddleocr/)")
            self.ocr = PaddleOCR(
                lang='vi', 
                use_gpu=False, 
                show_log=False, 
                use_angle_cls=True  # Bắt buộc bật để chạy mô hình nhận dạng góc nghiêng/ngược
            )

    def determine_and_rotate_image(self, img, log_prefix="", silent=False) -> np.ndarray:
        """
        Nhận diện góc xoay của ma trận ảnh (img) và xoay thẳng về hướng chuẩn bằng OpenCV.
        
        Args:
            img: Ma trận ảnh OpenCV (numpy array).
            log_prefix: Tiền tố in log (ví dụ tên file).
            silent: Nếu True, sẽ tắt bớt log chi tiết để tránh spam màn hình console.
            
        Returns:
            Ma trận ảnh đã được xoay thẳng.
        """
        try:
            # Chạy phân loại góc (det=False, rec=False, cls=True để giảm thiểu tài nguyên và thời gian quét)
            cls_res = self.ocr.ocr(img, det=False, rec=False, cls=True)
            if cls_res and len(cls_res) > 0 and cls_res[0] and len(cls_res[0]) > 0:
                angle_str, confidence = cls_res[0][0]
                
                try:
                    angle = int(float(angle_str))
                except ValueError:
                    angle = 0
                
                # Chỉ thực hiện xoay nếu phát hiện có xoay góc và độ tin cậy > 0.5
                if angle != 0 and confidence > 0.5:
                    if not silent:
                        prefix = f"[{log_prefix}] " if log_prefix else ""
                        print(f"{prefix}Phát hiện ảnh bị xoay {angle} độ (độ tin cậy: {confidence:.2f}). Tiến hành xoay thẳng...")
                    if angle == 90:
                        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    elif angle == 180:
                        img = cv2.rotate(img, cv2.ROTATE_180)
                    elif angle == 270 or angle == -90:
                        img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
                else:
                    if not silent:
                        prefix = f"[{log_prefix}] " if log_prefix else ""
                        print(f"{prefix}Hướng ảnh bình thường hoặc độ tin cậy phân loại góc thấp (góc: {angle}, độ tin cậy: {confidence:.2f})")
        except Exception as e:
            print(f"[WARNING] Lỗi khi nhận diện hướng và xoay ma trận ảnh: {str(e)}")
        
        return img

    def extract_text_from_image_matrix(self, img) -> str:
        """
        Nhận diện chữ từ ma trận ảnh đã được xử lý bằng PaddleOCR.
        Sử dụng thuật toán Horizontal Line Reconstruction (nhóm các block cùng dòng ngang và sắp xếp từ trái qua phải)
        để bảo toàn cấu trúc dòng/cột của hóa đơn, giúp việc trích xuất phí và số tiền chính xác hơn nhiều.
        
        Args:
            img: Ma trận ảnh (numpy array) đã được xoay thẳng.
            
        Returns:
            Văn bản thô phân tách bằng dấu xuống dòng.
        """
        try:
            # Chạy nhận diện chữ (chế độ cls=False vì ảnh đã được xoay thẳng vật lý ở bước trước)
            result = self.ocr.ocr(img, cls=False)
            if not result:
                return ""
            
            all_blocks = []
            for line in result:
                if line is None:
                    continue
                for word_info in line:
                    if not word_info or len(word_info) < 2:
                        continue
                    bbox = word_info[0]
                    text_info = word_info[1]
                    if not text_info or not bbox:
                        continue
                    text = text_info[0]
                    
                    # Tính Y center và X min từ bbox
                    y_coords = [p[1] for p in bbox]
                    x_coords = [p[0] for p in bbox]
                    
                    y_center = sum(y_coords) / len(y_coords)
                    x_min = min(x_coords)
                    height = max(y_coords) - min(y_coords)
                    
                    all_blocks.append({
                        "text": text,
                        "y_center": y_center,
                        "x_min": x_min,
                        "height": height
                    })
            
            if not all_blocks:
                return ""
                
            # Sắp xếp theo chiều dọc (Y center) từ trên xuống dưới
            all_blocks.sort(key=lambda b: b["y_center"])
            
            # Nhóm các block cùng dòng ngang
            lines_grouped = []
            for block in all_blocks:
                placed = False
                for g_line in lines_grouped:
                    avg_y = sum(b["y_center"] for b in g_line) / len(g_line)
                    avg_h = sum(b["height"] for b in g_line) / len(g_line)
                    # Nếu khoảng cách Y center nhỏ hơn 60% chiều cao trung bình của dòng
                    if abs(block["y_center"] - avg_y) < (avg_h * 0.6):
                        g_line.append(block)
                        placed = True
                        break
                if not placed:
                    lines_grouped.append([block])
            
            # Sắp xếp các block trong từng dòng theo thứ tự từ trái qua phải (X tăng dần) và ghép chuỗi
            reconstructed_lines = []
            for g_line in lines_grouped:
                g_line.sort(key=lambda b: b["x_min"])
                line_text = " ".join(b["text"] for b in g_line)
                avg_y = sum(b["y_center"] for b in g_line) / len(g_line)
                reconstructed_lines.append((avg_y, line_text))
                
            # Sắp xếp các dòng từ trên xuống dưới
            reconstructed_lines.sort(key=lambda x: x[0])
            
            return "\n".join(line[1] for line in reconstructed_lines)
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi nhận diện OCR ma trận ảnh: {str(e)}")
            return ""

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Nhận diện chữ từ file ảnh (JPG, JPEG, PNG,...) sử dụng PaddleOCR.
        Tự động xoay thẳng ảnh bị nghiêng/ngược trước khi nhận diện chữ.
        
        Args:
            image_path: Đường dẫn tuyệt đối đến file ảnh.
            
        Returns:
            Chuỗi văn bản thô đã ghép nối từ tất cả các khối chữ tìm thấy.
        """
        try:
            # Đọc ảnh hỗ trợ tên file/đường dẫn Unicode tiếng Việt trên Windows
            img_array = np.fromfile(image_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                print(f"[ERROR] Không thể đọc ảnh từ đường dẫn: {image_path}")
                return ""
            
            file_name = os.path.basename(image_path)
            # Bước A, B, C: Nhận diện góc xoay và xoay thẳng vật lý ma trận ảnh
            img = self.determine_and_rotate_image(img, log_prefix=file_name)
            
            # Bước D: Chạy OCR trên ảnh đã xoay thẳng
            return self.extract_text_from_image_matrix(img)
        except Exception as e:
            print(f"[ERROR] Lỗi khi nhận diện OCR ảnh {image_path}: {str(e)}")
            return ""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Trích xuất văn bản từ file PDF.
        Tuân thủ quy trình phân cấp nghiêm ngặt (Fallback mechanism):
        1. Thử cào chữ trực tiếp trước bằng pdfplumber (cho PDF văn bản kỹ thuật số).
           Nếu cào được chữ (bool(text.strip()) == True), in log và TRẢ VỀ NGAY LẬP TỨC.
        2. Nếu PDF rỗng hoặc không cào được chữ (PDF Scan), chuyển sang chế độ render ảnh
           để tự động kiểm tra hướng/xoay ảnh thẳng và chạy OCR.
        
        Args:
            pdf_path: Đường dẫn tuyệt đối đến file PDF.
            
        Returns:
            Chuỗi văn bản thô thu được từ PDF.
        """
        text = ""
        file_name = os.path.basename(pdf_path)
        
        # Bước 1: Thử cào chữ trực tiếp dùng pdfplumber (Chỉ dùng cho PDF văn bản hệ thống)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # Loại bỏ khoảng trắng thừa để kiểm tra dữ liệu thực tế
            cleaned_text = text.strip()
            
            # BẮT BUỘC: Nếu có dữ liệu chữ đọc được trực tiếp
            if cleaned_text:
                print(f"[PDF] Phát hiện PDF văn bản hệ thống ({file_name}). Trích xuất chữ trực tiếp thành công.")
                return cleaned_text

        except Exception as e:
            print(f"[WARNING] Không thể cào chữ trực tiếp từ PDF {pdf_path}: {str(e)}")
        
        # Bước 2: PDF quét - Render các trang thành numpy array rồi tự động xoay thẳng hướng và OCR
        print(f"[PDF] PDF không có text trực tiếp (PDF Scan) ({file_name}). Kích hoạt bộ chuyển đổi ảnh và OCR...")
        ocr_text_list = []
        doc = None
        try:
            doc = fitz.open(pdf_path)
            for page_idx, page in enumerate(doc):
                # Render với độ phân giải tăng 2 lần để OCR chính xác hơn
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Chuyển đổi pixmap PyMuPDF trực tiếp sang ma trận numpy (tránh ghi đĩa)
                img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                img = img_data.reshape((pix.height, pix.width, pix.n))
                
                # Chuyển RGB/RGBA sang BGR của OpenCV
                if pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                elif pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                
                # Nhận diện góc xoay và xoay thẳng trang PDF quét (chỉ in log cho trang đầu tiên để tránh spam màn hình)
                is_silent = (page_idx > 0)
                img = self.determine_and_rotate_image(img, log_prefix=f"{file_name} Trang {page_idx + 1}", silent=is_silent)
                
                # Chạy OCR nhận dạng chữ trên ma trận ảnh đã được xoay thẳng
                page_ocr_text = self.extract_text_from_image_matrix(img)
                if page_ocr_text:
                    ocr_text_list.append(page_ocr_text)
                        
            return "\n".join(ocr_text_list)
        except Exception as e:
            print(f"[ERROR] Lỗi khi xử lý PDF quét {pdf_path}: {str(e)}")
            return ""
        finally:
            if doc:
                doc.close()

    def extract_text_by_pages(self, file_path: str) -> list[str]:
        """
        Trích xuất văn bản của file dưới dạng danh sách các trang (mỗi trang là một chuỗi).
        Nếu là file ảnh, trả về danh sách chứa 1 phần tử.
        
        Args:
            file_path: Đường dẫn tuyệt đối đến file.
            
        Returns:
            Danh sách các chuỗi văn bản của từng trang.
        """
        if not os.path.exists(file_path):
            print(f"[ERROR] File không tồn tại: {file_path}")
            return [""]
            
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".pdf"]:
            # File ảnh thông thường
            return [self.extract_text_from_image(file_path)]
            
        # Xử lý file PDF theo từng trang
        pages_text = []
        file_name = os.path.basename(file_path)
        
        # Bước 1: Thử cào chữ trực tiếp từng trang dùng pdfplumber (cho PDF văn bản hệ thống)
        try:
            with pdfplumber.open(file_path) as pdf:
                is_digital = False
                if pdf.pages:
                    first_text = pdf.pages[0].extract_text()
                    if first_text and first_text.strip():
                        is_digital = True
                
                if is_digital:
                    print(f"[PDF] Phát hiện PDF văn bản hệ thống ({file_name}). Trích xuất chữ trực tiếp từng trang.")
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        pages_text.append(page_text if page_text else "")
                    return pages_text
        except Exception as e:
            print(f"[WARNING] Lỗi khi cào chữ PDF bằng pdfplumber: {str(e)}")
            
        # Bước 2: PDF quét - Render các trang thành numpy array rồi tự động xoay thẳng hướng và OCR
        print(f"[PDF] PDF không có text trực tiếp (PDF Scan) ({file_name}). Kích hoạt bộ chuyển đổi ảnh và OCR từng trang...")
        doc = None
        try:
            doc = fitz.open(file_path)
            for page_idx, page in enumerate(doc):
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                img = img_data.reshape((pix.height, pix.width, pix.n))
                
                if pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                elif pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                
                # Nhận diện góc xoay và xoay thẳng trang PDF quét (chỉ in log cho trang đầu tiên để tránh spam màn hình)
                is_silent = (page_idx > 0)
                img = self.determine_and_rotate_image(img, log_prefix=f"{file_name} Trang {page_idx + 1}", silent=is_silent)
                
                page_ocr_text = self.extract_text_from_image_matrix(img)
                pages_text.append(page_ocr_text if page_ocr_text else "")
            return pages_text
        except Exception as e:
            print(f"[ERROR] Lỗi khi xử lý PDF quét {file_name}: {str(e)}")
            return [""]
        finally:
            if doc:
                doc.close()

    def extract_text(self, file_path: str) -> str:
        """
        Hàm chính: Nhận diện đường dẫn file, tự động phân loại xử lý ảnh hay PDF.
        Trả về chuỗi văn bản thô ghép nối từ tất cả các trang bằng dấu xuống dòng.
        
        Args:
            file_path: Đường dẫn tuyệt đối đến file cần trích xuất text.
            
        Returns:
            Chuỗi văn bản thô thu được.
        """
        pages = self.extract_text_by_pages(file_path)
        return "\n".join(pages)

    def get_corrected_image(self, file_path: str) -> Image.Image:
        """
        Nhận diện đường dẫn file (ảnh hoặc PDF), tự động xoay thẳng ảnh vật lý,
        và trả về đối tượng PIL Image đã xoay thẳng để hiển thị trên GUI.
        Nếu là file PDF, hàm sẽ trả về trang đầu tiên (trang 1) đã xoay thẳng.
        
        Đối với PDF văn bản hệ thống, bỏ qua việc gọi mô hình phân loại góc xoay để tối ưu hóa hiệu năng.
        
        Args:
            file_path: Đường dẫn tuyệt đối đến file.
            
        Returns:
            Đối tượng PIL.Image.Image đã được xoay thẳng hướng đọc chuẩn.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Không tìm thấy file: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        file_name = os.path.basename(file_path)
        
        if ext == ".pdf":
            # PDF: Kiểm tra xem có phải PDF văn bản hệ thống hay không bằng cách xem trang 1 có text trực tiếp không
            is_digital_pdf = False
            try:
                with pdfplumber.open(file_path) as pdf:
                    if pdf.pages:
                        first_page_text = pdf.pages[0].extract_text()
                        if first_page_text and first_page_text.strip():
                            is_digital_pdf = True
            except Exception:
                pass
            
            # Render trang đầu tiên bằng PyMuPDF
            doc = fitz.open(file_path)
            try:
                page = doc.load_page(0)
                zoom = 2.0  # Tăng độ phân giải để ảnh hiển thị sắc nét
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                
                # Chuyển đổi sang numpy
                img_data = np.frombuffer(pix.samples, dtype=np.uint8)
                img = img_data.reshape((pix.height, pix.width, pix.n))
                
                if pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                elif pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                
                # Nếu là PDF văn bản hệ thống, bỏ qua bước kiểm tra góc xoay của PaddleOCR để tối ưu tốc độ
                if is_digital_pdf:
                    print(f"[PREVIEW] PDF văn bản hệ thống ({file_name}) - Bỏ qua bước kiểm tra hướng xoay của OCR.")
                else:
                    # Nhận diện góc xoay và xoay thẳng trang PDF quét
                    img = self.determine_and_rotate_image(img, log_prefix=f"{file_name} Trang 1", silent=False)
                
                # Chuyển đổi ngược lại RGB để tạo đối tượng PIL Image
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                return Image.fromarray(img_rgb)
            finally:
                doc.close()
        else:
            # File hình ảnh thông thường
            img_array = np.fromfile(file_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Không thể đọc hoặc giải mã hình ảnh từ: {file_path}")
            
            # Nhận diện góc xoay và xoay thẳng hình ảnh
            img = self.determine_and_rotate_image(img, log_prefix=file_name, silent=False)
            
            # Chuyển đổi ngược lại RGB để tạo đối tượng PIL Image
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            return Image.fromarray(img_rgb)
