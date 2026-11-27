"""Isometric 3D Contribution City SVG geometry, intensity mapper, animations, and renderer."""

from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from src.config import CONTRIBUTION_CITY_SVG_PATH, NEOFETCH_PALETTE as P
from src.validators import validate_contributions_payload, validate_svg_document

CITY_WIDTH = 1009
CITY_HEIGHT = 620
MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# 5-tier midnight/cyan/teal building palette harmonizing with Repo Galaxy & Neofetch
LEVEL_PALETTES: dict[int, dict[str, str]] = {
    0: {
        "top": "#0c1428",
        "left": "#080e1d",
        "right": "#0a1122",
        "stroke": "#162447",
        "win": "#0c1428",
    },
    1: {
        "top": "#1f6f8a",
        "left": "#114054",
        "right": "#175770",
        "stroke": "#298aa8",
        "win": "#47b5d1",
    },
    2: {
        "top": "#28a2c4",
        "left": "#145770",
        "right": "#1c7896",
        "stroke": "#42c6e8",
        "win": "#7be3ff",
    },
    3: {
        "top": "#3bd4eb",
        "left": "#186f8c",
        "right": "#259ab8",
        "stroke": "#6ef0ff",
        "win": "#bdf8ff",
    },
    4: {
        "top": "#7ef9ff",
        "left": "#1d87a8",
        "right": "#2eb6d9",
        "stroke": "#c4feff",
        "win": "#ffffff",
    },
}


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def compute_building_height(count: int, max_count: int, level: int) -> float:
    """Map daily contribution count and tier deterministically to isometric pixel height."""
    if count <= 0 or level <= 0:
        return 1.8
    norm = math.sqrt(count / max(1, max_count)) if max_count > 1 else 1.0
    if level == 1:
        return round(10.0 + 8.0 * norm, 1)
    if level == 2:
        return round(22.0 + 14.0 * norm, 1)
    if level == 3:
        return round(40.0 + 22.0 * norm, 1)
    return round(66.0 + 26.0 * norm, 1)


def iso_project(
    col: float,
    row: float,
    z: float,
    origin_x: float,
    origin_y: float,
    tw: float,
    th: float,
) -> tuple[float, float]:
    """Project isometric grid coordinate (col, row, vertical height z) to 2D SVG (x, y)."""
    sx = origin_x + (col - row) * tw
    sy = origin_y + (col + row) * th - z
    return round(sx, 1), round(sy, 1)


def _pts(coords: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)


@dataclass(frozen=True)
class CityTile:
    """Single isometric tile/building cell in the Contribution City."""

    col: int
    row: int
    date: str
    count: int
    level: int
    intensity_label: str
    weekday_name: str
    height: float


@dataclass(frozen=True)
class ContributionCityModel:
    """Normalized model consumed by the SVG Contribution City renderer."""

    username: str
    source: str
    graphql_available: bool
    is_fallback: bool
    total_contributions: int
    active_days: int
    current_streak_days: int
    best_streak_days: int
    max_daily_contributions: int
    busiest_date: str | None
    busiest_count: int
    date_start: str | None
    date_end: str | None
    weeks_count: int
    tiles: tuple[CityTile, ...]
    month_markers: tuple[tuple[int, str], ...]


