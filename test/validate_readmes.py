#!/usr/bin/env python3
"""Check portable README links and complete legacy figure galleries."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
FORBIDDEN = (
    "Materials/GeS/vasp_SOC/GeS_tb.dat",
    "Materials/Fe/vasp_SOC/Fe_tb.dat",
    "/Users/",
    "/private/",
    "file://",
)


def main():
    readmes = sorted(ROOT.rglob("README.md"))
    failures = []
    figure_count = 0
    for readme in readmes:
        text = readme.read_text()
        for token in FORBIDDEN:
            if token in text:
                failures.append(f"{readme.relative_to(ROOT)}: forbidden README path {token}")
        for target in LINK.findall(text):
            if target.startswith(("https://", "http://", "mailto:", "#")):
                continue
            path = target.split("#", 1)[0].strip("<>")
            if path and not (readme.parent / path).exists():
                failures.append(f"{readme.relative_to(ROOT)}: broken link {target}")
        if readme.parent.name[:2] in {f"{i:02d}" for i in range(1, 10)}:
            lines = text.splitlines()
            for png in sorted((readme.parent / "figures").glob("*.png")):
                if f"](figures/{png.name})" not in text:
                    failures.append(f"{readme.relative_to(ROOT)}: unshown PNG {png.name}")
                pdf = png.with_suffix(".pdf")
                if not pdf.is_file() or f"](figures/{pdf.name})" not in text:
                    failures.append(f"{readme.relative_to(ROOT)}: missing PDF link {pdf.name}")
                audit = png.with_suffix(".plot.json")
                if not audit.is_file() or f"](figures/{audit.name})" not in text:
                    failures.append(f"{readme.relative_to(ROOT)}: missing plot-audit link {audit.name}")
                image_lines = [i for i, line in enumerate(lines) if f"](figures/{png.name})" in line]
                if len(image_lines) != 1 or image_lines[0] + 2 >= len(lines):
                    failures.append(f"{readme.relative_to(ROOT)}: missing figure caption {png.name}")
                else:
                    caption = lines[image_lines[0] + 2].lower()
                    if not caption.startswith("*") or not any(
                        label in caption for label in ("presentation only", "diagnostic display")
                    ):
                        failures.append(f"{readme.relative_to(ROOT)}: missing qualification caption {png.name}")
                figure_count += 1
    if failures:
        raise SystemExit("\n".join(failures))
    assert figure_count == 36, figure_count
    print(f"README_LINKS_OK files={len(readmes)} legacy_figures={figure_count}")


if __name__ == "__main__":
    main()
