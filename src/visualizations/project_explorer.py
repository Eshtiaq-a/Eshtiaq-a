"""Terminal-inspired SVG renderer for Section 03 Automatic GitHub Project Explorer."""

from __future__ import annotations

import html
from typing import Literal

from src.config import EXPLORER_PALETTE as P, EXPLORER_WIDTH
from src.explorer_builder import ExplorerModel, ExplorerRow
from src.validators import validate_svg_document

LayoutMode = Literal["desktop", "compact"]


def _esc(text: str) -> str:
    return html.escape(text, quote=True)


def _render_language_icon(row: ExplorerRow, x: float, y: float) -> str:
    """Render a crisp 22x22 self-contained SVG icon matching the repository's primary language."""
    tag = row.language_tag
    bg = row.badge_bg
    border = row.badge_border
    fg = row.badge_fg

    # Custom geometric symbols for major languages + neat monogram/fallback
    if tag == "PY":
        inner = (
            f'<rect x="{x + 5:.1f}" y="{y + 5:.1f}" width="7" height="5" rx="2" fill="#4b8bbe" />'
            f'<rect x="{x + 10:.1f}" y="{y + 12:.1f}" width="7" height="5" rx="2" fill="#f2cb62" />'
            f'<rect x="{x + 8:.1f}" y="{y + 9:.1f}" width="6" height="4" rx="1" fill="#82b8e8" />'
            f'<circle cx="{x + 7.2:.1f}" cy="{y + 7.2:.1f}" r="0.9" fill="#0d0f14" />'
            f'<circle cx="{x + 14.8:.1f}" cy="{y + 14.8:.1f}" r="0.9" fill="#0d0f14" />'
        )
    elif tag == "HTML":
        inner = (
            f'<path d="M {x + 8.5:.1f} {y + 7.2:.1f} L {x + 4.8:.1f} {y + 11:.1f} L {x + 8.5:.1f} {y + 14.8:.1f}" '
            f'fill="none" stroke="{fg}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />'
            f'<path d="M {x + 13.5:.1f} {y + 7.2:.1f} L {x + 17.2:.1f} {y + 11:.1f} L {x + 13.5:.1f} {y + 14.8:.1f}" '
            f'fill="none" stroke="{fg}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />'
            f'<line x1="{x + 12:.1f}" y1="{y + 6.5:.1f}" x2="{x + 10:.1f}" y2="{y + 15.5:.1f}" '
            f'stroke="#f2cb62" stroke-width="1.3" stroke-linecap="round" />'
        )
    elif tag == "DIR":
        inner = (
            f'<path d="M {x + 5:.1f} {y + 7.5:.1f} h 4.2 l 1.5 1.8 h 6.3 v 6.7 h -12 Z" '
            f'fill="none" stroke="{fg}" stroke-width="1.4" stroke-linejoin="round" />'
        )
    elif tag in {"SH", "PS"}:
        inner = (
            f'<path d="M {x + 5.8:.1f} {y + 7.5:.1f} l 3.5 3.3 l -3.5 3.3" '
            f'fill="none" stroke="{fg}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" />'
            f'<line x1="{x + 11.2:.1f}" y1="{y + 14.2:.1f}" x2="{x + 16.4:.1f}" y2="{y + 14.2:.1f}" '
            f'stroke="{fg}" stroke-width="1.6" stroke-linecap="round" />'
        )
    elif tag == "SQL":
        inner = (
            f'<ellipse cx="{x + 11:.1f}" cy="{y + 7.2:.1f}" rx="5.5" ry="2.1" fill="none" stroke="{fg}" stroke-width="1.3" />'
            f'<path d="M {x + 5.5:.1f} {y + 7.2:.1f} v 7.4 c 0 1.2 2.5 2.1 5.5 2.1 s 5.5 -0.9 5.5 -2.1 v -7.4" '
            f'fill="none" stroke="{fg}" stroke-width="1.3" />'
        )
    else:
        font_sz = "7.6" if len(tag) >= 3 else "9.2"
        inner = (
            f'<text x="{x + 11:.1f}" y="{y + 14.4:.1f}" text-anchor="middle" '
            f'font-size="{font_sz}" font-weight="700" fill="{fg}">{_esc(tag)}</text>'
        )

    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="22" height="22" rx="4.5" '
        f'fill="{bg}" stroke="{border}" stroke-width="1" />'
        f"{inner}"
    )


