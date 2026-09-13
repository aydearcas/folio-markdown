"""Deterministic converters for editable documents; no OCR or network calls."""
from __future__ import annotations

import csv
import html
import io
from pathlib import Path
from types import SimpleNamespace
import re
from urllib.parse import quote, urlsplit

from .core import ConversionError, Options, write_json
from .formats import read_text


def escape_md(value: str) -> str:
    value = html.escape(value, quote=False)
    value = re.sub(r"([\\`*_\[\]|#])", r"\\\1", value)
    value = re.sub(r"(?m)^(\s*)([-+])(?=\s)", r"\1\\\2", value)
    return re.sub(r"(?m)^(\s*\d+)([.)])(?=\s)", r"\1\\\2", value)


def markdown_table(rows: list[list[str]], header: bool = False) -> str:
    width = max((len(row) for row in rows), default=0)
    if not width:
        return ""
    cells = [[cell.replace("\n", "<br>") for cell in row] + [""] * (width - len(row)) for row in rows]
    # Do not invent column names or interpret a data row as a header.
    first = cells.pop(0) if header else [""] * width
    return "\n".join("| " + " | ".join(row) + " |" for row in [first, ["---"] * width, *cells])


class DocxReader:
    def __init__(self, source: Path, stage: Path, options: Options):
        try:
            from docx import Document
        except ImportError as exc:
            raise ConversionError("missing_engine", "python-docx") from exc
        try:
            self.doc = Document(source)
        except Exception as exc:
            raise ConversionError("invalid_docx", str(exc)) from exc
        self.stage, self.options = stage, options
        self.warnings, self.blocks, self.image_files = [], [], {}
        self.counters = {}
        self.has_lists = False

    def warn(self, code: str, detail: str = ""):
        notice = {"code": code}
        if detail:
            notice["detail"] = detail
        if notice not in self.warnings:
            self.warnings.append(notice)

    def image(self, run, node) -> str:
        from docx.oxml.ns import qn
        if not self.options.images:
            self.warn("docx_images_omitted")
            return ""
        rid = node.get(qn("r:embed"))
        if not rid:
            self.warn("docx_external_image")
            return ""
        try:
            part = run.part.related_parts[rid]
            key = str(part.partname)
            if key not in self.image_files:
                ext = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
                       "image/bmp": ".bmp", "image/tiff": ".tiff", "image/x-emf": ".emf",
                       "image/x-wmf": ".wmf", "image/svg+xml": ".svg"}.get(part.content_type, ".bin")
                folder = self.stage / "images"
                folder.mkdir(exist_ok=True)
                path = folder / f"image_{len(self.image_files) + 1:03d}{ext}"
                path.write_bytes(part.blob)
                self.image_files[key] = path.relative_to(self.stage).as_posix()
                if ext not in (".png", ".jpg", ".bmp"):
                    self.warn("image_preview_format", ext)
            return f"![Image](<{self.image_files[key]}>)"
        except (KeyError, AttributeError) as exc:
            self.warn("docx_image_failed", str(exc))
            return ""

    def run(self, run) -> str:
        from docx.oxml.ns import qn
        out = []
        for node in run._r:
            if node.tag == qn("w:t"):
                out.append(escape_md(node.text or ""))
            elif node.tag == qn("w:tab"):
                out.append("\t")
            elif node.tag in (qn("w:br"), qn("w:cr")):
                out.append("  \n")
            elif node.tag in (qn("w:drawing"), qn("w:pict")):
                for image in node.xpath(".//a:blip"):
                    out.append(self.image(run, image))
                if node.tag == qn("w:pict"):
                    self.warn("docx_complex", "VML drawing")
            elif node.tag in (qn("w:footnoteReference"), qn("w:endnoteReference")):
                kind = "fn" if node.tag == qn("w:footnoteReference") else "en"
                out.append(f"[^{kind}{node.get(qn('w:id'))}]")
        value = "".join(out)
        if not value.strip():
            return value
        lead, trail = value[:len(value) - len(value.lstrip())], value[len(value.rstrip()):]
        value = value.strip()
        if run.bold:
            value = f"**{value}**"
        if run.italic:
            value = f"*{value}*"
        if run.font.superscript:
            value = f"<sup>{value}</sup>"
        if run.font.subscript:
            value = f"<sub>{value}</sub>"
        return lead + value + trail

    def inline(self, paragraph) -> str:
        from docx.text.run import Run
        result = []
        for item in paragraph.iter_inner_content():
            if isinstance(item, Run):
                result.append(self.run(item))
            else:
                text = "".join(self.run(run) for run in item.runs)
                target = item.url
                if target and urlsplit(target).scheme in ("http", "https", "mailto"):
                    target = quote(target, safe=":/?#@!$&'*,;=+%")
                    result.append(f"[{text}](<{target}>)")
                else:
                    result.append(text)
        return "".join(result)

    def list_prefix(self, paragraph) -> str:
        from docx.oxml.ns import qn
        prop = paragraph._p.pPr
        num = prop.numPr if prop is not None else None
        style = paragraph.style
        visited = set()
        while num is None and style is not None and style.style_id not in visited:
            visited.add(style.style_id)
            ppr = style.element.pPr
            num = ppr.numPr if ppr is not None else None
            style = style.base_style
        if num is None or num.numId is None or num.numId.val == 0:
            return ""
        self.has_lists = True
        num_id, level = str(num.numId.val), num.ilvl.val if num.ilvl is not None else 0
        root = self.doc.part.numbering_part.element
        nums = root.xpath(f'./w:num[@w:numId="{num_id}"]')
        if not nums:
            self.warn("docx_numbering")
            return "    " * level + "- "
        abstract_id = nums[0].find(qn("w:abstractNumId")).get(qn("w:val"))
        levels = root.xpath(f'./w:abstractNum[@w:abstractNumId="{abstract_id}"]/w:lvl[@w:ilvl="{level}"]')
        if not levels:
            self.warn("docx_numbering")
            return "    " * level + "- "
        overrides = nums[0].xpath(f'./w:lvlOverride[@w:ilvl="{level}"]')
        effective = levels[0]
        if overrides and overrides[0].find(qn("w:lvl")) is not None:
            effective = overrides[0].find(qn("w:lvl"))
        fmt = effective.find(qn("w:numFmt"))
        fmt = fmt.get(qn("w:val")) if fmt is not None else "decimal"
        if fmt == "bullet":
            return "    " * level + "- "
        start = effective.find(qn("w:start"))
        start_value = int(start.get(qn("w:val"))) if start is not None else 1
        if overrides:
            override = overrides[0].find(qn("w:startOverride"))
            if override is not None:
                start_value = int(override.get(qn("w:val")))
        key = (num_id, level)
        count = self.counters.get(key, start_value - 1) + 1
        self.counters[key] = count
        for other in list(self.counters):
            if other[0] == num_id and other[1] > level:
                del self.counters[other]
        # Markdown supports decimal numbering; labels such as a) or 1.2 are lossy.
        label = effective.find(qn("w:lvlText"))
        if fmt != "decimal" or (label is not None and label.get(qn("w:val")) != f"%{level + 1}."):
            self.warn("docx_numbering")
        return "    " * level + f"{count}. "

    def paragraph(self, paragraph, in_cell: bool = False) -> str:
        value = self.inline(paragraph)
        style = paragraph.style.name if paragraph.style else ""
        match = re.fullmatch(r"Heading (\d+)", style, re.I)
        prefix = ""
        if not in_cell:
            if match:
                prefix = "#" * min(int(match[1]), 6) + " "
            elif style == "Title":
                prefix = "# "
            else:
                prefix = self.list_prefix(paragraph)
        return prefix + value if value.strip() else ""

    def table(self, table) -> tuple[str, dict]:
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        rows, raw = [], []
        merged = bool(table._tbl.xpath(".//w:gridSpan | .//w:vMerge"))
        if merged:
            self.warn("docx_merged_cells")
        for row in table.rows:
            cells, plain = [], []
            # Preserve absent grid cells as blanks so columns don't shift.
            cells.extend([""] * row.grid_cols_before)
            plain.extend([""] * row.grid_cols_before)
            for cell in row.cells:
                parts = []
                for child in cell.iter_inner_content():
                    if isinstance(child, Paragraph):
                        parts.append(self.paragraph(child, in_cell=True))
                    elif isinstance(child, Table):
                        nested, _ = self.table(child)
                        parts.append(escape_md(nested))
                        self.warn("docx_nested_table")
                cells.append("<br>".join(p for p in parts if p))
                plain.append(cell.text)
            cells.extend([""] * row.grid_cols_after)
            plain.extend([""] * row.grid_cols_after)
            rows.append(cells)
            raw.append(plain)
        header = bool(table.rows and table.rows[0]._tr.xpath("./w:trPr/w:tblHeader[not(@w:val) or @w:val='1' or @w:val='true' or @w:val='on']"))
        return markdown_table(rows, header), {"type": "table", "rows": raw, "merged_cells_expanded": merged}

    def convert(self) -> dict:
        from docx.oxml import parse_xml
        from docx.oxml.ns import qn
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        parts = []
        body = self.doc.element.body
        # These constructs are not exposed faithfully by python-docx iteration.
        unsupported = {
            "tracked changes": ".//w:ins | .//w:del | .//w:moveFrom | .//w:moveTo",
            "text boxes": ".//w:txbxContent", "equations": ".//m:oMath",
            "content controls": ".//w:sdt", "embedded objects": ".//w:object | .//w:altChunk",
            "charts / diagrams": ".//c:chart | .//dgm:relIds",
        }
        for label, expression in unsupported.items():
            # c and dgm are not registered in every python-docx version.
            if label == "charts / diagrams":
                found = body.xpath('.//*[local-name()="chart" or local-name()="relIds"]')
            else:
                found = body.xpath(expression)
            if found:
                self.warn("docx_complex", label)
        for item in self.doc.iter_inner_content():
            if isinstance(item, Paragraph):
                md = self.paragraph(item)
                block = {"type": "paragraph", "style": item.style.name if item.style else "", "text": item.text, "markdown": md}
            elif isinstance(item, Table):
                md, block = self.table(item)
            else:
                continue
            block["index"] = len(self.blocks) + 1
            self.blocks.append(block)
            if md:
                parts.append(md)
        if self.options.keep_headers:
            seen = set()
            for section in self.doc.sections:
                for holder in (section.header, section.first_page_header, section.even_page_header,
                               section.footer, section.first_page_footer, section.even_page_footer):
                    if holder.is_linked_to_previous:
                        continue
                    key = str(holder.part.partname)
                    if key in seen:
                        continue
                    seen.add(key)
                    for item in holder.iter_inner_content():
                        md = self.paragraph(item) if isinstance(item, Paragraph) else self.table(item)[0]
                        if md:
                            parts.append(md)
                            self.blocks.append({"index": len(self.blocks) + 1, "type": "header_footer", "markdown": md})
                    self.warn("docx_headers_appended")
        for rel in self.doc.part.rels.values():
            kind = "fn" if rel.reltype.endswith("/footnotes") else "en" if rel.reltype.endswith("/endnotes") else None
            if kind is None:
                continue
            root = parse_xml(rel.target_part.blob)
            for note in root:
                ident = note.get(qn("w:id"))
                if ident is None or int(ident) < 1:
                    continue
                parent = SimpleNamespace(part=rel.target_part)
                paragraphs = [self.inline(Paragraph(p, parent)) for p in note.findall(qn("w:p"))]
                content = "\n    ".join(p for p in paragraphs if p)
                if content:
                    parts.append(f"[^{kind}{ident}]: {content}")
                    self.blocks.append({"index": len(self.blocks) + 1, "type": "note", "id": kind + ident, "markdown": content})
                if any(child.tag != qn("w:p") for child in note):
                    self.warn("docx_complex", "non-paragraph footnote content")
        (self.stage / "document.md").write_text("\n\n".join(parts).rstrip() + "\n", encoding="utf-8")
        return {"blocks": self.blocks, "images": list(self.image_files.values()), "warnings": self.warnings}


