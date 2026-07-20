"""Research buddy: open-access PDF acquisition → structure-aware markdown (Phase 1).

PDF is converted to markdown before any model sees it; PDF, markdown, and metadata
are stored together as PaperAssets (ARCHITECTURE.md §3.1, §6).
"""

from __future__ import annotations

import hashlib
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pymupdf
from pypdf import PdfReader

from ..storage.models import Paper, PaperAsset
from .library import DEFAULT_LIBRARY_DIR, load_paper, save_paper


def acquire_pdf_markdown(paper_id: str, library_dir: Path | None = None) -> tuple[Paper, Path]:
    """Download a paper PDF and convert the original extracted text to markdown."""

    library_dir = library_dir or DEFAULT_LIBRARY_DIR
    paper = load_paper(paper_id, library_dir)
    if not paper:
        raise ValueError(f"Paper not found: {paper_id}")
    if not paper.pdf_url:
        raise ValueError(f"Paper has no PDF URL: {paper_id}")

    paper_dir = library_dir / paper.paper_id
    paper_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = paper_dir / "paper.pdf"
    markdown_path = paper_dir / "paper.md"

    _download(paper.pdf_url, pdf_path)
    markdown = pdf_to_markdown(pdf_path, title=paper.title)
    markdown_path.write_text(markdown, encoding="utf-8")
    extraction = pdf_extraction_report(pdf_path, markdown)

    now = datetime.now(UTC).isoformat()
    assets = [asset for asset in paper.assets if asset.kind not in {"pdf", "markdown"}]
    assets.extend(
        [
            PaperAsset(kind="pdf", uri=str(pdf_path), created_at=now, metadata={"source_url": paper.pdf_url}),
            PaperAsset(
                kind="markdown",
                uri=str(markdown_path),
                created_at=now,
                metadata={"source": "pdf_extract", **extraction},
            ),
        ]
    )
    updated = Paper(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        venue=paper.venue,
        abstract=paper.abstract,
        source=paper.source,
        external_ids=paper.external_ids,
        verification_status=paper.verification_status,
        pdf_url=paper.pdf_url,
        landing_url=paper.landing_url,
        imported_at=paper.imported_at,
        assets=assets,
        chunks=paper.chunks,
        summary=paper.summary,
    )
    save_paper(updated, library_dir)
    return updated, markdown_path


