"""
PDF Batch Extractor - Setup Module
راه‌اندازی اولیه، API Keys، GPT-5، و UI انتخاب فایل
"""

import os
import base64
import time
import asyncio
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from IPython.display import display, HTML, clear_output
from PyPDF2 import PdfReader
import ipywidgets as widgets
from threading import Thread

# ====================================
# Proxy Configuration (V2Ray)
# ====================================
# تنظیم پروکسی برای عبور از محدودیت‌ها
os.environ["HTTP_PROXY"] = "http://127.0.0.1:10808"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:10808"
os.environ["ALL_PROXY"] = "socks5://127.0.0.1:10808"
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
print("🔒 Proxy configured: 127.0.0.1:10808")

from datalab_sdk import AsyncDatalabClient
from datalab_sdk.models import ConvertOptions
from openai import AsyncOpenAI

# Import API configuration
from api_config import (
    DATALAB_API_KEYS,
    GITHUB_TOKEN,
    GITHUB_ENDPOINT,
    GPT5_MODEL,
    CORRECTION_PROMPT,
    load_api_keys_from_md
)

# ====================================
# Initialize GPT-5 Client
# ====================================
llm_client = AsyncOpenAI(
    base_url=GITHUB_ENDPOINT,
    api_key=GITHUB_TOKEN
)

# ====================================
# Processing Options
# ====================================
USE_LLM = True
EXTRACT_IMAGES = True
FORMAT_LINES = True
PAGINATE = False
OUTPUT_FORMAT = "markdown"

options = ConvertOptions(
    output_format=OUTPUT_FORMAT,
    disable_image_extraction=not EXTRACT_IMAGES,
    use_llm=USE_LLM,
    paginate=PAGINATE,
    force_ocr=False,
    format_lines=FORMAT_LINES,
    strip_existing_ocr=False
)

# ====================================
# Global Variables
# ====================================
setup_errors = []
selected_pdf_files = []
pdf_files = []
clients = []

# ====================================
# API Client Setup
# ====================================
async def test_api_key(client, client_num, api_key):
    """تست یک API key با یک PDF کوچک"""
    try:
        test_pdf_path = f"test_datalab_{client_num}.pdf"
        pdf_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 100 700 Td (Test Page) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000317 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n410\n%%EOF"
        
        with open(test_pdf_path, 'wb') as f:
            f.write(pdf_data)
        
        result = await client.convert(test_pdf_path, options=options)
        
        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)
        
        return True, None
    except Exception as e:
        error_msg = f"Client {client_num} (API: {api_key[:20]}...): {str(e)}"
        return False, error_msg

async def setup_clients():
    """راه‌اندازی clients با تست API keys"""
    global clients, setup_errors
    
    # بارگذاری API keys از فایل MD (یا استفاده از پیش‌فرض)
    API_KEYS = load_api_keys_from_md()
    
    print("🔄 در حال تست API Keys...")
    valid_clients = []
    valid_keys = []
    
    for i, api_key in enumerate(API_KEYS, 1):
        try:
            client = AsyncDatalabClient(api_key=api_key)
            is_valid, error = await test_api_key(client, i, api_key)
            
            if is_valid:
                valid_clients.append(client)
                valid_keys.append(api_key)
                print(f"✅ Client {i}: موفق")
            else:
                setup_errors.append(error)
                print(f"❌ Client {i}: خطا")
        except Exception as e:
            error_msg = f"Client {i}: {str(e)}"
            setup_errors.append(error_msg)
            print(f"❌ Client {i}: خطا")
    
    clients = valid_clients
    print(f"\n✅ {len(clients)} API Client آماده است!")
    
    if setup_errors:
        print(f"⚠️ {len(setup_errors)} خطا")

# ====================================
# File Selection UI
# ====================================
def get_pdf_info(pdf_path):
    """دریافت تعداد صفحات و حجم فایل"""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            pages = len(reader.pages)
        size_mb = pdf_path.stat().st_size / (1024 * 1024)
        return pages, size_mb
    except:
        return 0, 0

