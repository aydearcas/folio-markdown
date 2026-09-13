"""Regenerate synthetic PDF fixtures. Development only; requires reportlab/Pillow."""
from pathlib import Path
import reportlab
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "examples"


def main():
    ROOT.mkdir(exist_ok=True)
    font_dir = Path(reportlab.__file__).parent / "fonts"
    pdfmetrics.registerFont(TTFont("FolioSans", str(font_dir / "Vera.ttf")))
    pdfmetrics.registerFont(TTFont("FolioSans-Bold", str(font_dir / "VeraBd.ttf")))
    pdf = canvas.Canvas(str(ROOT / "synthetic_article.pdf"), pagesize=(595, 842))
    pdf.setTitle("Folio synthetic conversion fixture - not clinical evidence")
    for page in (1, 2):
        pdf.setFillColor(colors.HexColor("#236f60"))
        pdf.setFont("FolioSans-Bold", 11)
        pdf.drawString(45, 795, "FOLIO / SYNTHETIC TEST DOCUMENT")
        pdf.setFillColor(colors.HexColor("#26343b"))
        pdf.setFont("FolioSans-Bold", 22)
        pdf.drawString(45, 749, "Document conversion test" if page == 1 else "Second page: provenance")
        pdf.setFont("FolioSans", 10)
        lines = (["This is an artificial PDF for software testing, not clinical evidence.",
                  "The application must preserve Unicode text: español, français.",
                  "Two pages, a short table, headings and a footnote follow."] if page == 1 else
                 ["This second page tests ordering and page attribution.",
                  "Unique marker: FOLIO-PAGE-TWO-9281.",
                  "All values in this fixture are invented for conversion testing.",
                  "Page numbers refer to PDF order, not journal pagination."])
        for n, line in enumerate(lines):
            pdf.drawString(45, 710 - n * 19, line)
        if page == 1:
            pdf.setFont("FolioSans-Bold", 15)
            pdf.drawString(45, 605, "Table 1. Artificial values")
            rows = [("Group", "N", "Value"), ("Sample A", "10", "8"), ("Sample B", "12", "5")]
            for r, row in enumerate(rows):
                y = 565 - r * 34
                pdf.setFillColor(colors.HexColor("#e9f1ee") if r == 0 else colors.white)
                pdf.rect(45, y - 10, 500, 34, fill=1, stroke=0)
                pdf.setFillColor(colors.HexColor("#26343b"))
                pdf.setFont("FolioSans-Bold" if r == 0 else "FolioSans", 11)
                for x, cell in zip((57, 265, 430), row):
                    pdf.drawString(x, y, cell)
                pdf.setStrokeColor(colors.HexColor("#ccd8d4"))
                pdf.line(45, y - 10, 545, y - 10)
            pdf.setFont("FolioSans", 9)
            pdf.drawString(45, 431, "Note: N is an arbitrary count. No results represent real patients.")
            pdf.setFillColor(colors.HexColor("#e1ede9"))
            pdf.roundRect(45, 295, 170, 85, 8, fill=1, stroke=0)
            pdf.setFillColor(colors.HexColor("#236f60"))
            pdf.setFont("FolioSans-Bold", 11)
            pdf.drawString(64, 336, "Vector illustration")
            # Raster fixture so image extraction is genuinely exercised too.
            pic = Image.new("RGB", (200, 90), "#e2ebe8")
            draw = ImageDraw.Draw(pic)
            draw.rectangle((25, 20, 65, 75), fill="#27735f")
            draw.rectangle((85, 40, 125, 75), fill="#649b8d")
            draw.rectangle((145, 10, 185, 75), fill="#acc5bb")
            pdf.drawImage(ImageReader(pic), 285, 295, width=200, height=90)
        pdf.setFont("FolioSans", 9)
        pdf.setFillColor(colors.HexColor("#687980"))
        pdf.drawString(45, 42, "Synthetic test fixture | Not a scientific publication")
        pdf.drawRightString(545, 42, str(page))
        pdf.showPage()
    pdf.save()

    image = Image.new("RGB", (1190, 1684), "white")
    draw = ImageDraw.Draw(image)
    # Pillow's default scalable font avoids platform-specific font paths.
    font = ImageFont.load_default(size=27)
    title = ImageFont.load_default(size=38)
    draw.text((90, 115), "FOLIO OCR FIXTURE", fill="#236f60", font=title)
    for i, line in enumerate(["Synthetic scanned document for software testing.",
                              "Unique marker: FOLIO-OCR-4729.",
                              "This page has no selectable text layer.",
                              "A successful OCR run should recover these sentences.",
                              "Not clinical evidence. No real patient data."]):
        draw.text((90, 230 + i * 60), line, fill="#25343b", font=font)
    scanned = canvas.Canvas(str(ROOT / "synthetic_scan.pdf"), pagesize=(595, 842))
    scanned.setTitle("Folio synthetic OCR fixture")
    scanned.drawImage(ImageReader(image), 0, 0, width=595, height=842)
    scanned.save()
    print(f"Created two synthetic fixtures in {ROOT}")


if __name__ == "__main__":
    main()
