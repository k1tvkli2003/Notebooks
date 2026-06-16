"""
PDF Batch Extractor (AvalAI OCR) - Setup Module
راه‌اندازی اولیه، API Key، مدل OCR، و UI انتخاب فایل
"""

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
# AvalAI OCR Configuration
# ====================================
AVALAI_API_KEY = "aa-Lj6XkFpMKukoR4OSK8aCC38Ubj6ACCthvsnieV0gxMWIuLyG"
AVALAI_BASE_URL = "https://api.avalai.ir/v1"
AVALAI_USER_API_URL = "https://api.avalai.ir/user/v1"  # برای دریافت اعتبار باقی‌مانده

# مدل‌های OCR قابل انتخاب
OCR_MODELS = {
    "gemini-flash-lite-latest": {
        "name": "Gemini Flash Lite",
        "description": "مدل سریع و سبک گوگل - ویژن",
        "api_type": "chat",  # Uses /v1/chat/completions (standard vision)
        "supports_prompt": True,
    },
    "gpt-5-nano": {
        "name": "GPT-5 Nano",
        "description": "مدل سریع و ارزان OpenAI - ویژن",
        "api_type": "chat",  # Uses /v1/chat/completions (standard vision)
        "supports_prompt": True,
    },
}

# مدل انتخاب شده (پیش‌فرض: gemini-flash-lite-latest)
selected_model = "gemini-flash-lite-latest"

# ====================================
# Load OCR Prompts from PROMPT-MODULES
# ====================================
def load_ocr_prompts():
    """بارگذاری تمام پرامپت‌ها از پوشه PROMPT-MODULES"""
    prompt_dir = Path(__file__).parent / "PROMPT-MODULES"
    if not prompt_dir.exists():
        print("⚠️ پوشه PROMPT-MODULES یافت نشد!")
        return "Extract all text from this image precisely."
    
    combined_prompt = ""
    prompt_files = sorted(prompt_dir.glob("*.md"))
    prompt_files = [f for f in prompt_files if f.name != "README.md"]
    
    for pf in prompt_files:
        try:
            content = pf.read_text(encoding="utf-8")
            combined_prompt += content + "\n\n"
            print(f"   📄 Loaded: {pf.name}")
        except Exception as e:
            print(f"   ⚠️ Error loading {pf.name}: {e}")
    
    if not combined_prompt.strip():
        return "Extract all text from this image precisely."
    
    return combined_prompt.strip()

# پرامپت ترکیبی OCR
OCR_PROMPT = ""

# ====================================
# Global Variables
# ====================================
setup_errors = []
selected_pdf_files = []
pdf_files = []
selected_formats = ["md"]  # فرمت‌های خروجی پیش‌فرض
extract_images = True  # استخراج تصاویر از PDF (پیش‌فرض فعال)

# ====================================
# API Test
# ====================================
def test_api_key():
    """تست اتصال به AvalAI API"""
    import httpx
    try:
        http = httpx.Client(timeout=30)
        resp = http.get(
            f"{AVALAI_BASE_URL}/models",
            headers={"Authorization": f"Bearer {AVALAI_API_KEY}"}
        )
        if resp.status_code == 200:
            data = resp.json()
            available = [m["id"] for m in data.get("data", []) if m["id"] in OCR_MODELS]
            return True, available
        else:
            return False, f"Status {resp.status_code}"
    except Exception as e:
        return False, str(e)

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
                        if line and line.lower().endswith('.pdf'):
                            line = line.lstrip('- *•→►▪▫◦').strip()
                            pdf_path = Path(line)
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

btn_select_files.on_click(select_files_dialog)
btn_select_folder.on_click(select_folder_dialog)
btn_load_md.on_click(load_md_dialog)
btn_clear.on_click(clear_files_dialog)

buttons_box = widgets.HBox([btn_select_files, btn_select_folder, btn_load_md, btn_clear])
buttons_box.layout.width = '100%'

# ====================================
# Model Selection Widget
# ====================================
model_dropdown = widgets.Dropdown(
    options=[(info["name"], model_id) for model_id, info in OCR_MODELS.items()],
    value="gemini-flash-lite-latest",
    description='🤖 مدل OCR:',
    style={'description_width': 'initial'},
    layout=widgets.Layout(width='400px')
)

