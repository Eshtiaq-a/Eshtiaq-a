"""Self-contained animated SVG generator for Section 01 (Workspace + Movie Credits)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import (
    COMMITS_PATH,
    MONITOR_SCREEN_BOX,
    SAMPLE_COMMITS_PATH,
    WORKSPACE_HEIGHT,
    WORKSPACE_PALETTE as P,
    WORKSPACE_SVG_PATH,
    WORKSPACE_WIDTH,
    ProfileConfig,
    atomic_write_text,
    load_profile_config,
)
from src.credits_formatter import build_credit_sequence, render_credit_lines_svg
from src.validators import validate_commits_payload, validate_svg_document
from src.workspace_scene import render_workspace_room_layers


def build_workspace_svg(
    commits_payload: dict[str, Any],
    config: ProfileConfig,
) -> str:
    """Compose the self-contained animated workspace SVG with scrolling movie credits."""
    validate_commits_payload(commits_payload)
    lines, seq_height, duration_sec = build_credit_sequence(
        commits_payload,
        scroll_speed_px_per_sec=config.scroll_speed_px_per_sec,
    )

    sx, sy, sw, sh = MONITOR_SCREEN_BOX
    center_x = sx + sw / 2.0
    credit_markup = render_credit_lines_svg(lines, center_x=center_x)
    room_layers = render_workspace_room_layers(config)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WORKSPACE_WIDTH} {WORKSPACE_HEIGHT}" width="{WORKSPACE_WIDTH}" height="{WORKSPACE_HEIGHT}" role="img" aria-label="Eshtiaq Ahmad pixel-art developer workspace with MacBook connected to external monitor displaying GitHub commit movie end credits" shape-rendering="crispEdges">
  <defs>
    <clipPath id="room-card-clip">
      <rect x="0" y="0" width="{WORKSPACE_WIDTH}" height="{WORKSPACE_HEIGHT}" rx="14" ry="14" />
    </clipPath>
    <clipPath id="monitor-screen-clip">
      <rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="2" ry="2" />
    </clipPath>
    <linearGradient id="screen-top-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{P["screen_bg"]}" stop-opacity="0.95" />
      <stop offset="100%" stop-color="{P["screen_bg"]}" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="screen-bottom-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{P["screen_bg"]}" stop-opacity="0" />
      <stop offset="100%" stop-color="{P["screen_bg"]}" stop-opacity="0.95" />
    </linearGradient>
  </defs>

  <style>
    .credit-text-group {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }}
    @keyframes scrollCredits {{
      0% {{
        transform: translateY(0px);
      }}
      100% {{
        transform: translateY(-{seq_height}px);
      }}
    }}
    #credits-track {{
      animation: scrollCredits {duration_sec:.2f}s linear infinite;
      will-change: transform;
    }}
  </style>

  <g clip-path="url(#room-card-clip)">
    {room_layers["background"]}

    <g clip-path="url(#monitor-screen-clip)" class="credit-text-group" shape-rendering="auto">
      <g id="credits-track">
        <g transform="translate(0, {sy})">
          {credit_markup}
        </g>
        <g transform="translate(0, {sy + seq_height})">
          {credit_markup}
        </g>
      </g>
      <rect x="{sx}" y="{sy}" width="{sw}" height="14" fill="url(#screen-top-fade)" />
      <rect x="{sx}" y="{sy + sh - 14}" width="{sw}" height="14" fill="url(#screen-bottom-fade)" />
    </g>

    {room_layers["foreground"]}
  </g>
</svg>
'''
    validate_svg_document(svg)
    return svg


def generate_workspace_svg_file(
    commits_path: Path | None = None,
    output_path: Path = WORKSPACE_SVG_PATH,
    config_path: Path | None = None,
) -> Path:
    """Load commit JSON + profile config, render animated SVG, validate, and write atomically."""
    config = load_profile_config() if config_path is None else load_profile_config(config_path)
    source_path = commits_path or (COMMITS_PATH if COMMITS_PATH.exists() else SAMPLE_COMMITS_PATH)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    svg_text = build_workspace_svg(payload, config)
    return atomic_write_text(output_path, svg_text)


if __name__ == "__main__":
    written = generate_workspace_svg_file()
    print(f"Generated {written} ({written.stat().st_size} bytes)")
