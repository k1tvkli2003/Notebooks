"""
Audio Transcriber - Processor Module
پردازش و رونویسی فایل‌های صوتی
"""

import subprocess
import os
import math
import base64
import requests
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from audio_setup import AVALAI_API_KEY, AVALAI_BASE_URL, MODEL
try:
    from openai import OpenAI
except ImportError:
    pass

# ====================================
# Configuration
# ====================================
MAX_CONCURRENT = 1  # پردازش ترتیبی (غیر همزمان)
SEGMENT_DURATION = 300  # هر قطعه حداکثر 5 دقیقه (300 ثانیه) - کاهش برای جلوگیری از خطای 413

# ====================================
# Helper Functions
# ====================================
def format_time(seconds):
    """تبدیل ثانیه به فرمت خوانا"""
    if seconds < 60:
        return f"{seconds:.1f} ثانیه"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} دقیقه {secs} ثانیه"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} ساعت {minutes} دقیقه"

def get_duration(file_path):
    """دریافت مدت زمان فایل صوتی به ثانیه"""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
           "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"❌ خطا در دریافت مدت زمان {file_path}: {e}")
        return 0

def split_audio(file_path, segment_time=SEGMENT_DURATION):
    """تقسیم فایل صوتی به قطعات کوچکتر"""
    duration = get_duration(file_path)
    if duration == 0:
        return []
    
    if duration <= segment_time:
        # نیازی به تقسیم نیست
        return [file_path]
    
    num_parts = math.ceil(duration / segment_time)
    print(f"   ✂️ تقسیم به {num_parts} قطعه ({segment_time//60} دقیقه‌ای)...")
    
    # ایجاد پوشه موقت (و پاکسازی قبلی‌ها)
    temp_dir = Path("temp_audio_chunks")
    if temp_dir.exists():
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    temp_dir.mkdir(exist_ok=True)
    
    output_pattern = str(temp_dir / f"{file_path.stem}_part_%03d{file_path.suffix}")
    
    cmd = [
        "ffmpeg", "-i", str(file_path), "-f", "segment",
        "-segment_time", str(segment_time),
        "-c", "copy", "-reset_timestamps", "1",
        output_pattern
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        chunks = sorted(list(temp_dir.glob(f"{file_path.stem}_part_*{file_path.suffix}")))
        return chunks
    except subprocess.CalledProcessError as e:
        print(f"❌ خطا در تقسیم فایل: {e}")
        return [file_path]  # تلاش با فایل اصلی

def transcribe_chunk(chunk_path):
    """رونویسی یک قطعه با AvalAI"""
    try:
        # بررسی مدل Gemini برای استفاده از Chat Completion
        if "gemini" in MODEL.lower():
            # خواندن فایل و تبدیل به base64
            with open(chunk_path, "rb") as audio_file:
                audio_data = audio_file.read()
                base64_audio = base64.b64encode(audio_data).decode("utf-8")
            
            # تشخیص MIME type
            ext = chunk_path.suffix.lower()
            mime_type = "audio/mp3"  # پیش‌فرض
            if ext == ".wav": mime_type = "audio/wav"
            elif ext == ".mp3": mime_type = "audio/mp3"
            elif ext == ".ogg": mime_type = "audio/ogg"
            elif ext == ".flac": mime_type = "audio/flac"
            elif ext == ".aac": mime_type = "audio/aac"
            elif ext == ".m4a": mime_type = "audio/mp4"  # یا audio/aac
            
            # ارسال درخواست به Chat Completion API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AVALAI_API_KEY}"
            }
            
            payload = {
                "model": MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please transcribe this audio file accurately. Output ONLY the transcription text, no other commentary."},
                        {
                            "type": "file",
                            "file": {
                                "file_data": f"data:{mime_type};base64,{base64_audio}"
                            }
                        }
                    ]
                }]
            }
            
            response = requests.post(f"{AVALAI_BASE_URL}/chat/completions", headers=headers, json=payload)
            
            if response.status_code != 200:
                return "", f"Error {response.status_code}: {response.text}"
                
            result = response.json()
            return result['choices'][0]['message']['content'], None

        else:
            # استفاده از روش استاندارد برای سایر مدل‌ها (مثل Whisper)
            client = OpenAI(
                api_key=AVALAI_API_KEY,
                base_url=AVALAI_BASE_URL
            )
            
            with open(chunk_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model=MODEL,
                    file=audio_file,
                    response_format="text"
                )
                
            return transcription, None
        
    except Exception as e:
        return "", str(e)

