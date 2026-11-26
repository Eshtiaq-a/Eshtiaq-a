"""Cohesive SVG renderer combining left Repo Galaxy + right Neofetch developer terminal."""

from __future__ import annotations

import html
from typing import Literal

from src.config import NEOFETCH_HEIGHT, NEOFETCH_PALETTE as P, NEOFETCH_WIDTH
from src.neofetch_builder import DotRow, NeofetchModel
from src.validators import validate_svg_document
from src.visualizations.repo_galaxy import (
    get_galaxy_css,
    reflow_repo_galaxy_model,
    render_repo_galaxy_defs,
    render_repo_galaxy_group,
)

LayoutMode = Literal["desktop", "compact"]


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _render_dot_row_tspans(row: DotRow) -> str:
    """Render colored tspans inside a monospace text element for crisp alignment."""
    return (
        f'<tspan fill="{P["label_blue"]}">▪ {_esc(row.label)}: </tspan>'
        f'<tspan fill="{P["dots"]}">{_esc(row.dots)}</tspan>'
        f'<tspan fill="{P["text"]}"> {_esc(row.value)}</tspan>'
    )


def _render_section_header(title: str, x: float, y: float, right_edge_x: float) -> str:
    """Render section heading with blue text, emerald bullet accent, and crisp divider rule."""
    clean_title = title.lstrip("- ").strip() if title.startswith("-") else title
    display = f"- {clean_title}" if title.startswith("-") else title
    line_x1 = x + len(display) * 7.4 + 14.0
    if title.startswith("-"):
        prefix = f'<tspan fill="{P["ascii_green"]}">-</tspan> {_esc(clean_title)}'
    else:
        prefix = f'<tspan fill="{P["ascii_green"]}">●</tspan> {_esc(display)}'
        line_x1 = x + len(display) * 7.4 + 22.0

    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="12.2" font-weight="700" fill="{P["header_blue"]}" xml:space="preserve">'
        f"{prefix}</text>\n"
        f'    <line x1="{min(line_x1, right_edge_x - 10):.1f}" y1="{y - 4:.1f}" x2="{right_edge_x:.1f}" y2="{y - 4:.1f}" '
        f'stroke="{P["divider"]}" stroke-width="1" />'
    )


def render_neofetch_info_panel(
    model: NeofetchModel,
    panel_x: float,
    start_y: float,
    right_edge_x: float,
) -> tuple[str, float]:
    """Render IDENTITY, ABOUT, CONTACT, GITHUB STATS, and terminal swatches inside right/lower column."""
    elements: list[str] = []
    y = start_y

    elements.append(_render_section_header(model.header_title, panel_x, y, right_edge_x))
    y += 20.0

    row_step = 17.5
    for row in model.system_rows:
        elements.append(
            f'<text x="{panel_x:.1f}" y="{y:.1f}" xml:space="preserve">{_render_dot_row_tspans(row)}</text>'
        )
        y += row_step

    y += 6.0
    elements.append(_render_section_header("- About", panel_x, y, right_edge_x))
    y += 18.5
    for bio_line in model.about_lines:
        elements.append(
            f'<text x="{panel_x:.1f}" y="{y:.1f}" fill="{P["text"]}" xml:space="preserve">{_esc(bio_line)}</text>'
        )
        y += 16.5

    y += 7.0
    elements.append(_render_section_header("- Contact", panel_x, y, right_edge_x))
    y += 18.5
    for c_row in model.contact_rows:
        elements.append(
            f'<text x="{panel_x:.1f}" y="{y:.1f}" xml:space="preserve">{_render_dot_row_tspans(c_row)}</text>'
        )
        y += row_step

    y += 7.0
    elements.append(_render_section_header("- GitHub Stats", panel_x, y, right_edge_x))
    y += 18.5
    for stat_pair in model.stats_rows:
        left_spans = _render_dot_row_tspans(stat_pair.left)
        if stat_pair.right is not None:
            right_spans = _render_dot_row_tspans(stat_pair.right)
            pipe = f'<tspan fill="{P["divider"]}"> | </tspan>'
            content = f"{left_spans}{pipe}{right_spans}"
        else:
            content = left_spans
        elements.append(
            f'<text x="{panel_x:.1f}" y="{y:.1f}" xml:space="preserve">{content}</text>'
        )
        y += row_step

    # Classic Neofetch terminal color swatch palette anchored cleanly below stats
    y += 10.0
    swatches = ("#1d2333", "#e3623a", "#73b88d", "#f1e05a", "#5aa9ff", "#8294ea", "#4b8bbe", "#ebf0f4")
    swatch_elems = [
        f'<rect x="{panel_x + idx * 28.0:.1f}" y="{y:.1f}" width="24" height="12" rx="2" fill="{col}" />'
        for idx, col in enumerate(swatches)
    ]
    elements.extend(swatch_elems)
    y += 22.0

    return "\n      ".join(elements), y


