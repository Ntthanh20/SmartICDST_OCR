# -*- coding: utf-8 -*-

import os
import sys

# Thiết lập stdout sử dụng mã hóa UTF-8 để tránh các lỗi in console trên Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Đảm bảo Python có thể import được các package nội bộ (core, gui, config) từ thư mục gốc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gui.app import MainApp

def main():
    """Hàm chạy chính khởi tạo giao diện ứng dụng."""
    print("[SYSTEM] Đang khởi chạy SmartICDST_OCR v2.0...")
    app = MainApp()
    app.mainloop()

if __name__ == "__main__":
    main()
