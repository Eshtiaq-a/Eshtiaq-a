"""Render Section 02 Repo Galaxy + Neofetch Developer Terminal SVG."""

from __future__ import annotations

from pathlib import Path

from src.config import (
    ASCII_PORTRAIT_PATH,
    COMMITS_PATH,
    CONFIG_PATH,
    NEOFETCH_SVG_PATH,
    PROFILE_DATA_PATH,
    REPOSITORIES_PATH,
    atomic_write_text,
)
from src.neofetch_builder import NeofetchModel, build_neofetch_model, load_phase2_inputs
from src.visualizations.neofetch_terminal import LayoutMode, build_neofetch_terminal_svg


def build_neofetch_svg(model: NeofetchModel, layout: LayoutMode = "desktop") -> str:
    """Render a cohesive, Camo-safe Repo Galaxy + Neofetch terminal SVG."""
    return build_neofetch_terminal_svg(model, layout=layout)


def generate_neofetch_svg_file(
    profile_path: Path = PROFILE_DATA_PATH,
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    output_path: Path = NEOFETCH_SVG_PATH,
    layout: LayoutMode = "desktop",
) -> Path:
    """Load Phase 2 JSON datasets, build Repo Galaxy + Neofetch SVG, validate XML, and write atomically."""
    profile_data, repos_data, commits_data, config_raw = load_phase2_inputs(
        profile_path=profile_path,
        repos_path=repos_path,
        commits_path=commits_path,
        config_path=config_path,
    )
    model = build_neofetch_model(
        profile_data=profile_data,
        repositories_data=repos_data,
        commits_data=commits_data,
        config_raw=config_raw,
        ascii_path=ascii_path,
    )
    svg_text = build_neofetch_svg(model, layout=layout)
    return atomic_write_text(output_path, svg_text)


if __name__ == "__main__":
    written = generate_neofetch_svg_file()
    print(f"Generated {written} ({written.stat().st_size} bytes)")
