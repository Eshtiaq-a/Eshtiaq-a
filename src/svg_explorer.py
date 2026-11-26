"""Generate and persist Section 03 Project Explorer SVG & divider assets."""

from __future__ import annotations

from pathlib import Path

from src.config import (
    COMMITS_PATH,
    CONFIG_PATH,
    DIVIDER_SVG_PATH,
    EXPLORER_SVG_PATH,
    REPOSITORIES_PATH,
    atomic_write_text,
)
from src.explorer_builder import ExplorerSortOrder, build_explorer_model, load_explorer_inputs
from src.visualizations.project_explorer import (
    LayoutMode,
    build_explorer_svg,
    build_section_divider_svg,
)


def generate_explorer_svg_file(
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
    output_path: Path = EXPLORER_SVG_PATH,
    divider_path: Path | None = DIVIDER_SVG_PATH,
    layout: LayoutMode = "desktop",
    sort_by: ExplorerSortOrder | None = None,
) -> Path:
    """Load Phase 2 JSON datasets, build Section 03 Explorer SVG, validate, and write atomically."""
    repos_data, commits_data, config_raw = load_explorer_inputs(
        repos_path=repos_path,
        commits_path=commits_path,
        config_path=config_path,
    )
    model = build_explorer_model(
        repositories_data=repos_data,
        commits_data=commits_data,
        config_raw=config_raw,
        sort_by=sort_by,
    )
    svg_text = build_explorer_svg(model, layout=layout)
    written = atomic_write_text(output_path, svg_text)
    if divider_path is not None:
        atomic_write_text(divider_path, build_section_divider_svg())
    return written


if __name__ == "__main__":
    written_path = generate_explorer_svg_file()
    print(f"Generated {written_path} ({written_path.stat().st_size} bytes)")