def build_neofetch_terminal_svg(
    model: NeofetchModel,
    layout: LayoutMode = "desktop",
) -> str:
    """Compose cohesive SVG combining animated Repo Galaxy + Neofetch developer info terminal."""
    galaxy_css = get_galaxy_css()

    if layout == "compact":
        canvas_w = 560
        box_x, box_y, box_w, box_h = 24.0, 54.0, 512.0, 446.0
        compact_galaxy = reflow_repo_galaxy_model(
            model.galaxy,
            box_x=box_x,
            box_y=box_y,
            box_w=box_w,
            box_h=box_h,
        )
        galaxy_svg = render_repo_galaxy_group(
            compact_galaxy,
            box_x=box_x,
            box_y=box_y,
            box_w=box_w,
            box_h=box_h,
        )
        panel_svg, content_bottom_y = render_neofetch_info_panel(
            model,
            panel_x=24.0,
            start_y=box_y + box_h + 28.0,
            right_edge_x=canvas_w - 24.0,
        )
        canvas_h = int(max(940, content_bottom_y + 52.0))
        galaxy_cx = box_x + box_w / 2.0
        galaxy_cy = box_y + 216.0
    else:
        # Desktop side-by-side: Galaxy ~42% left (422px of 1009px), Info ~55% right
        canvas_w = NEOFETCH_WIDTH
        box_x, box_y, box_w, box_h = 24.0, 52.0, 422.0, 508.0
        right_x = 468.0
        right_edge_x = 978.0

        galaxy_svg = render_repo_galaxy_group(
            model.galaxy,
            box_x=box_x,
            box_y=box_y,
            box_w=box_w,
            box_h=box_h,
        )
        panel_svg, content_bottom_y = render_neofetch_info_panel(
            model,
            panel_x=right_x,
            start_y=70.0,
            right_edge_x=right_edge_x,
        )
        canvas_h = int(max(NEOFETCH_HEIGHT, box_y + box_h + 48.0, content_bottom_y + 44.0))
        galaxy_cx = box_x + box_w / 2.0
        galaxy_cy = box_y + 240.0

    bottom_prompt_y = canvas_h - 24
    cursor_x = 24 + (len(model.prompt_prefix) + 4) * 7.8

    prompt_top = (
        f'<text x="24" y="34" font-size="12.5" xml:space="preserve">'
        f'<tspan fill="{P["ascii_green"]}" font-weight="700">{_esc(model.prompt_prefix)}</tspan>'
        f'<tspan fill="{P["prompt_path"]}">:~$</tspan>'
        f'<tspan fill="{P["prompt_cmd"]}"> neofetch</tspan>'
        f'<tspan fill="{P["dots"]}"> --repo-galaxy</tspan>'
        f"</text>\n"
        f'    <circle cx="{canvas_w - 125}" cy="30" r="3.5" fill="{P["ascii_green"]}" />'
        f'<text x="{canvas_w - 24}" y="34" text-anchor="end" font-size="10.5" fill="{P["muted"]}">LIVE TELEMETRY</text>'
    )

    prompt_bot = (
        f'<text x="24" y="{bottom_prompt_y}" font-size="12.5" xml:space="preserve">'
        f'<tspan fill="{P["ascii_green"]}" font-weight="700">{_esc(model.prompt_prefix)}</tspan>'
        f'<tspan fill="{P["prompt_path"]}">:~$</tspan>'
        f"</text>\n"
        f'    <rect class="nf-cursor" x="{cursor_x:.1f}" y="{bottom_prompt_y - 12}" width="8" height="15" fill="{P["cursor"]}" />'
    )

    galaxy_defs = render_repo_galaxy_defs(galaxy_cx, galaxy_cy)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}" role="img" aria-label="{_esc(model.prompt_prefix)} animated Repo Galaxy and Neofetch developer terminal">
  <defs>
{galaxy_defs}
  </defs>

  <style>
    .nf-mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    .nf-panel {{
      font-size: 11.4px;
    }}
    @keyframes nfCursorBlink {{
      0%, 49% {{ opacity: 1; }}
      50%, 100% {{ opacity: 0.15; }}
    }}
    .nf-cursor {{
      animation: nfCursorBlink 1.3s step-end infinite;
    }}
    @media (prefers-reduced-motion: reduce) {{
      .nf-cursor {{ animation: none; opacity: 1; }}
    }}
    {galaxy_css}
  </style>

  <rect x="4" y="4" width="{canvas_w - 8}" height="{canvas_h - 8}" rx="12" ry="12" fill="{P["bg"]}" stroke="{P["border"]}" stroke-width="1.5" />

  <g class="nf-mono">
    {prompt_top}

    {galaxy_svg}

    <g class="nf-panel">
      {panel_svg}
    </g>

    {prompt_bot}
  </g>
</svg>
'''
    validate_svg_document(svg)
    return svg
