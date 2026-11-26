"""Render Section 02 Neofetch Developer Terminal SVG matching Reference Image 2."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from src.config import (
    ASCII_PORTRAIT_PATH,
    COMMITS_PATH,
    CONFIG_PATH,
    NEOFETCH_HEIGHT,
    NEOFETCH_PALETTE as P,
    NEOFETCH_SVG_PATH,
    NEOFETCH_WIDTH,
    PROFILE_DATA_PATH,
    REPOSITORIES_PATH,
    atomic_write_text,
)
from src.neofetch_builder import (
    DotRow,
    NeofetchModel,
    RIGHT_COL_CHARS,
    build_neofetch_model,
    load_phase2_inputs,
)
from src.validators import validate_svg_document


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _render_dot_row_tspans(row: DotRow) -> str:
    """Render colored tspans inside a single monospace text element for exact alignment."""
    return (
        f'<tspan fill="{P["label_blue"]}">▪ {_esc(row.label)}: </tspan>'
        f'<tspan fill="{P["dots"]}">{_esc(row.dots)}</tspan>'
        f'<tspan fill="{P["text"]}"> {_esc(row.value)}</tspan>'
    )


def _render_section_header(title: str, x: int, y: int, right_edge_x: int = 927) -> str:
    """Render `- Section` blue heading with crisp horizontal divider rule."""
    # Approximate monospace title width at font-size 12.2 (~7.4px/char) + padding
    line_x1 = x + len(title) * 8 + 10
    return (
        f'<text x="{x}" y="{y}" font-size="12.5" font-weight="700" fill="{P["header_blue"]}">'
        f"{_esc(title)}</text>\n"
        f'    <line x1="{line_x1}" y1="{y - 4}" x2="{right_edge_x}" y2="{y - 4}" '
        f'stroke="{P["divider"]}" stroke-width="1" />'
    )


def build_neofetch_svg(model: NeofetchModel) -> str:
    """Render a faithful, Camo-safe Neofetch terminal SVG from a NeofetchModel."""
    left_x = 50
    right_x = 420
    right_edge_x = 927

    # Vertically center ASCII art inside main body region (y=80..540)
    ascii_line_height = 13.5
    ascii_block_h = len(model.ascii_lines) * ascii_line_height
    ascii_start_y = max(96.0, 82.0 + (450.0 - ascii_block_h) / 2.0)

    ascii_elements: list[str] = []
    for idx, line in enumerate(model.ascii_lines):
        ly = ascii_start_y + idx * ascii_line_height
        ascii_elements.append(
            f'<text x="{left_x}" y="{ly:.1f}" xml:space="preserve">{_esc(line)}</text>'
        )

    # Right column progressive vertical flow
    right_elements: list[str] = []
    y = 84
    right_elements.append(_render_section_header(model.header_title, right_x, y, right_edge_x))
    y += 22

    # Compute row spacing cleanly so all system rows + About + Contact + Stats fit inside 610px
    row_step = 19
    for row in model.system_rows:
        right_elements.append(
            f'<text x="{right_x}" y="{y}" xml:space="preserve">{_render_dot_row_tspans(row)}</text>'
        )
        y += row_step

    y += 8
    right_elements.append(_render_section_header("- About", right_x, y, right_edge_x))
    y += 20
    for bio_line in model.about_lines:
        right_elements.append(
            f'<text x="{right_x}" y="{y}" fill="{P["text"]}" xml:space="preserve">{_esc(bio_line)}</text>'
        )
        y += 18

    y += 8
    right_elements.append(_render_section_header("- Contact", right_x, y, right_edge_x))
    y += 20
    for c_row in model.contact_rows:
        right_elements.append(
            f'<text x="{right_x}" y="{y}" xml:space="preserve">{_render_dot_row_tspans(c_row)}</text>'
        )
        y += row_step

    y += 8
    right_elements.append(_render_section_header("- GitHub Stats", right_x, y, right_edge_x))
    y += 20
    for stat_pair in model.stats_rows:
        left_spans = _render_dot_row_tspans(stat_pair.left)
        if stat_pair.right is not None:
            right_spans = _render_dot_row_tspans(stat_pair.right)
            pipe = f'<tspan fill="{P["divider"]}"> | </tspan>'
            content = f"{left_spans}{pipe}{right_spans}"
        else:
            content = left_spans
        right_elements.append(
            f'<text x="{right_x}" y="{y}" xml:space="preserve">{content}</text>'
        )
        y += row_step

    # Ensure terminal height grows gracefully only if custom links/stats ever exceed default 610px
    canvas_height = max(NEOFETCH_HEIGHT, y + 48)
    bottom_prompt_y = canvas_height - 32
    cursor_x = 34 + (len(model.prompt_prefix) + 4) * 8.1

    prompt_markup_top = (
        f'<text x="34" y="42" font-size="13" xml:space="preserve">'
        f'<tspan fill="{P["prompt_user"]}" font-weight="700">{_esc(model.prompt_prefix)}</tspan>'
        f'<tspan fill="{P["prompt_path"]}">:~$</tspan>'
        f'<tspan fill="{P["prompt_cmd"]}"> neofetch</tspan>'
        f"</text>"
    )
    prompt_markup_bot = (
        f'<text x="34" y="{bottom_prompt_y}" font-size="13" xml:space="preserve">'
        f'<tspan fill="{P["prompt_user"]}" font-weight="700">{_esc(model.prompt_prefix)}</tspan>'
        f'<tspan fill="{P["prompt_path"]}">:~$</tspan>'
        f"</text>\n"
        f'  <rect x="{cursor_x:.1f}" y="{bottom_prompt_y - 12}" width="9" height="16" fill="{P["cursor"]}" />'
    )

    _ = RIGHT_COL_CHARS
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {NEOFETCH_WIDTH} {canvas_height}" width="{NEOFETCH_WIDTH}" height="{canvas_height}" role="img" aria-label="{_esc(model.prompt_prefix)} Neofetch developer system information terminal">
  <style>
    .nf-mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    .nf-ascii {{
      font-size: 11.5px;
      fill: {P["ascii_green"]};
      letter-spacing: 0px;
    }}
    .nf-panel {{
      font-size: 12.2px;
    }}
  </style>

  <rect x="4" y="4" width="{NEOFETCH_WIDTH - 8}" height="{canvas_height - 8}" rx="12" ry="12" fill="{P["bg"]}" stroke="{P["border"]}" stroke-width="1.5" />

  <g class="nf-mono">
    {prompt_markup_top}

    <g class="nf-ascii">
      {"      ".join(ascii_elements)}
    </g>

    <g class="nf-panel">
      {"      ".join(right_elements)}
    </g>

    {prompt_markup_bot}
  </g>
</svg>
'''
    validate_svg_document(svg)
    return svg


def generate_neofetch_svg_file(
    profile_path: Path = PROFILE_DATA_PATH,
    repos_path: Path = REPOSITORIES_PATH,
    commits_path: Path = COMMITS_PATH,
    config_path: Path = CONFIG_PATH,
    ascii_path: Path = ASCII_PORTRAIT_PATH,
    output_path: Path = NEOFETCH_SVG_PATH,
) -> Path:
    """Load Phase 2 JSON datasets, build Neofetch SVG, validate XML, and write atomically."""
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
    svg_text = build_neofetch_svg(model)
    return atomic_write_text(output_path, svg_text)


if __name__ == "__main__":
    written = generate_neofetch_svg_file()
    print(f"Generated {written} ({written.stat().st_size} bytes)")