def pdf_to_markdown(
    pdf_path: Path,
    *,
    title: str = "",
    figures: list[dict[str, Any]] | None = None,
    formulas: list[dict[str, Any]] | None = None,
    tables: list[dict[str, Any]] | None = None,
) -> str:
    """Build readable markdown without duplicating figure or equation glyphs."""

    document = pymupdf.open(pdf_path)
    figures = figures if figures is not None else _find_figure_regions(document)
    formulas = formulas if formulas is not None else _find_formula_regions(document)
    tables = tables if tables is not None else _find_table_regions(document)
    placed_figures: set[str] = set()
    placed_tables: set[str] = set()
    page_outputs: list[list[str]] = []
    lines: list[str] = []
    if title:
        lines.extend([f"# {title}", ""])
    lines.extend(["<!-- Layout-aware PDF text; figures omitted and formulas preserved by marker. -->", ""])
    try:
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            page_figures = [
                pymupdf.Rect(item["bbox"])
                for item in figures
                if item["page_number"] == page_number
            ]
            page_formulas = [item for item in formulas if item["page_number"] == page_number]
            page_tables = [
                pymupdf.Rect(item["bbox"])
                for item in tables
                if item["page_number"] == page_number
            ]
            emitted_formulas: set[str] = set()
            page_lines: list[str] = []

            for block in page.get_text("dict", sort=False).get("blocks", []):
                block_lines: list[str] = []
                for line in block.get("lines", []):
                    line_rect = pymupdf.Rect(line["bbox"])
                    formula = next(
                        (
                            item
                            for item in page_formulas
                            if _rect_overlap_ratio(line_rect, pymupdf.Rect(item["bbox"])) >= 0.5
                        ),
                        None,
                    )
                    if formula:
                        formula_id = str(formula["formula_id"])
                        if formula_id not in emitted_formulas:
                            block_lines.append(f"[[FORMULA:{formula_id}]]")
                            emitted_formulas.add(formula_id)
                        continue
                    if any(_rect_overlap_ratio(line_rect, region) >= 0.5 for region in page_figures):
                        continue
                    if any(_rect_overlap_ratio(line_rect, region) >= 0.5 for region in page_tables):
                        continue

                    text = "".join(str(span.get("text", "")) for span in line.get("spans", []))
                    text = _normalize_text(text)
                    if text:
                        block_lines.append(text)

                if block_lines:
                    block_text = " ".join(
                        text for text in block_lines if not text.startswith("[[FORMULA:")
                    )
                    table_markers_after: dict[int, list[str]] = {}
                    for table in tables:
                        table_id = str(table["table_id"])
                        if table_id in placed_tables:
                            continue
                        for line_index, text in enumerate(block_lines):
                            mention = re.search(
                                rf"\bTable\s*{re.escape(str(table['number']))}\b",
                                text,
                                re.IGNORECASE,
                            )
                            if not mention:
                                continue
                            placement_index = line_index
                            while (
                                placement_index + 1 < len(block_lines)
                                and not re.search(r"[.!?](?:\s|$)", block_lines[placement_index])
                            ):
                                placement_index += 1
                            table_markers_after.setdefault(placement_index, []).append(table_id)
                            placed_tables.add(table_id)
                            break

                    for line_index, text in enumerate(block_lines):
                        page_lines.append(text)
                        for table_id in table_markers_after.get(line_index, []):
                            page_lines.append(f"[[TABLE:{table_id}]]")

                    mentioned_figures: list[tuple[int, dict[str, Any]]] = []
                    for figure in figures:
                        figure_id = str(figure["figure_id"])
                        if figure_id in placed_figures:
                            continue
                        mention = re.search(
                            rf"\b(?:Figure|Fig\.)\s*{re.escape(str(figure['number']))}\b",
                            block_text,
                            re.IGNORECASE,
                        )
                        if mention:
                            mentioned_figures.append((mention.start(), figure))
                    for _, figure in sorted(mentioned_figures, key=lambda item: item[0]):
                        figure_id = str(figure["figure_id"])
                        page_lines.append(f"[[FIGURE:{figure_id}]]")
                        placed_figures.add(figure_id)
                    page_lines.append("")

            for formula in page_formulas:
                formula_id = str(formula["formula_id"])
                if formula_id not in emitted_formulas:
                    page_lines.extend([f"[[FORMULA:{formula_id}]]", ""])

            page_outputs.append(page_lines)
    finally:
        document.close()

    for figure in figures:
        figure_id = str(figure["figure_id"])
        if figure_id in placed_figures:
            continue
        source_page = int(figure["page_number"]) - 1
        page_outputs[source_page].extend([f"[[FIGURE:{figure_id}]]", ""])

    for table in tables:
        table_id = str(table["table_id"])
        if table_id in placed_tables:
            continue
        source_page = int(table["page_number"]) - 1
        page_outputs[source_page].extend([f"[[TABLE:{table_id}]]", ""])

    for page_index, page_lines in enumerate(page_outputs):
        while page_lines and not page_lines[-1]:
            page_lines.pop()
        if not page_lines:
            page_lines.append(
                "> This page has no extractable prose. Switch to Original PDF to view the complete page."
            )
        lines.extend([f"## Page {page_index + 1}", "", *page_lines, ""])
    return "\n".join(lines).strip() + "\n"


def markdown_asset_path(paper: Paper) -> Path | None:
    for asset in paper.assets:
        if asset.kind == "markdown" and asset.uri:
            return Path(asset.uri)
    return None


