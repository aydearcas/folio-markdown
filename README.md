# Folio 0.2.3

**Local document-to-Markdown conversion with a clean bilingual desktop interface.**

Folio converts PDF, DOCX, TXT, Markdown, CSV and TSV files into Markdown that is easier to read, search and use as input for large language models. PDF processing can use either [LiteParse](https://github.com/run-llama/liteparse) or [Docling](https://github.com/docling-project/docling), while editable text formats are handled directly on your computer.

[English user guide](README_EN.md) · [Guía en español](README_ES.md) · [Upgrade notes](UPDATE_0.2.3.md)

Folio can help prepare openly licensed scientific articles and other documents you are permitted to process for literature reviews and evidence extraction. Markdown makes document structure easier to inspect; it does not guarantee better LLM answers or lossless extraction.

> [!IMPORTANT]
> Folio is a technical preview. Always compare tables, figures, numerical values and references against the original document before using extracted content in research or evidence synthesis.

![Folio desktop interface showing a mixed PDF, DOCX, TXT and CSV batch](screenshots/interface_en.png)

## Highlights

- Local desktop application built with Python and PySide6.
- Spanish and English interface, switchable at any time.
- Mixed batches containing PDF and text documents.
- Automatic file-type detection with optional PDF/Text enforcement.
- Choice of LiteParse, Docling or automatic routing for PDFs.
- PDFium as Docling's default PDF reader, including when automatic routing selects Docling.
- Direct DOCX conversion that preserves document order, headings, common lists, emphasis, hyperlinks, tables and simple notes.
- Direct TXT, Markdown, CSV and TSV conversion without OCR or model downloads.
- Optional structured JSON, image extraction and PDF page-marked Markdown.
- Responsive interface: conversions run in a separate process.
- Originals and previous results are never overwritten.
- No LLM API, account or conversion service required.
- Exportable conversion logs, native exception diagnostics and a Windows shortcut icon.

## What's new in 0.2.3

- **Docling uses PDFium by default on all platforms.** Its layout, table and OCR models are retained; only the component reading the PDF changes.
- The original Docling reader is available under **Advanced settings → Docling PDF reader → Use original (experimental)**. It is initially unchecked. Folio warns that it tends to fail in the tested Windows environment and should only be used for testing.
- Existing installations migrate their old reader preference to PDFium. Other preferences are retained. An explicit choice of the experimental reader made after upgrading is remembered.
- Recent updates also added **Save log**, clearer native exception reports, context-menu and selected-text contrast fixes under a dark system palette, and a validated multi-size `.ico` file. Folio keeps its light interface; this is not a full dark theme.

The original reader produced access-violation and heap-corruption messages in the tested Windows setup. Conversion of the affected document with PDFium was reported successful. This is evidence for a practical default in Folio, not a guarantee that PDFium handles every document or that the original reader fails everywhere.

## Supported formats

| Input | Conversion method | Notes |
| --- | --- | --- |
| PDF | LiteParse or Docling with PDFium by default | Optional OCR, images, structured JSON and page markers. Original Docling reader is experimental in Folio. |
| DOCX | `python-docx` | Preserves the main reading order and common document structure. Optional embedded images. |
| TXT, TEXT, LOG | Direct text reader | Normalizes supported encodings to UTF-8 and escapes literal Markdown syntax. |
| MD, MARKDOWN | Direct copy | Preserves Markdown syntax. Linked assets are not copied. |
| CSV, TSV | Delimited-text reader | Preserves rows and values, including quoted fields and embedded line breaks. |

Legacy DOC, RTF, ODT, XLSX and HTML files are not currently supported. Save them as DOCX/TXT, or export tables as CSV/TSV, before adding them to Folio.

## How automatic mode works

Folio has two separate automatic settings:

1. **Document type → Automatic** detects whether every item is a PDF, DOCX or supported text format. This allows mixed batches.
2. **PDF engine → Automatic** uses LiteParse's document probe as an advisory OCR signal. It selects Docling when OCR appears necessary and Docling is installed; otherwise it uses LiteParse. If only Docling is installed, it uses Docling. It records the reason. Docling uses PDFium unless the experimental original reader was explicitly selected.

Automatic PDF routing is a convenience, not a quality score. It cannot reliably identify every complex table, column layout or extraction problem. When a PDF matters, compare both engines on a representative sample.

## Installation

### Windows

1. Install [64-bit Python 3.12](https://www.python.org/downloads/windows/) and enable **Add python.exe to PATH**.
2. Download or clone this repository and place it in a writable folder, such as `Documents\Folio`.
3. Double-click `install_windows.cmd`.
4. Select an installation profile:
   - **LiteParse + Docling** — complete PDF support; largest download.
   - **LiteParse only** — lighter PDF setup.
   - **Docling only** — Docling PDF setup.
   - **Text documents only** — DOCX, TXT, Markdown, CSV and TSV; no PDF engine.
5. Double-click `start_windows.cmd`.

The installer creates an isolated `.venv` inside the project and does not require administrator rights. It records the resolved packages in `installed-versions.txt`.

To inspect startup errors, use `debug_windows.cmd`. To run the automated checks and example conversions, use `check_windows.cmd`.

### macOS and Linux

The installer accepts 64-bit Python 3.10–3.13; Python 3.12 is the recommended baseline. This range is an installer check, not a claim that every dependency combination has been tested.

```bash
python3 tools/bootstrap.py --engine both
.venv/bin/python main.py
```

Available installation profiles are `both`, `liteparse`, `docling` and `text`:

```bash
python3 tools/bootstrap.py --engine liteparse
python3 tools/bootstrap.py --engine docling
python3 tools/bootstrap.py --engine text
```

Linux systems may require the platform libraries used by Qt. Complete native installation and launcher testing has not yet been performed on macOS.

### Updating an existing Folio 0.2.x installation

1. Close Folio and back up the application folder.
2. Extract this release separately. Copy `folio/`, `tools/` and `diagnose_docling.cmd` over your current installation. Compare any personal code changes before replacing them.
3. Copy `README.md`, `README_EN.md`, `README_ES.md`, `UPDATE_0.2.3.md`, `VALIDATION.md` and `tests/` to keep the documentation and checks current. Include `screenshots/` if you want the linked screenshots locally.
4. Keep your existing `.venv`, model caches, source documents and conversion results. Start Folio with your usual launcher; an already working 0.2.x environment does not need a dependency reinstall for this update.

Folio now initializes the reader preference to PDFium even if a previous version stored the old default. Other preferences remain unchanged. For a 0.1 installation, use the installer to add the text-document dependencies introduced in 0.2. See [upgrade notes](UPDATE_0.2.3.md).

## Using Folio

1. Select **Add files** or drag documents onto the window.
2. Choose **Automatic**, **PDF** or **Text** under document type.
3. For PDFs, choose LiteParse, Docling or the automatic PDF engine.
4. Enable OCR only when needed and select the document language.
5. Choose an output folder and any optional outputs.
6. Select **Convert to Markdown**.
7. Review the rendered Markdown, source, original document and conversion log. Use **Save log** to export the displayed log when troubleshooting.

The PDF controls are disabled for text-only batches because DOCX, TXT, Markdown, CSV and TSV do not require OCR or a PDF engine.

Leave **Use original (experimental)** unchecked for the default Docling configuration. The language selector changes the interface, not the document content or third-party diagnostic messages.

## Output structure

Every successful conversion creates a new folder named after the source, the conversion method and a unique identifier:

```text
report__python-docx__a1b2c3d4e5f6/
├── document.md
├── conversion.json
├── structure.json       # optional
└── images/              # optional
```

| Output | Purpose |
| --- | --- |
| `document.md` | Main UTF-8 Markdown document. |
| `conversion.json` | Provenance report with source SHA-256, detected format, method, settings, versions, duration, status and notices. |
| `structure.json` | Optional structured representation. Its schema depends on the input and engine. |
| `images/` | Optional exported images referenced with relative links. |
| `document.pages.md` | Optional PDF-only copy with `<!-- PDF page: N -->` markers. |

Text documents report `pages: null`; Folio does not invent physical page numbers for reflowable formats. The JSON produced by Docling, LiteParse and direct text conversion is intentionally not presented as interchangeable.

Failed or cancelled work may leave a `.partial_...` directory with an incomplete report. These directories are never presented as completed conversions and are not deleted automatically.

## Python API

Folio's conversion layer can also be used without the GUI:

```python
from pathlib import Path

from folio.core import Options, convert_file

result = convert_file(
    source=Path("report.docx"),
    destination=Path("results"),
    options=Options(
        document_type="auto",
        engine="auto",
        ocr=True,
        ocr_language="eng",
        structured_json=True,
    ),
)

print(result["markdown"])
```

For a PDF with an explicit engine:

```python
options = Options(
    document_type="pdf",
    engine="docling",
    docling_pdfium=True,  # default; keeps the Docling models and uses PDFium to read the PDF
    ocr=True,
    ocr_language="spa",
    images=True,
    page_copy=True,
)
```

Manual engine selection never silently falls back to another PDF engine.

For an explicit experimental comparison only, set `docling_pdfium=False`. Changing this option affects Docling PDF conversions, not LiteParse or direct text conversion.

## Troubleshooting Docling

Start with PDFium, the default reader. If a conversion fails after enabling **Use original (experimental)**, uncheck it and retry. Handled per-file errors allow the batch to continue; an abrupt native process crash stops the current batch. Completed results are retained, and pending files can be retried.

On Windows, double-click `diagnose_docling.cmd`. Select **P** for PDFium, then choose whether to enable OCR. **O** selects the experimental original reader. The script uses the bundled synthetic PDF and creates a separate folder under `diagnostics/` for every run.

```bat
.venv\Scripts\python.exe tools\diagnose_docling.py
.venv\Scripts\python.exe tools\diagnose_docling.py --ocr
.venv\Scripts\python.exe tools\diagnose_docling.py --source "C:\path\document.pdf"
.venv\Scripts\python.exe tools\diagnose_docling.py --original-reader
```

The first three commands use PDFium. `--pdfium` remains available as an explicit flag; `--original-reader` opts into the experimental reader. On macOS/Linux, use `.venv/bin/python` instead of `.venv\Scripts\python.exe`.

The report includes `diagnostic.json` (versions, settings, process result and native exception counts) and `worker.log` (the worker output). These diagnostic files are distinct from each conversion's `conversion.json`.

| Diagnostic status | Meaning | Diagnostic command exit code |
| --- | --- | --- |
| `completed` | Conversion and batch reported completion, with no detected native exception messages. This does not verify content fidelity. | 0 |
| `completed_with_native_notices` | Conversion finished, but native exception messages were detected. Review the log and output. | 2 |
| `failed` / `cancelled` | Conversion failed, completion was not confirmed, or the diagnostic was cancelled. | 1 |

On Windows, a native exception message can appear even when the worker later exits normally. A Qt `CrashExit` confirms abnormal termination, but Qt's raw exit value is not guaranteed valid in that state; the independent diagnostic records the operating-system return code. Ordinary deprecation or cache warnings alone do not establish a fatal failure.

The diagnostic does not reinstall packages or clear caches. Model downloads may still occur. Review local paths and file names before sharing logs; source documents are not needed for an initial report.

## Windows shortcut icon

The application uses `folio/assets/folio.png`; `folio/assets/folio.ico` contains 16, 24, 32, 48, 64, 128 and 256 pixel versions for Windows shortcuts.

Create a shortcut to `start_windows.cmd`, then open the shortcut's **Properties → Shortcut → Change Icon → Browse** and select `folio/assets/folio.ico`. Keep the icon in a permanent location. The `.cmd` file itself does not automatically acquire a custom icon.

## Validation and tests

Run the complete automated suite with the interpreter from Folio's environment:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Run actual example conversions:

```bash
.venv/bin/python tools/smoke_test.py --engine text
.venv/bin/python tools/smoke_test.py --engine liteparse
.venv/bin/python tools/smoke_test.py --engine docling
.venv/bin/python tools/smoke_test.py --engine liteparse --ocr
```

Folio 0.2.3 passed **69 automated tests** in the Linux development environment, with no skipped tests. The documented checks across this release and preceding versions include:

- actual PySide6 interface tests;
- a real worker-process DOCX/TXT batch;
- real DOCX, TXT, Markdown, CSV and TSV conversions;
- a real LiteParse conversion of a two-page synthetic PDF;
- a real mixed PDF, DOCX, TXT and CSV batch from the GUI;
- interface rendering in English and Spanish at compact and standard sizes.
- default PDFium selection, explicit experimental selection, preference migration and persistence;
- native exception reporting and saving logs.

Docling adapter tests use explicit test doubles; actual Docling, Tesseract and EasyOCR conversion were not executed in that development environment. A user reported a successful Docling/PDFium conversion on Windows with 0.2.2; 0.2.3 changes defaults and presentation, not that reader implementation. Native installation, DPI and platform testing remain limited. The synthetic fixtures establish functional behaviour, not general extraction accuracy. This documentation update does not change the application version. See [VALIDATION.md](VALIDATION.md) for the exact scope and remaining checks.

## Privacy and offline use

Document conversion runs locally. Folio does not contain an LLM integration and does not upload documents to a conversion service. Remote Docling services are explicitly disabled, and the worker disables standard Hugging Face telemetry.

Text-document conversion requires no downloads at runtime. Package installation requires internet access, and Docling, EasyOCR or Tesseract language data may download models or resources on first use. Once the required caches have been prepared, they can be reused locally. Folio does not itself enforce a network firewall.

Advanced settings allow prepared Tesseract data and Docling model folders to be selected. Test every required engine and OCR language before relying on an offline workflow.

## Known limitations

### PDF

- Reading order can be wrong in complex multi-column layouts.
- Multi-level or multi-page tables may lose structure.
- Small notes, negative signs, superscripts, equations and figure values require verification.
- Page markers refer to PDF order, which may differ from printed numbering.

### DOCX

- Merged cells are expanded and may repeat content.
- Nested tables are flattened.
- Complex numbering is normalized.
- Text boxes, equations, charts, embedded objects, content controls and pending tracked changes may be omitted or lose structure.
- Images are exported when requested but are not described or OCR-processed.

Folio emits notices for several detectable limitations, but absence of a notice does not guarantee a complete conversion.

## Project structure

```text
Folio/
├── folio/
│   ├── app.py             # PySide6 desktop interface
│   ├── core.py            # conversion orchestration and provenance
│   ├── engines.py         # LiteParse and Docling adapters
│   ├── formats.py         # format and text-encoding detection
│   ├── text_engines.py    # DOCX and direct-text conversion
│   ├── worker.py          # isolated conversion process
│   └── i18n.py            # Spanish and English interface strings
├── tests/
├── tools/
├── examples/
├── screenshots/
├── main.py
└── requirements*.txt
```

## Contributing

Issues and pull requests are welcome. Please include:

- a clear description of the input format and expected result;
- a minimal, non-confidential reproduction file when possible;
- operating system, Python version and installed engine versions;
- the selected Docling reader, relevant warnings from `conversion.json`, and reviewed `diagnostic.json` / `worker.log` files when available.

Do not submit confidential, copyrighted or sensitive source documents unless you have permission to share them. New conversion behaviour should include tests and must preserve originals, provenance and explicit failure reporting.

## License

Folio's own source code is released under the [MIT License](LICENSE).

Dependencies and downloaded models retain their own licenses. Folio does not redistribute their binaries or model weights. Notable dependencies include LiteParse (Apache-2.0), Docling and python-docx (MIT), and PySide6 (LGPLv3/GPLv3 or commercial license).

## Acknowledgements

Folio builds on:

- [LiteParse](https://github.com/run-llama/liteparse) for lightweight PDF-to-Markdown conversion;
- [Docling](https://github.com/docling-project/docling) for local document-layout analysis;
- [python-docx](https://python-docx.readthedocs.io/) for DOCX access;
- [PySide6](https://doc.qt.io/qtforpython-6/) for the desktop interface.
