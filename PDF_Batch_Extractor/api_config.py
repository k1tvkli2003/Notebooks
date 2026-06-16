"""
API Configuration Module
تمام API Keys و تنظیمات مرتبط در این فایل قرار دارند
برای تغییر API ها فقط این فایل را ویرایش کنید
"""

from pathlib import Path

# ====================================
# Datalab API Keys
# ====================================
# می‌توانید این لیست را به راحتی تغییر دهید
DATALAB_API_KEYS = [
    "HPsPAUZ_EPb9sq5MTrGkC3ptA15P_fsweWu3fB00cI4",
    "s2ANGrsoJXx8jGzF1jaCq4s1PrZj6lZTC614j1Vh8EI",
    "GcwqTyDiDGvu8up8FMX8-O4FH3ELwRPZ_NtDnWMCcRE",
    "d9PXRyYfXX0yxRHAp8g5N2p3edV4eY_3G_qo1ckG1b0",
    "i1hrHnhcFl0glOPIFpoeJkAgBGvgLbd4KAUgjl-L7HQ"
]

# ====================================
# GitHub GPT-5 Configuration
# ====================================
GITHUB_TOKEN = "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"
GITHUB_ENDPOINT = "https://models.github.ai/inference"
GPT5_MODEL = "openai/gpt-5"

# ====================================
# Helper Function: Load API Keys from File
# ====================================
def load_api_keys_from_md(md_file_path=None):
    """
    بارگذاری API keys از فایل markdown
    
    Args:
        md_file_path: مسیر فایل MD. اگر None باشد، از مسیر پیش‌فرض استفاده می‌شود
    
    Returns:
        list: لیست API keys
    """
    if md_file_path is None:
        # مسیر پیش‌فرض
        md_file_path = Path(__file__).parent / "Docs" / "datalabAPI.md"
    else:
        md_file_path = Path(md_file_path)
    
    if not md_file_path.exists():
        print(f"⚠️ فایل {md_file_path} یافت نشد. از API keys پیش‌فرض استفاده می‌شود.")
        return DATALAB_API_KEYS
    
    try:
        api_keys = []
        with open(md_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                raw_line = line.strip()
                # فقط خطوطی که شبیه API key هستند (حداقل 20 کاراکتر و بدون فاصله)
                if raw_line and len(raw_line) > 20 and ' ' not in raw_line and not raw_line.startswith('#'):
                    # رفع escape های معمول در Markdown (مثل \_ به جای _)
                    cleaned = raw_line.replace("\\_", "_")
                    api_keys.append(cleaned)

        if api_keys:
            print(f"✅ {len(api_keys)} API key از {md_file_path.name} بارگذاری شد")
            return api_keys
        else:
            print(f"⚠️ هیچ API key معتبری در {md_file_path.name} یافت نشد. از keys پیش‌فرض استفاده می‌شود.")
            return DATALAB_API_KEYS
            
    except Exception as e:
        print(f"❌ خطا در خواندن فایل: {str(e)}")
        print("⚠️ از API keys پیش‌فرض استفاده می‌شود.")
        return DATALAB_API_KEYS

# ====================================
# Auto-load from MD file (optional)
# ====================================
# اگر می‌خواهید به صورت خودکار از فایل MD بارگذاری شود، خط زیر را uncomment کنید:
# DATALAB_API_KEYS = load_api_keys_from_md()

# ====================================
# GPT-5 Correction Prompt
# ====================================
CORRECTION_PROMPT = """شما یک ویرایشگر متن حرفه‌ای هستید. وظیفه شما اصلاح و بهبود متن استخراج شده از PDF است.

**مشکلاتی که باید برطرف کنید:**
1. خطاهای OCR (املا، حروف اشتباه، کلمات چسبیده/جدا)
2. ناپیوستگی متن بین صفحات
3. پانویس‌ها (فرمت [^1])
4. هدر و فوتر تکراری (حذف)
5. جداول (بازسازی ساختار)
6. فرمول‌های ریاضی (فرمت LaTeX)
7. لیست‌ها و شماره‌گذاری
8. فاصله‌گذاری و paragraph ها

**قوانین:**
- فقط متن اصلاح شده را برگردانید
- ساختار Markdown را حفظ کنید
- محتوای اصلی را تغییر ندهید
- فرمت تصاویر را دست نزنید
"""