def find_pdfs_in_folder(folder_path):
    """پیدا کردن تمام PDFهای Chapter در یک پوشه"""
    folder = Path(folder_path)
    pdf_files = list(folder.rglob("*.pdf"))
    return [pdf for pdf in pdf_files if "Chapter" in pdf.name]

status_html = widgets.HTML(
    value='<div style="font-family: monospace; background: #f0f0f0; padding: 15px; border-radius: 10px; margin-top: 10px;"><strong>📋 هیچ فایلی انتخاب نشده</strong></div>'
)

def update_status_widget():
    """به‌روزرسانی widget نمایش وضعیت"""
    global status_html
    
    if not selected_pdf_files:
        status_html.value = '<div style="font-family: monospace; background: #f0f0f0; padding: 15px; border-radius: 10px;"><strong>📋 هیچ فایلی انتخاب نشده</strong></div>'
        return
    
    total_size = sum(pdf.stat().st_size for pdf in selected_pdf_files) / (1024 * 1024)
    
    html = '<div style="font-family: monospace; background: #d4edda; padding: 15px; border-radius: 10px;">'
    html += f'<strong style="color: #155724;">✅ {len(selected_pdf_files)} فایل انتخاب شده</strong><br>'
    html += f'💾 حجم کل: {total_size:.2f} MB<br><br>'
    
    if len(selected_pdf_files) <= 20:
        html += '<details><summary style="cursor: pointer; color: #0066cc;"><strong>📂 لیست فایل‌ها (کلیک کنید)</strong></summary>'
        html += '<div style="margin-top: 10px; max-height: 300px; overflow-y: auto; background: white; padding: 10px; border-radius: 5px;">'
        for i, pdf in enumerate(selected_pdf_files, 1):
            pages, size = get_pdf_info(pdf)
            html += f'<div style="padding: 3px 0; border-bottom: 1px solid #eee;">'
            html += f'{i}. <strong>{pdf.name}</strong><br>'
            html += f'   <small style="color: #666;">📄 {pages} صفحه | 💾 {size:.1f} MB</small>'
            html += '</div>'
        html += '</div></details>'
    else:
        html += f'<div style="color: #666;"><small>تعداد زیاد برای نمایش (بیش از 20 فایل)</small></div>'
    
    html += '</div>'
    status_html.value = html

