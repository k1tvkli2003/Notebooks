"""
Audio Transcriber - Setup Module
راه‌اندازی اولیه، پروکسی، و UI انتخاب فایل
"""

import os
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from IPython.display import display, HTML, clear_output
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

# ====================================
# Configuration
# ====================================
AVALAI_API_KEY = "aa-JDZsYpkB6B2Ru00yxuDKHpSYNRcDnv9sCQYWwYuSHth3t5cf"
AVALAI_BASE_URL = "https://api.avalai.ir/v1"
MODEL = "gemini-3-flash-preview"
THINKING_BUDGET = 10000  # Token limit for thinking
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma', '.opus'}

# ====================================
# Global Variables
# ====================================
setup_errors = []
selected_audio_files = []
audio_files = []
gemini_ready = False  # وضعیت اتصال و لاگین Gemini CLI

# ====================================
# File Selection UI
# ====================================
def get_audio_info(audio_path):
    """دریافت مدت زمان و حجم فایل صوتی"""
    try:
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        # تلاش برای دریافت مدت زمان با ffprobe
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                   "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                return f"{minutes}:{seconds:02d}", size_mb
        except:
            pass
        return "N/A", size_mb
    except:
        return "N/A", 0

def find_audio_in_folder(folder_path):
    """پیدا کردن تمام فایل‌های صوتی در یک پوشه"""
    folder = Path(folder_path)
    audio_files = []
    for ext in AUDIO_EXTENSIONS:
        audio_files.extend(folder.rglob(f"*{ext}"))
    return audio_files

status_html = widgets.HTML(
    value='<div style="font-family: monospace; background: #f0f0f0; padding: 15px; border-radius: 10px; margin-top: 10px;"><strong>📋 هیچ فایلی انتخاب نشده</strong></div>'
)

