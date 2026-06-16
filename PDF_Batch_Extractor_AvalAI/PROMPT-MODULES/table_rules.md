# Table Recognition Rules — CRITICAL

Tables are one of the MOST IMPORTANT elements in medical/academic PDFs. You MUST extract them with the HIGHEST accuracy and precision.

## Detection
- Tables have visible borders/grid lines OR aligned columns of text
- Headers are often bold or in a different style
- Medical textbooks frequently use comparison tables
- Even borderless tables (aligned text in columns) MUST be detected and formatted as Markdown tables

## Extraction Rules (MANDATORY)

### 1. Format — Standard Markdown Table
Every table MUST be reproduced using proper Markdown table syntax:
```
| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Cell 1   | Cell 2   | Cell 3   |
```

### 2. Column Order — Language-Aware (CRITICAL)
- **RTL tables (Persian/Arabic)**: Columns MUST be written RIGHT-TO-LEFT — the rightmost column in the original appears as the FIRST column in Markdown output
- **LTR tables (English/Latin)**: Columns MUST be written LEFT-TO-RIGHT — the leftmost column in the original appears as the FIRST column in Markdown output
- **Mixed tables**: Follow the PRIMARY language direction of the table header
- **NEVER** reverse, shuffle, or reorder columns arbitrarily

### 3. Row Order — Preserve Exactly
- Rows MUST appear in the EXACT same order as the original table (top to bottom)
- DO NOT sort, reorder, or group rows
- DO NOT skip any row, even if it seems redundant or empty

### 4. Cell Content — Complete and Precise
- **Preserve ALL cell content**: Every single cell must be reproduced — never skip or summarize
- **Multi-line cells**: If a cell contains multiple lines, join them with `<br>` or use natural inline separation
- **Bullet points in cells**: Use `•` or `-` for items listed within table cells
- **Numbers**: Reproduce numbers exactly as shown (do not convert or round)
- **Units**: Keep all measurement units (mg, mL, %, etc.) exactly as written
- **Abbreviations**: Do not expand abbreviations — keep them as they appear

### 5. Headers
- Identify the header row correctly — it is usually the FIRST row, often bold or visually distinct
- If a table has NO clear header, still use the first row as the Markdown header
- Multi-level headers (stacked): serialize top-to-bottom, e.g., `Main Category / Sub-category`

### 6. Merged Cells and Spans
- If a cell spans multiple columns, write its content once and leave the spanned cells empty, or note with the same content
- If a row header spans the full width, place it as a single-cell row or a sub-heading line above the table segment

### 7. Empty Cells
- Represent empty cells as empty (`| |`) — do NOT insert placeholder text like "N/A" or "-" unless the original has it

### 8. Table Placement in Text
- Place the table at its EXACT position in the text flow
- If the table has a title/caption (e.g., "جدول ۱" or "Table 1"), include it as a bold line ABOVE the table
- If there are footnotes below the table, include them immediately AFTER the table

### 9. Complex Table Scenarios
- **Nested tables**: Flatten into a single table if possible, preserving structure
- **Tables split across pages**: If a table continues from a previous page, reproduce the visible portion on this page. Do NOT fabricate missing rows
- **Very wide tables** (many columns): Include ALL columns — never truncate
- **Color-coded cells**: Ignore background colors, extract text content only

### 10. Quality Checklist (Self-Verify)
Before outputting a table, verify:
- ✅ Number of columns matches the original
- ✅ Number of rows matches the original
- ✅ Column order matches the reading direction (RTL or LTR)
- ✅ Row order matches top-to-bottom
- ✅ No cells are missing or duplicated
- ✅ Header row is correctly identified
- ✅ All cell content is complete
