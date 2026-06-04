# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Tìm đường dẫn tuyệt đối của thư mục cài đặt customtkinter để sao chép assets (themes, icons) vào thư mục đóng gói
try:
    import customtkinter
    customtkinter_dir = os.path.dirname(customtkinter.__file__)
    customtkinter_datas = (os.path.join(customtkinter_dir, "assets"), "customtkinter/assets")
    print(f"[SPEC] Tim thay customtkinter tai: {customtkinter_datas[0]}")
except ImportError:
    customtkinter_datas = []
    print("[SPEC] Canh bao: Khong tim thay customtkinter de dong goi tu dong!")

# Gom cac file datas (bao gồm assets của customtkinter)
added_datas = []
if customtkinter_datas:
    added_datas.append(customtkinter_datas)

# Khai báo Analysis: nạp main.py làm điểm chạy chính
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_datas,
    hiddenimports=[
        'paddleocr',
        'paddlepaddle',
        'pdfplumber',
        'fitz',
        'pandas',
        'openpyxl',
        'PIL',
        'PIL.Image',
        'PIL._imagingtk',
        'customtkinter',
        'tkinter',
        'openpyxl.descriptors.excel',
        'openpyxl.xml'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure, 
    a.zipped_data, 
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SmartICDST_OCR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Giữ lại Console Window để hiển thị tiến trình và log OCR cho người dùng dễ theo dõi
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SmartICDST_OCR',
)