def pdf_asset_path(paper: Paper) -> Path | None:
    """Return the locally stored source PDF, when acquisition succeeded."""

    for asset in paper.assets:
        if asset.kind == "pdf" and asset.uri:
            return Path(asset.uri)
    return None


def pdf_extraction_report(pdf_path: Path, markdown: str = "") -> dict[str, object]:
    """Describe whether every source page yielded readable text.

    The original PDF remains the completeness authority because text extraction
    cannot faithfully represent image-only pages, figures, or equations.
    """

    reader = PdfReader(str(pdf_path))
    missing_pages: list[int] = []
    extracted_page_count = 0
    for index, page in enumerate(reader.pages, start=1):
        if _normalize_text(page.extract_text() or ""):
            extracted_page_count += 1
        else:
            missing_pages.append(index)
    return {
        "page_count": len(reader.pages),
        "extracted_page_count": extracted_page_count,
        "missing_text_pages": missing_pages,
        "text_extraction_complete": not missing_pages,
        "character_count": len(markdown),
        "word_count": len(re.findall(r"\S+", markdown)),
    }


def extract_pdf_figures(paper: Paper) -> list[dict[str, Any]]:
    """Locate captioned figures without flattening the entire PDF page.

    Academic PDFs commonly draw figures as vectors, so ``get_images()`` alone
    misses them. This extractor finds Figure/Fig. captions and records a tight
    page clip containing the connected layout immediately above each caption.
    """

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        return []

    document = pymupdf.open(pdf_path)
    try:
        return _find_figure_regions(document)
    finally:
        document.close()


def render_pdf_figure(paper: Paper, figure_id: str, *, scale: float = 2.0) -> Path:
    """Render one detected figure, including vector artwork, to a cached PNG."""

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        raise ValueError("Original PDF is not available locally.")
    if not re.fullmatch(r"figure-\d+-page-\d+(?:-\d+)?", figure_id):
        raise ValueError("Invalid figure identifier.")

    document = pymupdf.open(pdf_path)
    try:
        figures = _find_figure_regions(document)
        figure = next((item for item in figures if item["figure_id"] == figure_id), None)
        if not figure:
            raise ValueError(f"Figure not found: {figure_id}")

        output_dir = pdf_path.parent / "rendered_figures"
        output_dir.mkdir(parents=True, exist_ok=True)
        crop_key = hashlib.sha1(
            ",".join(f"{coordinate:.2f}" for coordinate in figure["bbox"]).encode("ascii")
        ).hexdigest()[:10]
        output_path = output_dir / f"{figure_id}-{crop_key}.png"
        if output_path.exists() and output_path.stat().st_mtime >= pdf_path.stat().st_mtime:
            return output_path

        page = document[int(figure["page_number"]) - 1]
        clip = pymupdf.Rect(figure["bbox"])
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False)
        pixmap.save(output_path)
        return output_path
    finally:
        document.close()


def extract_pdf_formulas(paper: Paper) -> list[dict[str, Any]]:
    """Locate displayed equations so their original PDF typography can be retained."""

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        return []

    document = pymupdf.open(pdf_path)
    try:
        return _find_formula_regions(document)
    finally:
        document.close()


def render_pdf_formula(paper: Paper, formula_id: str, *, scale: float = 3.0) -> Path:
    """Render a displayed equation directly from its PDF region."""

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        raise ValueError("Original PDF is not available locally.")
    if not re.fullmatch(r"formula-\d+-page-\d+", formula_id):
        raise ValueError("Invalid formula identifier.")

    document = pymupdf.open(pdf_path)
    try:
        formulas = _find_formula_regions(document)
        formula = next((item for item in formulas if item["formula_id"] == formula_id), None)
        if not formula:
            raise ValueError(f"Formula not found: {formula_id}")

        output_dir = pdf_path.parent / "rendered_formulas"
        output_dir.mkdir(parents=True, exist_ok=True)
        crop_key = hashlib.sha1(
            ",".join(f"{coordinate:.2f}" for coordinate in formula["bbox"]).encode("ascii")
        ).hexdigest()[:10]
        output_path = output_dir / f"{formula_id}-{crop_key}.png"
        if output_path.exists() and output_path.stat().st_mtime >= pdf_path.stat().st_mtime:
            return output_path

        page = document[int(formula["page_number"]) - 1]
        clip = pymupdf.Rect(formula["bbox"])
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False)
        pixmap.save(output_path)
        return output_path
    finally:
        document.close()


