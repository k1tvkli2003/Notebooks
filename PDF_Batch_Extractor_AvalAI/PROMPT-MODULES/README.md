# PROMPT-MODULES

This folder contains all prompt rules and instructions that the OCR agent **MUST** read before processing any PDF page. These prompts ensure accurate, clean, and reliable text extraction from PDF images.

## Files

| File | Purpose |
|------|---------|
| `ocr_system_prompt.md` | Core system prompt for OCR extraction |
| `rtl_rules.md` | Rules for right-to-left (Persian/Arabic) text handling |
| `table_rules.md` | Rules for accurate table recognition and formatting |
| `column_rules.md` | Rules for multi-column layout detection and ordering |
| `page_continuity_rules.md` | Rules for handling text continuity across pages |
| `quality_rules.md` | Quality control rules for clean output |

## Usage

The OCR processor reads ALL files in this folder at startup and combines them into the final prompt sent to the OCR model. Modifying any file here will affect all future OCR processing.
