"""Renders a story to a landscape A4 PDF for printing."""

import os
from pathlib import Path
from fpdf import FPDF

# A4 landscape dimensions (mm)
PAGE_W = 297
PAGE_H = 210
MARGIN = 12
GAP = 10

# Panel widths
USABLE_W = PAGE_W - 2 * MARGIN
LEFT_W = round(USABLE_W * 0.65, 2)
RIGHT_W = USABLE_W - LEFT_W - GAP
RIGHT_X = MARGIN + LEFT_W + GAP
USABLE_H = PAGE_H - 2 * MARGIN

FONT_DIR = Path(__file__).parent.parent / "fonts"

PLACEHOLDER_GREY = (200, 200, 200)
PAGE_NUM_GREY = (180, 180, 180)
SUBTITLE_GREY = (100, 100, 100)


class StoryPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)
        self.add_font("Poppins", style="", fname=str(FONT_DIR / "Poppins-Regular.ttf"))
        self.add_font("Poppins", style="B", fname=str(FONT_DIR / "Poppins-Bold.ttf"))
        self.add_font("Poppins", style="I", fname=str(FONT_DIR / "Poppins-Italic.ttf"))

    def _draw_image_panel(self, image_path: str | None, output_dir: str):
        """Draw the left image panel — image or grey placeholder."""
        panel_x = MARGIN
        panel_y = MARGIN

        if image_path:
            # Paths in the DB are already workspace-relative (e.g. output/story_x/img.png)
            if os.path.isabs(image_path):
                full_path = image_path
            elif os.path.exists(image_path):
                full_path = image_path
            else:
                full_path = os.path.join(output_dir, image_path)
            if os.path.exists(full_path):
                # Fit 3:2 image inside panel, preserve aspect ratio, center vertically
                img_h = LEFT_W * 2 / 3
                if img_h > USABLE_H:
                    img_h = USABLE_H
                    img_w = img_h * 3 / 2
                else:
                    img_w = LEFT_W
                img_x = panel_x + (LEFT_W - img_w) / 2
                img_y = panel_y + (USABLE_H - img_h) / 2
                self.image(full_path, x=img_x, y=img_y, w=img_w, h=img_h)
                return

        # Placeholder
        self.set_fill_color(*PLACEHOLDER_GREY)
        self.rect(panel_x, panel_y, LEFT_W, USABLE_H, style="F")

    def _draw_text_panel(self, text: str, page_num: int, total_pages: int):
        """Draw the right text panel — centered story text + page number."""
        self.set_font("Poppins", size=22)
        line_height = 9  # mm per line at 22pt

        # Measure wrapped lines to compute total block height
        lines = self._wrap_text(text, RIGHT_W)
        block_h = len(lines) * line_height

        # Vertically center the text block
        text_y = MARGIN + (USABLE_H - block_h) / 2
        text_y = max(MARGIN, text_y)

        self.set_text_color(0, 0, 0)
        for line in lines:
            self.set_xy(RIGHT_X, text_y)
            self.cell(RIGHT_W, line_height, line, align="L")
            text_y += line_height

        # Page number — bottom right of text panel
        self.set_font("Poppins", size=10)
        self.set_text_color(*PAGE_NUM_GREY)
        label = f"{page_num} / {total_pages}"
        self.set_xy(RIGHT_X, MARGIN + USABLE_H - 7)
        self.cell(RIGHT_W, 7, label, align="R")

    def _wrap_text(self, text: str, width_mm: float) -> list[str]:
        """Word-wrap text to fit within width_mm using current font settings."""
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if self.get_string_width(candidate) <= width_mm:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def add_title_page(self, title: str, tone: str):
        self.add_page()
        # Center everything vertically
        self.set_font("Poppins", style="B", size=36)
        title_h = 20
        subtitle_h = 12
        footer_h = 10
        block_h = title_h + 6 + subtitle_h + 20 + footer_h
        y = (PAGE_H - block_h) / 2

        self.set_text_color(0, 0, 0)
        self.set_xy(MARGIN, y)
        self.cell(PAGE_W - 2 * MARGIN, title_h, title, align="C")

        self.set_font("Poppins", style="I", size=18)
        self.set_text_color(*SUBTITLE_GREY)
        self.set_xy(MARGIN, y + title_h + 6)
        self.cell(PAGE_W - 2 * MARGIN, subtitle_h, f"A {tone} story", align="C")

        self.set_font("Poppins", size=11)
        self.set_text_color(*PAGE_NUM_GREY)
        self.set_xy(MARGIN, PAGE_H - MARGIN - footer_h)
        self.cell(PAGE_W - 2 * MARGIN, footer_h, "Made with TaleSnap", align="C")

    def add_story_page(self, text: str, image_path: str | None, output_dir: str, page_num: int, total_pages: int):
        self.add_page()
        self._draw_image_panel(image_path, output_dir)
        self._draw_text_panel(text, page_num, total_pages)


def render_story_pdf(story: dict, output_dir: str) -> bytes:
    """Generate a PDF for the given story dict and return the raw bytes."""
    pdf = StoryPDF()

    pages = sorted(story["pages"], key=lambda p: p["page_number"])
    total = len(pages)

    pdf.add_title_page(story["title"], story["tone"])

    for page in pages:
        pdf.add_story_page(
            text=page["text"],
            image_path=page.get("illustration_path"),
            output_dir=output_dir,
            page_num=page["page_number"],
            total_pages=total,
        )

    return bytes(pdf.output())