def extract_pdf_tables(paper: Paper) -> list[dict[str, Any]]:
    """Locate captioned ruled tables and preserve their source geometry."""

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        return []

    document = pymupdf.open(pdf_path)
    try:
        return _find_table_regions(document)
    finally:
        document.close()


def render_pdf_table(paper: Paper, table_id: str, *, scale: float = 3.0) -> Path:
    """Render a complete table and caption directly from the source PDF."""

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        raise ValueError("Original PDF is not available locally.")
    if not re.fullmatch(r"table-\d+-page-\d+(?:-\d+)?", table_id):
        raise ValueError("Invalid table identifier.")

    output_dir = pdf_path.parent / "rendered_tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    freshness_time = max(pdf_path.stat().st_mtime, Path(__file__).stat().st_mtime)
    cached_outputs = sorted(output_dir.glob(f"{table_id}-*.png"), key=lambda path: path.stat().st_mtime)
    if cached_outputs and cached_outputs[-1].stat().st_mtime >= freshness_time:
        return cached_outputs[-1]

    document = pymupdf.open(pdf_path)
    try:
        tables = _find_table_regions(document)
        table = next((item for item in tables if item["table_id"] == table_id), None)
        if not table:
            raise ValueError(f"Table not found: {table_id}")

        crop_key = hashlib.sha1(
            ",".join(f"{coordinate:.2f}" for coordinate in table["bbox"]).encode("ascii")
        ).hexdigest()[:10]
        output_path = output_dir / f"{table_id}-{crop_key}.png"
        if output_path.exists() and output_path.stat().st_mtime >= pdf_path.stat().st_mtime:
            return output_path

        page = document[int(table["page_number"]) - 1]
        clip = pymupdf.Rect(table["bbox"])
        pixmap = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False)
        pixmap.save(output_path)
        return output_path
    finally:
        document.close()


def render_pdf_tables(
    paper: Paper,
    tables: list[dict[str, Any]],
    *,
    scale: float = 3.0,
) -> dict[str, Path]:
    """Warm every detected table crop so the reader never waits on lazy requests."""

    pdf_path = pdf_asset_path(paper)
    if not pdf_path or not pdf_path.exists():
        raise ValueError("Original PDF is not available locally.")

    output_dir = pdf_path.parent / "rendered_tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    freshness_time = max(pdf_path.stat().st_mtime, Path(__file__).stat().st_mtime)
    rendered: dict[str, Path] = {}
    document = pymupdf.open(pdf_path)
    try:
        for table in tables:
            table_id = str(table.get("table_id", ""))
            bbox = table.get("bbox")
            page_number = int(table.get("page_number", 0))
            if (
                not re.fullmatch(r"table-\d+-page-\d+(?:-\d+)?", table_id)
                or not isinstance(bbox, list)
                or len(bbox) != 4
                or not 1 <= page_number <= document.page_count
            ):
                continue

            crop_key = hashlib.sha1(
                ",".join(f"{float(coordinate):.2f}" for coordinate in bbox).encode("ascii")
            ).hexdigest()[:10]
            output_path = output_dir / f"{table_id}-{crop_key}.png"
            if not output_path.exists() or output_path.stat().st_mtime < freshness_time:
                page = document[page_number - 1]
                clip = pymupdf.Rect(bbox)
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale),
                    clip=clip,
                    alpha=False,
                )
                pixmap.save(output_path)
            rendered[table_id] = output_path
    finally:
        document.close()
    return rendered


