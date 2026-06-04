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
        """Khởi tạo khung Split-View ở giữa chia tỉ lệ 60% trái (Treeview) và 40% phải (Xem ảnh)."""
        split_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        split_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        split_frame.grid_columnconfigure(0, weight=6)
        split_frame.grid_columnconfigure(1, weight=4)
        split_frame.grid_rowconfigure(0, weight=1)

        # PANEL TRÁI (60%): ttk.Treeview hiển thị dạng Monospace Consolas
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
                        borderwidth=0)
        
        # Định nghĩa kiểu chữ Consolas cho dữ liệu bảng để căn dòng đẹp mắt
        style.configure("Treeview.Cell", font=("Consolas", 11))
        
        style.configure("Treeview.Heading", 
                        background=header_bg,
                        foreground=header_fg,
                        font=("Segoe UI", 12, "bold"),
                        relief="flat")
        
        style.map('Treeview', background=[('selected', '#1f538d')])

        cols = ("container_id", "fee_type", "amount")
        self.tree = ttk.Treeview(left_panel, columns=cols, show="headings", style="Treeview")
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=10)

        self.tree.heading("container_id", text="Số Container")
        self.tree.heading("fee_type", text="Loại chi phí")
        self.tree.heading("amount", text="Số tiền (VNĐ)")

        self.tree.column("container_id", width=180, anchor="center")
        self.tree.column("fee_type", width=180, anchor="center")
        self.tree.column("amount", width=150, anchor="e")

        scrollbar = customtkinter.CTkScrollbar(left_panel, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=10)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_table_row_select)
        self.tree.bind("<Double-1>", self._on_table_row_double_click)

        # PANEL PHẢI (40%): Khung xem trước hình ảnh/PDF bằng Label chứa CTkImage
        self.right_panel = customtkinter.CTkFrame(split_frame)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_columnconfigure(0, weight=1)

        self.lbl_preview = customtkinter.CTkLabel(
            self.right_panel, 
            text="Chọn dòng trong bảng để xem ảnh/PDF",
            font=("Segoe UI", 12, "italic"),
            text_color="gray"
        )
        self.lbl_preview.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

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
        bottom_frame.grid_columnconfigure(3, weight=1)

        self.btn_scan = customtkinter.CTkButton(
            bottom_frame,
            text="🔍 Quét thư mục",
            font=("Segoe UI", 13, "bold"),
            width=150,
            command=self._on_scan_directory
        )
        self.btn_scan.grid(row=0, column=1, padx=15, pady=15)

        self.btn_export = customtkinter.CTkButton(
            bottom_frame,
            text="📥 Xuất Excel",
            font=("Segoe UI", 13, "bold"),
            width=150,
            fg_color="#27ae60",
            hover_color="#219653",
            command=self._on_export_excel
        )
        self.btn_export.grid(row=0, column=2, padx=15, pady=15)

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

        # Hiển thị thanh tiến độ
        self.progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.progress_bar.set(0)
        self.lbl_progress.configure(text="Bắt đầu chuẩn bị quét...")

        # Vô hiệu hóa các nút điều khiển để tránh click nhiều lần khi đang chạy
        self.btn_scan.configure(state="disabled")
        self.btn_export.configure(state="disabled")

        # Xóa dữ liệu cũ trên bảng và trong bộ nhớ
        self.tree.delete(*self.tree.get_children())
        self.scanned_results = []
        self.lbl_preview.configure(image=None, text="Chọn dòng trong bảng để xem ảnh/PDF")

        # Bắt đầu đa luồng
        scan_thread = threading.Thread(target=self._scan_worker, args=(path,), daemon=True)
        scan_thread.start()

    def _scan_worker(self, path):
        """Hàm chạy nền trong thread riêng để quét thư mục."""
        from core.batch_scanner import BatchScanner
        
        # Khởi tạo batch scanner
        scanner = BatchScanner()

        def progress_update(current, total, file_name):
            # Sử dụng self.after để cập nhật giao diện Tkinter an toàn từ Thread nền
            self.after(0, lambda: self._update_progress_ui(current, total, file_name))

        try:
            results = scanner.scan_directory(path, progress_callback=progress_update)
            # Hoàn tất quét, đẩy kết quả về luồng chính
            self.after(0, lambda: self._on_scan_completed(results))
        except Exception as e:
            self.after(0, lambda: self._on_scan_failed(str(e)))

    def _update_progress_ui(self, current, total, file_name):
        """Cập nhật giao diện thanh tiến trình."""
        ratio = current / total
        self.progress_bar.set(ratio)
        self.lbl_progress.configure(text=f"Đang xử lý [{current}/{total}]: {file_name}")

    def _on_scan_completed(self, results):
        """Xử lý giao diện khi hoàn tất quét thư mục thành công."""
        self.progress_frame.grid_remove()  # Ẩn thanh tiến trình
        self.btn_scan.configure(state="normal")
        self.btn_export.configure(state="normal")

        # Lưu trữ kết quả và hiển thị lên bảng kết quả
        self.scanned_results = results
        for idx, res in enumerate(self.scanned_results):
            # Chèn dòng vào Treeview
            item_id = self.tree.insert("", "end", values=(
                res["container_id"], 
                res["fee_type"], 
                f"{res['amount']:,}"
            ))
            # Gắn ID hàng vào data để quản lý chỉnh sửa
            res["row_id"] = item_id

        total_scanned = len(results)
        messagebox.showinfo("Hoàn tất", f"Đã quét xong thư mục đối soát!\nTổng số bản ghi trích xuất: {total_scanned} dòng.")

    def _on_scan_failed(self, error_msg):
        """Xử lý giao diện khi xảy ra lỗi trong quá trình quét nền."""
        self.progress_frame.grid_remove()
        self.btn_scan.configure(state="normal")
        self.btn_export.configure(state="normal")
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
        if not os.path.exists(file_path):
            self.lbl_preview.configure(image=None, text="File gốc đã bị xóa hoặc di chuyển!")
            return

        # Hiển thị ảnh xem trước
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            # 1. Trích xuất ảnh xem trước (PIL Image)
            if ext == ".pdf":
                # Render trang đầu tiên của file PDF thành ảnh dùng PyMuPDF (fitz)
                doc = fitz.open(file_path)
                page = doc.load_page(0)
                # Render ở độ phân giải trung bình (dpi=100) để đảm bảo tốc độ preview nhanh
                pix = page.get_pixmap(dpi=100)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                doc.close()
            else:
                # File hình ảnh thông thường
                img = Image.open(file_path)

            # 2. Thay đổi kích thước giữ nguyên tỷ lệ ảnh vừa khớp với panel
            panel_w = self.lbl_preview.winfo_width()
            panel_h = self.lbl_preview.winfo_height()
            
            # Dự phòng kích thước nếu cửa sổ chưa vẽ xong
            if panel_w < 20 or panel_h < 20:
                panel_w, panel_h = 420, 550

            img_w, img_h = img.size
            ratio = min(panel_w / img_w, panel_h / img_h)
            new_w = max(int(img_w * ratio) - 10, 10)
            new_h = max(int(img_h * ratio) - 10, 10)

            # Resize ảnh dùng Lanczos filter
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Chuyển đổi sang CTkImage để hiển thị
            ctk_img = customtkinter.CTkImage(
                light_image=img_resized, 
                dark_image=img_resized, 
                size=(new_w, new_h)
            )
            
            self.lbl_preview.configure(image=ctk_img, text="")
        except Exception as e:
            print(f"[ERROR] Lỗi khi tạo ảnh xem trước: {str(e)}")
            self.lbl_preview.configure(image=None, text=f"Lỗi khi hiển thị file xem trước:\n{str(e)}")

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

    def _update_row_data(self, item_id, data_item, new_fee, new_amount):
        """Cập nhật dữ liệu chỉnh sửa vào bảng kết quả và mảng lưu trữ bộ nhớ."""
        # 1. Cập nhật trong bộ nhớ
        data_item["fee_type"] = new_fee
        data_item["amount"] = new_amount

        # 2. Cập nhật trên bảng Treeview
        self.tree.item(item_id, values=(
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
                data_list.append({
                    "STT": idx,
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