STATUS_PILL_STYLES: dict[str, tuple[str, str, str, float]] = {
    "LIVE": ("#112b22", "#357958", "#73b88d", 36.0),
    "EMPTY": ("#171c28", "#343d52", "#7f8aa1", 40.0),
    "ARCHIVED": ("#292018", "#61482c", "#d6a45c", 56.0),
}
DEFAULT_STATUS_PILL_STYLE: tuple[str, str, str, float] = ("#162238", "#345082", "#7aa6eb", 38.0)


def _status_pill_width(status: str | None) -> float:
    if not status:
        return 0.0
    return STATUS_PILL_STYLES.get(status, DEFAULT_STATUS_PILL_STYLE)[3]


def _render_status_pill(status: str | None, x: float, y: float) -> str:
    if not status:
        return ""
    bg, stroke, fg, w = STATUS_PILL_STYLES.get(status, DEFAULT_STATUS_PILL_STYLE)
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="15" rx="3.5" '
        f'fill="{bg}" stroke="{stroke}" stroke-width="0.8" />'
        f'<text x="{x + w / 2.0:.1f}" y="{y + 10.6:.1f}" text-anchor="middle" '
        f'font-size="8.4" font-weight="700" fill="{fg}">{_esc(status)}</text>'
    )


def _build_accessible_title(row: ExplorerRow) -> str:
    langs = ", ".join(row.languages) if row.languages else row.primary_language
    parts = [
        row.full_name,
        row.description,
        f"Language: {langs}",
        f"Stars: {row.stars}",
        f"Updated: {row.updated_label}",
    ]
    if row.homepage:
        parts.append(f"Live: {row.homepage}")
    return " | ".join(parts)


def _wrap_row_link(row: ExplorerRow, inner_lines: list[str]) -> str:
    body = "\n      ".join(inner_lines)
    if not row.html_url:
        return body
    return "\n      ".join(
        [
            f'<a class="exp-repo-link" href="{_esc(row.html_url)}" target="_blank" rel="noopener noreferrer" aria-label="Open {_esc(row.name)} repository on GitHub">',
            body,
            "</a>",
        ]
    )