def _find_figure_regions(document: pymupdf.Document) -> list[dict[str, Any]]:
    caption_pattern = re.compile(r"(?:^|\n)\s*(?:Figure|Fig\.)\s*(\d+)\s*[:.]", re.IGNORECASE)
    figures: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}

    for page_index, page in enumerate(document):
        page_width = page.rect.width
        text_blocks = list(page.get_text("blocks", sort=True))
        drawings = list(page.get_drawings())

        for caption_block in text_blocks:
            block_text = str(caption_block[4])
            match = caption_pattern.search(block_text)
            if not match:
                continue

            caption = " ".join(block_text[match.start() :].split())
            caption_rect = pymupdf.Rect(caption_block[:4])
            if caption_rect.width > page_width * 0.52:
                column_left, column_right = page_width * 0.07, page_width * 0.93
            elif caption_rect.x0 + caption_rect.x1 < page_width:
                column_left, column_right = page_width * 0.07, page_width * 0.49
            else:
                column_left, column_right = page_width * 0.51, page_width * 0.93

            intervals: list[tuple[float, float]] = []
            for block in text_blocks:
                block_rect = pymupdf.Rect(block[:4])
                block_type = int(block[6]) if len(block) > 6 else 0
                if block_type != 1 or block_rect.y1 > caption_rect.y0 + 1:
                    continue
                if _horizontal_overlap(block_rect, column_left, column_right):
                    intervals.append((block_rect.y0, block_rect.y1))
            for drawing in drawings:
                drawing_rect = pymupdf.Rect(drawing["rect"])
                if drawing_rect.y1 > caption_rect.y0 + 1:
                    continue
                if _horizontal_overlap(drawing_rect, column_left, column_right):
                    intervals.append((drawing_rect.y0, drawing_rect.y1))

            merged = _merge_vertical_intervals(intervals, gap=8.0)
            figure_top = caption_rect.y0
            for start, end in reversed(merged):
                if end > figure_top + 1:
                    continue
                if figure_top - end <= 45.0:
                    figure_top = start
                else:
                    break

            clip = pymupdf.Rect(
                column_left - 3,
                max(page.rect.y0, figure_top - 5),
                column_right + 3,
                min(page.rect.y1, caption_rect.y1 + 1),
            )
            base_id = f"figure-{match.group(1)}-page-{page_index + 1}"
            duplicate = seen_ids.get(base_id, 0)
            seen_ids[base_id] = duplicate + 1
            figure_id = base_id if duplicate == 0 else f"{base_id}-{duplicate + 1}"
            figures.append(
                {
                    "figure_id": figure_id,
                    "number": match.group(1),
                    "page_number": page_index + 1,
                    "caption": caption,
                    "bbox": [clip.x0, clip.y0, clip.x1, clip.y1],
                }
            )
    return figures


