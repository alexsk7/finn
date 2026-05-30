"""Generate a lightweight coverage dashboard from coverage.xml.

The output is a standalone HTML page with a compact bar chart by file,
plus a link to the standard htmlcov/index.html detail report.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html import escape
from pathlib import Path


@dataclass
class FileCoverage:
    filename: str
    percent: float


def _parse_coverage_xml(xml_path: Path) -> tuple[float, list[FileCoverage]]:
    root = ET.fromstring(xml_path.read_text(encoding="utf-8"))

    overall = float(root.attrib.get("line-rate", "0")) * 100.0
    rows: list[FileCoverage] = []

    for cls in root.findall("./packages/package/classes/class"):
        filename = cls.attrib.get("filename", "unknown")
        pct = float(cls.attrib.get("line-rate", "0")) * 100.0
        rows.append(FileCoverage(filename=filename, percent=pct))

    rows.sort(key=lambda r: (r.percent, r.filename))
    return overall, rows


def _color_for_percent(percent: float) -> str:
    if percent >= 90:
        return "#2e7d32"
    if percent >= 75:
        return "#558b2f"
    if percent >= 60:
        return "#f9a825"
    if percent >= 40:
        return "#ef6c00"
    return "#c62828"


def _row_html(row: FileCoverage) -> str:
    width = max(1.0, min(100.0, row.percent))
    color = _color_for_percent(row.percent)
    file_label = escape(row.filename)
    pct_label = f"{row.percent:.1f}%"

    return (
        "<tr>"
        f"<td class='file'>{file_label}</td>"
        "<td class='bar-cell'>"
        "<div class='bar-track'>"
        f"<div class='bar-fill' style='width:{width:.1f}%; background:{color};'></div>"
        "</div>"
        "</td>"
        f"<td class='pct'>{pct_label}</td>"
        "</tr>"
    )


def build_dashboard(xml_path: Path, out_path: Path) -> None:
    overall, rows = _parse_coverage_xml(xml_path)
    rows_html = "\n".join(_row_html(r) for r in rows)

    template_path = Path(__file__).parent / "coverage_dashboard_template.html"
    template = template_path.read_text(encoding="utf-8")
    html = template.replace("__OVERALL__", f"{overall:.1f}%").replace("__ROWS__", rows_html)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")


def main() -> None:
    xml_path = Path("coverage.xml")
    out_path = Path("htmlcov") / "dashboard.html"

    if not xml_path.exists():
        raise SystemExit("coverage.xml not found. Run tests with coverage first.")

    build_dashboard(xml_path, out_path)


if __name__ == "__main__":
    main()