def _render_desktop_row_content(row: ExplorerRow, index: int, y: float, is_slice: bool = False) -> str:
    alt_fill = P["row_even"] if index % 2 == 0 else P["row_odd"]
    is_dim = row.archived or row.is_empty
    mode_col = P["dir_muted"] if is_dim else P["dir_green"]
    name_col = P["muted"] if is_dim else P["repo_blue"]
    desc_col = P["dim"] if row.description == "No description provided." else P["desc"]
    star_col = P["star_gold"] if row.stars > 0 else P["muted"]

    lang_display = row.primary_language
    if len(lang_display) > 12:
        lang_display = lang_display[:11].rstrip() + "…"
    extra_span = (
        f'<tspan fill="{P["muted"]}"> +{row.extra_language_count}</tspan>'
        if row.extra_language_count > 0
        else ""
    )

    shown_name = row.display_name
    pill_w = _status_pill_width(row.status_badge)
    if row.status_badge:
        max_pill_x = 326.0 - pill_w
        est_name_w = len(shown_name) * 7.5
        pill_x = min(max_pill_x, 110.0 + est_name_w + 8.0)
        if 110.0 + est_name_w + 6.0 > pill_x:
            max_chars = max(6, int((pill_x - 116.0) / 7.5))
            if len(shown_name) > max_chars:
                base = shown_name.rstrip("/…")
                shown_name = f"{base[: max(4, max_chars - 2)].rstrip()}…/"
        pill_svg = _render_status_pill(row.status_badge, pill_x, y + 11.5)
    else:
        pill_svg = ""
    icon_svg = _render_language_icon(row, 76.0, y + 8.0)

    if is_slice:
        row_bg = (
            f'    <rect class="exp-row-bg" x="4" y="{y:.1f}" width="1001" height="40" rx="7" '
            f'fill="{alt_fill}" stroke="#1d2b4d" stroke-width="1.1" pointer-events="all" />'
        )
        accent_bar = (
            f'    <rect class="exp-accent-bar" x="5" y="{y + 7:.1f}" width="3" height="26" rx="1.5" '
            f'fill="{row.language_color}" fill-opacity="{0.28 if is_dim else 0.78}" />'
        )
    else:
        row_bg = (
            f'    <rect class="exp-row-bg" x="20" y="{y:.1f}" width="969" height="38" rx="5" '
            f'fill="{alt_fill}" stroke="transparent" stroke-width="1" pointer-events="all" />'
        )
        accent_bar = (
            f'    <rect class="exp-accent-bar" x="20" y="{y + 7:.1f}" width="3" height="24" rx="1.5" '
            f'fill="{row.language_color}" fill-opacity="{0.28 if is_dim else 0.72}" />'
        )

    inner_lines = [
        '  <g class="exp-row">',
        f"    <title>{_esc(_build_accessible_title(row))}</title>",
        row_bg,
        accent_bar,
        f'    <text x="34" y="{y + 23:.1f}" font-size="11.5" fill="{mode_col}">{_esc(row.dir_mode)}</text>',
        f"    {icon_svg}",
        f'    <text class="exp-repo-name" x="110" y="{y + 23:.1f}" font-size="12.5" font-weight="700" fill="{name_col}">{_esc(shown_name)}</text>',
        f"    {pill_svg}" if pill_svg else "",
        f'    <text x="332" y="{y + 23:.1f}" font-size="11.5" fill="{desc_col}">{_esc(row.short_description)}</text>',
        f'    <circle cx="726" cy="{y + 19:.1f}" r="3.8" fill="{row.language_color}" />',
        f'    <text x="736" y="{y + 23:.1f}" font-size="11.5" fill="{P["text"]}" xml:space="preserve">{_esc(lang_display)}{extra_span}</text>',
        f'    <text x="860" y="{y + 23:.1f}" font-size="11.0" fill="{P["muted"]}">{_esc(row.updated_label)}</text>',
        f'    <text x="978" y="{y + 23:.1f}" text-anchor="end" font-size="11.5" font-weight="600" fill="{star_col}">★ {row.stars}</text>',
        "  </g>",
    ]
    return _wrap_row_link(row, [line for line in inner_lines if line])


def _render_desktop_row(row: ExplorerRow, index: int, y: float) -> str:
    return _render_desktop_row_content(row, index, y, is_slice=False)


def _render_compact_row(row: ExplorerRow, index: int, y: float) -> str:
    alt_fill = P["row_even"] if index % 2 == 0 else P["row_odd"]
    is_dim = row.archived or row.is_empty
    mode_col = P["dir_muted"] if is_dim else P["dir_green"]
    name_col = P["muted"] if is_dim else P["repo_blue"]
    desc_col = P["dim"] if row.description == "No description provided." else P["desc"]
    star_col = P["star_gold"] if row.stars > 0 else P["muted"]

    compact_name = row.name + "/"
    if len(compact_name) > 26:
        compact_name = row.name[:24].rstrip() + "…/"

    icon_svg = _render_language_icon(row, 68.0, y + 8.0)
    est_name_w = len(compact_name) * 7.4
    compact_pill_w = _status_pill_width(row.status_badge)
    pill_svg = _render_status_pill(
        row.status_badge,
        min(466.0 - compact_pill_w, 98.0 + est_name_w + 8.0),
        y + 11.0,
    )

    extra_txt = f" (+{row.extra_language_count})" if row.extra_language_count > 0 else ""
    meta_line = f"{row.primary_language}{extra_txt} · Updated {row.updated_label}"

    desc_elems = []
    for li, line in enumerate(row.compact_description_lines[:2]):
        desc_elems.append(
            f'    <text x="28" y="{y + 42 + li * 15:.1f}" font-size="10.8" fill="{desc_col}">{_esc(line)}</text>'
        )

    inner_lines = [
        '  <g class="exp-row">',
        f"    <title>{_esc(_build_accessible_title(row))}</title>",
        f'    <rect class="exp-row-bg" x="18" y="{y:.1f}" width="524" height="82" rx="5" fill="{alt_fill}" stroke="transparent" stroke-width="1" pointer-events="all" />',
        f'    <rect class="exp-accent-bar" x="18" y="{y + 7:.1f}" width="3" height="68" rx="1.5" fill="{row.language_color}" fill-opacity="{0.28 if is_dim else 0.72}" />',
        f'    <text x="28" y="{y + 23:.1f}" font-size="11.0" fill="{mode_col}">{_esc(row.dir_mode)}</text>',
        f"    {icon_svg}",
        f'    <text class="exp-repo-name" x="98" y="{y + 23:.1f}" font-size="12.2" font-weight="700" fill="{name_col}">{_esc(compact_name)}</text>',
        f"    {pill_svg}" if pill_svg else "",
        f'    <text x="530" y="{y + 23:.1f}" text-anchor="end" font-size="11.5" font-weight="600" fill="{star_col}">★ {row.stars}</text>',
        *desc_elems,
        f'    <circle cx="32" cy="{y + 72:.1f}" r="3.2" fill="{row.language_color}" />',
        f'    <text x="41" y="{y + 75.5:.1f}" font-size="10.0" fill="{P["muted"]}">{_esc(meta_line)}</text>',
        "  </g>",
    ]
    return _wrap_row_link(row, [line for line in inner_lines if line])