def _find_table_regions(document: pymupdf.Document) -> list[dict[str, Any]]:
    caption_pattern = re.compile(r"^\s*Table\s*(\d+)\s*:", re.IGNORECASE)
    tables: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}

    for page_index, page in enumerate(document):
        detected_tables = list(page.find_tables().tables)
        caption_lines: list[tuple[str, pymupdf.Rect]] = []
        for block in page.get_text("dict", sort=True).get("blocks", []):
            for line in block.get("lines", []):
                caption_lines.append(
                    (
                        " ".join(
                            "".join(
                                str(span.get("text", "")) for span in line.get("spans", [])
                            ).split()
                        ),
                        pymupdf.Rect(line["bbox"]),
                    )
                )

        for caption, caption_rect in caption_lines:
            match = caption_pattern.match(caption)
            if not match:
                continue

            candidates: list[tuple[float, pymupdf.Rect]] = []
            for detected in detected_tables:
                table_rect = pymupdf.Rect(detected.bbox)
                vertical_gap = caption_rect.y0 - table_rect.y1
                horizontal_overlap = max(
                    0.0,
                    min(table_rect.x1, caption_rect.x1) - max(table_rect.x0, caption_rect.x0),
                )
                if -2 <= vertical_gap <= 35 and horizontal_overlap >= min(
                    table_rect.width, caption_rect.width
                ) * 0.25:
                    candidates.append((vertical_gap, table_rect))
            if candidates:
                _, table_rect = min(candidates, key=lambda item: item[0])
            else:
                horizontal_rules = []
                for drawing in page.get_drawings():
                    rule = pymupdf.Rect(drawing["rect"])
                    overlap = max(
                        0.0,
                        min(rule.x1, caption_rect.x1) - max(rule.x0, caption_rect.x0),
                    )
                    if (
                        rule.height <= 1.5
                        and rule.width >= page.rect.width * 0.25
                        and rule.y1 <= caption_rect.y0 + 1
                        and caption_rect.y0 - rule.y1 <= 80
                        and overlap >= min(rule.width, caption_rect.width) * 0.25
                    ):
                        horizontal_rules.append(rule)
                horizontal_rules.sort(key=lambda rect: rect.y0)
                if len(horizontal_rules) < 2:
                    continue
                selected_rules = [horizontal_rules[-1]]
                for rule in reversed(horizontal_rules[:-1]):
                    if selected_rules[-1].y0 - rule.y1 > 45:
                        break
                    selected_rules.append(rule)
                if len(selected_rules) < 2:
                    continue
                table_rect = pymupdf.Rect(
                    min(rule.x0 for rule in selected_rules),
                    min(rule.y0 for rule in selected_rules),
                    max(rule.x1 for rule in selected_rules),
                    max(rule.y1 for rule in selected_rules),
                )
            clip = pymupdf.Rect(
                max(page.rect.x0, min(table_rect.x0, caption_rect.x0) - 3),
                max(page.rect.y0, table_rect.y0 - 3),
                min(page.rect.x1, max(table_rect.x1, caption_rect.x1) + 3),
                min(page.rect.y1, caption_rect.y1 + 1),
            )
            base_id = f"table-{match.group(1)}-page-{page_index + 1}"
            duplicate = seen_ids.get(base_id, 0)
            seen_ids[base_id] = duplicate + 1
            table_id = base_id if duplicate == 0 else f"{base_id}-{duplicate + 1}"
            tables.append(
                {
                    "table_id": table_id,
                    "number": match.group(1),
                    "page_number": page_index + 1,
                    "caption": caption,
                    "bbox": [clip.x0, clip.y0, clip.x1, clip.y1],
                }
            )
    return tables