def build_contribution_city_model(payload: dict[str, Any]) -> ContributionCityModel:
    """Convert validated `data/contributions.json` payload into isometric city tiles."""
    validate_contributions_payload(payload)
    weeks = list(payload.get("weeks") or [])
    max_daily = int(payload.get("max_daily_contributions") or 0)

    tiles: list[CityTile] = []
    month_markers: list[tuple[int, str]] = []
    last_month: int | None = None

    for w_idx, week in enumerate(weeks):
        days = sorted(week.get("days") or [], key=lambda d: int(d.get("weekday", 0)))
        if days:
            try:
                first_d = date.fromisoformat(str(days[0]["date"]))
                if first_d.month != last_month and (w_idx == 0 or first_d.day <= 7):
                    month_markers.append((w_idx, MONTH_ABBR[first_d.month - 1]))
                    last_month = first_d.month
            except ValueError:
                pass
        for day in days:
            cnt = int(day["count"])
            lvl = int(day["level"])
            tiles.append(
                CityTile(
                    col=w_idx,
                    row=int(day["weekday"]),
                    date=str(day["date"]),
                    count=cnt,
                    level=lvl,
                    intensity_label=str(day.get("intensity_label") or "None"),
                    weekday_name=str(day.get("weekday_name") or ""),
                    height=compute_building_height(cnt, max_daily, lvl),
                )
            )

    # Sort strictly back-to-front via painter's order (col + row, col)
    tiles.sort(key=lambda t: (t.col + t.row, t.col))

    busiest = payload.get("busiest_day") or {}
    date_range = payload.get("date_range") or {}
    return ContributionCityModel(
        username=str(payload.get("username") or "Eshtiaq-a"),
        source=str(payload.get("source") or "unknown"),
        graphql_available=bool(payload.get("graphql_available")),
        is_fallback=bool(payload.get("is_fallback")),
        total_contributions=int(payload.get("total_contributions") or 0),
        active_days=int(payload.get("active_days") or 0),
        current_streak_days=int(payload.get("current_streak_days") or 0),
        best_streak_days=int(payload.get("best_streak_days") or 0),
        max_daily_contributions=max_daily,
        busiest_date=busiest.get("date"),
        busiest_count=int(busiest.get("count") or 0),
        date_start=date_range.get("start"),
        date_end=date_range.get("end"),
        weeks_count=max(1, len(weeks)),
        tiles=tuple(tiles),
        month_markers=tuple(month_markers),
    )


def _render_voxel_prism(
    col: int,
    row: int,
    height: float,
    level: int,
    origin_x: float,
    origin_y: float,
    tw: float,
    th: float,
    pad: float = 0.14,
    is_peak: bool = False,
) -> str:
    """Render 3D isometric voxel (top, left, right faces + window tiers & peak crown)."""
    pal = LEVEL_PALETTES.get(level, LEVEL_PALETTES[0])
    c0, c1 = col + pad, col + 1.0 - pad
    r0, r1 = row + pad, row + 1.0 - pad

    # Base points (z=0) and roof points (z=height)
    b_r = iso_project(c1, r0, 0.0, origin_x, origin_y, tw, th)
    b_f = iso_project(c1, r1, 0.0, origin_x, origin_y, tw, th)
    b_l = iso_project(c0, r1, 0.0, origin_x, origin_y, tw, th)

    t_b = iso_project(c0, r0, height, origin_x, origin_y, tw, th)
    t_r = iso_project(c1, r0, height, origin_x, origin_y, tw, th)
    t_f = iso_project(c1, r1, height, origin_x, origin_y, tw, th)
    t_l = iso_project(c0, r1, height, origin_x, origin_y, tw, th)

    if level == 0:
        # Flat dark ground tile with subtle isometric bevel
        return (
            f'<polygon class="city-top" points="{_pts([t_b, t_r, t_f, t_l])}" '
            f'fill="{pal["top"]}" stroke="{pal["stroke"]}" stroke-width="0.6" />'
        )

    parts = [
        f'<polygon points="{_pts([t_l, t_f, b_f, b_l])}" fill="{pal["left"]}" stroke="{pal["stroke"]}" stroke-width="0.45" />',
        f'<polygon points="{_pts([t_f, t_r, b_r, b_f])}" fill="{pal["right"]}" stroke="{pal["stroke"]}" stroke-width="0.45" />',
        f'<polygon class="city-top" points="{_pts([t_b, t_r, t_f, t_l])}" fill="{pal["top"]}" stroke="{pal["stroke"]}" stroke-width="0.65" />',
    ]

    # Subtle glowing horizontal window bands + rooftop parapet on taller buildings
    if level >= 1 and height >= 12.0:
        bands = 1 if level <= 2 else (2 if level == 3 else 3)
        for b in range(1, bands + 1):
            wz = round(height * (b / (bands + 1.15)), 1)
            wl0 = iso_project(c0 + 0.08, r1, wz, origin_x, origin_y, tw, th)
            wl1 = iso_project(c1 - 0.08, r1, wz, origin_x, origin_y, tw, th)
            wr0 = iso_project(c1, r1 - 0.08, wz, origin_x, origin_y, tw, th)
            wr1 = iso_project(c1, r0 + 0.08, wz, origin_x, origin_y, tw, th)
            parts.append(
                f'<line x1="{wl0[0]}" y1="{wl0[1]}" x2="{wl1[0]}" y2="{wl1[1]}" '
                f'stroke="{pal["win"]}" stroke-width="1.15" stroke-opacity="0.78" />'
            )
            parts.append(
                f'<line x1="{wr0[0]}" y1="{wr0[1]}" x2="{wr1[0]}" y2="{wr1[1]}" '
                f'stroke="{pal["win"]}" stroke-width="1.15" stroke-opacity="0.90" />'
            )

    # Crown tier + beacon spire on Peak towers
    if is_peak or level == 4:
        spire_h = height + 9.0
        sp_b = iso_project(col + 0.30, row + 0.30, spire_h, origin_x, origin_y, tw, th)
        sp_r = iso_project(col + 0.70, row + 0.30, spire_h, origin_x, origin_y, tw, th)
        sp_f = iso_project(col + 0.70, row + 0.70, spire_h, origin_x, origin_y, tw, th)
        sp_l = iso_project(col + 0.30, row + 0.70, spire_h, origin_x, origin_y, tw, th)
        b_f_c = iso_project(col + 0.70, row + 0.70, height, origin_x, origin_y, tw, th)
        b_l_c = iso_project(col + 0.30, row + 0.70, height, origin_x, origin_y, tw, th)
        b_r_c = iso_project(col + 0.70, row + 0.30, height, origin_x, origin_y, tw, th)
        parts.extend(
            [
                f'<polygon points="{_pts([sp_l, sp_f, b_f_c, b_l_c])}" fill="#2196b8" />',
                f'<polygon points="{_pts([sp_f, sp_r, b_r_c, b_f_c])}" fill="#3ad0eb" />',
                f'<polygon class="city-beacon" points="{_pts([sp_b, sp_r, sp_f, sp_l])}" fill="#ffffff" />',
                f'<circle class="city-beacon-halo" cx="{(sp_b[0] + sp_f[0]) / 2:.1f}" cy="{(sp_b[1] + sp_f[1]) / 2:.1f}" r="6.5" fill="#7ef9ff" />',
            ]
        )

    return "".join(parts)


