"""Generate and persist Section 03 Project Explorer SVG, clickable slices, and divider assets."""

from __future__ import annotations

from pathlib import Path

from src.config import (
    COMMITS_PATH,
    CONFIG_PATH,
    DIVIDER_SVG_PATH,
    EXPLORER_SLICES_DIR,
    EXPLORER_SVG_PATH,
    REPOSITORIES_PATH,
    atomic_write_text,
)
from src.explorer_builder import ExplorerSortOrder, build_explorer_model, load_explorer_inputs
from src.visualizations.project_explorer import (
    LayoutMode,
    build_explorer_slice_svgs,
    build_explorer_svg,
    build_section_divider_svg,
)


def write_explorer_slices(
    slices: dict[str, object],
    slices_dir: Path = EXPLORER_SLICES_DIR,
) -> list[Path]:
    """Persist header, clickable row SVGs, and footer, pruning any stale row files."""
    rows_dir = slices_dir / "rows"
    rows_dir.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    header_path = atomic_write_text(slices_dir / "header.svg", str(slices["header"]))
    footer_path = atomic_write_text(slices_dir / "footer.svg", str(slices["footer"]))
    written_paths.extend([header_path, footer_path])

    active_filenames: set[str] = set()
    for slug, row_svg in slices["rows"]:  # type: ignore[attr-defined]
        fname = f"{slug}.svg"
        active_filenames.add(fname)
        written_paths.append(atomic_write_text(rows_dir / fname, row_svg))

    empty_svg = slices.get("empty")
    if empty_svg:
        active_filenames.add("_empty.svg")
        written_paths.append(atomic_write_text(rows_dir / "_empty.svg", str(empty_svg)))

    # Remove orphaned row SVGs so deleted or renamed repos never linger in assets/explorer/rows/
    for existing in rows_dir.glob("*.svg"):
        if existing.name not in active_filenames:
            existing.unlink(missing_ok=True)

    return written_paths


def generate_explorer_svg_file(
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
    output_path: Path = EXPLORER_SVG_PATH,
    slices_dir: Path | None = EXPLORER_SLICES_DIR,
    divider_path: Path | None = DIVIDER_SVG_PATH,
    layout: LayoutMode = "desktop",
    sort_by: ExplorerSortOrder | None = None,
) -> Path:
    """Load Phase 2 JSON datasets, build Section 03 Explorer SVGs, validate, and write atomically."""
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
    if slices_dir is not None:
        write_explorer_slices(build_explorer_slice_svgs(model), slices_dir=slices_dir)
    if divider_path is not None:
        atomic_write_text(divider_path, build_section_divider_svg())
    return written


if __name__ == "__main__":
    written_path = generate_explorer_svg_file()
    print(f"Generated {written_path} ({written_path.stat().st_size} bytes)")