def build_explorer_svg(
    model: ExplorerModel,
    layout: LayoutMode = "desktop",
) -> str:
    """Render Section 03 Terminal Project Explorer SVG cleanly for desktop or narrow viewports."""
    is_compact = layout == "compact"
    canvas_w = 560 if is_compact else EXPLORER_WIDTH
    row_stride = 86.0 if is_compact else 40.0
    rows_start_y = 86.0 if is_compact else 116.0

    row_count = len(model.rows)
    if row_count == 0:
        rows_height = 56.0
    else:
        rows_height = row_count * row_stride

    panel_x = 12.0 if is_compact else 16.0
    panel_w = canvas_w - 2 * panel_x
    panel_y = 78.0 if is_compact else 82.0
    panel_h = (rows_start_y - panel_y) + rows_height + 10.0
    footer_y = panel_y + panel_h + 26.0
    canvas_h = int(footer_y + 18.0)

    if row_count == 0:
        rows_markup = (
            f'<text x="{canvas_w / 2.0:.1f}" y="{rows_start_y + 28:.1f}" '
            f'text-anchor="middle" font-size="11.5" fill="{P["muted"]}">'
            "ls: ~/projects: No public repositories discovered yet.</text>"
        )
    elif is_compact:
        rows_markup = "\n      ".join(
            _render_compact_row(row, idx, rows_start_y + idx * row_stride)
            for idx, row in enumerate(model.rows)
        )
    else:
        rows_markup = "\n      ".join(
            _render_desktop_row(row, idx, rows_start_y + idx * row_stride)
            for idx, row in enumerate(model.rows)
        )

    repo_word = "repo" if model.total_repositories == 1 else "repos"
    summary_text = f"{model.total_repositories} total · {model.active_repositories} active · ★ {model.total_stars}"
    header_pill = (
        f"{model.total_repositories} {repo_word}"
        if is_compact
        else f"{model.total_repositories} {repo_word} · sort:{model.sort_by}"
    )
    title_x = canvas_w / 2.0

    header_row = (
        ""
        if is_compact
        else (
            f'<rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_w:.1f}" height="28" rx="6" fill="#0b101d" />\n'
            f'      <line x1="{panel_x:.1f}" y1="{panel_y + 28:.1f}" x2="{panel_x + panel_w:.1f}" y2="{panel_y + 28:.1f}" stroke="{P["rule"]}" stroke-width="1" />\n'
            f'      <text x="34" y="{panel_y + 18:.1f}" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">MODE</text>\n'
            f'      <text x="76" y="{panel_y + 18:.1f}" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">REPOSITORY</text>\n'
            f'      <text x="332" y="{panel_y + 18:.1f}" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">DESCRIPTION</text>\n'
            f'      <text x="722" y="{panel_y + 18:.1f}" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">LANGUAGE</text>\n'
            f'      <text x="860" y="{panel_y + 18:.1f}" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">UPDATED</text>\n'
            f'      <text x="978" y="{panel_y + 18:.1f}" text-anchor="end" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">STARS</text>'
        )
    )

    prompt_prefix = f"{model.username.lower()}@github"
    footer_prompt_prefix = (
        f"{model.username.lower()[:24]}…@github"
        if is_compact and len(prompt_prefix) > 34
        else prompt_prefix
    )
    window_title_svg = (
        f'<text x="{title_x:.1f}" y="27" text-anchor="middle" font-size="11.5" fill="{P["muted"]}"><tspan fill="{P["text"]}" font-weight="700">~/projects</tspan> — zsh</text>'
        if is_compact
        else f'<text x="{title_x:.1f}" y="27" text-anchor="middle" font-size="11.5" fill="{P["muted"]}">{_esc(prompt_prefix)} — <tspan fill="{P["text"]}" font-weight="700">~/projects</tspan> — zsh</text>'
    )
    top_prompt_svg = (
        f'<text x="20" y="65" font-size="12.5" xml:space="preserve">'
        f'<tspan fill="{P["dir_green"]}" font-weight="700">$</tspan>'
        f'<tspan fill="{P["text"]}" font-weight="700"> ls ~/projects</tspan></text>'
        if is_compact
        else (
            f'<text x="20" y="65" font-size="12.5" xml:space="preserve">'
            f'<tspan fill="{P["dir_green"]}" font-weight="700">{_esc(prompt_prefix)}</tspan>'
            f'<tspan fill="{P["muted"]}">:</tspan>'
            f'<tspan fill="{P["prompt_blue"]}" font-weight="700">~/projects</tspan>'
            f'<tspan fill="{P["dir_green"]}" font-weight="700"> $</tspan>'
            f'<tspan fill="{P["text"]}" font-weight="700"> ls ~/projects</tspan></text>'
        )
    )
    bottom_prompt = f"{footer_prompt_prefix}:~/projects$"
    cursor_x = 22.0 + len(bottom_prompt) * 7.6 + 6.0
    footer_right = (
        f"synced {model.generated_at}"
        if is_compact
        else f"synced {model.generated_at} · all public repositories synced automatically"
    )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}" role="img" aria-label="{_esc(model.username)} terminal project explorer listing public GitHub repositories">
  <defs>
    <clipPath id="exp-window-clip">
      <rect x="4" y="4" width="{canvas_w - 8}" height="{canvas_h - 8}" rx="12" ry="12" />
    </clipPath>
  </defs>

  <style>
    .exp-mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    .exp-repo-link {{
      cursor: pointer;
      pointer-events: all;
      text-decoration: none;
    }}
    .exp-row-bg {{
      transition: fill 0.16s ease, stroke 0.16s ease;
    }}
    .exp-accent-bar {{
      transition: fill-opacity 0.16s ease;
    }}
    .exp-repo-name {{
      transition: fill 0.16s ease;
    }}
    .exp-row:hover .exp-row-bg {{
      fill: {P["row_hover"]};
      stroke: #2c4375;
    }}
    .exp-row:hover .exp-accent-bar {{
      fill-opacity: 1;
    }}
    .exp-row:hover .exp-repo-name {{
      fill: #91ccff;
    }}
    @keyframes expCursorBlink {{
      0%, 49% {{ opacity: 1; }}
      50%, 100% {{ opacity: 0.15; }}
    }}
    .exp-cursor {{
      animation: expCursorBlink 1.3s step-end infinite;
    }}
    @media (prefers-reduced-motion: reduce) {{
      .exp-cursor {{ animation: none; opacity: 1; }}
      .exp-row-bg, .exp-accent-bar, .exp-repo-name {{ transition: none; }}
    }}
  </style>

  <rect x="4" y="4" width="{canvas_w - 8}" height="{canvas_h - 8}" rx="12" ry="12" fill="{P["bg"]}" pointer-events="none" />

  <g clip-path="url(#exp-window-clip)" class="exp-mono">
    <!-- macOS Terminal Top Title Bar -->
    <g pointer-events="none">
      <rect x="4" y="4" width="{canvas_w - 8}" height="38" fill="{P["titlebar_bg"]}" />
      <line x1="4" y1="42" x2="{canvas_w - 4}" y2="42" stroke="{P["inner_border"]}" stroke-width="1" />

      <circle cx="26" cy="23" r="5.5" fill="{P["win_red"]}" />
      <circle cx="45" cy="23" r="5.5" fill="{P["win_yellow"]}" />
      <circle cx="64" cy="23" r="5.5" fill="{P["win_green"]}" />

      {window_title_svg}
      <circle cx="{canvas_w - 22 - len(header_pill) * 6.3:.1f}" cy="23" r="3" fill="{P["dir_green"]}" />
      <text x="{canvas_w - 18}" y="27" text-anchor="end" font-size="10.2" fill="{P["muted"]}">{_esc(header_pill)}</text>

      <!-- Terminal Command Prompt -->
      {top_prompt_svg}
      <text x="{canvas_w - 20}" y="65" text-anchor="end" font-size="10.8" fill="{P["muted"]}">{_esc(summary_text)}</text>

      <!-- Directory Listing Container Frame -->
      <rect x="{panel_x:.1f}" y="{panel_y:.1f}" width="{panel_w:.1f}" height="{panel_h:.1f}" rx="8" fill="{P["panel_bg"]}" stroke="{P["inner_border"]}" stroke-width="1.1" />
      {header_row}
    </g>
    {rows_markup}

    <!-- Bottom Terminal Status Line -->
    <g pointer-events="none">
      <text x="22" y="{footer_y:.1f}" font-size="12.0" xml:space="preserve"><tspan fill="{P["dir_green"]}" font-weight="700">{_esc(footer_prompt_prefix)}</tspan><tspan fill="{P["muted"]}">:</tspan><tspan fill="{P["prompt_blue"]}" font-weight="700">~/projects</tspan><tspan fill="{P["dir_green"]}" font-weight="700">$</tspan></text>
      <rect class="exp-cursor" x="{cursor_x:.1f}" y="{footer_y - 12:.1f}" width="8" height="15" fill="{P["prompt_blue"]}" />
      <text x="{canvas_w - 20}" y="{footer_y:.1f}" text-anchor="end" font-size="10.2" fill="{P["dim"]}">{_esc(footer_right)}</text>
    </g>
  </g>

  <rect x="4" y="4" width="{canvas_w - 8}" height="{canvas_h - 8}" rx="12" ry="12" fill="none" stroke="{P["border"]}" stroke-width="1.5" pointer-events="none" />