def build_contribution_city_svg(payload: dict[str, Any]) -> str:
    """Render a self-contained, Camo-safe 3D Isometric Contribution City SVG."""
    model = build_contribution_city_model(payload)
    w_count = model.weeks_count

    # Fit grid proportionally inside 1009x620 diorama frame while preserving 2:1 isometric angle
    tw = min(15.5, max(8.5, 730.0 / (w_count + 7)))
    th = tw * 0.5
    origin_x = 504.5 - ((w_count - 7) / 2.0) * tw
    origin_y = 337.0 - ((w_count + 7) / 2.0) * th

    # 3D isometric base slab encompassing the full calendar grid
    slab_d = 12.0
    margin = 0.45
    sb = iso_project(-margin, -margin, 0.0, origin_x, origin_y, tw, th)
    sr = iso_project(w_count + margin, -margin, 0.0, origin_x, origin_y, tw, th)
    sf = iso_project(w_count + margin, 7.0 + margin, 0.0, origin_x, origin_y, tw, th)
    sl = iso_project(-margin, 7.0 + margin, 0.0, origin_x, origin_y, tw, th)
    sl_d = (sl[0], round(sl[1] + slab_d, 1))
    sf_d = (sf[0], round(sf[1] + slab_d, 1))
    sr_d = (sr[0], round(sr[1] + slab_d, 1))

    slab_markup = "\n      ".join(
        [
            f'<polygon points="{_pts([sl, sf, sf_d, sl_d])}" fill="#060a14" stroke="#182a4f" stroke-width="0.9" />',
            f'<polygon points="{_pts([sf, sr, sr_d, sf_d])}" fill="#0a1224" stroke="#182a4f" stroke-width="0.9" />',
            f'<polygon points="{_pts([sb, sr, sf, sl])}" fill="#090e1c" stroke="#243c6e" stroke-width="1.1" />',
        ]
    )

    # Subtle month markers along back-right edge (row=0) & weekday ticks along left edge (col=0)
    axis_elems: list[str] = []
    for m_col, m_label in model.month_markers:
        mx, my = iso_project(m_col + 0.5, -0.75, 0.0, origin_x, origin_y, tw, th)
        axis_elems.append(
            f'<text x="{mx:.1f}" y="{my:.1f}" text-anchor="middle" font-size="8.2" fill="#6f80a3">{_esc(m_label)}</text>'
        )
    for wd_row, wd_label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        wx, wy = iso_project(-0.85, wd_row + 0.5, 0.0, origin_x, origin_y, tw, th)
        axis_elems.append(
            f'<text x="{wx:.1f}" y="{wy:.1f}" text-anchor="end" font-size="8.0" fill="#6f80a3">{wd_label}</text>'
        )

    # Render all tiles in painter's back-to-front order
    tile_elems: list[str] = []
    for tile in model.tiles:
        is_peak = bool(model.busiest_date and tile.date == model.busiest_date and tile.count > 0)
        prism = _render_voxel_prism(
            col=tile.col,
            row=tile.row,
            height=tile.height,
            level=tile.level,
            origin_x=origin_x,
            origin_y=origin_y,
            tw=tw,
            th=th,
            is_peak=is_peak,
        )
        plural = "contribution" if tile.count == 1 else "contributions"
        tip = (
            f"{tile.date} ({tile.weekday_name}): {tile.count} {plural} · "
            f"{tile.intensity_label} · Week {tile.col + 1}"
        )
        if tile.level > 0:
            delay = round((tile.col / max(1, w_count)) * 1.4, 2)
            body = f'<g class="city-bldg" style="animation-delay:{delay:.2f}s">{prism}</g>'
        else:
            body = prism

        tile_elems.append(
            f'<g class="city-tile" tabindex="0" role="graphics-symbol" '
            f'aria-label="{_esc(tip)}" data-date="{_esc(tile.date)}" '
            f'data-count="{tile.count}" data-level="{_esc(tile.intensity_label)}" '
            f'data-week="{tile.col + 1}" data-weekday="{_esc(tile.weekday_name)}">'
            f'<title>{_esc(tip)}</title>{body}</g>'
        )

    # Mini 5-tier isometric legend cubes in bottom-left negative space (x=24..294, y=390..526)
    legend_cubes: list[str] = []
    legend_labels = ((0, "None"), (1, "Low"), (2, "Mod"), (3, "High"), (4, "Peak"))
    for idx, (lvl, lbl) in enumerate(legend_labels):
        lx = 46.0 + idx * 50.0
        ly = 456.0
        lh = 2.0 if lvl == 0 else float(3 + lvl * 4)
        cube = _render_voxel_prism(0, 0, lh, lvl, lx, ly, 7.0, 3.5, pad=0.05)
        legend_cubes.append(
            f'<g>{cube}<text x="{lx:.1f}" y="476.0" text-anchor="middle" font-size="8.6" fill="#9fb0cf">{lbl}</text></g>'
        )

    range_str = (
        f"{model.date_start} → {model.date_end}"
        if (model.date_start and model.date_end)
        else "No dates available"
    )
    busiest_str = (
        f"{model.busiest_date} ({model.busiest_count})"
        if model.busiest_date and model.busiest_count > 0
        else "None yet"
    )
    source_badge = "GRAPHQL CALENDAR" if model.graphql_available else "COMMITS FALLBACK"
    badge_bg = "#132c24" if model.graphql_available else "#18263e"
    badge_border = "#2f7858" if model.graphql_available else "#3e6199"
    badge_fg = "#73b88d" if model.graphql_available else "#7db8ff"
    footer_source = (
        "Live GitHub GraphQL contributionsCollection"
        if model.graphql_available
        else "Fallback: public-branch commits (set GITHUB_TOKEN for GraphQL)"
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CITY_WIDTH} {CITY_HEIGHT}" width="{CITY_WIDTH}" height="{CITY_HEIGHT}" role="img" aria-label="{_esc(model.username)} 3D Isometric GitHub Contribution City showing {model.total_contributions} contributions across {model.active_days} active days">
  <defs>
    <clipPath id="city-frame-clip">
      <rect x="1" y="1" width="{CITY_WIDTH - 2}" height="{CITY_HEIGHT - 2}" rx="10" ry="10" />
    </clipPath>
    <radialGradient id="city-sky-glow" cx="50%" cy="46%" r="58%">
      <stop offset="0%" stop-color="#112952" stop-opacity="0.72" />
      <stop offset="50%" stop-color="#0b1630" stop-opacity="0.45" />
      <stop offset="100%" stop-color="#080c18" stop-opacity="0" />
    </radialGradient>
  </defs>

  <style>
    .city-mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    .city-title {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      letter-spacing: 1.4px;
    }}
    @keyframes cityGrow {{
      0% {{
        opacity: 0.78;
      }}
      50% {{
        opacity: 1;
      }}
      100% {{
        opacity: 0.86;
      }}
    }}
    @keyframes cityBeaconPulse {{
      0%, 100% {{
        opacity: 0.38;
      }}
      50% {{
        opacity: 0.95;
      }}
    }}
    @keyframes cityAmbientGlow {{
      0%, 100% {{
        opacity: 0.72;
      }}
      50% {{
        opacity: 0.96;
      }}
    }}
    .city-bldg {{
      animation: cityGrow 4.8s ease-in-out infinite;
    }}
    .city-beacon-halo {{
      animation: cityBeaconPulse 2.8s ease-in-out infinite;
    }}
    .city-ambient-glow {{
      animation: cityAmbientGlow 6.0s ease-in-out infinite;
    }}
    .city-tile {{
      cursor: pointer;
      outline: none;
      transition: transform 0.14s ease;
    }}
    .city-tile:hover,
    .city-tile:focus-visible {{
      transform: translateY(-2px);
    }}
    .city-tile:hover .city-top,
    .city-tile:focus-visible .city-top {{
      stroke: #ffffff;
      stroke-width: 1.3;
    }}
    @media (prefers-reduced-motion: reduce) {{
      .city-bldg,
      .city-beacon-halo,
      .city-ambient-glow {{
        animation: none;
      }}
      .city-tile {{
        transition: none;
      }}
    }}
  </style>

  <rect x="1" y="1" width="{CITY_WIDTH - 2}" height="{CITY_HEIGHT - 2}" rx="10" ry="10" fill="{P["bg"]}" stroke="{P["border"]}" stroke-width="1.2" />

  <g clip-path="url(#city-frame-clip)" class="city-mono">
    <!-- Top Terminal Bar -->
    <rect x="1" y="1" width="{CITY_WIDTH - 2}" height="40" fill="#121723" />
    <line x1="1" y1="41" x2="{CITY_WIDTH - 1}" y2="41" stroke="#1d2b4d" stroke-width="1" />
    <circle cx="24" cy="21" r="4.5" fill="#38bdf8" />
    <circle cx="24" cy="21" r="8" fill="#38bdf8" fill-opacity="0.22" />
    <text x="38" y="25" font-size="12.5" font-weight="700" fill="{P["prompt_user"]}">{_esc(model.username.lower())}@github<tspan fill="{P["prompt_path"]}">:~$</tspan> <tspan fill="{P["prompt_cmd"]}">contribution-city --iso --3d</tspan></text>

    <rect x="854" y="11" width="136" height="20" rx="5" fill="{badge_bg}" stroke="{badge_border}" stroke-width="0.9" />
    <text x="922" y="24.5" text-anchor="middle" font-size="9.2" font-weight="700" fill="{badge_fg}">{source_badge}</text>

    <!-- Main Isometric Diorama Viewport -->
    <rect x="16" y="49" width="977" height="492" rx="8" fill="#080c18" stroke="#1d2b4d" stroke-width="1" />
    <ellipse class="city-ambient-glow" cx="504.5" cy="295" rx="420" ry="210" fill="url(#city-sky-glow)" />

    <!-- Subtle decorative stars -->
    <circle cx="88" cy="96" r="1.1" fill="#c9d8ff" fill-opacity="0.45" />
    <circle cx="156" cy="78" r="0.9" fill="#c9d8ff" fill-opacity="0.35" />
    <circle cx="348" cy="74" r="1.2" fill="#c9d8ff" fill-opacity="0.40" />
    <circle cx="516" cy="68" r="0.9" fill="#c9d8ff" fill-opacity="0.38" />
    <circle cx="628" cy="92" r="1.1" fill="#c9d8ff" fill-opacity="0.35" />
    <circle cx="944" cy="292" r="1.0" fill="#c9d8ff" fill-opacity="0.40" />
    <circle cx="912" cy="396" r="1.2" fill="#c9d8ff" fill-opacity="0.35" />

    <!-- Top-Left Title Subtitle -->
    <text x="32" y="76" class="city-title" font-size="13.0" font-weight="700" fill="#e5e9f3">3D CONTRIBUTION CITY</text>
    <text x="32" y="94" font-size="10.0" fill="#7080a3">Isometric skyline · height scaled by daily GitHub activity</text>

    <!-- Isometric Diorama Slab + Axis Labels + Sorted Voxel Skyline -->
    <g id="city-diorama">
      {slab_markup}
      {"".join(axis_elems)}
      {"".join(tile_elems)}
    </g>

    <!-- Top-Right Compact Telemetry HUD Card (negative space above right edge of diamond) -->
    <rect x="692" y="60" width="286" height="156" rx="8" fill="#0a1020" fill-opacity="0.92" stroke="#243a6b" stroke-width="1" />
    <text x="708" y="81" font-size="9.5" font-weight="700" letter-spacing="1.2" fill="#5aa9ff">ACTIVITY TELEMETRY</text>
    <text x="708" y="96" font-size="8.6" fill="#6f80a3">{_esc(range_str)}</text>
    <line x1="708" y1="104" x2="962" y2="104" stroke="#18274a" stroke-width="1" />

    <text x="708" y="124" font-size="10.2" fill="#8b9bc0">Total Contributions</text>
    <text x="962" y="124" text-anchor="end" font-size="13.5" font-weight="700" fill="#7ef9ff">{model.total_contributions}</text>

    <text x="708" y="146" font-size="10.2" fill="#8b9bc0">Active Days</text>
    <text x="962" y="146" text-anchor="end" font-size="11.5" font-weight="700" fill="#dce6ff">{model.active_days}</text>

    <text x="708" y="168" font-size="10.2" fill="#8b9bc0">Highest Day Count</text>
    <text x="962" y="168" text-anchor="end" font-size="11.5" font-weight="700" fill="#3bd4eb">{model.max_daily_contributions}</text>

    <text x="708" y="190" font-size="10.2" fill="#8b9bc0">Busiest Day</text>
    <text x="962" y="190" text-anchor="end" font-size="10.2" font-weight="600" fill="#f2cb62">{_esc(busiest_str)}</text>

    <text x="708" y="207" font-size="8.8" fill="#6f80a3">Streak: {model.current_streak_days}d current · {model.best_streak_days}d best</text>

    <!-- Bottom-Left Intensity Legend Card (negative space below left edge of diamond) -->
    <rect x="28" y="402" width="262" height="124" rx="8" fill="#0a1020" fill-opacity="0.92" stroke="#243a6b" stroke-width="1" />
    <text x="42" y="423" font-size="9.2" font-weight="700" letter-spacing="1.2" fill="#5aa9ff">INTENSITY SCALE</text>
    <line x1="42" y1="431" x2="276" y2="431" stroke="#18274a" stroke-width="1" />
    {"".join(legend_cubes)}
    <text x="42" y="501" font-size="9.0" fill="#7080a3">Flat lot = 0 commits · Spire = Peak day</text>
    <text x="42" y="516" font-size="8.8" fill="#5aa9ff">Hover or Tab tiles in standalone SVG view</text>

    <!-- Bottom Terminal Status Bar -->
    <rect x="16" y="550" width="977" height="54" rx="8" fill="#0b101c" stroke="#1d2b4d" stroke-width="1" />
    <text x="32" y="573" font-size="10.5" fill="{P["ascii_green"]}">● <tspan fill="#dce6ff">{_esc(footer_source)}</tspan></text>
    <text x="32" y="592" font-size="9.6" fill="#7080a3">Period: {_esc(range_str)} · {model.weeks_count} weeks · {len(model.tiles)} daily tiles</text>
    <text x="977" y="582" text-anchor="end" font-size="9.8" fill="#5aa9ff">{_esc(model.username)}@github:~/city$</text>
  </g>
</svg>
'''
    validate_svg_document(svg)
    return svg


def generate_contribution_city_svg_file(
    contributions_payload: dict[str, Any],
    output_path: Path = CONTRIBUTION_CITY_SVG_PATH,
) -> Path:
    """Render and atomically write `assets/contribution_city.svg`."""
    from src.config import atomic_write_text

    svg_text = build_contribution_city_svg(contributions_payload)
    return atomic_write_text(output_path, svg_text)
