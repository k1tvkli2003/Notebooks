"""
PDF Batch Extractor - Processing Module
پردازش همزمان PDFها با تعداد worker برابر با تعداد APIهای فعال (بدون GPT-5)
"""

import base64
import time
import asyncio
from pathlib import Path
from IPython.display import clear_output, display, HTML

# Import from setup module
from pdf_setup import clients, options

# Import API config (if needed for any future use)
from api_config import DATALAB_API_KEYS

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

# ====================================
# Progress Display
# ====================================
def update_progress_display(total, completed, success, failed, processing_dict, retry_info=None, error_logs=None):
    """به‌روزرسانی نمایش پیشرفت بر اساس تعداد واقعی worker ها"""
    percent = (completed / total) * 100 if total > 0 else 0
    worker_count = max(len(processing_dict), 1)
    clear_output(wait=True)
    
    html = f"""
    <div style="font-family: monospace; background: #f5f5f5; padding: 15px; border-radius: 5px;">
        <h3 style="margin: 0 0 10px 0;">📊 پیشرفت کلی</h3>
        <div style="margin: 10px 0; font-size: 16px;">
            <strong>{completed}/{total}</strong> فایل (<strong>{percent:.1f}%</strong>) | 
            ✅ موفق: <strong style="color: green;">{success}</strong> | 
            ❌ خطا: <strong style="color: red;">{failed}</strong>
        </div>
        <hr style="border: none; border-top: 1px solid #ccc; margin: 15px 0;">
        <h4 style="margin: 10px 0;">⚙️ فایل‌های در حال پردازش:</h4>
    """
    
    active_count = 0
    # نمایش داینامیک همه worker ها بر اساس تعداد clients
    for i in sorted(processing_dict.keys()):
        if processing_dict[i]:
            html += (
                f'<div style="padding: 3px 0;">'
                f'🔵 <strong>Client {i}</strong>: '
                f'<code style="background: #e0e0e0; padding: 2px 5px; border-radius: 3px;">{processing_dict[i]}</code>'
                f'</div>'
            )
            active_count += 1
        else:
            html += f'<div style="padding: 3px 0; color: #999;">⚪ Client {i}: آماده...</div>'
    
    html += f'<div style="margin-top: 10px; color: #666;"><small>Workers فعال: {active_count}/{worker_count}</small></div>'
    
    if retry_info and any(count > 1 for count in retry_info.values()):
        html += '<hr style="border: none; border-top: 1px solid #ccc; margin: 15px 0;">'
        html += '<h4 style="margin: 10px 0; color: orange;">🔄 تلاش‌های مجدد:</h4>'
        html += '<div style="max-height: 150px; overflow-y: auto; background: #fff; padding: 10px; border-radius: 3px;">'
        retry_shown = False
        for file_path, count in list(retry_info.items())[-10:]:
            if count > 1:
                retry_shown = True
                html += f'<div style="margin: 5px 0; padding: 5px; background: #fff3cd; border-left: 3px solid orange;">'
                html += f'<strong>{Path(file_path).name}</strong>: تلاش {count}/5'
                html += '</div>'
        if not retry_shown:
            html += '<div style="color: #999;">هنوز تلاش مجددی نیست</div>'
        html += '</div>'
    
    if error_logs:
        html += '<hr style="border: none; border-top: 1px solid #ccc; margin: 15px 0;">'
        html += '<h4 style="margin: 10px 0; color: red;">❌ خطاهای اخیر:</h4>'
        html += '<div style="max-height: 200px; overflow-y: auto; background: #fff; padding: 10px; border-radius: 3px;">'
        for error in error_logs[-10:]:
            html += f'<div style="margin: 5px 0; padding: 5px; background: #ffe0e0; border-left: 3px solid red;">'
            html += f'<strong>{error["file"]}</strong> (تلاش {error["attempt"]})<br>'
            html += f'<small style="color: #666;">{error["error"][:300]}...</small>'
            html += '</div>'
        if len(error_logs) > 10:
            html += f'<div style="text-align: center; color: #999; margin-top: 5px;"><small>... و {len(error_logs) - 10} خطای دیگر</small></div>'
        html += '</div>'
    
    html += "</div>"
    display(HTML(html))