def _find_formula_regions(document: pymupdf.Document) -> list[dict[str, Any]]:
    formulas: list[dict[str, Any]] = []
    formula_number = 0
    figure_regions = _find_figure_regions(document)

    for page_index, page in enumerate(document):
        column_width = page.rect.width * 0.42
        candidates: list[dict[str, Any]] = []
        excluded_regions = [
            pymupdf.Rect(item["bbox"])
            for item in figure_regions
            if item["page_number"] == page_index + 1
        ]
        excluded_regions.extend(_find_ruled_regions(page))
        page_dict = page.get_text("dict", sort=True)
        for block in page_dict.get("blocks", []):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = "".join(str(span.get("text", "")) for span in spans).strip()
                if not text:
                    continue
                rect = pymupdf.Rect(line["bbox"])
                compact_chars = re.sub(r"\s+", "", text)
                math_chars = sum(
                    len(re.sub(r"\s+", "", str(span.get("text", ""))))
                    for span in spans
                    if _is_math_font(str(span.get("font", "")))
                )
                math_ratio = math_chars / max(1, len(compact_chars))
                has_equation_operator = bool(re.search(r"[=≤≥∪∩∑∏∀∃⇒→↦⊆⊂]", text))
                prose_words = [
                    word
                    for span in spans
                    if not _is_math_font(str(span.get("font", "")))
                    and float(span.get("size", 0)) >= 8
                    for word in re.findall(r"[A-Za-z]{3,}", str(span.get("text", "")))
                ]
                compact_geometry = rect.width <= column_width * 0.86
                math_signal = math_ratio >= 0.28 or (
                    has_equation_operator and len(prose_words) <= 3
                )
                if (
                    not compact_geometry
                    or not math_signal
                    or prose_words
                    or any(region.contains(rect.tl) and region.contains(rect.br) for region in excluded_regions)
                ):
                    continue
                column = 0 if rect.x0 + rect.x1 < page.rect.width else 1
                candidates.append({"rect": rect, "text": text, "column": column})

        groups: list[list[dict[str, Any]]] = []
        for candidate in sorted(candidates, key=lambda item: (item["column"], item["rect"].y0)):
            if (
                groups
                and groups[-1][-1]["column"] == candidate["column"]
                and candidate["rect"].y0 - max(item["rect"].y1 for item in groups[-1]) <= 9
            ):
                groups[-1].append(candidate)
            else:
                groups.append([candidate])

        for group in groups:
            group_text = " ".join(item["text"] for item in group)
            if len(re.sub(r"\s+", "", group_text)) < 4 or not (
                len(group) > 1 or re.search(r"[=≤≥∪∩∑∏∀∃⇒→↦⊆⊂]", group_text)
            ):
                continue
            formula_number += 1
            left = min(item["rect"].x0 for item in group)
            top = min(item["rect"].y0 for item in group)
            right = max(item["rect"].x1 for item in group)
            bottom = max(item["rect"].y1 for item in group)
            clip = pymupdf.Rect(
                max(page.rect.x0, left - 8),
                max(page.rect.y0, top - 1),
                min(page.rect.x1, right + 8),
                min(page.rect.y1, bottom + 1),
            )
            formulas.append(
                {
                    "formula_id": f"formula-{formula_number}-page-{page_index + 1}",
                    "page_number": page_index + 1,
                    "text": group_text,
                    "bbox": [clip.x0, clip.y0, clip.x1, clip.y1],
                }
            )
    return formulas


def _is_math_font(font_name: str) -> bool:
    lowered = font_name.lower()
    return any(marker in lowered for marker in ("math", "txsys", "txmia", "txex"))


def _find_ruled_regions(page: pymupdf.Page) -> list[pymupdf.Rect]:
    """Return table/algorithm boxes so they are not mislabeled as equations."""

    regions: list[pymupdf.Rect] = []
    page_midpoint = page.rect.width / 2
    for column in (0, 1):
        rules: list[pymupdf.Rect] = []
        for drawing in page.get_drawings():
            rect = pymupdf.Rect(drawing["rect"])
            center = (rect.x0 + rect.x1) / 2
            if (center < page_midpoint) != (column == 0):
                continue
            if rect.height <= 1.5 and rect.width >= page.rect.width * 0.30:
                rules.append(rect)
        if len(rules) < 2:
            continue
        top = min(rect.y0 for rect in rules)
        bottom = max(rect.y1 for rect in rules)
        if bottom - top < 12:
            continue
        regions.append(
            pymupdf.Rect(
                min(rect.x0 for rect in rules) - 2,
                top - 2,
                max(rect.x1 for rect in rules) + 2,
                bottom + 2,
            )
        )
    return regions


def _rect_overlap_ratio(rect: pymupdf.Rect, region: pymupdf.Rect) -> float:
    rect_area = rect.get_area()
    if rect_area <= 0:
        return 0.0
    intersection = rect & region
    return max(0.0, intersection.get_area()) / rect_area


def _horizontal_overlap(rect: pymupdf.Rect, left: float, right: float) -> bool:
    if rect.width <= 0:
        return left <= rect.x0 <= right
    overlap = max(0.0, min(rect.x1, right) - max(rect.x0, left))
    if overlap <= 0:
        return False
    return overlap >= min(rect.width, right - left) * 0.25


def _merge_vertical_intervals(
    intervals: list[tuple[float, float]], *, gap: float
) -> list[tuple[float, float]]:
    if not intervals:
        return []
    merged: list[tuple[float, float]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + gap:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "PhD-Buddy/0.1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def _normalize_text(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