def select_files_dialog(b=None):
    """دیالوگ انتخاب فایل‌ها"""
    def run_dialog():
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        
        files = filedialog.askopenfilenames(
            title="انتخاب فایل‌های PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        root.destroy()
        
        if files:
            selected_pdf_files.clear()
            selected_pdf_files.extend([Path(f) for f in files])
            update_status_widget()
    
    Thread(target=run_dialog, daemon=True).start()

def select_folder_dialog(b=None):
    """دیالوگ انتخاب پوشه"""
    def run_dialog():
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        
        folder = filedialog.askdirectory(title="انتخاب پوشه")
        
        root.destroy()
        
        if folder:
            pdfs = find_pdfs_in_folder(folder)
            selected_pdf_files.clear()
            selected_pdf_files.extend(pdfs)
            update_status_widget()
    
    Thread(target=run_dialog, daemon=True).start()

def load_md_dialog(b=None):
    """بارگذاری لیست PDF ها از فایل MD"""
    def run_dialog():
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        
        # انتخاب فایل MD که حاوی لیست مسیرهای PDF است
        md_file = filedialog.askopenfilename(
            title="انتخاب فایل MD حاوی لیست PDF ها",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        root.destroy()
        
        if md_file:
            try:
                pdf_files_found = []
                with open(md_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # فقط خطوطی که با .pdf تمام می‌شوند
                        if line and line.lower().endswith('.pdf'):
                            # حذف کاراکترهای اضافی مثل - یا * در ابتدای خط
                            line = line.lstrip('- *•→►▪▫◦')
                            line = line.strip()
                            
                            pdf_path = Path(line)
                            # اگر مسیر نسبی است، نسبت به پوشه فایل MD حل می‌شود
                            if not pdf_path.is_absolute():
                                md_parent = Path(md_file).parent
                                pdf_path = (md_parent / pdf_path).resolve()
                            
                            if pdf_path.exists() and pdf_path.suffix.lower() == '.pdf':
                                pdf_files_found.append(pdf_path)
                
                selected_pdf_files.clear()
                selected_pdf_files.extend(pdf_files_found)
                update_status_widget()
                
                if not pdf_files_found:
                    print("⚠️ هیچ مسیر PDF معتبری در فایل یافت نشد!")
                else:
                    print(f"✅ {len(pdf_files_found)} فایل PDF از لیست بارگذاری شد")
                    
            except Exception as e:
                print(f"❌ خطا در خواندن فایل: {str(e)}")
    
    Thread(target=run_dialog, daemon=True).start()

def clear_files_dialog(b=None):
    """پاک کردن لیست فایل‌ها"""
    selected_pdf_files.clear()
    update_status_widget()

# ====================================
# Create UI Buttons
# ====================================
btn_select_files = widgets.Button(
    description='📄 انتخاب فایل‌ها',
    button_style='primary',
    tooltip='انتخاب فایل‌های PDF به صورت جداگانه',
    layout=widgets.Layout(width='auto', height='40px')
)

btn_select_folder = widgets.Button(
    description='📁 انتخاب پوشه',
    button_style='success',
    tooltip='جستجوی خودکار Chapter.pdf در پوشه',
    layout=widgets.Layout(width='auto', height='40px')
)

btn_load_md = widgets.Button(
    description='📝 بارگذاری از MD',
    button_style='info',
    tooltip='بارگذاری لیست PDF ها از فایل MD',
    layout=widgets.Layout(width='auto', height='40px')
)

btn_clear = widgets.Button(
    description='🗑️ پاک کردن',
    button_style='warning',
    tooltip='پاک کردن لیست فایل‌ها',
    layout=widgets.Layout(width='auto', height='40px')
)

# اتصال callbacks
btn_select_files.on_click(select_files_dialog)
btn_select_folder.on_click(select_folder_dialog)
btn_load_md.on_click(load_md_dialog)
btn_clear.on_click(clear_files_dialog)

buttons_box = widgets.HBox([btn_select_files, btn_select_folder, btn_load_md, btn_clear])
buttons_box.layout.width = '100%'

# ====================================
# Auto-execute setup when imported
# ====================================
def _initialize():
    """تابع راه‌اندازی خودکار"""
    global pdf_files
    
    print("="*80)
    print("🚀 شروع راه‌اندازی PDF Batch Extractor...")
    print("="*80)
    print()
    
    # Setup clients
    try:
        # در Jupyter از event loop موجود استفاده می‌کنیم
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # اگر loop نداریم، یکی جدید می‌سازیم
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        import nest_asyncio
        nest_asyncio.apply(loop)
    except ImportError:
        pass

    # اجرا بدون بستن loop
    if loop.is_running():
        # اگر loop در حال اجرا است (Jupyter)
        # به جای asyncio.run (که با ipykernel سازگار نیست)،
        # با کمک nest_asyncio از همان loop استفاده می‌کنیم
        loop.run_until_complete(setup_clients())
    else:
        # اگر loop در حال اجرا نیست
        loop.run_until_complete(setup_clients())
    
    print()
    print("="*80)
    print("✅ راه‌اندازی کامل شد!")
    print("📋 از دکمه‌های زیر برای انتخاب فایل استفاده کنید:")
    print("="*80)
    print()
    
    # نمایش UI
    display(buttons_box)
    display(status_html)
    
    # نمایش خطاها (اگر وجود دارد)
    if setup_errors:
        error_html = '<div style="background: #f8d7da; padding: 15px; border-radius: 10px; margin-top: 15px;">'
        error_html += '<h4 style="color: #721c24; margin: 0 0 10px 0;">⚠️ لاگ خطاها:</h4>'
        for err in setup_errors:
            error_html += f'<div style="color: #721c24; margin: 5px 0; padding: 8px; background: #f5c6cb; border-radius: 5px;">{err}</div>'
        error_html += '</div>'
        display(HTML(error_html))
    
    # تنظیم pdf_files
    pdf_files = selected_pdf_files

# اجرای خودکار
_initialize()
