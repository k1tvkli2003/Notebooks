"""
PDF Batch Extractor (AvalAI OCR) - Processing Module
پردازش PDFها با استفاده از APIهای OCR مختلف AvalAI
"""

import os
import base64
import time
import asyncio
import json
import re
from pathlib import Path
from IPython.display import clear_output, display, HTML

import httpx
import fitz  # PyMuPDF

# Import from setup module
from avalai_ocr_setup import (
    AVALAI_API_KEY, AVALAI_BASE_URL,
    selected_model, OCR_MODELS, OCR_PROMPT,
    selected_pdf_files, extract_images
)

# ====================================
# Constants
# ====================================
DPI = 250  # وضوح تصویر برای تبدیل PDF به عکس
MAX_RETRIES = 5
HANDSHAKE_TIMEOUT = 90   # ثانیه برای شروع دریافت پاسخ (هندشیک / اولین بایت) = ۱.۵ دقیقه
                          # پس از شروع استریم، هیچ تایم‌اوتی وجود ندارد
CONCURRENT_FILES = 5  # تعداد فایل‌های همزمان

# تایم‌اوت هندشیک بر اساس شماره تلاش (per-page)
# تلاش ۱ → ۹۰s  |  تلاش ۲ → ۱۸۰s  |  تلاش ۳+ → ۳۰۰s
def _page_handshake_timeout(attempt: int) -> int:
    if attempt <= 1:
        return HANDSHAKE_TIMEOUT      # 90s
    elif attempt == 2:
        return 180                    # 3 دقیقه
    else:
        return 300                    # 5 دقیقه (ثابت از تلاش ۳ به بعد)

# ====================================
# Helper Functions
# ====================================
def format_time(seconds):
    """تبدیل ثانیه به فرمت خوانا"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def pdf_page_to_base64_image(pdf_path, page_num, dpi=DPI):
    """تبدیل یک صفحه PDF به تصویر JPEG base64 (کیفیت 90 — حجم کمتر برای ارسال به API)"""
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_bytes = pix.tobytes("jpeg", jpg_quality=90)
    doc.close()
    return base64.b64encode(img_bytes).decode("utf-8")


def pdf_to_base64(pdf_path):
    """تبدیل فایل PDF به base64"""
    with open(pdf_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_pdf_page_count(pdf_path):
    """دریافت تعداد صفحات PDF"""
    doc = fitz.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count


# ====================================
# Image Extraction Functions
# ====================================
IMAGE_MIN_SIZE = 50  # حداقل اندازه پیکسل برای تصاویر معنادار


def extract_page_images(pdf_path, page_num, images_dir, start_index=1):
    """
    استخراج تصاویر از یک صفحه PDF با برش ناحیه تصویر.
    
    Args:
        pdf_path: مسیر فایل PDF
        page_num: شماره صفحه (0-based)
        images_dir: پوشه ذخیره تصاویر
        start_index: شماره شروع نام‌گذاری تصاویر
    
    Returns:
        لیست دیکشنری‌ها: [{index, filename, y_pos, width, height}]
    """
    doc = fitz.open(str(pdf_path))
    page = doc[page_num]
    
    # جمع‌آوری bounding box تصاویر
    rects_to_extract = []
    seen_xrefs = set()
    
    for img in page.get_images(full=True):
        xref = img[0]
        if xref in seen_xrefs:
            continue
        seen_xrefs.add(xref)
        
        try:
            img_rects = page.get_image_rects(xref)
            if not img_rects:
                continue
            rect = img_rects[0]
            # تصاویر کوچک (آیکون/تزئینی) را رد کن
            if rect.width < IMAGE_MIN_SIZE or rect.height < IMAGE_MIN_SIZE:
                continue
            rects_to_extract.append(rect)
        except Exception:
            continue
    
    # مرتب‌سازی از بالا به پایین
    rects_to_extract.sort(key=lambda r: r.y0)
    
    # حذف تصاویر تکراری (بر اساس overlap)
    filtered = []
    for rect in rects_to_extract:
        is_dup = False
        for existing in filtered:
            overlap = rect & existing  # اشتراک
            if overlap.is_empty:
                continue
            overlap_area = overlap.width * overlap.height
            rect_area = rect.width * rect.height
            if rect_area > 0 and overlap_area / rect_area > 0.5:
                is_dup = True
                break
        if not is_dup:
            filtered.append(rect)
    
    # استخراج و ذخیره تصاویر
    images_info = []
    zoom = DPI / 72
    mat = fitz.Matrix(zoom, zoom)
    
    for i, rect in enumerate(filtered):
        img_index = start_index + i
        img_filename = f"image_{img_index:03d}.png"
        img_path = images_dir / img_filename
        
        try:
            pix = page.get_pixmap(matrix=mat, clip=rect)
            # اگر تصویر نتیجه خیلی کوچک بود، رد کن
            if pix.width < IMAGE_MIN_SIZE or pix.height < IMAGE_MIN_SIZE:
                continue
            pix.save(str(img_path))
            
            images_info.append({
                'index': img_index,
                'filename': img_filename,
                'y_pos': rect.y0,
                'width': pix.width,
                'height': pix.height,
            })
        except Exception:
            continue
    
    doc.close()
    return images_info


def get_image_prompt_addition(num_images, start_index):
    """تولید دستورالعمل اضافی پرامپت برای صفحات دارای تصویر"""
    return f"""

