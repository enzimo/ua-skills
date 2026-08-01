---
name: markitdown
description: Convert local documents and supported URLs to Markdown with Microsoft's MarkItDown. Use when Codex needs LLM-friendly Markdown extracted from PDFs, Word documents, PowerPoint decks, Excel workbooks, HTML, CSV, JSON, XML, images, audio, ZIP archives, EPubs, Outlook messages, YouTube URLs, or other document formats.
---

# MarkItDown

Use Microsoft's MarkItDown when a user asks to convert a document or supported
URL into Markdown for reading, summarization, indexing, or downstream LLM
analysis.

## Universal Agents Shell Behavior

Before running conversion commands through Universal Agents, load
`shell-execution-workflows`. Pass the underlying command without an `rtk`
prefix, set `work_dir` instead of relying on a persistent shell, and set an
explicit timeout for large documents or `uvx` dependency startup. Inputs and
outputs must stay inside the configured workspace. Inspect status, exit code,
separate output/error, termination reason, RTK mode, and warnings before
diagnosing conversion failure.

## Core Workflow

1. Identify the source file or URL and the desired output path.
2. Prefer writing Markdown to a file instead of dumping large conversions into
   chat.
3. Use the bundled wrapper script when working from this repo:

```bash
python "${SKILLS_DIR:-skills}/markitdown/scripts/convert_with_markitdown.py" input.pdf -o output.md
```

The wrapper uses an installed `markitdown` command if available. If not, it
falls back to `uvx --from 'markitdown[all]' markitdown ...` when `uvx` is
available, keeping MarkItDown out of the project dependency set.

## Direct CLI

If MarkItDown is already installed in the active environment, direct CLI use is
also fine:

```bash
markitdown path/to/document.pdf -o path/to/document.md
```

For one-off isolated execution:

```bash
uvx --from 'markitdown[all]' markitdown path/to/document.pdf -o path/to/document.md
```

## Supported Inputs

MarkItDown supports common document formats including PDF, DOCX, PPTX, XLSX,
HTML, text-based formats such as CSV/JSON/XML, images, audio, ZIP archives,
YouTube URLs, EPubs, and Outlook messages. Optional dependency groups control
some format support; use `markitdown[all]` for broad compatibility unless the
task needs a smaller install surface.

## Plugins and OCR

Plugins are disabled by default. Enable them only when the conversion requires a
known installed plugin:

```bash
python "${SKILLS_DIR:-skills}/markitdown/scripts/convert_with_markitdown.py" input.pdf -o output.md --use-plugins
```

For image-heavy PDFs, DOCX, PPTX, or XLSX files, consider the `markitdown-ocr`
plugin if it is installed and an LLM vision client is configured. Do not assume
OCR ran unless the command output or resulting Markdown shows extracted image
text.

## Azure Document Intelligence

When the user explicitly wants Azure Document Intelligence conversion and has
provided an endpoint, pass it through:

```bash
python "${SKILLS_DIR:-skills}/markitdown/scripts/convert_with_markitdown.py" input.pdf -o output.md \
  --docintel-endpoint "$DOCUMENT_INTELLIGENCE_ENDPOINT"
```

Do not invent, persist, or request service credentials in chat. Prefer existing
environment variables, configured CLI auth, credential-store values, or
secret-file mounts. If Azure or another service credential is required and not
already hydrated, instruct the user to provide it through the runtime credential
collection form before retrying.

## Validation

After conversion:

- Confirm the output file exists and is non-empty.
- Skim the first section and relevant headings/tables for obvious extraction
  failures.
- For scanned or image-heavy inputs, state whether OCR was used or whether text
  may be missing.
- If conversion fails because MarkItDown or `uvx` is unavailable, report the
  exact missing tool and the install command:

```bash
python -m pip install 'markitdown[all]'
```
