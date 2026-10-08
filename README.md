# Notebooks

Notebooks is the content-generation workbench behind StudyHUB: Jupyter notebooks plus Python tooling that turn raw sources (textbooks, PDFs, audio) into structured lesson Markdown, validated chapters, and print-ready PDFs.

## What's inside

- **Lesson_MD_PDF** — the main pipeline: chapter/lesson staging, Markdown writer and splitter, Markdown-to-PDF export, prompt builder, source loader, staged orchestration, tests, and deployment helpers.
- **prompt_modules/** — shared prompt library plus delegator tools (`workflow_delegator.py`, `prompt_delegator`, `validation.py`, `task_utils.py`, `optimizer_delegator.py`) — the prompts and gates that studyhub-content later ported to Jules.
- **PDF_Batch_Extractor** — Jupyter-driven batch PDF extraction (`PDF_Batch_Extractor.ipynb` plus processor/setup/cleanup modules).
- **PDF_Batch_Extractor_AvalAI** — AvalAI-routed OCR variant (`avalai_ocr_processor.py`, prompt modules).
- **Audio_Transcriber** — audio-to-text notebook and processor for lecture recordings.

## Tech stack

Python, Jupyter, Markdown-to-PDF tooling, Gemini research helpers, image download and chunking utilities.

## Getting started

Open the relevant `.ipynb` in Jupyter (or run the `lesson_nb` / extractor modules directly) against local sources. Outputs land in `out/`; nothing here deploys on its own — downstream repos (studyhub-content, StudyHUB apps) consume what this workbench produces.

## Status

Active workbench. All three pipelines exist with tools, prompts, and tests; outputs are work-in-progress content rather than releases.