model_info_html = widgets.HTML()

def update_model_info(change=None):
    """به‌روزرسانی اطلاعات مدل انتخاب شده"""
    global selected_model
    selected_model = model_dropdown.value
    info = OCR_MODELS[selected_model]
    model_info_html.value = f'''
    <div style="font-family: monospace; background: #e7f3ff; padding: 10px; border-radius: 8px; margin-top: 5px; border-left: 4px solid #007bff;">
        <strong>{info["name"]}</strong><br>
        <small style="color: #666;">{info["description"]}</small><br>
        <small>API Type: <code>{info["api_type"]}</code> | Prompt: {"✅" if info["supports_prompt"] else "❌"}</small>
    </div>'''

model_dropdown.observe(update_model_info, names='value')
update_model_info()

model_box = widgets.VBox([model_dropdown, model_info_html])

# ====================================
# Output Format Selector Widget
# ====================================
# فرمت خروجی ثابت: فقط Markdown
selected_formats = ["md"]

# ====================================
# Image Extraction Checkbox
# ====================================
chk_extract_images = widgets.Checkbox(
    value=True, description='🖼️  استخراج تصاویر از PDF',
    indent=False,
    layout=widgets.Layout(width='300px')
)
img_info_html = widgets.HTML()

def update_extract_images(change=None):
    """به‌روزرسانی وضعیت استخراج تصاویر"""
    global extract_images
    extract_images = chk_extract_images.value
    if extract_images:
        img_info_html.value = '''
        <div style="font-family: monospace; background: #fff3e0; padding: 8px; border-radius: 6px; margin-top: 5px; border-left: 4px solid #ff9800;">
            <small>🖼️  تصاویر از PDF استخراج شده و در پوشه <code>images_*</code> ذخیره می‌شوند</small>
        </div>'''
    else:
        img_info_html.value = '''
        <div style="font-family: monospace; background: #f0f0f0; padding: 8px; border-radius: 6px; margin-top: 5px;">
            <small>🖼️  استخراج تصاویر غیرفعال</small>
        </div>'''

chk_extract_images.observe(update_extract_images, names='value')
update_extract_images()

image_box = widgets.VBox([chk_extract_images, img_info_html])

# ====================================
# Auto-execute setup when imported
# ====================================
def _initialize():
    """تابع راه‌اندازی خودکار"""
    global pdf_files, OCR_PROMPT
    
    print("="*80)
    print("🚀 شروع راه‌اندازی PDF Batch Extractor (AvalAI OCR)")
    print("="*80)
    print()
    
    # تست API
    print("🔄 در حال تست اتصال به AvalAI...")
    is_valid, result = test_api_key()
    if is_valid:
        print(f"✅ اتصال برقرار! مدل‌های فعال: {', '.join(result)}")
    else:
        print(f"⚠️ مشکل اتصال: {result}")
        setup_errors.append(f"API connection: {result}")
    
    # بارگذاری پرامپت‌ها
    print("\n📝 بارگذاری پرامپت‌های OCR از PROMPT-MODULES:")
    OCR_PROMPT = load_ocr_prompts()
    print(f"   ✅ پرامپت ترکیبی: {len(OCR_PROMPT)} کاراکتر")
    
    print()
    print("="*80)
    print("✅ راه‌اندازی کامل شد!")
    print("🤖 ابتدا مدل OCR را انتخاب کنید، سپس فرمت خروجی و فایل‌ها:")
    print("="*80)
    print()
    
    # نمایش UI - مدل اول، سپس فرمت، سپس تصاویر، سپس فایل‌ها
    display(model_box)
    print()
    display(image_box)
    print()
    display(buttons_box)
    display(status_html)
    
    if setup_errors:
        error_html = '<div style="background: #f8d7da; padding: 15px; border-radius: 10px; margin-top: 15px;">'
        error_html += '<h4 style="color: #721c24; margin: 0 0 10px 0;">⚠️ لاگ خطاها:</h4>'
        for err in setup_errors:
            error_html += f'<div style="color: #721c24; margin: 5px 0; padding: 8px; background: #f5c6cb; border-radius: 5px;">{err}</div>'
        error_html += '</div>'
        display(HTML(error_html))
    
    pdf_files = selected_pdf_files

_initialize()
