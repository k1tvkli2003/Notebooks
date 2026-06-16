# Page Continuity Rules

## Context
- Each page is processed as a separate image
- Text may be cut mid-sentence at page boundaries
- The merge process will combine pages later

## Rules
1. **No artificial breaks**: Do not add "---" or page separators
2. **Incomplete sentences**: If text is cut at the bottom of the page, output it exactly as-is (do not try to complete it)
3. **Continuation from previous page**: If text starts mid-sentence at the top, output it as-is without adding context
4. **Headers/Footers**: Include page numbers and headers only if they are part of the meaningful content. Skip repetitive running headers/footers (e.g., book title, chapter name repeated on every page)
5. **Cross-references**: Keep references like "به صفحه بعد مراجعه شود" (see next page) or "ادامه از صفحه قبل" (continued from previous page) exactly as they appear