</svg>
'''
    validate_svg_document(svg)
    return svg


_EXP_SLICE_STYLE = f'''    .exp-mono {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    .exp-repo-link {{
      cursor: pointer;
      pointer-events: all;
      text-decoration: none;
    }}
    .exp-row-bg {{
      transition: fill 0.16s ease, stroke 0.16s ease;
    }}
    .exp-accent-bar {{
      transition: fill-opacity 0.16s ease;
    }}
    .exp-repo-name {{
      transition: fill 0.16s ease;
    }}
    .exp-row:hover .exp-row-bg {{
      fill: {P["row_hover"]};
      stroke: #2c4375;
    }}
    .exp-row:hover .exp-accent-bar {{
      fill-opacity: 1;
    }}
    .exp-row:hover .exp-repo-name {{
      fill: #91ccff;
    }}'''


def build_explorer_header_slice_svg(model: ExplorerModel) -> str:
    """Render the top terminal header + column labels slice for clickable GitHub README stacking."""
    canvas_w = EXPLORER_WIDTH
    canvas_h = 112
    repo_word = "repo" if model.total_repositories == 1 else "repos"
    summary_text = f"{model.total_repositories} total · {model.active_repositories} active · ★ {model.total_stars}"
    header_pill = f"{model.total_repositories} {repo_word} · sort:{model.sort_by}"
    prompt_prefix = f"{model.username.lower()}@github"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}" role="img" aria-label="{_esc(model.username)} terminal project explorer header">
  <defs>
    <clipPath id="exp-hdr-clip">
      <rect x="4" y="2" width="{canvas_w - 8}" height="{canvas_h - 4}" rx="12" ry="12" />
    </clipPath>
  </defs>
  <style>
{_EXP_SLICE_STYLE}
  </style>
  <rect x="4" y="2" width="{canvas_w - 8}" height="{canvas_h - 4}" rx="12" ry="12" fill="{P["bg"]}" />
  <g clip-path="url(#exp-hdr-clip)" class="exp-mono">
    <rect x="4" y="2" width="{canvas_w - 8}" height="38" fill="{P["titlebar_bg"]}" />
    <line x1="4" y1="40" x2="{canvas_w - 4}" y2="40" stroke="{P["inner_border"]}" stroke-width="1" />
    <circle cx="26" cy="21" r="5.5" fill="{P["win_red"]}" />
    <circle cx="45" cy="21" r="5.5" fill="{P["win_yellow"]}" />
    <circle cx="64" cy="21" r="5.5" fill="{P["win_green"]}" />
    <text x="{canvas_w / 2.0:.1f}" y="25" text-anchor="middle" font-size="11.5" fill="{P["muted"]}">{_esc(prompt_prefix)} — <tspan fill="{P["text"]}" font-weight="700">~/projects</tspan> — zsh</text>
    <circle cx="{canvas_w - 22 - len(header_pill) * 6.3:.1f}" cy="21" r="3" fill="{P["dir_green"]}" />
    <text x="{canvas_w - 18}" y="25" text-anchor="end" font-size="10.2" fill="{P["muted"]}">{_esc(header_pill)}</text>
    <text x="20" y="63" font-size="12.5" xml:space="preserve"><tspan fill="{P["dir_green"]}" font-weight="700">{_esc(prompt_prefix)}</tspan><tspan fill="{P["muted"]}">:</tspan><tspan fill="{P["prompt_blue"]}" font-weight="700">~/projects</tspan><tspan fill="{P["dir_green"]}" font-weight="700"> $</tspan><tspan fill="{P["text"]}" font-weight="700"> ls ~/projects</tspan></text>
    <text x="{canvas_w - 20}" y="63" text-anchor="end" font-size="10.8" fill="{P["muted"]}">{_esc(summary_text)}</text>
    <rect x="14" y="76" width="{canvas_w - 28}" height="28" rx="6" fill="#0b101d" stroke="{P["inner_border"]}" stroke-width="1" />
    <text x="34" y="94" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">MODE</text>
    <text x="76" y="94" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">REPOSITORY</text>
    <text x="332" y="94" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">DESCRIPTION</text>
    <text x="722" y="94" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">LANGUAGE</text>
    <text x="860" y="94" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">UPDATED</text>
    <text x="978" y="94" text-anchor="end" font-size="9.5" font-weight="700" letter-spacing="1.1" fill="{P["muted"]}">STARS</text>
  </g>
  <rect x="4" y="2" width="{canvas_w - 8}" height="{canvas_h - 4}" rx="12" ry="12" fill="none" stroke="{P["border"]}" stroke-width="1.5" />
</svg>
'''
    validate_svg_document(svg)
    return svg


def build_explorer_row_slice_svg(row: ExplorerRow, index: int) -> str:
    """Render a self-contained single clickable repository row SVG slice (1009x42)."""
    canvas_w = EXPLORER_WIDTH
    canvas_h = 42
    row_markup = _render_desktop_row_content(row, index, 1.0, is_slice=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}" role="img" aria-label="{_esc(row.name)} repository row">
  <style>
{_EXP_SLICE_STYLE}
  </style>
  <g class="exp-mono">
    {row_markup}
  </g>
</svg>
'''
    validate_svg_document(svg)
    return svg


def build_explorer_empty_slice_svg() -> str:
    """Render graceful empty-state repository slice SVG (1009x46)."""
    canvas_w = EXPLORER_WIDTH
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} 46" width="{canvas_w}" height="46" role="img" aria-label="No public repositories discovered yet">
  <style>
    .exp-mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
  </style>
  <rect x="4" y="2" width="{canvas_w - 8}" height="42" rx="7" fill="{P["row_odd"]}" stroke="{P["inner_border"]}" stroke-width="1.1" />
  <text x="{canvas_w / 2.0:.1f}" y="27" text-anchor="middle" class="exp-mono" font-size="11.5" fill="{P["muted"]}">ls: ~/projects: No public repositories discovered yet.</text>
</svg>
'''
    validate_svg_document(svg)
    return svg


def build_explorer_footer_slice_svg(model: ExplorerModel) -> str:
    """Render the bottom terminal status bar slice SVG (1009x42)."""
    canvas_w = EXPLORER_WIDTH
    canvas_h = 42
    prompt_prefix = f"{model.username.lower()}@github"
    bottom_prompt = f"{prompt_prefix}:~/projects$"
    cursor_x = 22.0 + len(bottom_prompt) * 7.6 + 6.0
    footer_right = f"synced {model.generated_at} · click any repository row to open on GitHub"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {canvas_w} {canvas_h}" width="{canvas_w}" height="{canvas_h}" role="img" aria-label="{_esc(model.username)} terminal project explorer footer">
  <style>
    .exp-mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    @keyframes expCursorBlink {{
      0%, 49% {{ opacity: 1; }}
      50%, 100% {{ opacity: 0.15; }}
    }}
    .exp-cursor {{ animation: expCursorBlink 1.3s step-end infinite; }}
    @media (prefers-reduced-motion: reduce) {{ .exp-cursor {{ animation: none; opacity: 1; }} }}
  </style>
  <rect x="4" y="2" width="{canvas_w - 8}" height="{canvas_h - 4}" rx="10" ry="10" fill="{P["bg"]}" stroke="{P["border"]}" stroke-width="1.3" />
  <g class="exp-mono">
    <text x="22" y="25" font-size="12.0" xml:space="preserve"><tspan fill="{P["dir_green"]}" font-weight="700">{_esc(prompt_prefix)}</tspan><tspan fill="{P["muted"]}">:</tspan><tspan fill="{P["prompt_blue"]}" font-weight="700">~/projects</tspan><tspan fill="{P["dir_green"]}" font-weight="700">$</tspan></text>
    <rect class="exp-cursor" x="{cursor_x:.1f}" y="13" width="8" height="15" fill="{P["prompt_blue"]}" />
    <text x="{canvas_w - 20}" y="25" text-anchor="end" font-size="10.2" fill="{P["dim"]}">{_esc(footer_right)}</text>
  </g>
</svg>
'''
    validate_svg_document(svg)
    return svg


def build_explorer_slice_svgs(model: ExplorerModel) -> dict[str, object]:
    """Generate header, per-repository rows, and footer SVGs for clickable GitHub README rendering."""
    row_svgs: list[tuple[str, str]] = [
        (row.row_slug, build_explorer_row_slice_svg(row, idx))
        for idx, row in enumerate(model.rows)
    ]
    return {
        "header": build_explorer_header_slice_svg(model),
        "rows": row_svgs,
        "empty": None if row_svgs else build_explorer_empty_slice_svg(),
        "footer": build_explorer_footer_slice_svg(model),
    }


def build_section_divider_svg(width: int = EXPLORER_WIDTH) -> str:
    """Render a minimal, crisp dark-mode diamond divider connecting the three visual sections."""
    mid = width / 2.0
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 22" width="{width}" height="22" role="presentation">
  <line x1="20" y1="11" x2="{mid - 34:.1f}" y2="11" stroke="#1f2d4d" stroke-width="1.2" stroke-dasharray="4 4" />
  <line x1="{mid + 34:.1f}" y1="11" x2="{width - 20}" y2="11" stroke="#1f2d4d" stroke-width="1.2" stroke-dasharray="4 4" />
  <polygon points="{mid - 20:.1f},11 {mid - 16:.1f},7 {mid - 12:.1f},11 {mid - 16:.1f},15" fill="#5aa9ff" fill-opacity="0.7" />
  <polygon points="{mid:.1f},5 {mid + 6:.1f},11 {mid:.1f},17 {mid - 6:.1f},11" fill="#f2cb62" fill-opacity="0.9" />
  <polygon points="{mid + 12:.1f},11 {mid + 16:.1f},7 {mid + 20:.1f},11 {mid + 16:.1f},15" fill="#5aa9ff" fill-opacity="0.7" />
</svg>
'''
    validate_svg_document(svg)
    return svg
