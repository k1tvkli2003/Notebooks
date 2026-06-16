"""
PDF Batch Extractor (AvalAI OCR) - Cleanup Module
حذف فایل‌های Markdown و پوشه‌های تصاویر تولید شده توسط AvalAI OCR
"""

import shutil
from pathlib import Path
from IPython.display import display, HTML

OUTPUT_EXTENSIONS = [".md"]

def cleanup_generated_files(pdf_files_list):
    """حذف همه فایل‌های خروجی و پوشه‌های تصاویر تولید شده"""
    print("="*80)
    print("🗑️  شروع حذف فایل‌های تولید شده...")
    print("="*80)
    print()
    
    deleted = {ext: [] for ext in OUTPUT_EXTENSIONS}
    deleted_img_dirs = []
    errors = []
    
    # پیدا کردن و حذف فایل‌ها
    for pdf_file in pdf_files_list:
        pdf_path = Path(pdf_file)
        for ext in OUTPUT_EXTENSIONS:
            out_file = pdf_path.parent / f"{pdf_path.stem}{ext}"
            if out_file.exists():
                try:
                    out_file.unlink()
                    deleted[ext].append(str(out_file))
                    print(f"✅ فایل حذف شد: {out_file.name}")
                except Exception as e:
                    error_msg = f"❌ خطا در حذف {out_file.name}: {str(e)}"
                    errors.append(error_msg)
                    print(error_msg)

        # حذف پوشه تصاویر
        images_dir = pdf_path.parent / f"images_{pdf_path.stem}"
        if images_dir.exists() and images_dir.is_dir():
            try:
                img_count = len(list(images_dir.glob("*")))
                shutil.rmtree(str(images_dir))
                deleted_img_dirs.append(str(images_dir))
                print(f"✅ پوشه تصاویر حذف شد: {images_dir.name} ({img_count} فایل)")
            except Exception as e:
                error_msg = f"❌ خطا در حذف پوشه {images_dir.name}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
    
    total_deleted = sum(len(v) for v in deleted.values())
    
    # نمایش خلاصه
    print()
    print("="*80)
    print("📊 خلاصه حذف:")
    print("="*80)
    for ext in OUTPUT_EXTENSIONS:
        print(f"🗑️  فایل‌های {ext} حذف شده: {len(deleted[ext])}")
    if deleted_img_dirs:
        print(f"🖼️  پوشه‌های تصاویر حذف شده: {len(deleted_img_dirs)}")
    print(f"📋 مجموع فایل‌ها: {total_deleted}")
    
    if errors:
        print(f"⚠️  خطاها: {len(errors)}")
        for error in errors:
            print(f"   {error}")
    else:
        print("✅ همه فایل‌ها با موفقیت حذف شدند!")
    
    # نمایش HTML
    summary_html = '<div style="font-family: monospace; background: #f8f8f8; padding: 20px; border-radius: 10px; margin-top: 20px;">'
    summary_html += '<h3 style="margin: 0 0 15px 0; color: #333;">🗑️ خلاصه حذف فایل‌ها</h3>'
    
    total_all = total_deleted + len(deleted_img_dirs)
    if total_all > 0:
        summary_html += '<div style="background: #d4edda; padding: 15px; border-radius: 5px; margin-bottom: 10px;">'
        summary_html += f'<strong style="color: #155724;">✅ {total_deleted} فایل و {len(deleted_img_dirs)} پوشه تصویر حذف شد</strong><br>'
        for ext in OUTPUT_EXTENSIONS:
            if deleted[ext]:
                summary_html += f'<small>{ext}: {len(deleted[ext])} فایل</small><br>'
        if deleted_img_dirs:
            summary_html += f'<small>🖼️ پوشه تصاویر: {len(deleted_img_dirs)}</small><br>'
        if total_all <= 15:
            summary_html += '<ul style="margin: 10px 0 0 0; padding-left: 20px;">'
            for ext in OUTPUT_EXTENSIONS:
                for f in deleted[ext]:
                    summary_html += f'<li style="margin: 3px 0;"><code style="background: #fff; padding: 2px 5px; border-radius: 3px;">{Path(f).name}</code></li>'
            for d in deleted_img_dirs:
                summary_html += f'<li style="margin: 3px 0;"><code style="background: #fff; padding: 2px 5px; border-radius: 3px;">📁 {Path(d).name}</code></li>'
            summary_html += '</ul>'
        summary_html += '</div>'
    else:
        summary_html += '<div style="background: #fff3cd; padding: 15px; border-radius: 5px;">'
        summary_html += '<strong style="color: #856404;">📋 فایلی برای حذف یافت نشد</strong>'
        summary_html += '</div>'
    
    if errors:
        summary_html += '<div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin-top: 10px;">'
        summary_html += f'<strong style="color: #721c24;">⚠️ {len(errors)} خطا</strong>'
        summary_html += '</div>'
    
    summary_html += '</div>'
    display(HTML(summary_html))