# ====================================
# Main Processing Function
# ====================================
def process_audio_files(files):
    """پردازش لیست فایل‌های صوتی"""
    if not files:
        print("❌ هیچ فایلی انتخاب نشده است!")
        return {'success': [], 'failed': []}
    
    results = {'success': [], 'failed': []}
    total_files = len(files)
    
    print("="*80)
    print(f"🚀 شروع پردازش {total_files} فایل صوتی")
    print("="*80)
    print()
    
    # Progress bar
    progress = widgets.FloatProgress(
        value=0,
        min=0,
        max=total_files,
        description='پیشرفت:',
        bar_style='info',
        style={'bar_color': '#3b82f6'},
        layout=widgets.Layout(width='100%')
    )
    
    status_label = widgets.HTML(value="<b>در حال پردازش...</b>")
    display(widgets.VBox([progress, status_label]))
    
    start_time = time.time()
    
    for i, audio_file in enumerate(files, 1):
        file_start_time = time.time()
        
        # بررسی کش
        final_md_path = audio_file.parent / f"{audio_file.stem}.md"
        # if final_md_path.exists():
        #     print(f"   💾 کش: {audio_file.name} -> قبلاً پردازش شده، رد شد")
        #     results['success'].append({
        #         'file': str(audio_file),
        #         'time': 0,
        #         'duration': 0,
        #         'cached': True
        #     })
        #     progress.value = i
        #     continue
        
        status_label.value = f"<b>🎵 [{i}/{total_files}] {audio_file.name}</b>"
        print(f"\n🎵 [{i}/{total_files}] پردازش: {audio_file.name}")
        
        try:
            # تقسیم به قطعات
            chunks = split_audio(audio_file)
            
            if not chunks:
                raise Exception("خطا در تقسیم فایل")
            
            # نوشتن هدر فایل قبل از شروع پردازش قطعات
            with open(final_md_path, "w", encoding="utf-8") as f:
                f.write(f"# 🎵 رونویسی: {audio_file.name}\n\n")
            
            # پردازش هر قطعه و نوشتن فوری پس از موفقیت
            successful_chunks = 0
            
            for j, chunk in enumerate(chunks, 1):
                print(f"   🤖 [{j}/{len(chunks)}] رونویسی قطعه...")
                attempt = 0
                
                while True:
                    attempt += 1
                    text, error = transcribe_chunk(chunk)
                    
                    if error:
                        print(f"   ⚠️ خطا در قطعه {j} (تلاش {attempt}): {error[:80]}...")
                        print(f"   🔄 تلاش مجدد قطعه {j} در 5 ثانیه...")
                        time.sleep(5)
                        continue
                    else:
                        # بلافاصله پارت موفق را به فایل اضافه کن
                        with open(final_md_path, "a", encoding="utf-8") as f:
                            if j > 1:
                                f.write("\n\n")
                            f.write(text)
                        successful_chunks += 1
                        print(f"   ✅ قطعه {j}/{len(chunks)} موفقیت‌آمیز بود و ذخیره شد")
                        break
                
                # پاکسازی قطعه موقت بلافاصله پس از ذخیره
                if chunk != audio_file and chunk.exists():
                    try:
                        os.remove(chunk)
                    except:
                        pass
            
            duration = get_duration(audio_file)
            elapsed = time.time() - file_start_time
            
            results['success'].append({
                'file': str(audio_file),
                'time': elapsed,
                'duration': duration,
                'cached': False
            })
            print(f"   ✅ همه {successful_chunks} قطعه ذخیره شد: {final_md_path.name} ({format_time(elapsed)})")
                
        except Exception as e:
            results['failed'].append({
                'file': str(audio_file),
                'error': str(e)
            })
            print(f"   ❌ خطا: {e}")
        
        progress.value = i
        
        # وقفه کوتاه بین فایل‌ها برای اطمینان از تکمیل پردازش
        if i < total_files:
            print("   ⏳ مکث کوتاه قبل از فایل بعدی...")
            time.sleep(2)
    
    # پاکسازی پوشه موقت
    temp_dir = Path("temp_audio_chunks")
    if temp_dir.exists():
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
    
    # گزارش نهایی
    total_time = time.time() - start_time
    
    progress.bar_style = 'success'
    status_label.value = f"<b style='color: green;'>✅ پردازش کامل شد! ({format_time(total_time)})</b>"
    
    print()
    print("="*80)
    print(f"📊 خلاصه: {len(results['success'])} موفق | {len(results['failed'])} ناموفق | زمان کل: {format_time(total_time)}")
    print("="*80)
    
    return results