def run_text(source: Path, stage: Path, options: Options, file_format: str, emit) -> dict:
    emit({"event": "phase", "code": "parsing", "engine": "python-docx" if file_format == "docx" else file_format.upper()})
    if file_format == "docx":
        data = DocxReader(source, stage, options).convert()
        warnings = data.pop("warnings")
    else:
        value, encoding, warnings = read_text(source)
        if not value.strip():
            raise ConversionError("empty_text")
        data = {"encoding": encoding}
        if file_format in ("csv", "tsv"):
            delimiter = "\t" if file_format == "tsv" else ","
            if file_format == "csv":
                try:
                    delimiter = csv.Sniffer().sniff(value[:65536], delimiters=",;\t").delimiter
                except csv.Error:
                    pass
            try:
                rows = list(csv.reader(io.StringIO(value, newline=""), delimiter=delimiter, strict=True))
            except csv.Error as exc:
                raise ConversionError("invalid_delimited", str(exc)) from exc
            data.update(rows=rows, delimiter=delimiter)
            md = markdown_table([[escape_md(cell) for cell in row] for row in rows]) + "\n"
        elif file_format == "md":
            md = value
            data["text"] = value
            if re.search(r"!\[|<img\b|\]\[", value, re.I):
                warnings.append({"code": "markdown_assets"})
        else:
            data["text"] = value
            md = escape_md(value).replace("\n", "  \n").rstrip() + "\n"
        (stage / "document.md").write_text(md, encoding="utf-8")
    if options.page_copy:
        warnings.append({"code": "text_no_pages"})
    if options.structured_json:
        write_json(stage / "structure.json", {"schema": "folio.text.v1", "format": file_format, **data})
    return {"pages": None, "warnings": warnings, "text_encoding": data.get("encoding"),
            "block_count": len(data.get("blocks", [])) or None}
