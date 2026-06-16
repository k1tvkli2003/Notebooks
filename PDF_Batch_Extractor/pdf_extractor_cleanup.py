"""
PDF Batch Extractor - Cleanup Module
حذف فایل‌های تولید شده در مرحله پردازش
"""

from pathlib import Path
from IPython.display import display, HTML

def cleanup_generated_files(pdf_files_list):
    """حذف همه فایل‌های .md و پوشه‌های images_*"""
    print("="*80)
    print("🗑️  شروع حذف فایل‌های تولید شده...")
    print("="*80)
    print()
    
    deleted_md = []
    deleted_folders = []
    errors = []
    
    # پیدا کردن و حذف فایل‌های .md
    for pdf_file in pdf_files_list:
        md_file = pdf_file.parent / f"{pdf_file.stem}.md"
        if md_file.exists():
            try:
                md_file.unlink()
                deleted_md.append(str(md_file))
                print(f"✅ فایل حذف شد: {md_file.name}")
            except Exception as e:
                error_msg = f"❌ خطا در حذف {md_file.name}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
    
    # پیدا کردن و حذف پوشه‌های images_*
    for pdf_file in pdf_files_list:
        images_folder = pdf_file.parent / f"images_{pdf_file.stem}"
        if images_folder.exists() and images_folder.is_dir():
            try:
                # حذف همه فایل‌ها در پوشه
                for img_file in images_folder.iterdir():
                    img_file.unlink()
                # حذف پوشه
                images_folder.rmdir()
                deleted_folders.append(str(images_folder))
                print(f"✅ پوشه حذف شد: {images_folder.name}")
            except Exception as e:
                error_msg = f"❌ خطا در حذف پوشه {images_folder.name}: {str(e)}"
                errors.append(error_msg)
                print(error_msg)
    
    # نمایش خلاصه
    print()
    print("="*80)
    print("📊 خلاصه حذف:")
    print("="*80)
    print(f"🗑️  فایل‌های .md حذف شده: {len(deleted_md)}")
    print(f"📁 پوشه‌های images حذف شده: {len(deleted_folders)}")
    
    if errors:
        print(f"⚠️  خطاها: {len(errors)}")
        print("\n❌ جزئیات خطاها:")
        for error in errors:
            print(f"   {error}")
    else:
        print("✅ همه فایل‌ها با موفقیت حذف شدند!")
    
    # نمایش HTML
    summary_html = '<div style="font-family: monospace; background: #f8f8f8; padding: 20px; border-radius: 10px; margin-top: 20px;">'
    summary_html += '<h3 style="margin: 0 0 15px 0; color: #333;">🗑️ خلاصه حذف فایل‌ها</h3>'
    
    if deleted_md:
        summary_html += '<div style="background: #d4edda; padding: 15px; border-radius: 5px; margin-bottom: 10px;">'
        summary_html += f'<strong style="color: #155724;">✅ {len(deleted_md)} فایل .md حذف شد</strong>'
        if len(deleted_md) <= 10:
            summary_html += '<ul style="margin: 10px 0 0 0; padding-left: 20px;">'
            for md in deleted_md:
                summary_html += f'<li style="margin: 3px 0;"><code style="background: #fff; padding: 2px 5px; border-radius: 3px;">{Path(md).name}</code></li>'
            summary_html += '</ul>'
        else:
            summary_html += f'<div style="margin-top: 10px; font-size: 14px;">(تعداد زیاد - لیست نمایش داده نشد)</div>'
        summary_html += '</div>'
    
    if deleted_folders:
        summary_html += '<div style="background: #d1ecf1; padding: 15px; border-radius: 5px; margin-bottom: 10px;">'
        summary_html += f'<strong style="color: #0c5460;">📁 {len(deleted_folders)} پوشه images حذف شد</strong>'
        if len(deleted_folders) <= 10:
            summary_html += '<ul style="margin: 10px 0 0 0; padding-left: 20px;">'
            for folder in deleted_folders:
                summary_html += f'<li style="margin: 3px 0;"><code style="background: #fff; padding: 2px 5px; border-radius: 3px;">{Path(folder).name}</code></li>'
            summary_html += '</ul>'
        else:
            summary_html += f'<div style="margin-top: 10px; font-size: 14px;">(تعداد زیاد - لیست نمایش داده نشد)</div>'
        summary_html += '</div>'
    
    if errors:
        summary_html += '<div style="background: #f8d7da; padding: 15px; border-radius: 5px;">'
        summary_html += f'<strong style="color: #721c24;">⚠️ {len(errors)} خطا رخ داد</strong>'
        summary_html += '<div style="max-height: 200px; overflow-y: auto; margin-top: 10px; background: #fff; padding: 10px; border-radius: 3px;">'
        for error in errors:
            summary_html += f'<div style="margin: 5px 0; font-size: 13px; color: #721c24;">{error}</div>'
        summary_html += '</div></div>'
    
    if not deleted_md and not deleted_folders:
        summary_html += '<div style="background: #fff3cd; padding: 15px; border-radius: 5px; color: #856404;">'
        summary_html += '<strong>ℹ️ هیچ فایلی برای حذف یافت نشد</strong>'
        summary_html += '</div>'
    
    summary_html += '</div>'
    display(HTML(summary_html))
    
    return {
        'deleted_md': deleted_md,
        'deleted_folders': deleted_folders,
        'errors': errors
    }