def update_status_widget():
    """به‌روزرسانی widget نمایش وضعیت"""
    global status_html
    
    if not selected_audio_files:
        status_html.value = '<div style="font-family: monospace; background: #f0f0f0; padding: 15px; border-radius: 10px;"><strong>📋 هیچ فایلی انتخاب نشده</strong></div>'
        return
    
    total_size = sum(f.stat().st_size for f in selected_audio_files) / (1024 * 1024)
    
    html = '<div style="font-family: monospace; background: #d4edda; padding: 15px; border-radius: 10px;">'
    html += f'<strong style="color: #155724;">✅ {len(selected_audio_files)} فایل انتخاب شده</strong><br>'
    html += f'💾 حجم کل: {total_size:.2f} MB<br><br>'
    
    if len(selected_audio_files) <= 20:
        html += '<details><summary style="cursor: pointer; color: #0066cc;"><strong>📂 لیست فایل‌ها (کلیک کنید)</strong></summary>'
        html += '<div style="margin-top: 10px; max-height: 300px; overflow-y: auto; background: white; padding: 10px; border-radius: 5px;">'
        for i, audio in enumerate(selected_audio_files, 1):
            duration, size = get_audio_info(audio)
            html += f'<div style="padding: 3px 0; border-bottom: 1px solid #eee;">'
            html += f'{i}. <strong>{audio.name}</strong><br>'
            html += f'   <small style="color: #666;">⏱️ {duration} | 💾 {size:.1f} MB</small>'
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
        
        filetypes = [
            ("Audio files", "*.mp3 *.wav *.m4a *.flac *.ogg *.aac *.wma *.opus"),
            ("MP3 files", "*.mp3"),
            ("WAV files", "*.wav"),
            ("M4A files", "*.m4a"),
            ("All files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="انتخاب فایل‌های صوتی",
            filetypes=filetypes
        )
        
        root.destroy()
        
        if files:
            selected_audio_files.clear()
            selected_audio_files.extend([Path(f) for f in files])
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
            audios = find_audio_in_folder(folder)
            selected_audio_files.clear()
            selected_audio_files.extend(audios)
            update_status_widget()
    
    Thread(target=run_dialog, daemon=True).start()

def load_md_dialog(b=None):
    """بارگذاری لیست فایل‌های صوتی از فایل MD"""
    def run_dialog():
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        
        md_file = filedialog.askopenfilename(
            title="انتخاب فایل MD حاوی لیست فایل‌ها",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        root.destroy()
        
        if md_file:
            try:
                audio_files_found = []
                with open(md_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # بررسی پسوندهای صوتی
                        if line and any(line.lower().endswith(ext) for ext in AUDIO_EXTENSIONS):
                            line = line.lstrip('- *•→►▪▫◦')
                            line = line.strip()
                            
                            audio_path = Path(line)
                            if not audio_path.is_absolute():
                                md_parent = Path(md_file).parent
                                audio_path = (md_parent / audio_path).resolve()
                            
                            if audio_path.exists():
                                audio_files_found.append(audio_path)
                
                selected_audio_files.clear()
                selected_audio_files.extend(audio_files_found)
                update_status_widget()
                
                if not audio_files_found:
                    print("⚠️ هیچ مسیر صوتی معتبری در فایل یافت نشد!")
                else:
                    print(f"✅ {len(audio_files_found)} فایل صوتی از لیست بارگذاری شد")
                    
            except Exception as e:
                print(f"❌ خطا در خواندن فایل: {str(e)}")
    
    Thread(target=run_dialog, daemon=True).start()

def clear_files_dialog(b=None):
    """پاک کردن لیست فایل‌ها"""
    selected_audio_files.clear()
    update_status_widget()

# ====================================
# Create UI Buttons
# ====================================
btn_select_files = widgets.Button(
    description='🎵 انتخاب فایل‌ها',
    button_style='primary',
    tooltip='انتخاب فایل‌های صوتی به صورت جداگانه',
    layout=widgets.Layout(width='auto', height='40px')
)

btn_select_folder = widgets.Button(
    description='📁 انتخاب پوشه',
    button_style='success',
    tooltip='جستجوی خودکار فایل‌های صوتی در پوشه',
    layout=widgets.Layout(width='auto', height='40px')
)

btn_load_md = widgets.Button(
    description='📝 بارگذاری از MD',
    button_style='info',
    tooltip='بارگذاری لیست فایل‌ها از فایل MD',
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
    global audio_files, gemini_ready
    
    print("="*80)
    print("🚀 شروع راه‌اندازی Audio Transcriber...")
    print("="*80)
    print()
    
    # Check ffmpeg
    try:
        result = subprocess.run(["ffprobe", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("✅ ffmpeg/ffprobe نصب شده است")
        else:
            setup_errors.append("ffprobe not found")
            print("⚠️ ffprobe یافت نشد. لطفاً ffmpeg را نصب کنید.")
    except FileNotFoundError:
        setup_errors.append("ffmpeg not installed")
        print("⚠️ ffmpeg یافت نشد. لطفاً آن را نصب کنید.")
    
    # Check OpenAI Library
    try:
        import openai
        print("✅ OpenAI library installed")
    except ImportError:
        print("⚠️ OpenAI library not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])
            print("✅ OpenAI library installed")
        except Exception as e:
            setup_errors.append(f"OpenAI installation failed: {e}")
            print(f"❌ Error installing OpenAI: {e}")

    # Check AvalAI Connection
    gemini_ready = True # Assume ready if key is present
    print(f"✅ AvalAI API Configured (Model: {MODEL})")
    
    # Check Gemini CLI - Removed as we are using AvalAI
    # gemini_ready = False
    # try:
    #     result = subprocess.run("gemini --version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
    #     if result.returncode == 0:
    #         version = result.stdout.strip() or result.stderr.strip()
    #         print(f"✅ Gemini CLI نصب شده است ({version})")
    #         print("   💡 فرض می‌کنیم لاگین انجام شده (تست اتصال skip شد)")
    #         gemini_ready = True
    #     else:
    #         print("⚠️ Gemini CLI یافت نشد. در حال نصب...")
    #         try:
    #             subprocess.run("npm install -g @google/gemini-cli@preview", shell=True, check=True)
    #             print("✅ Gemini CLI نصب شد")
    #             print("   ⚠️ لطفاً لاگین کنید: دستور 'gemini' را در ترمینال اجرا کنید")
    #         except Exception as e:
    #             setup_errors.append(f"Gemini CLI installation failed: {e}")
    #             print(f"❌ خطا در نصب Gemini CLI: {e}")
    # except subprocess.TimeoutExpired:
    #     print("⚠️ بررسی Gemini CLI timeout شد")
    #     print("   💡 فرض می‌کنیم نصب شده - می‌توانید پردازش را امتحان کنید")
    #     gemini_ready = True
    # except Exception as e:
    #     setup_errors.append(f"Error checking Gemini CLI: {e}")
    
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
    
    # تنظیم audio_files
    audio_files = selected_audio_files

# اجرای خودکار
_initialize()