## IMPORTANT - Image Handling (This Page)
This page contains {num_images} image(s)/figure(s). For each image you encounter:
1. At the EXACT position where the image appears in the text flow, insert the marker:
   {{{{IMG_N: Brief descriptive title}}}}
2. N starts from {start_index} and goes up to {start_index + num_images - 1}
3. Write the description in the SAME language as the surrounding text
4. Only mark meaningful content images (figures, diagrams, charts, photos, illustrations)
5. Keep descriptions brief but identifying
"""


def replace_image_markers(text, images_info, images_dir_name):
    """
    جایگزینی مارکرهای {{IMG_N: description}} با سینتکس Markdown تصویر.
    
    Args:
        text: متن OCR با مارکرها
        images_info: لیست اطلاعات تصاویر از extract_page_images
        images_dir_name: نام پوشه تصاویر (مثلاً "images_Chapter01")
    
    Returns:
        متن با مارکرهای جایگزین شده: ![description](path)
    """
    pattern = r'\{\{IMG_(\d+):\s*(.+?)\}\}'
    
    def replacer(m):
        img_num = int(m.group(1))
        description = m.group(2).strip()
        for img in images_info:
            if img['index'] == img_num:
                return f'\n![{description}]({images_dir_name}/{img["filename"]})\n'
        return f'[{description}]'
    
    return re.sub(pattern, replacer, text)


def _append_unreferenced_images(text, page_images, images_dir_name):
    """اضافه کردن تصاویری که در متن ارجاع داده نشده‌اند"""
    referenced = set()
    for img in page_images:
        if f'{images_dir_name}/{img["filename"]}' in text:
            referenced.add(img['index'])
    
    unreferenced = [img for img in page_images if img['index'] not in referenced]
    if unreferenced:
        text += '\n'
        for img in unreferenced:
            text += f'\n![Image {img["index"]}]({images_dir_name}/{img["filename"]})'
    return text


# ====================================
# Output Save Functions
# ====================================

def save_output(pdf_path, text):
    """ذخیره متن OCR به صورت Markdown در کنار فایل PDF"""
    pdf_path = Path(pdf_path)
    out = pdf_path.parent / f"{pdf_path.stem}.md"
    try:
        out.write_text(text, encoding="utf-8")
        return True
    except Exception as e:
        print(f"⚠️ خطا در ذخیره {pdf_path.name}: {e}")
        return False


# ====================================
# Streaming Helper
# ====================================
async def _stream_chat_completion(http_client, url, payload, headers, model_id="",
                                  handshake_timeout: int = HANDSHAKE_TIMEOUT):
    """
    ارسال درخواست chat completion به صورت استریم SSE با دو فاز:

    فاز ۱ (هندشیک):  حداکثر handshake_timeout ثانیه منتظر اولین بایت می‌ماند.
                     اگر پاسخ شروع نشد → TimeoutError با پیام واضح.

    فاز ۲ (استریم): پس از دریافت اولین خط، بدون هیچ محدودیت زمانی
                     تا پایان کامل پاسخ منتظر می‌ماند.

    Returns:
        str: متن کامل پاسخ (از ترکیب همه delta‌های SSE)
    Raises:
        Exception: تایم‌اوت هندشیک، خطای HTTP، یا خطای شبکه
    """
    streaming_payload = {**payload, "stream": True}

    result_queue: asyncio.Queue = asyncio.Queue()
    error_holder: list = []

    async def _streamer():
        try:
            async with http_client.stream(
                "POST", url,
                json=streaming_payload,
                headers=headers,
                timeout=httpx.Timeout(
                    connect=handshake_timeout,
                    read=None,    # بدون محدودیت read پس از اتصال
                    write=180,    # ۳ دقیقه برای آپلود base64 تصویر
                    pool=30
                )
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise Exception(
                        f"HTTP {response.status_code}: {body.decode('utf-8', 'replace')[:500]}"
                    )
                async for raw_line in response.aiter_lines():
                    await result_queue.put(raw_line)
        except Exception as exc:
            error_holder.append(exc)
        finally:
            await result_queue.put(None)  # sentinel: پایان استریم

    task = asyncio.create_task(_streamer())

    # ─── فاز ۱: هندشیک ─────────────────────────────────────────────────────
    try:
        first_line = await asyncio.wait_for(
            result_queue.get(), timeout=handshake_timeout
        )
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        raise Exception(
            f"⏱️ تایم‌اوت هندشیک ({handshake_timeout}s) — "
            f"مدل '{model_id}' در {handshake_timeout} ثانیه پاسخ نداد"
        )

    if error_holder:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        raise error_holder[0]

    # ─── فاز ۲: استریم شروع شد — بدون تایم‌اوت ────────────────────────────
    content_parts: list = []

    def _parse_sse(line: str):
        """Returns (is_done: bool, content: str)"""
        if not line or not line.startswith("data: "):
            return False, ""
        data_str = line[6:].strip()
        if data_str == "[DONE]":
            return True, ""
        try:
            chunk = json.loads(data_str)
            delta = chunk["choices"][0]["delta"].get("content", "")
            return False, delta or ""
        except (json.JSONDecodeError, KeyError, IndexError):
            return False, ""

    # پردازش اولین خط دریافت شده در فاز هندشیک
    if first_line is not None:
        done, content = _parse_sse(first_line)
        if content:
            content_parts.append(content)
        if done:
            await task
            return "".join(content_parts)

    # جمع‌آوری بقیه بدون هیچ تایم‌اوتی
    while True:
        line = await result_queue.get()  # ← بدون تایم‌اوت
        if line is None:
            break
        done, content = _parse_sse(line)
        if content:
            content_parts.append(content)
        if done:
            break

    await task
    if error_holder:
        raise error_holder[0]

    return "".join(content_parts)


async def ocr_chat_vision(http_client, pdf_path, page_num, prompt, model_id="gemma-3-27b-it",
                          handshake_timeout: int = HANDSHAKE_TIMEOUT):
    """
    OCR با مدل‌های ویژن استاندارد (Gemma, Gemini Flash, ...) - از /v1/chat/completions
    از streaming استفاده می‌کند:
    - فاز هندشیک: حداکثر handshake_timeout ثانیه برای شروع دریافت
    - پس از شروع استریم: بدون محدودیت زمانی تا پایان پاسخ
    """
    img_b64 = pdf_page_to_base64_image(pdf_path, page_num)

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                    }
                ]
            }
        ],
        "max_tokens": 8192,
        "temperature": 0.0
    }

    url = f"{AVALAI_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {AVALAI_API_KEY}"}

    return await _stream_chat_completion(http_client, url, payload, headers,
                                         model_id=model_id,
                                         handshake_timeout=handshake_timeout)


# ====================================
# Progress Display
# ====================================
def update_progress_display(total_files, completed_files, success_count, failed_count,
                           active_files=None,
                           error_logs=None, model_name=None):
    """به‌روزرسانی نمایش پیشرفت — از چند فایل همزمان پشتیبانی می‌کند"""
    file_percent = (completed_files / total_files) * 100 if total_files > 0 else 0

    clear_output(wait=True)

    html = f"""
    <div style="font-family: monospace; background: #f5f5f5; padding: 15px; border-radius: 5px;">
        <h3 style="margin: 0 0 10px 0;">📊 پیشرفت کلی - مدل: {model_name or 'N/A'}</h3>
        <div style="margin: 10px 0; font-size: 16px;">
            <strong>{completed_files}/{total_files}</strong> فایل (<strong>{file_percent:.1f}%</strong>) |
            ✅ موفق: <strong style="color: green;">{success_count}</strong> |
            ❌ خطا: <strong style="color: red;">{failed_count}</strong>
        </div>
    """

    # Progress bar کلی
    html += f'''
        <div style="background: #ddd; border-radius: 10px; height: 20px; margin: 10px 0;">
            <div style="background: linear-gradient(90deg, #28a745, #20c997);
                        width: {file_percent}%; height: 100%; border-radius: 10px;
                        transition: width 0.3s;"></div>
        </div>
    '''

    if active_files:
        html += f'''
        <hr style="border: none; border-top: 1px solid #ccc; margin: 15px 0;">
        <h4 style="margin: 10px 0;">⚙️ در حال پردازش ({len(active_files)} فایل همزمان):</h4>
        '''
        for fname, (cur_page, tot_pages) in active_files.items():
            if tot_pages and tot_pages > 0:
                page_percent = (cur_page / tot_pages) * 100
                page_info = f" صفحه {cur_page}/{tot_pages} ({page_percent:.0f}%)"
                page_bar = f'''
                <div style="background: #ddd; border-radius: 6px; height: 8px; margin: 3px 0 6px 18px;">
                    <div style="background: linear-gradient(90deg, #007bff, #17a2b8);
                                width: {page_percent}%; height: 100%; border-radius: 6px;"></div>
                </div>'''
            else:
                page_info = " در حال شروع..."
                page_bar = ""

            html += f'''
            <div style="padding: 3px 0;">
                🔵 <code style="background: #e0e0e0; padding: 2px 5px; border-radius: 3px;">{fname}</code>
                <small style="color: #555;">{page_info}</small>
                {page_bar}
            </div>
            '''

    # Error logs
    if error_logs:
        html += '<hr style="border: none; border-top: 1px solid #ccc; margin: 15px 0;">'
        html += '<h4 style="margin: 10px 0; color: red;">❌ خطاهای اخیر:</h4>'
        html += '<div style="max-height: 200px; overflow-y: auto;">'
        for error in error_logs[-5:]:
            html += f'<div style="margin: 3px 0; padding: 5px; background: #ffe0e0; border-left: 3px solid red;">'
            html += f'<strong>{error["file"]}</strong><br>'
            html += f'<small style="color: #666;">{error["error"][:200]}</small>'
            html += '</div>'
        html += '</div>'

    html += "</div>"
    display(HTML(html))


# ====================================
# Single PDF Processing
# ====================================
async def process_single_pdf_vision(http_client, pdf_path, page_count, model_id,
                                    prompt, progress_callback=None, extract_images=False):
    """پردازش یک PDF صفحه‌به‌صفحه با مدل ویژن با پشتیبانی استخراج تصاویر"""
    all_pages_text = []
    global_img_index = 1
    total_images = 0
    images_dir = None
    images_dir_name = None

    if extract_images:
        images_dir = pdf_path.parent / f"images_{pdf_path.stem}"
        images_dir.mkdir(exist_ok=True)
        images_dir_name = images_dir.name

    model_info = OCR_MODELS.get(model_id, {})
    supports_prompt = model_info.get('supports_prompt', True)

    for page_num in range(page_count):
        if progress_callback:
            progress_callback(page_num + 1, page_count)

        # استخراج تصاویر از این صفحه
        page_images = []
        if extract_images and images_dir:
            page_images = extract_page_images(pdf_path, page_num, images_dir,
                                              start_index=global_img_index)
            global_img_index += len(page_images)
            total_images += len(page_images)

        # ساخت پرامپت مخصوص صفحه (با اطلاعات تصاویر)
        page_prompt = prompt
        if page_images and supports_prompt:
            page_prompt += get_image_prompt_addition(len(page_images), page_images[0]['index'])

        attempt = 0
        while True:
            attempt += 1
            hs_timeout = _page_handshake_timeout(attempt)
            try:
                text = await ocr_chat_vision(http_client, pdf_path, page_num,
                                             page_prompt, model_id=model_id,
                                             handshake_timeout=hs_timeout)

                # پردازش مارکرهای تصویر
                if page_images and images_dir_name:
                    text = replace_image_markers(text, page_images, images_dir_name)
                    text = _append_unreferenced_images(text, page_images, images_dir_name)

                all_pages_text.append(text)
                break
            except Exception as e:
                err_str = str(e)
                wait_secs = min(3 * attempt, 60)  # حداکثر ۶۰ ثانیه بین retry‌ها
                next_hs = _page_handshake_timeout(attempt + 1)
                print(
                    f"\n   ❌ [{model_id}] صفحه {page_num + 1} — "
                    f"تلاش {attempt} (هندشیک {hs_timeout}s): {err_str[:300]}"
                )
                print(f"   🔄 retry در {wait_secs}s — هندشیک تلاش بعدی: {next_hs}s")
                await asyncio.sleep(wait_secs)

    # حذف پوشه خالی تصاویر
    if images_dir and images_dir.exists() and not any(images_dir.iterdir()):
        images_dir.rmdir()

    return "\n\n".join(all_pages_text), total_images


# ====================================
# Main Processing Function  
# ====================================
async def process_pdfs(pdf_files_list, model_id=None, timeout=3600):
    """
    پردازش دسته‌ای PDFها با AvalAI OCR — حداکثر CONCURRENT_FILES فایل همزمان
    """
    from avalai_ocr_setup import (
        selected_model as current_model, OCR_PROMPT as current_prompt,
        extract_images as current_extract_images
    )

    if model_id is None:
        model_id = current_model

    model_info = OCR_MODELS.get(model_id)
    if not model_info:
        raise ValueError(f"❌ مدل نامعتبر: {model_id}")

    print("=" * 80)
    print(f"🚀 شروع پردازش {len(pdf_files_list)} فایل PDF")
    print(f"🤖 مدل: {model_info['name']} ({model_id})")
    print(f"   📦 فرمت خروجی: Markdown (.md)")
    print(f"   🖼️  استخراج تصاویر: {'✅ فعال' if current_extract_images else '❌ غیرفعال'}")
    print(f"   ⚡ پردازش همزمان: {CONCURRENT_FILES} فایل")
    print("=" * 80)
    print()

    start_time = time.time()
    results = {'success': [], 'failed': []}
    error_logs = []
    completed = 0
    active_files = {}   # {rel_name: (current_page, total_pages)}

    def refresh_display():
        update_progress_display(
            len(pdf_files_list), completed,
            len(results['success']), len(results['failed']),
            active_files=dict(active_files),
            error_logs=error_logs,
            model_name=model_info['name']
        )

    sem = asyncio.Semaphore(CONCURRENT_FILES)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=HANDSHAKE_TIMEOUT,
            read=None,
            write=180,
            pool=30
        ),
        limits=httpx.Limits(
            max_connections=CONCURRENT_FILES + 2,
            max_keepalive_connections=CONCURRENT_FILES
        )
    ) as http_client:

        async def process_one(pdf_file):
            nonlocal completed

            pdf_path = Path(pdf_file)
            rel_name = pdf_path.name

            # بررسی کش
            if (pdf_path.parent / f"{pdf_path.stem}.md").exists():
                completed += 1
                results['success'].append({
                    'file': str(pdf_path), 'time': 0, 'pages': 0, 'cached': True
                })
                refresh_display()
                return

            # دریافت تعداد صفحات
            try:
                page_count = get_pdf_page_count(pdf_path)
            except Exception as e:
                completed += 1
                results['failed'].append({
                    'file': str(pdf_path), 'error': f"Error reading PDF: {e}"
                })
                error_logs.append({'file': rel_name, 'error': str(e)})
                refresh_display()
                return

            # پردازش با semaphore
            async with sem:
                active_files[rel_name] = (0, page_count)
                refresh_display()

                file_start = time.time()

                def page_progress(current, total):
                    active_files[rel_name] = (current, total)
                    refresh_display()

                try:
                    text, img_count = await process_single_pdf_vision(
                        http_client, pdf_path, page_count, model_id,
                        current_prompt, progress_callback=page_progress,
                        extract_images=current_extract_images
                    )

                    save_output(pdf_path, text)

                    elapsed = time.time() - file_start
                    results['success'].append({
                        'file': str(pdf_path), 'time': elapsed,
                        'pages': page_count, 'cached': False,
                        'images': img_count
                    })

                except Exception as e:
                    error_msg = str(e)[:500]
                    error_logs.append({'file': rel_name, 'error': error_msg})
                    results['failed'].append({
                        'file': str(pdf_path), 'error': error_msg
                    })

                finally:
                    active_files.pop(rel_name, None)

            completed += 1
            refresh_display()

        tasks = [process_one(pdf_file) for pdf_file in pdf_files_list]
        await asyncio.gather(*tasks)

    # ===== خلاصه نهایی =====
    elapsed_total = time.time() - start_time
    clear_output(wait=True)

    cached_count = sum(1 for r in results['success'] if r.get('cached', False))
    processed = [r for r in results['success'] if not r.get('cached', False)]

    summary_html = '<div style="font-family: monospace; background: #f8f9fa; padding: 25px; border-radius: 15px; border: 3px solid #28a745;">'
    summary_html += f'<h2 style="margin: 0 0 20px 0; color: #28a745; text-align: center;">🎉 پردازش دسته‌ای کامل شد!</h2>'
    summary_html += f'<div style="text-align: center; color: #666; margin-bottom: 15px;">🤖 مدل: {model_info["name"]} ({model_id})</div>'

    # آمار کلی
    summary_html += '<div style="background: white; padding: 20px; border-radius: 10px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">'
    summary_html += '<h3 style="margin: 0 0 15px 0; color: #333;">📊 خلاصه کلی:</h3>'
    summary_html += f'<div style="font-size: 18px; line-height: 2;">'
    summary_html += f'⏱️  <strong>زمان کل:</strong> {format_time(elapsed_total)}<br>'
    summary_html += f'📋 <strong>تعداد کل:</strong> {len(pdf_files_list)} فایل<br>'
    summary_html += f'<span style="color: green;">✅ <strong>موفق:</strong> {len(results["success"])} فایل</span><br>'
    summary_html += f'<span style="color: red;">❌ <strong>خطا:</strong> {len(results["failed"])} فایل</span><br>'
    if cached_count > 0:
        summary_html += f'💾 <strong>کش شده:</strong> {cached_count} فایل<br>'
    summary_html += '</div></div>'

    # آمار تفصیلی
    if processed:
        avg_time = sum(r['time'] for r in processed) / len(processed)
        total_pages = sum(r['pages'] for r in processed)
        total_images = sum(r.get('images', 0) for r in processed)

        summary_html += '<div style="background: #e7f3ff; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #007bff;">'
        summary_html += f'<h3 style="margin: 0 0 15px 0; color: #007bff;">📈 آمار تفصیلی ({len(processed)} فایل جدید):</h3>'
        summary_html += f'<div style="font-size: 16px; line-height: 1.8;">'
        summary_html += f'⏱️  <strong>میانگین زمان:</strong> {format_time(avg_time)}<br>'
        summary_html += f'📄 <strong>مجموع صفحات:</strong> {total_pages:,}<br>'
        if total_images > 0:
            summary_html += f'🖼️  <strong>تصاویر استخراج شده:</strong> {total_images:,}<br>'
        if elapsed_total > 0:
            summary_html += f'🚀 <strong>سرعت پردازش:</strong> {len(processed) / (elapsed_total / 60):.1f} فایل/دقیقه'
        summary_html += '</div></div>'

    # فایل‌های ناموفق
    if results['failed']:
        summary_html += '<div style="background: #ffe7e7; padding: 20px; border-radius: 10px; border-left: 5px solid #dc3545;">'
        summary_html += f'<h3 style="margin: 0 0 15px 0; color: #dc3545;">❌ فایل‌های ناموفق ({len(results["failed"])} فایل):</h3>'
        summary_html += '<div style="max-height: 400px; overflow-y: auto; background: white; padding: 15px; border-radius: 5px;">'
        for idx, item in enumerate(results['failed'], 1):
            summary_html += f'<div style="margin-bottom: 15px; padding: 10px; background: #fff5f5; border-radius: 5px; border-left: 3px solid #dc3545;">'
            summary_html += f'<strong>{idx}. {Path(item["file"]).name}</strong><br>'
            summary_html += f'<small style="color: #666;">📁 {item["file"]}</small><br>'
            summary_html += f'<small style="color: #dc3545;">⚠️  {item["error"][:250]}</small>'
            summary_html += '</div>'
        summary_html += '</div></div>'

    summary_html += '</div>'
    display(HTML(summary_html))

    print("=" * 80)
    print(f"🎉 پردازش کامل شد!")
    print(f"✅ موفق: {len(results['success'])} | ❌ خطا: {len(results['failed'])}")
    print("=" * 80)

    return results
