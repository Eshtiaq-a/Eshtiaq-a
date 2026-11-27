"""Generate Section 04 3D Contribution City SVG and optional interactive HTML page."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from src.config import (
    CONTRIBUTION_CITY_PAGES_HTML_PATH,
    CONTRIBUTION_CITY_SVG_PATH,
    CONTRIBUTIONS_PATH,
    atomic_write_text,
)
from src.visualizations.contribution_city import build_contribution_city_svg


def build_standalone_city_html(city_svg: str, username: str) -> str:
    """Render an interactive standalone HTML page with mouse/keyboard/touch tile inspection."""
    safe_user = html.escape(username or "Eshtiaq-a", quote=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_user} — Interactive 3D Contribution City</title>
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
    .inspector {{
      margin-top: 12px;
      padding: 12px 16px;
      border-radius: 8px;
      background: #0d1324;
      border: 1px solid #243a6b;
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      justify-content: space-between;
      align-items: center;
      font-size: 13px;
    }}
    .inspector strong {{ color: #7ef9ff; }}
    .hint {{
      margin-top: 10px;
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
    {city_svg}
    <div id="city-inspector" class="inspector" aria-live="polite">
      <span>Selected Day: <strong id="ins-date">Hover, tap, or Tab onto any voxel block</strong></span>
      <span>Contributions: <strong id="ins-count">—</strong></span>
      <span>Intensity: <strong id="ins-level">—</strong></span>
      <span>Calendar: <strong id="ins-week">—</strong></span>
    </div>
    <p class="hint">Supports mouse hover, touch tap, and Tab keyboard focus · <a href="index.html">Repo Galaxy</a> · <a href="https://github.com/{safe_user}">@{safe_user} on GitHub</a></p>
  </main>
  <script>
    (function () {{
      var dateEl = document.getElementById("ins-date");
      var countEl = document.getElementById("ins-count");
      var levelEl = document.getElementById("ins-level");
      var weekEl = document.getElementById("ins-week");
      function showTile(tile) {{
        if (!tile) return;
        var count = tile.getAttribute("data-count") || "0";
        var wd = tile.getAttribute("data-weekday") || "";
        dateEl.textContent = (tile.getAttribute("data-date") || "Unknown") + (wd ? " (" + wd + ")" : "");
        countEl.textContent = count === "0" ? "0 (inactive ground tile)" : count;
        levelEl.textContent = tile.getAttribute("data-level") || "None";
        weekEl.textContent = "Week " + (tile.getAttribute("data-week") || "?");
      }}
      var tiles = document.querySelectorAll(".city-tile");
      for (var i = 0; i < tiles.length; i++) {{
        tiles[i].addEventListener("mouseenter", function () {{ showTile(this); }});
        tiles[i].addEventListener("focus", function () {{ showTile(this); }});
        tiles[i].addEventListener("click", function () {{ showTile(this); }});
      }}
    }})();
  </script>
</body>
</html>
"""


def write_standalone_city_page(
    city_svg: str,
    username: str,
    output_path: Path = CONTRIBUTION_CITY_PAGES_HTML_PATH,
) -> Path:
    """Persist optional interactive GitHub Pages Contribution City HTML atomically."""
    return atomic_write_text(output_path, build_standalone_city_html(city_svg, username))


def generate_city_svg_file(
    contributions_path: Path = CONTRIBUTIONS_PATH,
    output_path: Path = CONTRIBUTION_CITY_SVG_PATH,
) -> Path:
    """Load `data/contributions.json`, render 3D Contribution City SVG, validate, and write atomically."""
    payload: dict[str, Any] = json.loads(contributions_path.read_text(encoding="utf-8"))
    svg_text = build_contribution_city_svg(payload)
    return atomic_write_text(output_path, svg_text)


if __name__ == "__main__":
    written = generate_city_svg_file()
    print(f"Generated {written} ({written.stat().st_size} bytes)")
