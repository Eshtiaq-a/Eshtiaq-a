"""Self-contained animated SVG generator for Section 01 (Workspace + Movie Credits)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
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
from src.workspace_scene import WorkspaceTheme, render_workspace_room_layers, resolve_is_daytime


def build_workspace_svg(
    commits_payload: dict[str, Any],
    config: ProfileConfig,
    theme: WorkspaceTheme = "auto",
    now: datetime | None = None,
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
    is_daytime = resolve_is_daytime(timezone_name=config.timezone, theme=theme, now=now)
    room_layers = render_workspace_room_layers(config, theme=theme, now=now)
    aria_sky = "sunny sky and clouds with desk lamp off" if is_daytime else "night sky with lit desk lamp"

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WORKSPACE_WIDTH} {WORKSPACE_HEIGHT}" width="{WORKSPACE_WIDTH}" height="{WORKSPACE_HEIGHT}" role="img" aria-label="Eshtiaq Ahmad pixel-art developer workspace ({aria_sky}) with MacBook connected to external monitor displaying GitHub commit movie end credits" shape-rendering="crispEdges">
  <defs>
    <clipPath id="room-card-clip">
      <rect x="0" y="0" width="{WORKSPACE_WIDTH}" height="{WORKSPACE_HEIGHT}" rx="14" ry="14" />
    </clipPath>
    <clipPath id="monitor-screen-clip">
      <rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="2" ry="2" />
    </clipPath>
    <clipPath id="win-sky-clip">
      <rect x="44" y="63" width="92" height="88" />
      <rect x="144" y="63" width="92" height="88" />
      <rect x="44" y="159" width="92" height="90" />
      <rect x="144" y="159" width="92" height="90" />
    </clipPath>
    <linearGradient id="sunbeam-grad" x1="0.2" y1="0" x2="0.6" y2="1">
      <stop offset="0%" stop-color="#fff4bf" stop-opacity="0.16" />
      <stop offset="65%" stop-color="#ffe999" stop-opacity="0.07" />
      <stop offset="100%" stop-color="#ffe999" stop-opacity="0.0" />
    </linearGradient>
    <linearGradient id="screen-top-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{P["screen_bg"]}" stop-opacity="0.95" />
      <stop offset="100%" stop-color="{P["screen_bg"]}" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="screen-bottom-fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{P["screen_bg"]}" stop-opacity="0" />
      <stop offset="100%" stop-color="{P["screen_bg"]}" stop-opacity="0.95" />
    </linearGradient>
    <linearGradient id="lamp-beam-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{P["lamp_shade"]}" stop-opacity="0.24" />
      <stop offset="55%" stop-color="{P["lamp_shade"]}" stop-opacity="0.11" />
      <stop offset="100%" stop-color="{P["lamp_shade"]}" stop-opacity="0.03" />
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
    @keyframes clockSpin {{
      0% {{
        transform: rotate(0deg);
      }}
      100% {{
        transform: rotate(360deg);
      }}
    }}
    @keyframes steamRise {{
      0% {{
        transform: translateY(2px);
        opacity: 0;
      }}
      25% {{
        opacity: 0.62;
      }}
      60% {{
        transform: translateY(-7px);
        opacity: 0.40;
      }}
      85% {{
        transform: translateY(-11px);
        opacity: 0.16;
      }}
      100% {{
        transform: translateY(-14px);
        opacity: 0;
      }}
    }}
    @keyframes catTailWag {{
      0%, 100% {{
        transform: rotate(0deg);
      }}
      25% {{
        transform: rotate(-7deg);
      }}
      50% {{
        transform: rotate(4deg);
      }}
      75% {{
        transform: rotate(-5deg);
      }}
    }}
    @keyframes catBreathe {{
      0%, 100% {{
        transform: scaleY(1);
      }}
      50% {{
        transform: scaleY(0.95);
      }}
    }}
    @keyframes sleepFloat {{
      0% {{
        transform: translateY(2px);
        opacity: 0.25;
      }}
      50% {{
        opacity: 0.78;
      }}
      100% {{
        transform: translateY(-6px);
        opacity: 0.15;
      }}
    }}
    @keyframes starTwinkle {{
      0%, 100% {{
        opacity: 0.35;
      }}
      50% {{
        opacity: 1;
      }}
    }}
    @keyframes lampGlowPulse {{
      0%, 100% {{
        opacity: 0.85;
      }}
      50% {{
        opacity: 1;
      }}
    }}
    @keyframes steamPuff {{
      0% {{
        transform: translateY(2px);
        opacity: 0;
      }}
      20% {{
        opacity: 0.9;
      }}
      60% {{
        transform: translateY(-9px);
        opacity: 0.45;
      }}
      100% {{
        transform: translateY(-18px);
        opacity: 0;
      }}
    }}
    @keyframes cloudDrift {{
      0%, 100% {{
        transform: translateX(-10px);
      }}
      50% {{
        transform: translateX(14px);
      }}
    }}
    @keyframes shootingStar {{
      0% {{
        stroke-dasharray: 0 80;
        stroke-dashoffset: 0;
        transform: translate(0px, 0px);
        opacity: 0;
      }}
      1% {{
        opacity: 0.9;
        stroke-dasharray: 32 48;
      }}
      3% {{
        stroke-dasharray: 0 80;
        stroke-dashoffset: -80;
        transform: translate(60px, 28px);
        opacity: 0;
      }}
      100% {{
        stroke-dasharray: 0 80;
        transform: translate(60px, 28px);
        opacity: 0;
      }}
    }}
    #credits-track {{
      animation: scrollCredits {duration_sec:.2f}s linear infinite;
      will-change: transform;
    }}
    .clock-min-hand {{
      transform-origin: 0px 0px;
      animation: clockSpin 60s linear infinite;
    }}
    .clock-hour-hand {{
      transform-origin: 0px 0px;
      animation: clockSpin 720s linear infinite;
    }}
    .mug-steam-1 {{
      animation: steamRise 3.2s ease-in-out infinite;
    }}
    .mug-steam-2 {{
      animation: steamRise 3.8s ease-in-out 1.1s infinite;
    }}
    .mug-steam-3 {{
      animation: steamRise 3.5s ease-in-out 2.0s infinite;
    }}
    .cat-tail-wag {{
      transform-box: fill-box;
      transform-origin: 100% 50%;
      animation: catTailWag 4.8s ease-in-out infinite;
    }}
    .cat-breathe {{
      transform-box: fill-box;
      transform-origin: 50% 100%;
      animation: catBreathe 4.2s ease-in-out infinite;
    }}
    .sleep-z-1 {{
      animation: sleepFloat 3.6s ease-in-out infinite;
    }}
    .sleep-z-2 {{
      animation: sleepFloat 3.6s ease-in-out 1.6s infinite;
    }}
    .star-twinkle-a {{
      animation: starTwinkle 3.8s ease-in-out infinite;
    }}
    .star-twinkle-b {{
      animation: starTwinkle 5.2s ease-in-out 1.3s infinite;
    }}
    .star-twinkle-c {{
      animation: starTwinkle 6.4s ease-in-out 2.5s infinite;
    }}
    .lamp-glow-cone {{
      animation: lampGlowPulse 4.6s ease-in-out infinite;
    }}
    .mug-steam-puff-a {{
      animation: steamPuff 4.0s ease-in-out infinite;
    }}
    .mug-steam-puff-b {{
      animation: steamPuff 4.5s ease-in-out 1.4s infinite;
    }}
    .mug-steam-puff-c {{
      animation: steamPuff 5.2s ease-in-out 2.6s infinite;
    }}
    .cloud-drift-1 {{
      animation: cloudDrift 28s ease-in-out infinite;
    }}
    .cloud-drift-2 {{
      animation: cloudDrift 36s ease-in-out -4s reverse infinite;
    }}
    /* Shooting stars: 2-min initial delay, 5-min cycle, ~0.9s flash */
    .shooting-star-1 {{
      animation: shootingStar 300s linear 120s infinite;
    }}
    .shooting-star-2 {{
      animation: shootingStar 300s linear 217s infinite;
    }}
    .shooting-star-3 {{
      animation: shootingStar 300s linear 305s infinite;
    }}
    @media (prefers-reduced-motion: reduce) {{
      #credits-track, .clock-min-hand, .clock-hour-hand,
      .mug-steam-1, .mug-steam-2, .mug-steam-3,
      .mug-steam-puff-a, .mug-steam-puff-b, .mug-steam-puff-c,
      .cat-tail-wag, .cat-breathe, .sleep-z-1, .sleep-z-2,
      .star-twinkle-a, .star-twinkle-b, .star-twinkle-c, .lamp-glow-cone,
      .cloud-drift-1, .cloud-drift-2,
      .shooting-star-1, .shooting-star-2, .shooting-star-3 {{
        animation: none;
      }}
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
    theme: WorkspaceTheme = "auto",
) -> Path:
    """Load commit JSON + profile config, render animated SVG, validate, and write atomically."""
    config = load_profile_config() if config_path is None else load_profile_config(config_path)
    source_path = commits_path or (COMMITS_PATH if COMMITS_PATH.exists() else SAMPLE_COMMITS_PATH)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    svg_text = build_workspace_svg(payload, config, theme=theme)
    return atomic_write_text(output_path, svg_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Section 01 animated workspace SVG.")
    parser.add_argument(
        "--theme",
        choices=("auto", "day", "night"),
        default="auto",
        help="Workspace lighting theme (auto = day 06:00-17:59, night 18:00-05:59 in configured timezone).",
    )
    args = parser.parse_args()
    written = generate_workspace_svg_file(theme=args.theme)
    print(f"Generated {written} ({written.stat().st_size} bytes)")
