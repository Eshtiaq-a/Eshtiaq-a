"""Render Section 02 Repo Galaxy + Neofetch Developer Terminal SVG, clickable cards, and optional Pages HTML."""

from __future__ import annotations

import html
from pathlib import Path

from src.config import (
    ASCII_PORTRAIT_PATH,
    COMMITS_PATH,
    CONFIG_PATH,
    NEOFETCH_SVG_PATH,
    PROFILE_DATA_PATH,
    REPO_GALAXY_PAGES_HTML_PATH,
    REPOS_CARDS_DIR,
    REPOSITORIES_PATH,
    atomic_write_text,
)
from src.neofetch_builder import NeofetchModel, build_neofetch_model, load_phase2_inputs
from src.validators import make_repo_slug
from src.visualizations.neofetch_terminal import LayoutMode, build_neofetch_terminal_svg
from src.visualizations.repo_galaxy import RepoGalaxyModel, build_repo_galaxy_cards


def build_neofetch_svg(model: NeofetchModel, layout: LayoutMode = "desktop") -> str:
    """Render a cohesive, Camo-safe Repo Galaxy + Neofetch terminal SVG."""
    return build_neofetch_terminal_svg(model, layout=layout)


def write_repo_galaxy_cards(
    model: RepoGalaxyModel,
    cards_dir: Path = REPOS_CARDS_DIR,
) -> list[Path]:
    """Persist individual Repo Galaxy card SVGs atomically and prune stale card files."""
    cards_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    active_filenames: set[str] = set()
    for node, svg_text in build_repo_galaxy_cards(model):
        slug = node.card_slug or make_repo_slug(node.name, node.repository_id)
        fname = f"{slug}.svg"
        active_filenames.add(fname)
        written.append(atomic_write_text(cards_dir / fname, svg_text))

    for existing in cards_dir.glob("*.svg"):
        if existing.name not in active_filenames:
            existing.unlink(missing_ok=True)
    return written


def build_standalone_galaxy_html(neofetch_svg: str, username: str) -> str:
    """Render an optional standalone interactive HTML wrapper for free GitHub Pages hosting."""
    safe_user = html.escape(username or "Eshtiaq-a", quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_user} — Interactive Repo Galaxy</title>
  <style>
    :root {{ color-scheme: dark; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #080c18;
      color: #dce6ff;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      padding: 20px;
      box-sizing: border-box;
    }}
    main {{ width: min(100%, 1040px); }}
    svg {{ width: 100%; height: auto; display: block; }}
    .hint {{
      margin-top: 12px;
      text-align: center;
      font-size: 12px;
      color: #8b96ad;
    }}
    .hint a {{ color: #5aa9ff; text-decoration: none; }}
    .hint a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main>
    {neofetch_svg}
    <p class="hint">Interactive orbital nodes link directly to GitHub repositories · <a href="city.html">3D Contribution City</a> · <a href="https://github.com/{safe_user}">Back to @{safe_user} profile</a></p>
  </main>
</body>
</html>
"""


def write_standalone_galaxy_page(
    neofetch_svg: str,
    username: str,
    output_path: Path = REPO_GALAXY_PAGES_HTML_PATH,
) -> Path:
    """Persist optional GitHub Pages standalone interactive Repo Galaxy HTML atomically."""
    return atomic_write_text(output_path, build_standalone_galaxy_html(neofetch_svg, username))


def generate_neofetch_svg_file(
    profile_path: Path = PROFILE_DATA_PATH,
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    output_path: Path = NEOFETCH_SVG_PATH,
    cards_dir: Path | None = None,
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
    written = atomic_write_text(output_path, svg_text)
    if cards_dir is not None:
        write_repo_galaxy_cards(model.galaxy, cards_dir=cards_dir)
    return written


if __name__ == "__main__":
    written = generate_neofetch_svg_file(cards_dir=REPOS_CARDS_DIR)
    print(f"Generated {written} ({written.stat().st_size} bytes)")
