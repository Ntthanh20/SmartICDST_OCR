# -*- coding: utf-8 -*-

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter
from PIL import Image
import fitz  # PyMuPDF
import pandas as pd

# Cấu hình giao diện CustomTkinter
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

class EditDialog(customtkinter.CTkToplevel):
    """
    Hộp thoại CTkToplevel tùy chỉnh để sửa Loại chi phí và Số tiền của một container.
    Thiết lập modal (grab_set) để chặn tương tác với cửa sổ chính khi đang sửa.
    """
    def __init__(self, parent, fee_type, amount, callback):
        super().__init__(parent)
        self.parent = parent
        self.callback = callback

        self.title("Chỉnh sửa thông tin chi phí")
        self.geometry("380x220")
        self.resizable(False, False)
        
        # Bắt buộc hiển thị lên trên và khóa cửa sổ chính
        self.lift()
        self.focus_force()
        self.grab_set()

        # Căn giữa hộp thoại theo cửa sổ cha
        self._center_window()

        self.grid_columnconfigure((0, 1), weight=1)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        # 1. Nhãn và Ô nhập "Loại chi phí"
        lbl_fee = customtkinter.CTkLabel(self, text="Loại chi phí:", font=("Segoe UI", 12, "bold"))
        lbl_fee.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.entry_fee = customtkinter.CTkEntry(self, width=180, font=("Segoe UI", 12))
        self.entry_fee.insert(0, fee_type)
        self.entry_fee.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="ew")

        # 2. Nhãn và Ô nhập "Số tiền"
        lbl_amount = customtkinter.CTkLabel(self, text="Số tiền (VNĐ):", font=("Segoe UI", 12, "bold"))
        lbl_amount.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        self.entry_amount = customtkinter.CTkEntry(self, width=180, font=("Segoe UI", 12))
        self.entry_amount.insert(0, str(amount))
        self.entry_amount.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

        # 3. Hàng nút bấm Lưu / Hủy
        btn_save = customtkinter.CTkButton(
            self, 
            text="Lưu", 
            fg_color="#27ae60", 
            hover_color="#219653", 
            width=100, 
            command=self._save
        )
        btn_save.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="e")

        btn_cancel = customtkinter.CTkButton(
            self, 
            text="Hủy", 
            fg_color="#7f8c8d", 
            hover_color="#95a5a6", 
            width=100, 
            command=self._cancel
        )
        btn_cancel.grid(row=2, column=1, padx=20, pady=(10, 20), sticky="w")

    def _center_window(self):
        """Hàm căn giữa popup tương đối với cửa sổ cha."""
        self.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_w = self.parent.winfo_width()
        parent_h = self.parent.winfo_height()
        
        x = parent_x + (parent_w - self.winfo_width()) // 2
        y = parent_y + (parent_h - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _save(self):
        fee = self.entry_fee.get().strip()
        amount_str = self.entry_amount.get().strip().replace(".", "").replace(",", "")
        
        if not fee:
            messagebox.showwarning("Cảnh báo", "Loại chi phí không được để trống!", parent=self)
            return

        try:
            amount = int(amount_str)
        except ValueError:
            messagebox.showwarning("Cảnh báo", "Số tiền phải là số nguyên hợp lệ!", parent=self)
            return

        # Gọi hàm callback trả kết quả về cửa sổ chính
        self.callback(fee, amount)
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.grab_release()
        self.destroy()


class MainApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # 1. Cấu hình cửa sổ chính
        self.title("SmartICDST_OCR v2.0 – Đối Soát Hóa Đơn Logistics")
        self.geometry("1200x750")
        self.minsize(900, 550)

        # Biến quản lý dữ liệu
        self.source_dir = tk.StringVar(value="")
        self.scanned_results = []  # Danh sách lưu kết quả quét thực tế
        self.ocr_processor = None  # Đối tượng xử lý OCR dùng chung để tối ưu tốc độ
        self.stop_requested = False  # Cờ yêu cầu dừng phân tích

        # 2. Tạo bố cục lưới tổng thể (Hỗ trợ Progress Bar ở hàng 2)
        self.grid_rowconfigure(0, weight=0)  # Toolbar trên cùng
        self.grid_rowconfigure(1, weight=1)  # Split View ở giữa
        self.grid_rowconfigure(2, weight=0)  # Progress Bar (Mặc định ẩn)
        self.grid_rowconfigure(3, weight=0)  # Action Bar dưới cùng
        self.grid_columnconfigure(0, weight=1)

        # Khởi tạo giao diện các Panel
        self._init_top_bar()
        self._init_main_split_view()
        self._init_progress_bar()
        self._init_bottom_bar()

    def _init_top_bar(self):
        """Khởi tạo Toolbar phía trên để chọn thư mục."""
        top_frame = customtkinter.CTkFrame(self, corner_radius=0, height=60)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        top_frame.grid_columnconfigure(1, weight=1)

        lbl_dir = customtkinter.CTkLabel(top_frame, text="Thư mục nguồn:", font=("Segoe UI", 12, "bold"))
        lbl_dir.grid(row=0, column=0, padx=(15, 10), pady=15, sticky="w")

        self.entry_path = customtkinter.CTkEntry(
            top_frame, 
            placeholder_text="Chọn thư mục chứa ảnh hóa đơn / file PDF đối soát...",
            textvariable=self.source_dir,
            font=("Segoe UI", 12)
        )
        self.entry_path.grid(row=0, column=1, padx=10, pady=15, sticky="ew")

        btn_browse = customtkinter.CTkButton(
            top_frame, 
            text="...", 
            width=50, 
            command=self._on_choose_directory
        )
        btn_browse.grid(row=0, column=2, padx=(0, 15), pady=15, sticky="e")

    def _init_main_split_view(self):
        """Khởi tạo khung Split-View ở giữa chia tỉ lệ 50% trái (Treeview) và 50% phải (Xem ảnh)."""
        split_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        split_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        split_frame.grid_columnconfigure(0, weight=1, uniform="group1")
        split_frame.grid_columnconfigure(1, weight=1, uniform="group1")
        split_frame.grid_rowconfigure(0, weight=1)

        # PANEL TRÁI (50%): ttk.Treeview hiển thị dạng Monospace Consolas
        left_panel = customtkinter.CTkFrame(split_frame)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        left_panel.grid_rowconfigure(0, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        
        is_dark = customtkinter.get_appearance_mode() == "Dark"
        bg_color = "#2a2d2e" if is_dark else "#fcfcfc"
        fg_color = "#ffffff" if is_dark else "#000000"
        header_bg = "#1f1f1f" if is_dark else "#eaeaea"
        header_fg = "#ffffff" if is_dark else "#000000"

        style.configure("Treeview", 
                        background=bg_color,
                        foreground=fg_color,
                        rowheight=28,
                        fieldbackground=bg_color,
                        bordercolor="#3a3a3a",
                        borderwidth=1)
        
        # Định nghĩa kiểu chữ Consolas cho dữ liệu bảng để căn dòng đẹp mắt
        style.configure("Treeview.Cell", font=("Consolas", 11))
        
        style.configure("Treeview.Heading", 
                        background=header_bg,
                        foreground=header_fg,
                        font=("Segoe UI", 12, "bold"),
                        relief="flat")
        
        style.map('Treeview', background=[('selected', '#1f538d')])

        cols = ("document_key", "container_id", "fee_type", "amount")
        self.tree = ttk.Treeview(left_panel, columns=cols, show="headings", style="Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        self.tree.heading("document_key", text="Mã lô / Số HĐ")
        self.tree.heading("container_id", text="Số Container")
        self.tree.heading("fee_type", text="Loại chi phí")
        self.tree.heading("amount", text="Số tiền (VNĐ)")

        self.tree.column("document_key", width=140, anchor="center")
        self.tree.column("container_id", width=140, anchor="center")
        self.tree.column("fee_type", width=200, anchor="center")
        self.tree.column("amount", width=120, anchor="center")

        # Cấu hình các tag màu xen kẽ các dòng (Zebra Striping) để dễ quan sát
        self.tree.tag_configure("evenrow", background="#2d3135" if is_dark else "#f9f9f9")
        self.tree.tag_configure("oddrow", background="#202326" if is_dark else "#ececec")

        scrollbar = customtkinter.CTkScrollbar(left_panel, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_table_row_select)
        self.tree.bind("<Double-1>", self._on_table_row_double_click)

        # PANEL PHẢI (50%): Khung xem trước hình ảnh/PDF hỗ trợ zoom cuộn
        self.right_panel = customtkinter.CTkFrame(split_frame)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_panel.grid_rowconfigure(0, weight=0)  # Zoom toolbar
        self.right_panel.grid_rowconfigure(1, weight=1)  # Canvas preview
        self.right_panel.grid_columnconfigure(0, weight=1)

        # Thanh công cụ Zoom
        zoom_bar = customtkinter.CTkFrame(self.right_panel, fg_color="transparent")
        zoom_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        
        btn_zoom_in = customtkinter.CTkButton(
            zoom_bar, text="🔍 +", width=50, height=26, 
            font=("Segoe UI", 11, "bold"), command=self._zoom_in
        )
        btn_zoom_in.grid(row=0, column=0, padx=3)
        
        btn_zoom_out = customtkinter.CTkButton(
            zoom_bar, text="🔍 -", width=50, height=26, 
            font=("Segoe UI", 11, "bold"), command=self._zoom_out
        )
        btn_zoom_out.grid(row=0, column=1, padx=3)
        
        btn_zoom_fit = customtkinter.CTkButton(
            zoom_bar, text="Fit", width=50, height=26, 
            font=("Segoe UI", 11, "bold"), command=self._zoom_fit
        )
        btn_zoom_fit.grid(row=0, column=2, padx=3)
        
        self.lbl_zoom_val = customtkinter.CTkLabel(
            zoom_bar, text="100%", font=("Segoe UI", 11, "bold"), text_color="gray"
        )
        self.lbl_zoom_val.grid(row=0, column=3, padx=10)

        # Khung chứa canvas và thanh cuộn ngang/dọc cho preview file
        self.canvas_frame = customtkinter.CTkFrame(self.right_panel)
        self.canvas_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

        # Sử dụng tk.Canvas kết hợp CTkScrollbar để có cả thanh cuộn dọc và cuộn ngang
        self.canvas = tk.Canvas(self.canvas_frame, bg=bg_color, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = customtkinter.CTkScrollbar(self.canvas_frame, orientation="vertical", command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar = customtkinter.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(xscrollcommand=self.h_scrollbar.set, yscrollcommand=self.v_scrollbar.set)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _init_progress_bar(self):
        """Khởi tạo thanh tiến độ (Progress Bar) và nhãn hiển thị tiến trình (mặc định ẩn)."""
        self.progress_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        
        self.progress_frame.grid_columnconfigure(0, weight=1)
        self.progress_frame.grid_rowconfigure((0, 1), weight=1)

        self.progress_bar = customtkinter.CTkProgressBar(self.progress_frame, height=12)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=(5, 2))
        self.progress_bar.set(0)

        self.lbl_progress = customtkinter.CTkLabel(
            self.progress_frame, 
            text="Đang chuẩn bị quét...", 
            font=("Segoe UI", 12, "italic")
        )
        self.lbl_progress.grid(row=1, column=0, padx=20, pady=(2, 5))

    def _init_bottom_bar(self):
        """Khởi tạo Action Bar phía dưới chứa các nút chức năng chính."""
        bottom_frame = customtkinter.CTkFrame(self, corner_radius=0, height=60)
        bottom_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 10))

        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(5, weight=1)

        self.btn_scan = customtkinter.CTkButton(
            bottom_frame,
            text="🔍 Phân tích",
            font=("Segoe UI", 13, "bold"),
            width=150,
            command=self._on_scan_directory
        )
        self.btn_scan.grid(row=0, column=1, padx=10, pady=15)

        self.btn_stop = customtkinter.CTkButton(
            bottom_frame,
            text="⏹️ Dừng phân tích",
            font=("Segoe UI", 13, "bold"),
            width=150,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            state="disabled",
            command=self._on_stop_analysis
        )
        self.btn_stop.grid(row=0, column=2, padx=10, pady=15)

        self.btn_edit = customtkinter.CTkButton(
            bottom_frame,
            text="✏️ Sửa chi phí",
            font=("Segoe UI", 13, "bold"),
            width=150,
            fg_color="#d35400",
            hover_color="#e67e22",
            command=self._on_edit_click
        )
        self.btn_edit.grid(row=0, column=3, padx=10, pady=15)

        self.btn_export = customtkinter.CTkButton(
            bottom_frame,
            text="📥 Xuất Excel",
            font=("Segoe UI", 13, "bold"),
            width=150,
            fg_color="#27ae60",
            hover_color="#219653",
            command=self._on_export_excel
        )
        self.btn_export.grid(row=0, column=4, padx=10, pady=15)

    # ========================================================
    # XỬ LÝ SỰ KIỆN GIAO DIỆN (EVENT HANDLERS)
    # ========================================================

    def _on_choose_directory(self):
        """Mở dialog chọn thư mục nguồn."""
        selected_path = filedialog.askdirectory(title="Chọn thư mục đối soát hóa đơn")
        if selected_path:
            normalized_path = os.path.normpath(selected_path)
            self.source_dir.set(normalized_path)
            print(f"[UI] Đã chọn thư mục: {normalized_path}")

    def _on_scan_directory(self):
        """Khởi chạy quét thư mục hàng loạt sử dụng đa luồng (Threading)."""
        path = self.source_dir.get().strip()
        if not path:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn thư mục nguồn trước khi quét!")
            return

        # Đặt lại cờ yêu cầu dừng
        self.stop_requested = False

        # Hiển thị thanh tiến độ
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Bắt đầu chuẩn bị phân tích...")

        # Vô hiệu hóa các nút điều khiển để tránh click nhiều lần khi đang chạy
        self.btn_scan.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.btn_export.configure(state="disabled")

        # Xóa dữ liệu cũ trên bảng và trong bộ nhớ
        self.tree.delete(*self.tree.get_children())
        self.scanned_results = []
        self.ctk_preview_image = None
        self.canvas.delete("all")
        # Dự phòng kích thước nếu canvas chưa vẽ xong
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 50 or canvas_h < 50:
            canvas_w, canvas_h = 420, 550
        self.canvas.create_text(
            canvas_w / 2, canvas_h / 2,
            text="Chọn dòng trong bảng để xem ảnh/PDF",
            font=("Segoe UI", 12, "italic"),
            fill="gray",
            tags="placeholder"
        )
        self.canvas.configure(scrollregion=(0, 0, canvas_w, canvas_h))

        # Bắt đầu đa luồng
        scan_thread = threading.Thread(target=self._scan_worker, args=(path,), daemon=True)
        scan_thread.start()

    def _on_stop_analysis(self):
        """Yêu cầu dừng phân tích hiện tại."""
        self.stop_requested = True
        self.btn_stop.configure(state="disabled")
        self.lbl_progress.configure(text="Đang dừng tiến trình phân tích...")
        print("[UI] Người dùng yêu cầu dừng phân tích.")

    def _scan_worker(self, path):
        """Hàm chạy nền trong thread riêng để quét thư mục."""
        # Khởi tạo ocr_processor trong thread phụ để tránh làm đơ giao diện chính khi load mô hình
        if self.ocr_processor is None:
            from core.ocr_processor import OCRProcessor
            self.ocr_processor = OCRProcessor()

        from core.batch_scanner import BatchScanner
        
        # Khởi tạo batch scanner và truyền ocr_processor dùng chung
        scanner = BatchScanner(ocr_processor=self.ocr_processor)

        def progress_update(current, total, file_name):
            # Nếu người dùng yêu cầu dừng, ném ngoại lệ để hủy luồng
            if self.stop_requested:
                raise RuntimeError("USER_CANCELLED")
            # Sử dụng self.after để cập nhật giao diện Tkinter an toàn từ Thread nền
            self.after(0, lambda c=current, t=total, f=file_name: self._update_progress_ui(c, t, f))

        try:
            results = scanner.scan_directory(path, progress_callback=progress_update)
            # Hoàn tất quét, đẩy kết quả về luồng chính
            self.after(0, lambda r=results: self._on_scan_completed(r))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._on_scan_failed(msg))

    def _update_progress_ui(self, current, total, file_name):
        """Cập nhật giao diện thanh tiến trình."""
        ratio = current / total
        self.progress_bar.set(ratio)
        self.lbl_progress.configure(text=f"Đang xử lý [{current}/{total}]: {file_name}")

    def _on_scan_completed(self, results):
        """Xử lý giao diện khi hoàn tất quét thư mục thành công."""
        self.progress_frame.grid_remove()  # Ẩn thanh tiến trình
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_export.configure(state="normal")

        # Lưu trữ kết quả và hiển thị lên bảng kết quả
        self.scanned_results = results
        for idx, res in enumerate(self.scanned_results):
            # Định dạng hiển thị doc_key thân thiện
            file_path = res.get("file_path", "")
            ext = os.path.splitext(file_path)[1].lower()
            key_val = res.get("document_key", "")
            doc_key_display = ""
            
            if ext in (".jpg", ".jpeg", ".png"):
                doc_key_display = "Ảnh"
            elif key_val:
                if key_val.startswith("LO_"):
                    doc_key_display = f"Lô: {key_val[3:]}"
                elif key_val.startswith("HD_"):
                    doc_key_display = f"HĐ: {key_val[3:]}"
                elif key_val.startswith("GD_"):
                    doc_key_display = f"GD: {key_val[3:]}"
                else:
                    doc_key_display = key_val

            # Chèn dòng vào Treeview (đúng cột: Mã lô / Số HĐ -> Số Container -> Loại chi phí -> Số tiền)
            item_id = self.tree.insert("", "end", values=(
                doc_key_display,
                res["container_id"], 
                res["fee_type"], 
                f"{res['amount']:,}"
            ), tags=("evenrow" if idx % 2 == 0 else "oddrow",))
            # Gắn ID hàng vào data để quản lý chỉnh sửa
            res["row_id"] = item_id

        total_scanned = len(results)
        messagebox.showinfo("Hoàn tất", f"Đã quét xong thư mục đối soát!\nTổng số bản ghi trích xuất: {total_scanned} dòng.")

    def _on_scan_failed(self, error_msg):
        """Xử lý giao diện khi xảy ra lỗi hoặc dừng trong quá trình quét nền."""
        self.progress_frame.grid_remove()
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.btn_export.configure(state="normal")
        
        if error_msg == "USER_CANCELLED":
            messagebox.showinfo("Đã dừng", "Tiến trình phân tích đã được dừng theo yêu cầu.")
            print("[UI] Đã dừng phân tích theo yêu cầu người dùng.")
        else:
            messagebox.showerror("Lỗi hệ thống", f"Đã xảy ra lỗi khi quét thư mục:\n{error_msg}")

    def _on_table_row_select(self, event):
        """Hiển thị xem trước hình ảnh/PDF trang đầu tiên khi click chọn dòng tương ứng."""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        
        # Tìm dữ liệu tương ứng của dòng
        selected_data = None
        for res in self.scanned_results:
            if res.get("row_id") == item_id:
                selected_data = res
                break

        if not selected_data:
            return

        file_path = selected_data["file_path"]
        
        # Reset zoom factor khi chọn dòng mới
        self.zoom_factor = 1.0
        self.lbl_zoom_val.configure(text="100%")
        self.current_preview_file = file_path
        
        self._render_preview()

    def _render_preview(self):
        """Hiển thị ảnh hoặc PDF đã xoay thẳng hướng, hỗ trợ thu phóng."""
        # Lấy kích thước canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 50 or canvas_h < 50:
            canvas_w, canvas_h = 420, 550

        if not hasattr(self, "current_preview_file") or not self.current_preview_file:
            self.ctk_preview_image = None
            self.canvas.delete("all")
            self.canvas.create_text(
                canvas_w / 2, canvas_h / 2,
                text="Chọn dòng trong bảng để xem ảnh/PDF",
                font=("Segoe UI", 12, "italic"),
                fill="gray",
                tags="placeholder"
            )
            self.canvas.configure(scrollregion=(0, 0, canvas_w, canvas_h))
            return
            
        file_path = self.current_preview_file
        if not os.path.exists(file_path):
            self.ctk_preview_image = None
            self.canvas.delete("all")
            self.canvas.create_text(
                canvas_w / 2, canvas_h / 2,
                text="File gốc đã bị xóa hoặc di chuyển!",
                font=("Segoe UI", 12, "bold"),
                fill="red",
                tags="placeholder"
            )
            self.canvas.configure(scrollregion=(0, 0, canvas_w, canvas_h))
            return
            
        try:
            # Khởi tạo ocr_processor lazily nếu chưa tồn tại
            if self.ocr_processor is None:
                from core.ocr_processor import OCRProcessor
                self.ocr_processor = OCRProcessor()
                
            # Lấy ảnh đã xoay thẳng hướng chuẩn (hỗ trợ cả ảnh và PDF)
            img = self.ocr_processor.get_corrected_image(file_path)
            
            img_w, img_h = img.size
            ratio = min(canvas_w / img_w, canvas_h / img_h)
            
            zoom = getattr(self, "zoom_factor", 1.0)
            new_w = max(int(img_w * ratio * zoom) - 10, 10)
            new_h = max(int(img_h * ratio * zoom) - 10, 10)
            
            # Resize ảnh dùng Lanczos filter
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Chuyển đổi sang ImageTk.PhotoImage để vẽ lên Canvas
            from PIL import ImageTk
            self.ctk_preview_image = ImageTk.PhotoImage(img_resized)
            
            # Clear canvas and draw new image
            self.canvas.delete("all")
            
            # Căn giữa ảnh trên canvas nếu ảnh nhỏ hơn vùng hiển thị
            x_pos = max(0, (canvas_w - new_w) / 2)
            y_pos = max(0, (canvas_h - new_h) / 2)
            
            self.canvas.create_image(x_pos, y_pos, anchor="nw", image=self.ctk_preview_image)
            
            # Cấu hình lại vùng cuộn để thanh cuộn hoạt động chính xác
            scroll_w = max(canvas_w, new_w + x_pos)
            scroll_h = max(canvas_h, new_h + y_pos)
            self.canvas.configure(scrollregion=(0, 0, scroll_w, scroll_h))
            
        except Exception as e:
            print(f"[ERROR] Lỗi khi tạo ảnh xem trước: {str(e)}")
            self.ctk_preview_image = None
            self.canvas.delete("all")
            self.canvas.create_text(
                canvas_w / 2, canvas_h / 2,
                text=f"Lỗi khi hiển thị file xem trước:\n{str(e)}",
                font=("Segoe UI", 11),
                fill="red",
                tags="placeholder"
            )
            self.canvas.configure(scrollregion=(0, 0, canvas_w, canvas_h))

    def _zoom_in(self):
        if not hasattr(self, "zoom_factor"):
            self.zoom_factor = 1.0
        self.zoom_factor = min(self.zoom_factor * 1.2, 5.0)
        self.lbl_zoom_val.configure(text=f"{int(self.zoom_factor * 100)}%")
        self._render_preview()

    def _zoom_out(self):
        if not hasattr(self, "zoom_factor"):
            self.zoom_factor = 1.0
        self.zoom_factor = max(self.zoom_factor / 1.2, 0.2)
        self.lbl_zoom_val.configure(text=f"{int(self.zoom_factor * 100)}%")
        self._render_preview()

    def _zoom_fit(self):
        self.zoom_factor = 1.0
        self.lbl_zoom_val.configure(text="100%")
        self._render_preview()

    def _on_canvas_resize(self, event):
        """Căn giữa lại nhãn placeholder khi canvas thay đổi kích thước."""
        canvas_w = event.width
        canvas_h = event.height
        placeholders = self.canvas.find_withtag("placeholder")
        for item in placeholders:
            self.canvas.coords(item, canvas_w / 2, canvas_h / 2)

    def _on_table_row_double_click(self, event):
        """Mở popup CTkToplevel để chỉnh sửa đồng thời Loại chi phí và Số tiền khi double-click."""
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        # Tìm dữ liệu gốc trong mảng để sửa
        selected_data = None
        for res in self.scanned_results:
            if res.get("row_id") == item_id:
                selected_data = res
                break

        if not selected_data:
            return

        # Khởi chạy popup CTkToplevel để sửa
        EditDialog(
            parent=self,
            fee_type=selected_data["fee_type"],
            amount=selected_data["amount"],
            callback=lambda new_fee, new_amount: self._update_row_data(item_id, selected_data, new_fee, new_amount)
        )

    def _on_edit_click(self):
        """Mở popup CTkToplevel để chỉnh sửa khi chọn dòng và click nút Sửa."""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một dòng trên bảng để sửa!")
            return
            
        item_id = selected_items[0]
        
        # Tìm dữ liệu gốc trong mảng để sửa
        selected_data = None
        for res in self.scanned_results:
            if res.get("row_id") == item_id:
                selected_data = res
                break
                
        if not selected_data:
            return
            
        # Khởi chạy popup CTkToplevel để sửa
        EditDialog(
            parent=self,
            fee_type=selected_data["fee_type"],
            amount=selected_data["amount"],
            callback=lambda new_fee, new_amount: self._update_row_data(item_id, selected_data, new_fee, new_amount)
        )

    def _update_row_data(self, item_id, data_item, new_fee, new_amount):
        """Cập nhật dữ liệu chỉnh sửa vào bảng kết quả và mảng lưu trữ bộ nhớ."""
        # 1. Cập nhật trong bộ nhớ
        data_item["fee_type"] = new_fee
        data_item["amount"] = new_amount

        # 2. Cập nhật trên bảng Treeview
        # Định dạng hiển thị doc_key
        file_path = data_item.get("file_path", "")
        ext = os.path.splitext(file_path)[1].lower()
        key_val = data_item.get("document_key", "")
        doc_key_display = ""
        
        if ext in (".jpg", ".jpeg", ".png"):
            doc_key_display = "Ảnh"
        elif key_val:
            if key_val.startswith("LO_"):
                doc_key_display = f"Lô: {key_val[3:]}"
            elif key_val.startswith("HD_"):
                doc_key_display = f"HĐ: {key_val[3:]}"
            elif key_val.startswith("GD_"):
                doc_key_display = f"GD: {key_val[3:]}"
            else:
                doc_key_display = key_val

        self.tree.item(item_id, values=(
            doc_key_display,
            data_item["container_id"], 
            new_fee, 
            f"{new_amount:,}"
        ))
        print(f"[UI] Đã chỉnh sửa thành công: Cont={data_item['container_id']}, Phí={new_fee}, Tiền={new_amount:,}")

    def _on_export_excel(self):
        """Kết xuất dữ liệu từ bảng Treeview sang định dạng Excel (.xlsx) qua Pandas."""
        if not self.scanned_results:
            messagebox.showwarning("Cảnh báo", "Không có dữ liệu đối soát nào để xuất!")
            return

        # Yêu cầu người dùng chọn nơi lưu file Excel
        save_path = filedialog.asksaveasfilename(
            title="Lưu file Excel kết quả đối soát",
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not save_path:
            return

        print(f"[EXPORT] Đang kết xuất dữ liệu sang: {save_path}")

        try:
            # Chuẩn bị dữ liệu bảng
            data_list = []
            for idx, res in enumerate(self.scanned_results, 1):
                # Định dạng hiển thị doc_key
                file_path = res.get("file_path", "")
                ext = os.path.splitext(file_path)[1].lower()
                key_val = res.get("document_key", "")
                doc_key_display = ""
                
                if ext in (".jpg", ".jpeg", ".png"):
                    doc_key_display = "Ảnh"
                elif key_val:
                    if key_val.startswith("LO_"):
                        doc_key_display = f"Lô: {key_val[3:]}"
                    elif key_val.startswith("HD_"):
                        doc_key_display = f"HĐ: {key_val[3:]}"
                    elif key_val.startswith("GD_"):
                        doc_key_display = f"GD: {key_val[3:]}"
                    else:
                        doc_key_display = key_val

                data_list.append({
                    "STT": idx,
                    "Số HĐ / Mã lô": doc_key_display,
                    "Số Container": res["container_id"],
                    "Loại chi phí": res["fee_type"],
                    "Số tiền (VNĐ)": res["amount"]
                })

            # Đẩy dữ liệu vào Pandas DataFrame
            df = pd.DataFrame(data_list)

            # Ghi file Excel dùng openpyxl
            df.to_excel(save_path, index=False, sheet_name="Đối soát chi phí")
            
            messagebox.showinfo("Thành công", f"Đã xuất file Excel đối soát chi phí thành công!\nĐường dẫn: {save_path}")
            print(f"[EXPORT] Xuất Excel thành công tại: {save_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể xuất file Excel:\n{str(e)}")
            print(f"[EXPORT] Lỗi xuất Excel: {str(e)}")


if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