# ====================================
# PDF Processing
# ====================================
async def process_single_pdf(pdf_file, client, client_num, results, lock, 
                             processing_files, completed_count_ref, retry_counts, 
                             file_errors, error_logs, pdf_files_list, max_retries=5, 
                             timeout=3600):  # تغییر: تایم‌اوت پیش‌فرض 1 ساعت
    """پردازش یک PDF"""
    file_path_str = str(pdf_file)
    rel_path = pdf_file.name
    output_md = pdf_file.parent / f"{pdf_file.stem}.md"
    
    # بررسی کش
    if output_md.exists():
        async with lock:
            completed_count_ref[0] += 1
            results['success'].append({
                'file': file_path_str, 'time': 0, 'pages': 0,
                'images': 0, 'client': client_num, 'cached': True
            })
            update_progress_display(
                len(pdf_files_list), completed_count_ref[0],
                len(results['success']), len(results['failed']),
                processing_files, retry_counts, error_logs
            )
        return
    
    # تلاش برای پردازش
    for attempt in range(1, max_retries + 1):
        async with lock:
            retry_counts[file_path_str] = attempt
            processing_files[client_num] = f"{rel_path} (تلاش {attempt}/{max_retries})"
            update_progress_display(
                len(pdf_files_list), completed_count_ref[0],
                len(results['success']), len(results['failed']),
                processing_files, retry_counts, error_logs
            )
        
        start_time = time.time()
        
        try:
            # استخراج با تایم‌اوت
            # اضافه کردن تاخیر تصادفی کوچک برای جلوگیری از همزمانی دقیق درخواست‌ها
            await asyncio.sleep(client_num * 0.5)
            
            result = await asyncio.wait_for(
                client.convert(file_path_str, options=options),
                timeout=timeout
            )
            elapsed = time.time() - start_time
            
            # ذخیره تصاویر
            image_mapping = {}
            if result.images:
                images_dir = pdf_file.parent / f"images_{pdf_file.stem}"
                images_dir.mkdir(exist_ok=True)
                for img_idx, (img_name, img_data) in enumerate(result.images.items(), 1):
                    img_filename = f"image_{img_idx:03d}.png"
                    img_path = images_dir / img_filename
                    img_bytes = base64.b64decode(img_data) if isinstance(img_data, str) else img_data
                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)
                    image_mapping[img_name] = f"{images_dir.name}/{img_filename}"
            
            # ذخیره Markdown (بدون پردازش GPT-5)
            markdown_content = result.markdown
            for old_path, new_path in image_mapping.items():
                markdown_content = markdown_content.replace(f'src="{old_path}"', f'src="{new_path}"')
                markdown_content = markdown_content.replace(f']({old_path})', f']({new_path})')
            
            # ذخیره مستقیم فایل
            with open(output_md, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            async with lock:
                if file_path_str in file_errors:
                    del file_errors[file_path_str]
                results['success'].append({
                    'file': file_path_str, 'time': elapsed,
                    'pages': getattr(result, 'page_count', 0),
                    'images': len(image_mapping), 'client': client_num,
                    'cached': False, 'retries': attempt - 1
                })
                if file_path_str in retry_counts:
                    del retry_counts[file_path_str]
            break
            
        except asyncio.TimeoutError:
            error_msg = f"تایم‌اوت: پردازش بیش از {timeout} ثانیه طول کشید"
            async with lock:
                error_logs.append({
                    'file': rel_path, 'error': error_msg,
                    'attempt': attempt, 'client': client_num
                })
            
            if attempt >= max_retries:
                async with lock:
                    results['failed'].append({
                        'file': file_path_str, 'error': error_msg,
                        'client': client_num, 'retries': attempt
                    })
                    if file_path_str not in file_errors:
                        file_errors[file_path_str] = []
                    file_errors[file_path_str].append(error_msg)
            else:
                async with lock:
                    if file_path_str not in file_errors:
                        file_errors[file_path_str] = []
                    file_errors[file_path_str].append(f"تلاش {attempt}: {error_msg}")
                    update_progress_display(
                        len(pdf_files_list), completed_count_ref[0],
                        len(results['success']), len(results['failed']),
                        processing_files, retry_counts, error_logs
                    )
                await asyncio.sleep(2)
                continue
        
        except Exception as e:
            error_msg = str(e)
            async with lock:
                error_logs.append({
                    'file': rel_path, 'error': error_msg,
                    'attempt': attempt, 'client': client_num
                })
            
            if attempt >= max_retries:
                async with lock:
                    results['failed'].append({
                        'file': file_path_str, 'error': error_msg,
                        'client': client_num, 'retries': attempt
                    })
                    if file_path_str not in file_errors:
                        file_errors[file_path_str] = []
                    file_errors[file_path_str].append(error_msg)
            else:
                async with lock:
                    if file_path_str not in file_errors:
                        file_errors[file_path_str] = []
                    file_errors[file_path_str].append(f"تلاش {attempt}: {error_msg}")
                    update_progress_display(
                        len(pdf_files_list), completed_count_ref[0],
                        len(results['success']), len(results['failed']),
                        processing_files, retry_counts, error_logs
                    )
                await asyncio.sleep(2)
                continue
        
        finally:
            if attempt >= max_retries or output_md.exists():
                async with lock:
                    completed_count_ref[0] += 1
                    processing_files[client_num] = None
                    update_progress_display(
                        len(pdf_files_list), completed_count_ref[0],
                        len(results['success']), len(results['failed']),
                        processing_files, retry_counts, error_logs
                    )

# ====================================
# Main Processing Function
# ====================================
async def process_pdfs(pdf_files_list, timeout=3600):  # تغییر: پارامتر timeout به 1 ساعت
    """پردازش همزمان PDFها با تعداد worker برابر با تعداد APIهای آماده"""
    # تعداد worker ها را بر اساس تعداد clients تنظیم می‌کنیم
    worker_count = len(clients)
    if worker_count == 0:
        raise RuntimeError("❌ هیچ API Client فعالی پیدا نشد. لطفاً API keys را در فایل 'datalabAPI.md' یا 'api_config.py' بررسی کنید.")

    print("="*80)
    print(f"🚀 شروع پردازش {len(pdf_files_list)} فایل PDF با {worker_count} Worker همزمان (هر Worker = یک API)")
    print("   🔄 تلاش مجدد تا 5 بار در صورت خطا")
    print("="*80)
    print()
    
    start_time = time.time()
    results = {'success': [], 'failed': []}
    progress_lock = asyncio.Lock()
    
    completed_count_ref = [0]
    # دیکشنری وضعیت پردازش برای هر worker بر اساس تعداد clients
    processing_files = {i + 1: None for i in range(worker_count)}
    retry_counts = {}
    file_errors = {}
    error_logs = []
    
    update_progress_display(len(pdf_files_list), 0, 0, 0, processing_files, retry_counts, error_logs)
    
    async def process_with_semaphore(semaphore, pdf_file, client_idx):
        async with semaphore:
            client = clients[client_idx]
            client_num = client_idx + 1
            await process_single_pdf(
                pdf_file, client, client_num, results, progress_lock,
                processing_files, completed_count_ref, retry_counts,
                file_errors, error_logs, pdf_files_list, max_retries=5,
                timeout=timeout  # اضافه شد
            )
    
    # حداکثر تعداد کارهای همزمان = تعداد APIهای آماده
    semaphore = asyncio.Semaphore(worker_count)
    tasks = []
    for idx, pdf_file in enumerate(pdf_files_list):
        client_idx = idx % len(clients)
        task = process_with_semaphore(semaphore, pdf_file, client_idx)
        tasks.append(task)
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # خلاصه نهایی
    clear_output(wait=True)
    elapsed_total = time.time() - start_time
    
    # آمار محاسبه
    cached_count = sum(1 for r in results['success'] if r.get('cached', False))
    retry_success = [r for r in results['success'] if r.get('retries', 0) > 0]
    processed = [r for r in results['success'] if not r.get('cached', False)]
    
    # نمایش HTML زیبا
    summary_html = '<div style="font-family: monospace; background: #f8f9fa; padding: 25px; border-radius: 15px; border: 3px solid #28a745;">'
    summary_html += '<h2 style="margin: 0 0 20px 0; color: #28a745; text-align: center;">🎉 پردازش دسته‌ای کامل شد!</h2>'
    
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
    if retry_success:
        summary_html += f'🔄 <strong>موفق پس از retry:</strong> {len(retry_success)} فایل<br>'
    summary_html += '</div></div>'
    
    # آمار تفصیلی
    if processed:
        avg_time = sum(r['time'] for r in processed) / len(processed)
        total_pages = sum(r['pages'] for r in processed)
        total_images = sum(r['images'] for r in processed)
        
        summary_html += '<div style="background: #e7f3ff; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid #007bff;">'
        summary_html += f'<h3 style="margin: 0 0 15px 0; color: #007bff;">📈 آمار تفصیلی ({len(processed)} فایل جدید):</h3>'
        summary_html += f'<div style="font-size: 16px; line-height: 1.8;">'
        summary_html += f'⏱️  <strong>میانگین زمان:</strong> {format_time(avg_time)}<br>'
        summary_html += f'📄 <strong>مجموع صفحات:</strong> {total_pages:,}<br>'
        summary_html += f'🖼️  <strong>مجموع تصاویر:</strong> {total_images:,}<br>'
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
            summary_html += f'<small style="color: #dc3545;">⚠️  {item["error"][:250]}...</small>'
            summary_html += '</div>'
        summary_html += '</div></div>'
    
    summary_html += '</div>'
    
    display(HTML(summary_html))
    
    # پرینت ساده برای لاگ
    print("="*80)
    print("🎉 پردازش کامل شد!")
    print(f"✅ موفق: {len(results['success'])} | ❌ خطا: {len(results['failed'])}")
    print("="*80)
    
    return results
