# Quality Control Rules

## Output Quality Standards
1. **No hallucination**: Never invent or fabricate text that doesn't exist in the image
2. **No OCR artifacts**: Do not output garbled characters, random symbols, or encoding errors
3. **Whitespace**: Use single blank lines between paragraphs. Do not add excessive blank lines
4. **Consistent formatting**: 
   - Use `##` for section headings visible in the document
   - Use `-` or numbered lists for choice items (الف، ب، ج، د)
   - Use `**bold**` only for text that is visually bold in the original
5. **Medical terms**: Reproduce medical terminology exactly — do not "correct" specialized terms
6. **Choice formatting**: For multiple-choice questions, format as:
   ```
   الف) option text
   ب) option text
   ج) option text
   د) option text
   ```
7. **Parenthetical source references**: Keep exam source references exactly as written, e.g., `(دستیاری - اردیبهشت ۹۶)`
8. **Images/Figures**: If there are images/figures on the page, mark their positions using the format specified in the Image Rules section ({{IMG_N: title}}). If no image rules are provided, note the position with `[تصویر]` or `[Figure]`
