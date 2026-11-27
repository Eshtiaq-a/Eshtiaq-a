"""Configuration, paths, and visual design tokens for Eshtiaq Developer Universe."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "profile.json"
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"

SAMPLE_COMMITS_PATH = DATA_DIR / "sample_commits.json"
COMMITS_PATH = DATA_DIR / "commits.json"
REPOSITORIES_PATH = DATA_DIR / "repositories.json"
PROFILE_DATA_PATH = DATA_DIR / "profile_data.json"
CONTRIBUTIONS_PATH = DATA_DIR / "contributions.json"
WORKSPACE_SVG_PATH = ASSETS_DIR / "workspace.svg"
WORKSPACE_GIF_PATH = ASSETS_DIR / "workspace.gif"
ASCII_PORTRAIT_PATH = ASSETS_DIR / "ascii_portrait.txt"
NEOFETCH_SVG_PATH = ASSETS_DIR / "neofetch.svg"
REPOS_CARDS_DIR = ASSETS_DIR / "repos"
REPO_GALAXY_PAGES_HTML_PATH = ROOT_DIR / "docs" / "index.html"
CONTRIBUTION_CITY_SVG_PATH = ASSETS_DIR / "contribution_city.svg"
CONTRIBUTION_CITY_PAGES_HTML_PATH = ROOT_DIR / "docs" / "city.html"
EXPLORER_SVG_PATH = ASSETS_DIR / "explorer.svg"
EXPLORER_SLICES_DIR = ASSETS_DIR / "explorer"
EXPLORER_HEADER_SVG_PATH = EXPLORER_SLICES_DIR / "header.svg"
EXPLORER_ROWS_DIR = EXPLORER_SLICES_DIR / "rows"
EXPLORER_FOOTER_SVG_PATH = EXPLORER_SLICES_DIR / "footer.svg"
DIVIDER_SVG_PATH = ASSETS_DIR / "divider.svg"
README_PATH = ROOT_DIR / "README.md"

GITHUB_API_BASE = "https://api.github.com"
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
DEFAULT_HTTP_TIMEOUT_SEC = 15
DEFAULT_MAX_RETRIES = 3

# Measured Reference Image 1 palette (988x504 canvas)
WORKSPACE_PALETTE: dict[str, str] = {
    "wall_primary": "#1d2333",
    "wall_stripe": "#1b212f",
    "floor_base": "#3a2a23",
    "floor_seam": "#31231d",
    "floor_highlight": "#433129",
    "window_frame": "#0e1216",
    "window_sky": "#0a1a39",
    "window_star": "#4c5b7a",
    "cream": "#f3e8d4",
    "plaque_bg": "#f3e9d5",
    "plaque_border": "#14181e",
    "wood_top": "#6a4a31",
    "wood_highlight": "#7c573b",
    "wood_shadow": "#563926",
    "wood_dark": "#452d1e",
    "lamp_shade": "#f2cb62",
    "lamp_pole": "#272c38",
    "shadow_ambient": "#121723",
    "floor_shadow": "#241914",
    "poster_bg": "#101a30",
    "keycap_light": "#dce2ec",
    "keycap_esc": "#e25b47",
    "keycap_mod": "#5aa9ff",
    "mousepad_bg": "#1a2234",
    "mousepad_border": "#364668",
    "monitor_outer": "#333338",
    "monitor_inner": "#1f212c",
    "monitor_stand": "#4c4d52",
    "monitor_base": "#616773",
    "screen_bg": "#08172b",
    "screen_glow": "#0c1a33",
    "mac_aluminum": "#9aa1ad",
    "mac_edge": "#6c7380",
    "mac_dark": "#262b36",
    "mac_screen": "#0c1a33",
    "cable": "#181c24",
    "cable_highlight": "#4e5666",
    "chair_main": "#3d4350",
    "chair_highlight": "#4c4d52",
    "chair_shadow": "#2b303a",
    "mug_cream": "#ebe0cf",
    "mug_shadow": "#cfc3b2",
    "plant_pot": "#9a5a3a",
    "plant_pot_rim": "#7a492c",
    "plant_leaf": "#2ca042",
    "plant_leaf_dark": "#217a32",
    "cat_body": "#e8a55b",
    "cat_stripe": "#c3803a",
    "book_blue": "#3472a5",
    "book_red": "#f4422e",
    "book_yellow": "#f8de55",
    "book_cream": "#dad1c4",
    "credit_title": "#f2cb62",
    "credit_repo": "#93c8b2",
    "credit_text": "#e9ecf2",
    "credit_meta": "#88a8b5",
    "credit_divider": "#2c4966",
}

MAX_SVG_BYTES = 450_000
MAX_GIF_BYTES = 1_500_000
WORKSPACE_WIDTH = 988
WORKSPACE_HEIGHT = 504
MONITOR_SCREEN_BOX = (429, 132, 246, 142)  # (x, y, width, height)

NEOFETCH_WIDTH = 1009
NEOFETCH_HEIGHT = 610
NEOFETCH_PALETTE: dict[str, str] = {
    "bg": "#0d0f14",
    "border": "#5582bc",
    "prompt_user": "#5aa9ff",
    "prompt_path": "#888b92",
    "prompt_cmd": "#ebf0f4",
    "ascii_green": "#73b88d",
    "header_blue": "#5aa9ff",
    "label_blue": "#5aa9ff",
    "dots": "#6e737d",
    "divider": "#41444b",
    "text": "#ebf0f4",
    "muted": "#9aa1ad",
    "cursor": "#4c9aff",
}

EXPLORER_WIDTH = 1009
EXPLORER_PALETTE: dict[str, str] = {
    "bg": "#0d0f14",
    "titlebar_bg": "#121723",
    "panel_bg": "#090d16",
    "row_even": "#0c111c",
    "row_odd": "#090d16",
    "row_hover": "#141d33",
    "border": "#5582bc",
    "inner_border": "#1d2b4d",
    "rule": "#1b2540",
    "dir_green": "#73b88d",
    "dir_muted": "#626c82",
    "prompt_blue": "#5aa9ff",
    "repo_blue": "#68b5ff",
    "text": "#ebf0f4",
    "desc": "#a3adc2",
    "muted": "#7b879e",
    "dim": "#5d667a",
    "star_gold": "#f2cb62",
    "live_green": "#73b88d",
    "win_red": "#ff5f56",
    "win_yellow": "#ffbd2e",
    "win_green": "#27c93f",
}


@dataclass(frozen=True)
class ProfileConfig:
    """Loaded profile configuration settings."""

    username: str
    display_name: str
    location: str
    timezone: str
    scroll_speed_px_per_sec: float
    include_second_plant: bool
    show_human_character: bool
    human_character_gender: str
    watermark: str | None
    explorer_sort_by: str = "updated"


def load_profile_config(path: Path = CONFIG_PATH) -> ProfileConfig:
    """Load and validate static profile configuration."""
    raw: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    ws = raw.get("workspace", {})
    exp = raw.get("explorer", {})
    gender = str(ws.get("human_character_gender", "none")).lower()
    if gender == "female":
        raise ValueError("Female character/avatar is strictly prohibited by design rules.")
    sort_by = str(exp.get("sort_by", "updated")).lower()
    if sort_by not in {"updated", "stars", "name"}:
        sort_by = "updated"
    return ProfileConfig(
        username=str(raw["username"]),
        display_name=str(raw["display_name"]),
        location=str(raw.get("location", "Dhaka, Bangladesh")),
        timezone=str(raw.get("timezone", "Asia/Dhaka")),
        scroll_speed_px_per_sec=float(ws.get("scroll_speed_px_per_sec", 20.0)),
        include_second_plant=bool(ws.get("include_second_desk_or_shelf_plant", True)),
        show_human_character=bool(ws.get("show_human_character", False)),
        human_character_gender=gender,
        watermark=ws.get("watermark"),
        explorer_sort_by=sort_by,
    )


def atomic_write_text(path: Path, content: str) -> Path:
    """Atomically write UTF-8 text via a same-directory temp file and os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    return path


def atomic_write_json(path: Path, payload: Any) -> Path:
    """Serialize JSON deterministically (UTF-8, pretty-printed) and write atomically."""
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return atomic_write_text(path, serialized)
