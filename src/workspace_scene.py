"""Pixel-art room scene generator matching Reference Image 1 with inhabited details, Day/Night modes & animations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.config import (
    MONITOR_SCREEN_BOX,
    WORKSPACE_HEIGHT,
    WORKSPACE_PALETTE as P,
    WORKSPACE_WIDTH,
    ProfileConfig,
)

WorkspaceTheme = Literal["auto", "day", "night"]


def resolve_is_daytime(
    timezone_name: str = "Asia/Dhaka",
    theme: WorkspaceTheme = "auto",
    now: datetime | None = None,
) -> bool:
    """Return True from 06:00 through 17:59 in the configured timezone (or forced theme)."""
    if theme == "day":
        return True
    if theme == "night":
        return False

    ref_utc = now if now is not None else datetime.now(timezone.utc)
    if ref_utc.tzinfo is None:
        ref_utc = ref_utc.replace(tzinfo=timezone.utc)

    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        tz = timezone(timedelta(hours=6))

    local_dt = ref_utc.astimezone(tz)
    return 6 <= local_dt.hour < 18

# Crisp 5x7 pixel-bitmap font for the ESHTIAQ AHMAD wall plaque (zero system-font drift)
PIXEL_FONT_5X7: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def _render_pixel_text(text: str, start_x: int, start_y: int, px: int, color: str) -> str:
    """Render crisp bitmap glyph rectangles onto an integer SVG pixel grid."""
    rects: list[str] = []
    cursor_x = start_x
    for ch in text.upper():
        rows = PIXEL_FONT_5X7.get(ch)
        if rows is None or ch == " ":
            cursor_x += 4 * px
            continue
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    rects.append(
                        f'<rect x="{cursor_x + rx * px}" y="{start_y + ry * px}" '
                        f'width="{px}" height="{px}" fill="{color}" />'
                    )
        cursor_x += 6 * px
    return "\n    ".join(rects)


def _render_pixel_sprite(
    origin_x: int,
    origin_y: int,
    px: int,
    rows: tuple[str, ...],
    palette: dict[str, str],
) -> list[str]:
    """Emit horizontal run-merged pixel rectangles onto an integer SVG grid."""
    rects: list[str] = []
    for ry, row in enumerate(rows):
        rx = 0
        row_len = len(row)
        while rx < row_len:
            ch = row[rx]
            if ch not in palette:
                rx += 1
                continue
            run = 1
            while rx + run < row_len and row[rx + run] == ch:
                run += 1
            rects.append(
                f'<rect x="{origin_x + rx * px}" y="{origin_y + ry * px}" '
                f'width="{run * px}" height="{px}" fill="{palette[ch]}" />'
            )
            rx += run
    return rects


def _render_wall_and_floor() -> str:
    """Render navy striped wallpaper, baseboard molding, wooden plank floor, and ambient shadows."""
    parts: list[str] = [
        f'<rect x="0" y="0" width="{WORKSPACE_WIDTH}" height="395" fill="{P["wall_primary"]}" />'
    ]
    for x in range(0, WORKSPACE_WIDTH, 36):
        parts.append(
            f'<rect x="{x + 18}" y="0" width="18" height="395" fill="{P["wall_stripe"]}" />'
        )

    # Wooden baseboard molding along bottom of wall (y=385..395)
    parts.append(f'<rect x="0" y="385" width="{WORKSPACE_WIDTH}" height="2" fill="{P["wood_shadow"]}" />')
    parts.append(f'<rect x="0" y="387" width="{WORKSPACE_WIDTH}" height="8" fill="{P["wood_dark"]}" />')

    # Wooden plank floor (y=395..504)
    parts.append(f'<rect x="0" y="395" width="{WORKSPACE_WIDTH}" height="109" fill="{P["floor_base"]}" />')
    parts.append(f'<rect x="0" y="395" width="{WORKSPACE_WIDTH}" height="2" fill="{P["floor_seam"]}" />')

    plank_rows = (416, 438, 460, 482)
    joint_offsets = (
        (110, 390, 680, 910),
        (230, 520, 810),
        (150, 440, 730, 950),
        (90, 340, 620, 870),
        (260, 560, 840),
    )
    row_tops = (397, 418, 440, 462, 484)
    row_heights = (19, 20, 20, 20, 20)

    for seam_y in plank_rows:
        parts.append(
            f'<rect x="0" y="{seam_y}" width="{WORKSPACE_WIDTH}" height="2" fill="{P["floor_seam"]}" />'
        )
    for idx, (row_top, row_h, joints) in enumerate(zip(row_tops, row_heights, joint_offsets)):
        # Subtle warm wood grain highlight strip on alternating rows
        if idx % 2 == 0:
            parts.append(
                f'<rect x="0" y="{row_top + 1}" width="{WORKSPACE_WIDTH}" height="2" '
                f'fill="{P["floor_highlight"]}" fill-opacity="0.45" />'
            )
        for jx in joints:
            parts.append(
                f'<rect x="{jx}" y="{row_top}" width="2" height="{row_h}" fill="{P["floor_seam"]}" />'
            )

    # Ambient floor shadows under plant, desk, chair, and bed for grounded depth
    parts.extend(
        [
            f'<rect x="118" y="402" width="50" height="5" fill="{P["floor_shadow"]}" />',
            f'<rect x="264" y="399" width="464" height="6" fill="{P["floor_shadow"]}" fill-opacity="0.65" />',
            f'<rect x="520" y="402" width="64" height="5" fill="{P["floor_shadow"]}" />',
            f'<rect x="748" y="396" width="154" height="6" fill="{P["floor_shadow"]}" fill-opacity="0.7" />',
        ]
    )
    return "\n    ".join(parts)


def _render_window(is_daytime: bool = False) -> str:
    """Render 2x2 window: sunny sky + pixel sun + drifting clouds (Day), or crescent moon + twinkling/shooting stars (Night)."""
    if is_daytime:
        sky_panes = [
            # Bright sunny sky panes (Day: 06:00 - 17:59)
            f'<rect x="44" y="63" width="92" height="88" fill="#4ca8f5" />',
            f'<rect x="144" y="63" width="92" height="88" fill="#4ca8f5" />',
            f'<rect x="44" y="159" width="92" height="90" fill="#74c2ff" />',
            f'<rect x="144" y="159" width="92" height="90" fill="#74c2ff" />',
            # Soft warm horizon glow at bottom of lower panes
            f'<rect x="44" y="227" width="92" height="22" fill="#a8ddff" fill-opacity="0.8" />',
            f'<rect x="144" y="227" width="92" height="22" fill="#a8ddff" fill-opacity="0.8" />',
            # Crisp glass reflection ticks
            f'<rect x="50" y="69" width="10" height="2" fill="#ffffff" fill-opacity="0.40" />',
            f'<rect x="50" y="71" width="2" height="8" fill="#ffffff" fill-opacity="0.40" />',
            f'<rect x="150" y="165" width="10" height="2" fill="#ffffff" fill-opacity="0.40" />',
            # Pixel sun in upper-right pane with outer warmth + ray ticks
            f'<rect x="184" y="80" width="24" height="24" fill="#fff5b8" fill-opacity="0.35" />',
            f'<rect x="188" y="84" width="16" height="16" fill="#ffd94a" />',
            f'<rect x="190" y="86" width="12" height="12" fill="#fff29c" />',
            f'<rect x="195" y="76" width="2" height="4" fill="#ffd94a" />',
            f'<rect x="195" y="104" width="2" height="4" fill="#ffd94a" />',
            f'<rect x="180" y="91" width="4" height="2" fill="#ffd94a" />',
            f'<rect x="208" y="91" width="4" height="2" fill="#ffd94a" />',
            # Drifting pixel clouds clipped inside the 4 window panes (#win-sky-clip in <defs>)
            '<g clip-path="url(#win-sky-clip)" pointer-events="none">',
            '  <g class="cloud-drift-1">',
            f'    <rect x="64" y="112" width="38" height="10" fill="#ffffff" />',
            f'    <rect x="70" y="104" width="24" height="8" fill="#ffffff" />',
            f'    <rect x="76" y="100" width="12" height="4" fill="#ffffff" />',
            f'    <rect x="64" y="120" width="38" height="3" fill="#dceeff" />',
            f'    <rect x="150" y="122" width="30" height="8" fill="#ffffff" fill-opacity="0.95" />',
            f'    <rect x="156" y="116" width="16" height="6" fill="#ffffff" fill-opacity="0.95" />',
            f'    <rect x="150" y="128" width="30" height="2" fill="#dceeff" />',
            '  </g>',
            '  <g class="cloud-drift-2">',
            f'    <rect x="72" y="190" width="34" height="9" fill="#ffffff" fill-opacity="0.95" />',
            f'    <rect x="78" y="184" width="20" height="6" fill="#ffffff" fill-opacity="0.95" />',
            f'    <rect x="72" y="197" width="34" height="2" fill="#dceeff" />',
            f'    <rect x="166" y="176" width="42" height="10" fill="#ffffff" />',
            f'    <rect x="174" y="169" width="24" height="7" fill="#ffffff" />',
            f'    <rect x="166" y="184" width="42" height="3" fill="#dceeff" />',
            '  </g>',
            '</g>',
        ]
    else:
        sky_panes = [
            # 4 night sky panes (Night: 18:00 - 05:59)
            f'<rect x="44" y="63" width="92" height="88" fill="{P["window_sky"]}" />',
            f'<rect x="144" y="63" width="92" height="88" fill="{P["window_sky"]}" />',
            f'<rect x="44" y="159" width="92" height="90" fill="{P["window_sky"]}" />',
            f'<rect x="144" y="159" width="92" height="90" fill="{P["window_sky"]}" />',
            # Subtle night horizon gradient band at lower panes
            f'<rect x="44" y="229" width="92" height="20" fill="#10244a" fill-opacity="0.6" />',
            f'<rect x="144" y="229" width="92" height="20" fill="#10244a" fill-opacity="0.6" />',
            # Crisp pixel glass reflection ticks
            f'<rect x="50" y="69" width="10" height="2" fill="{P["window_star"]}" fill-opacity="0.25" />',
            f'<rect x="50" y="71" width="2" height="8" fill="{P["window_star"]}" fill-opacity="0.25" />',
            f'<rect x="150" y="165" width="10" height="2" fill="{P["window_star"]}" fill-opacity="0.25" />',
            # Staggered twinkling stars across panes
            f'<rect class="star-twinkle-a" x="68" y="92" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect class="star-twinkle-b" x="108" y="74" width="3" height="3" fill="{P["cream"]}" />',
            f'<rect class="star-twinkle-c" x="168" y="76" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect class="star-twinkle-a" x="154" y="124" width="3" height="3" fill="{P["cream"]}" />',
            f'<rect class="star-twinkle-b" x="86" y="198" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect class="star-twinkle-c" x="62" y="176" width="3" height="3" fill="{P["cream"]}" />',
            f'<rect class="star-twinkle-a" x="196" y="206" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect class="star-twinkle-b" x="218" y="172" width="3" height="3" fill="{P["window_star"]}" />',
            # Pixel L-crescent moon in upper-right pane + companion star dot
            f'<rect x="184" y="88" width="8" height="24" fill="{P["cream"]}" />',
            f'<rect x="184" y="104" width="24" height="8" fill="{P["cream"]}" />',
            f'<rect class="star-twinkle-c" x="208" y="120" width="4" height="4" fill="{P["cream"]}" />',
            # Shooting stars (clipped to window sky area via #win-sky-clip in <defs>, 2-min delay, 5-min cycle)
            '<g clip-path="url(#win-sky-clip)" pointer-events="none">',
            f'  <line class="shooting-star-1" x1="52" y1="67" x2="52" y2="67" stroke="{P["cream"]}" stroke-width="1.5" stroke-linecap="round" />',
            f'  <line class="shooting-star-2" x1="152" y1="70" x2="152" y2="70" stroke="#c8e0ff" stroke-width="1.5" stroke-linecap="round" />',
            f'  <line class="shooting-star-3" x1="56" y1="166" x2="56" y2="166" stroke="{P["window_star"]}" stroke-width="1.5" stroke-linecap="round" />',
            '</g>',
        ]

    return "\n    ".join(
        [
            # Drop shadow under sill & frame
            f'<rect x="38" y="59" width="208" height="202" fill="{P["shadow_ambient"]}" fill-opacity="0.45" />',
            f'<rect x="36" y="55" width="208" height="202" fill="{P["window_frame"]}" />',
            *sky_panes,
            # Wooden window sill with top bevel & cast wall shadow
            f'<rect x="28" y="257" width="224" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="28" y="259" width="224" height="6" fill="{P["wood_top"]}" />',
            f'<rect x="28" y="265" width="224" height="4" fill="{P["wood_shadow"]}" />',
            f'<rect x="30" y="269" width="220" height="4" fill="{P["shadow_ambient"]}" fill-opacity="0.55" />',
            # Hanging plant on window top-frame interior
            f'<rect x="73" y="56" width="4" height="6" fill="{P["wood_shadow"]}" />',
            f'<rect x="74" y="62" width="2" height="12" fill="#5a7a44" />',
            f'<rect x="68" y="74" width="16" height="2" fill="#b06434" />',
            f'<rect x="70" y="76" width="12" height="10" fill="#c0724a" />',
            f'<rect x="72" y="86" width="8" height="2" fill="#b06434" />',
            f'<rect x="70" y="74" width="12" height="4" fill="#5c3d20" />',
            f'<rect x="58" y="78" width="12" height="6" fill="{P["plant_leaf"]}" />',
            f'<rect x="52" y="82" width="10" height="6" fill="{P["plant_leaf"]}" />',
            f'<rect x="46" y="88" width="10" height="6" fill="{P["plant_leaf_dark"]}" />',
            f'<rect x="52" y="94" width="8" height="4" fill="{P["plant_leaf"]}" />',
            f'<rect x="46" y="99" width="8" height="4" fill="{P["plant_leaf_dark"]}" />',
            f'<rect x="84" y="78" width="12" height="6" fill="{P["plant_leaf"]}" />',
            f'<rect x="92" y="84" width="10" height="6" fill="{P["plant_leaf"]}" />',
            f'<rect x="98" y="90" width="8" height="6" fill="{P["plant_leaf_dark"]}" />',
            f'<rect x="92" y="96" width="8" height="4" fill="{P["plant_leaf"]}" />',
            f'<rect x="62" y="80" width="2" height="2" fill="#93c8b2" />',
            f'<rect x="88" y="80" width="2" height="2" fill="#93c8b2" />',
        ]
    )


def _render_name_plaque_and_wall_decor(display_name: str) -> str:
    """Render framed ESHTIAQ AHMAD plaque plus subtle framed developer wall decor."""
    plaque_x, plaque_y, plaque_w, plaque_h = 378, 50, 344, 46
    text_width = 225
    text_x = plaque_x + (plaque_w - text_width) // 2
    text_y = plaque_y + 12

    return "\n    ".join(
        [
            # Subtle framed pixel git-constellation poster left of plaque (x=276..344, y=54..104)
            f'<rect x="278" y="56" width="66" height="50" fill="{P["shadow_ambient"]}" fill-opacity="0.5" />',
            f'<rect x="276" y="54" width="66" height="50" fill="{P["plaque_border"]}" />',
            f'<rect x="280" y="58" width="58" height="42" fill="{P["poster_bg"]}" />',
            # Mini pixel git-branch art inside wall frame
            f'<rect x="288" y="78" width="42" height="2" fill="#35527a" />',
            f'<rect x="296" y="68" width="2" height="10" fill="#93c8b2" />',
            f'<rect x="296" y="68" width="24" height="2" fill="#93c8b2" />',
            f'<rect x="320" y="68" width="2" height="10" fill="#93c8b2" />',
            f'<rect x="288" y="76" width="6" height="6" fill="#5aa9ff" />',
            f'<rect x="304" y="66" width="6" height="6" fill="#93c8b2" />',
            f'<rect x="310" y="76" width="6" height="6" fill="#f2cb62" />',
            f'<rect x="328" y="76" width="6" height="6" fill="#5aa9ff" />',
            f'<rect x="288" y="88" width="38" height="2" fill="#2c4966" />',
            f'<rect x="288" y="92" width="24" height="2" fill="#2c4966" />',
            # Drop shadow & ESHTIAQ AHMAD nameplate plaque (x=378..722, y=50..96)
            f'<rect x="{plaque_x + 3}" y="{plaque_y + 4}" width="{plaque_w}" height="{plaque_h}" fill="{P["shadow_ambient"]}" fill-opacity="0.55" />',
            f'<rect x="{plaque_x}" y="{plaque_y}" width="{plaque_w}" height="{plaque_h}" fill="{P["plaque_border"]}" />',
            f'<rect x="{plaque_x + 4}" y="{plaque_y + 4}" width="{plaque_w - 8}" height="{plaque_h - 8}" fill="{P["plaque_bg"]}" />',
            _render_pixel_text(display_name, text_x, text_y, px=3, color=P["plaque_border"]),
            # Subtle pinboard sticky notes between plaque and wall clock (x=762..804, y=58..92)
            f'<rect x="762" y="58" width="20" height="20" fill="{P["lamp_shade"]}" />',
            f'<rect x="771" y="59" width="2" height="2" fill="#b43b2c" />',
            f'<rect x="765" y="65" width="12" height="2" fill="{P["wood_dark"]}" fill-opacity="0.55" />',
            f'<rect x="765" y="69" width="9" height="2" fill="{P["wood_dark"]}" fill-opacity="0.55" />',
            f'<rect x="786" y="64" width="18" height="18" fill="{P["credit_repo"]}" />',
            f'<rect x="794" y="65" width="2" height="2" fill="{P["window_frame"]}" />',
            f'<rect x="789" y="71" width="11" height="2" fill="{P["window_frame"]}" fill-opacity="0.45" />',
            f'<rect x="789" y="75" width="8" height="2" fill="{P["window_frame"]}" fill-opacity="0.45" />',
        ]
    )


def _render_desk_and_lamp(is_daytime: bool = False) -> str:
    """Render layered wooden desk with depth, ambient shadows, and Day (off) / Night (lit) table lamp."""
    if is_daytime:
        room_ambient_light = (
            f'<rect x="0" y="0" width="{WORKSPACE_WIDTH}" height="385" fill="#7cb8ff" fill-opacity="0.06" />',
            '<polygon class="day-sunbeam" points="44,269 244,269 420,428 110,428" fill="url(#sunbeam-grad)" pointer-events="none" />',
        )
        lamp_light_and_shade = [
            # Daytime: table lamp is OFF (no glow cone, unlit shade & dark bulb)
            f'<rect x="264" y="293" width="22" height="4" fill="{P["lamp_pole"]}" />',
            f'<rect x="273" y="192" width="4" height="101" fill="{P["lamp_pole"]}" />',
            f'<rect x="271" y="236" width="8" height="4" fill="{P["monitor_base"]}" />',
            f'<rect x="257" y="176" width="36" height="14" fill="#9e8748" />',
            f'<rect x="259" y="188" width="32" height="2" fill="#4f462d" />',
            f'<rect x="257" y="190" width="36" height="2" fill="#756333" />',
        ]
    else:
        room_ambient_light = (
            # Soft ambient desk glow from external monitor onto wall at night
            f'<rect x="410" y="118" width="280" height="170" fill="#5aa9ff" fill-opacity="0.035" />',
        )
        lamp_light_and_shade = [
            # Nighttime: animated warm desk lamp glow cone illuminating MacBook & left desk
            f'<polygon class="lamp-glow-cone" points="258,192 292,192 332,297 248,297" fill="url(#lamp-beam-grad)" />',
            # Desk lamp hardware (far left on desk)
            f'<rect x="264" y="293" width="22" height="4" fill="{P["lamp_pole"]}" />',
            f'<rect x="273" y="192" width="4" height="101" fill="{P["lamp_pole"]}" />',
            f'<rect x="271" y="236" width="8" height="4" fill="{P["monitor_base"]}" />',
            f'<rect x="257" y="176" width="36" height="14" fill="{P["lamp_shade"]}" />',
            f'<rect x="259" y="188" width="32" height="3" fill="#ffe694" />',
            f'<rect x="257" y="190" width="36" height="2" fill="#d4aa42" />',
        ]

    return "\n    ".join(
        [
            *room_ambient_light,
            # Desk legs & inner leg shadow (x=248..742, y=297..403)
            f'<rect x="266" y="323" width="14" height="80" fill="{P["wood_shadow"]}" />',
            f'<rect x="266" y="323" width="14" height="6" fill="{P["wood_dark"]}" />',
            f'<rect x="280" y="323" width="4" height="80" fill="{P["shadow_ambient"]}" fill-opacity="0.35" />',
            f'<rect x="710" y="323" width="14" height="80" fill="{P["wood_shadow"]}" />',
            f'<rect x="710" y="323" width="14" height="6" fill="{P["wood_dark"]}" />',
            f'<rect x="706" y="323" width="4" height="80" fill="{P["shadow_ambient"]}" fill-opacity="0.35" />',
            # Desk top surface with highlight rim and front apron
            f'<rect x="248" y="297" width="494" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="248" y="299" width="494" height="16" fill="{P["wood_top"]}" />',
            f'<rect x="256" y="315" width="478" height="8" fill="{P["wood_shadow"]}" />',
            f'<rect x="260" y="323" width="470" height="5" fill="{P["shadow_ambient"]}" fill-opacity="0.45" />',
            *lamp_light_and_shade,
        ]
    )


def _render_macbook_and_peripherals() -> str:
    """Render MacBook, USB-C dock/hub, connecting monitor cable, mechanical keyboard, mouse, notebook, and headphones."""
    # Generate compact pixel keycap grid inside mechanical keyboard (x=462..552, y=300..308)
    keycaps: list[str] = []
    # Top row keycaps (Esc red, alphas light, accent blue)
    for kx in range(463, 550, 5):
        fill = P["keycap_esc"] if kx == 463 else (P["keycap_mod"] if kx >= 543 else P["keycap_light"])
        keycaps.append(f'<rect x="{kx}" y="301" width="4" height="2" fill="{fill}" />')
    # Middle row keycaps
    for kx in range(463, 550, 5):
        fill = P["keycap_mod"] if kx >= 543 else P["keycap_light"]
        keycaps.append(f'<rect x="{kx}" y="304" width="4" height="2" fill="{fill}" />')
    # Bottom row + spacebar
    keycaps.append(f'<rect x="463" y="307" width="8" height="2" fill="{P["monitor_base"]}" />')
    keycaps.append(f'<rect x="473" y="307" width="6" height="2" fill="{P["monitor_base"]}" />')
    keycaps.append(f'<rect x="481" y="307" width="42" height="2" fill="{P["keycap_light"]}" />')
    keycaps.append(f'<rect x="525" y="307" width="8" height="2" fill="{P["monitor_base"]}" />')
    keycaps.append(f'<rect x="535" y="307" width="14" height="2" fill="{P["keycap_mod"]}" />')

    return "\n    ".join(
        [
            # USB-C Dock / External SSD next to MacBook + clear display cable routed cleanly to monitor underside
            f'<rect x="402" y="290" width="20" height="7" fill="{P["mac_dark"]}" />',
            f'<rect x="404" y="291" width="16" height="2" fill="{P["mac_edge"]}" />',
            f'<rect x="416" y="294" width="3" height="2" fill="#5aa9ff" />',
            f'<rect x="396" y="291" width="6" height="4" fill="{P["mac_aluminum"]}" />',
            f'<rect x="422" y="293" width="71" height="1" fill="{P["cable_highlight"]}" />',
            f'<rect x="422" y="294" width="71" height="2" fill="{P["cable"]}" />',
            f'<rect x="490" y="286" width="3" height="10" fill="{P["cable"]}" />',
            f'<rect x="490" y="287" width="1" height="7" fill="{P["cable_highlight"]}" />',
            f'<rect x="489" y="286" width="5" height="3" fill="{P["mac_edge"]}" />',
            # MacBook open lid / display (x=304..388, y=236..288)
            f'<rect x="304" y="236" width="84" height="52" fill="{P["mac_edge"]}" />',
            f'<rect x="306" y="238" width="80" height="48" fill="{P["mac_dark"]}" />',
            f'<rect x="310" y="242" width="72" height="40" fill="{P["mac_screen"]}" />',
            # Static clean syntax-highlighted IDE mockup on MacBook
            f'<rect x="314" y="246" width="16" height="3" fill="#64aee9" />',
            f'<rect x="332" y="246" width="8" height="3" fill="#93c8b2" />',
            f'<rect x="314" y="253" width="38" height="2" fill="{P["window_star"]}" />',
            f'<rect x="318" y="258" width="48" height="2" fill="#35527a" />',
            f'<rect x="318" y="263" width="30" height="2" fill="{P["lamp_shade"]}" fill-opacity="0.7" />',
            f'<rect x="314" y="268" width="44" height="2" fill="{P["window_star"]}" />',
            f'<rect x="314" y="273" width="26" height="2" fill="#93c8b2" fill-opacity="0.6" />',
            # MacBook aluminum unibody base (x=296..396, y=288..298)
            f'<rect x="296" y="288" width="100" height="6" fill="{P["mac_aluminum"]}" />',
            f'<rect x="310" y="288" width="72" height="2" fill="{P["mac_dark"]}" />',
            f'<rect x="296" y="294" width="100" height="4" fill="{P["mac_edge"]}" />',
            f'<rect x="340" y="294" width="12" height="2" fill="{P["mac_dark"]}" />',
            # Mini Raspberry Pi / Audio DAC box under right monitor edge (x=610..636, y=289..297)
            f'<rect x="610" y="289" width="26" height="8" fill="{P["monitor_inner"]}" />',
            f'<rect x="612" y="290" width="22" height="2" fill="{P["monitor_base"]}" />',
            f'<rect x="614" y="294" width="3" height="2" fill="#73b88d" />',
            f'<rect x="619" y="294" width="6" height="2" fill="#f2cb62" />',
            # Mechanical Keyboard (front center of desk y=299..310, completely unobstructed)
            f'<rect x="504" y="294" width="3" height="6" fill="{P["cable"]}" />',
            f'<rect x="460" y="300" width="92" height="10" fill="{P["mac_dark"]}" />',
            f'<rect x="460" y="310" width="92" height="2" fill="{P["cable"]}" />',
            *keycaps,
            # Stitched Mousepad + Wireless Pixel Mouse (x=564..616, y=299..311)
            f'<rect x="564" y="299" width="52" height="12" fill="{P["mousepad_border"]}" />',
            f'<rect x="565" y="300" width="50" height="10" fill="{P["mousepad_bg"]}" />',
            f'<rect x="582" y="297" width="16" height="10" fill="{P["chair_main"]}" />',
            f'<rect x="583" y="297" width="14" height="3" fill="{P["mac_aluminum"]}" />',
            f'<rect x="589" y="298" width="2" height="3" fill="#5aa9ff" />',
            # Developer Notebook & Pen (x=624..671, y=298..310)
            f'<rect x="624" y="299" width="34" height="10" fill="{P["book_cream"]}" />',
            f'<rect x="624" y="299" width="6" height="10" fill="{P["book_blue"]}" />',
            f'<rect x="633" y="302" width="20" height="1" fill="{P["monitor_base"]}" />',
            f'<rect x="633" y="305" width="16" height="1" fill="{P["monitor_base"]}" />',
            f'<rect x="662" y="297" width="3" height="11" fill="{P["lamp_shade"]}" />',
            f'<rect x="662" y="296" width="3" height="2" fill="{P["mac_aluminum"]}" />',
            f'<rect x="662" y="308" width="3" height="2" fill="{P["plaque_border"]}" />',
            # Studio Over-Ear Headphones on Sleek Aluminum Desk Stand (x=717..741, y=253..297)
            f'<rect x="720" y="294" width="18" height="3" fill="{P["monitor_base"]}" />',
            f'<rect x="727" y="260" width="4" height="34" fill="{P["mac_edge"]}" />',
            f'<rect x="719" y="254" width="20" height="4" fill="{P["mac_dark"]}" />',
            f'<rect x="721" y="255" width="16" height="2" fill="{P["chair_highlight"]}" />',
            # Headband side arms connecting seamlessly down into earcups
            f'<rect x="719" y="258" width="2" height="7" fill="{P["mac_edge"]}" />',
            f'<rect x="737" y="258" width="2" height="7" fill="{P["mac_edge"]}" />',
            f'<rect x="717" y="264" width="8" height="16" fill="{P["monitor_outer"]}" />',
            f'<rect x="723" y="266" width="3" height="12" fill="{P["chair_highlight"]}" />',
            f'<rect x="718" y="269" width="2" height="6" fill="#8294ea" />',
            f'<rect x="733" y="264" width="8" height="16" fill="{P["monitor_outer"]}" />',
            f'<rect x="732" y="266" width="3" height="12" fill="{P["chair_highlight"]}" />',
            f'<rect x="738" y="269" width="2" height="6" fill="#8294ea" />',
        ]
    )


def _render_external_monitor_shell() -> str:
    """Render external monitor stand, webcam, bezel, and backdrop behind the movie-credit screen."""
    sx, sy, sw, sh = MONITOR_SCREEN_BOX
    return "\n    ".join(
        [
            # Monitor stand neck & wide flat base resting on desk (y=297)
            f'<rect x="536" y="284" width="28" height="9" fill="{P["monitor_stand"]}" />',
            f'<rect x="504" y="293" width="92" height="4" fill="{P["monitor_base"]}" />',
            # Tiny webcam bar centered on top bezel (x=541..559, y=116..122)
            f'<rect x="541" y="116" width="18" height="6" fill="{P["mac_dark"]}" />',
            f'<rect x="548" y="117" width="4" height="4" fill="#5aa9ff" />',
            f'<rect x="554" y="118" width="2" height="2" fill="#73b88d" />',
            # Monitor wall/back drop shadow + outer bezel & inner dark bevel (x=414..686, y=122..284)
            f'<rect x="418" y="126" width="272" height="162" fill="{P["shadow_ambient"]}" fill-opacity="0.45" />',
            f'<rect x="414" y="122" width="272" height="164" fill="{P["monitor_outer"]}" />',
            f'<rect x="420" y="128" width="260" height="152" fill="{P["monitor_inner"]}" />',
            # Top bezel rim highlight + power indicator LED dot on bottom bezel chin
            f'<rect x="414" y="122" width="272" height="2" fill="{P["monitor_stand"]}" />',
            f'<rect x="668" y="281" width="4" height="2" fill="{P["credit_repo"]}" />',
            # Deep cinema screen backdrop
            f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{P["screen_bg"]}" />',
        ]
    )


def _render_mug_and_chair() -> str:
    """Render coffee mug with rising animated steam + foreground desk chair below tabletop."""
    return "\n    ".join(
        [
            # Coaster & Coffee mug cleanly to right of external monitor (x=688..715, y=274..297)
            f'<rect x="688" y="295" width="24" height="3" fill="{P["wood_dark"]}" />',
            f'<rect x="690" y="274" width="20" height="21" fill="{P["mug_cream"]}" />',
            f'<rect x="692" y="274" width="16" height="2" fill="#4e3222" />',
            f'<rect x="706" y="274" width="4" height="21" fill="{P["mug_shadow"]}" />',
            f'<rect x="710" y="278" width="5" height="3" fill="{P["mug_cream"]}" />',
            f'<rect x="712" y="281" width="3" height="7" fill="{P["mug_cream"]}" />',
            f'<rect x="710" y="288" width="5" height="3" fill="{P["mug_cream"]}" />',
            # ── Vertical rising coffee steam (straight up above mug rim, zero sideways drift) ──
            f'<rect class="mug-steam-puff-a" x="694" y="264" width="12" height="4" fill="{P["mug_cream"]}" fill-opacity="0.34" />',
            f'<rect class="mug-steam-puff-a" x="696" y="260" width="8" height="4" fill="{P["mug_cream"]}" fill-opacity="0.26" />',
            f'<rect class="mug-steam-puff-b" x="695" y="256" width="10" height="3" fill="{P["mug_cream"]}" fill-opacity="0.24" />',
            f'<rect class="mug-steam-puff-b" x="697" y="252" width="6" height="3" fill="{P["mug_cream"]}" fill-opacity="0.18" />',
            f'<rect class="mug-steam-puff-c" x="696" y="248" width="8" height="3" fill="{P["mug_cream"]}" fill-opacity="0.15" />',
            f'<rect class="mug-steam-puff-c" x="698" y="244" width="4" height="2" fill="{P["mug_cream"]}" fill-opacity="0.11" />',
            # Thin vertical wisps centered directly over coffee surface (x=695..705)
            f'<rect class="mug-steam-1" x="695" y="264" width="2" height="6" fill="{P["mug_cream"]}" fill-opacity="0.55" />',
            f'<rect class="mug-steam-2" x="700" y="260" width="2" height="8" fill="{P["mug_cream"]}" fill-opacity="0.45" />',
            f'<rect class="mug-steam-3" x="705" y="265" width="2" height="5" fill="{P["mug_cream"]}" fill-opacity="0.35" />',
            # Ergonomic desk chair positioned cleanly below tabletop y=312 (zero overlap with keyboard/screen)
            f'<rect x="524" y="312" width="56" height="30" fill="{P["chair_main"]}" />',
            f'<rect x="528" y="312" width="48" height="4" fill="{P["chair_highlight"]}" />',
            # Armrests
            f'<rect x="510" y="330" width="10" height="4" fill="{P["chair_highlight"]}" />',
            f'<rect x="514" y="334" width="4" height="10" fill="{P["chair_shadow"]}" />',
            f'<rect x="584" y="330" width="10" height="4" fill="{P["chair_highlight"]}" />',
            f'<rect x="586" y="334" width="4" height="10" fill="{P["chair_shadow"]}" />',
            # Seat pan, gas lift, and caster wheel base
            f'<rect x="514" y="342" width="76" height="12" fill="{P["chair_highlight"]}" />',
            f'<rect x="514" y="350" width="76" height="4" fill="{P["chair_shadow"]}" />',
            f'<rect x="546" y="354" width="12" height="40" fill="{P["chair_main"]}" />',
            f'<rect x="526" y="394" width="52" height="6" fill="{P["chair_shadow"]}" />',
            f'<rect x="528" y="400" width="6" height="4" fill="{P["mac_dark"]}" />',
            f'<rect x="549" y="400" width="6" height="4" fill="{P["mac_dark"]}" />',
            f'<rect x="570" y="400" width="6" height="4" fill="{P["mac_dark"]}" />',
        ]
    )


def _render_indoor_plants(include_second_plant: bool) -> str:
    """Render reference-shaped floor Monstera deliciosa beside desk plus optional shelf succulent."""
    monstera_palette = {
        "L": "#56c95e",  # sunlit / young upper leaf green
        "V": "#73dc78",  # crisp vein & lobe highlight
        "G": P["plant_leaf"],       # #2ca042 rich main leaf green
        "D": P["plant_leaf_dark"],  # #217a32 deep leaf shadow
        "F": "#185925",  # darkest leaf crease shadow
        "S": "#2b8238",  # main slender stems
        "T": "#1d5e28",  # shaded stem edge
        "P": "#7a4a2b",  # warm petiole base sheath accent (like reference photo)
        "B": "#36261d",  # dark potting soil rim
        "H": "#f5efe4",  # ceramic highlight
        "C": P["mug_cream"],        # #ebe0cf ceramic cylinder pot
        "M": P["mug_shadow"],       # #cfc3b2 ceramic right shadow
        "W": "#a3998b",  # subtle pot edge / base grounding
    }
    # 90-col x 76-row 2px pixel sprite -> 180x152px anchored at (66, 252), pot grounded at y=404, 4th leaf leans right toward display
    monstera_rows: tuple[str, ...] = (
        ".................................LLLLLL...................................................",
        "...............................LLLLVVLLLL.................................................",
        "..............................LLLVLLLLLLLL................................................",
        ".............................LLLL.LLLLL.LLL...............................................",
        ".............................LLL..LLLLL..LLL..............................................",
        ".........................GG.....LLLL..LLLL................................................",
        ".......................GGGGGG..LLLLL..LLLLL...............................................",
        ".....................GGGGVVGGGG..LLL.LLL..................................................",
        "...................GGGGGGVVGGGGGG.LLLLLL............GGGGGG................................",
        "................GGGGGGGGGGVGGGGGG.LLLLLL..........GGGGVVGGGGGG............................",
        "..............GGGGGGGGGGGGVGGGGGGDLLLLL..........GGGGVVGGGGGGGGG..........................",
        ".............GGGG....GGGGGVGGGGGGGDLL...........GGGGGVGGGGGGGGGGGG........................",
        "...........GGGGGGGGGGGGGGGGVGGGGGGGDD..........GGGGGGVGGGGGG....GGGG......................",
        ".........GGGGGGGGGGGGGGGGGGVGGGGGGGGD.........GGGGGGGVGGGGGGGGGGGGGGG.....................",
        "........GGGG.....GGGGGGGGGGVGGGGGGGGD.........GGGGGGGVGGGGGGGGGGGGGGGG....................",
        ".......GGGGGGGGGGGGGGGGGGGGVGGGGGGGDD........GGGGGGGGVGGGGGG.....GGGGGG...................",
        "......GGGGGGGGGGGGGGGGGGGGGVGGGGGGGDD........GGGGGGGGVGGGGGGGGGGGGGGGGGG..................",
        ".....GGGGGG......GGGGGGGGGGVGGGGGGGDD.......GGGGGGGGGVGGGGGGGGGGGGGGGGGGG.................",
        "....GGGGGGGGGGGGGGGGGGGGGGGVGGGGGGGDD.......GGGGGGGGGGGGGGGGGG......GGGGGG................",
        "....GGGGGGGGGGGGG..GGGGGGGGVVGGGGGGDD......GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG................",
        ".....GGGG........GGGGGGGGGGVGGGGGGGDD......GGGGGGGGGGGG..GGGGGGGGGGGGGGGGG................",
        "......GGGGGGGGGGGGGGGGGGGGGVGGGGGGGDD......GGGGGGGGGGGGGGGGGG........GGGG.................",
        ".......GGGGGGGGGGGGGGGGGGGGVGGGGGGGDD......GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG.................",
        "........GGGG....GGGGGGGGGGGVGGGGGGGDD.......GGGGGGGGGGG..GGGGGGGGGGGGGGG..........GGGGGG..",
        ".........GGGGGGGGGGGGGGGGGGVGGGGGGDDD.......GGGGGGGGGGGGGGGGGGGG..GGGG..........GGGGVVGGGG",
        "..........GGGGGGGGGGGGGGGGGGGGGGGGDDD........GGGGGGGGGGGGGGGGGGGGGGGG..........GGGGVVGGGGG",
        "...........GGGG....GGGGGGGGGGGGGGDDD.........GGGGGG....GGGGGGGGGGGGGG.........GGGGGVGGGGGG",
        "............GGGGGGGGGGGGGGGGGGGGDDDD..........GGGGGG....GGGGGGGGGGGG.........GGGGGGVGGGGGG",
        ".............GGGGGGGGGGGGGGGGGGGDDD............GGGGGG....GGGGGGGGGG.........GGGGGGGVGG....",
        "..............GGGG....GGGGGGGGGDDD..............GGGGG.....GGGGGGGG.........GGGGGGGGVVGGGGG",
        "...............GG.....GGGGGGGGDDDD...............GGGG......GGGGGG.........GGGGGGGGGGVGGGGG",
        ".......................GGGGGGGDD.D................GGG.......GGGG.........GGGGGGGGGGGGVGGGG",
        "........................GGGGGGDD..................GGG........GG..........GGGGGG...GGGGVGGG",
        ".........................GGGGDD...................SS....................GGGGGGGGGGGGGGGVGG",
        "..........................SSST.S..................SS...................GGGGGGGGGGGGGGGGGGD",
        "..........................SST..ST................SST..................GGGGGG....GGGGGGGGGD",
        "...........................SST.ST...............SST..................GGGGGGGGGGGGGGGGGGGDD",
        "...........................SST.ST..............SST...................GGGGGGGGGGGGGGGGGGDDD",
        "............................SSTST.............SST...................GGGG....GGGGGGGGGGDDDD",
        "............................SSTST............SST....................GGG....GGGGGGGGGGDDDD.",
        ".............................SSST...........SST..................SSSGG.....GGGGGGGGDDDD...",
        ".............................SSST..........SSPT................SSSST.......GGGGGGDDDD.....",
        "..............................SSST.........SPT...............SSSST..........GGGGDDD.......",
        "..............................SSST........SSPT.............SSSST............GGGDD.........",
        "...............................SSST......SSPT............SSSPT............................",
        "...............................SSST.....SSPT...........SSSPT..............................",
        "................................SSST....SPT..........SSSPT................................",
        "................................SSST...SSPT........SSSPT..................................",
        ".................................SSST.SSPT.......SSSPT....................................",
        ".................................SSSTSSPT......SSSPT......................................",
        "..................................SSSTPT....SSSSPT........................................",
        "..................................SSSPT..SSSSPT...........................................",
        "...................................SSPTSSSPT..............................................",
        "...........................BBBBBBBBBBBBBBBBBBBBBBBB.......................................",
        "...........................HBBBBBBBBBBBBBBBBBBBBBBM.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMM.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMM.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMM.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMM.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "...........................HHCCCCCCCCCCCCCCCCCCCCMW.......................................",
        "............................HCCCCCCCCCCCCCCCCCCCMW........................................",
        "............................HHCCCCCCCCCCCCCCCCCCMW........................................",
        ".............................HCCCCCCCCCCCCCCCCCMW.........................................",
        "..............................MMMMMMMMMMMMMMMMWW..........................................",
        "................................WWWWWWWWWWWWWW............................................",
    )
    parts = _render_pixel_sprite(
        origin_x=66,
        origin_y=252,
        px=2,
        rows=monstera_rows,
        palette=monstera_palette,
    )
    if include_second_plant:
        # Plant 2: Small potted succulent on left end of bottom right shelf (y=279)
        parts.extend(
            [
                f'<rect x="774" y="261" width="24" height="4" fill="{P["plant_pot"]}" />',
                f'<rect x="776" y="265" width="20" height="14" fill="{P["plant_pot_rim"]}" />',
                f'<rect x="778" y="267" width="16" height="12" fill="{P["plant_pot"]}" />',
                f'<rect x="782" y="245" width="8" height="16" fill="{P["plant_leaf"]}" />',
                f'<rect x="774" y="251" width="8" height="10" fill="{P["plant_leaf_dark"]}" />',
                f'<rect x="790" y="251" width="8" height="10" fill="{P["plant_leaf"]}" />',
            ]
        )
    return "\n    ".join(parts)


def _render_bed_and_cat() -> str:
    """Render wooden storage bed beside the desk with under-bed drawers, plank footboard, and sleeping cat on top."""
    parts: list[str] = [
        # Soft wall shadow behind headboard & floor shadow beneath angled bed base
        f'<rect x="756" y="324" width="146" height="22" fill="{P["shadow_ambient"]}" fill-opacity="0.35" />',
        f'<rect x="802" y="446" width="154" height="8" fill="{P["floor_shadow"]}" fill-opacity="0.85" />',
        # Headboard against wall (x=752..898, y=320..398)
        f'<rect x="752" y="324" width="10" height="74" fill="{P["wood_top"]}" />',
        f'<rect x="752" y="324" width="2" height="74" fill="{P["wood_highlight"]}" />',
        f'<rect x="760" y="324" width="2" height="30" fill="{P["wood_dark"]}" />',
        f'<rect x="888" y="324" width="10" height="34" fill="{P["wood_top"]}" />',
        f'<rect x="888" y="324" width="2" height="22" fill="{P["wood_highlight"]}" />',
        f'<rect x="896" y="324" width="2" height="34" fill="{P["wood_shadow"]}" />',
        # Gently arched headboard top rail & 2 recessed horizontal planks
        f'<rect x="804" y="320" width="42" height="2" fill="{P["wood_highlight"]}" />',
        f'<rect x="782" y="322" width="86" height="2" fill="{P["wood_highlight"]}" />',
        f'<rect x="762" y="324" width="126" height="2" fill="{P["wood_highlight"]}" />',
        f'<rect x="762" y="326" width="126" height="8" fill="{P["wood_top"]}" />',
        f'<rect x="762" y="334" width="126" height="2" fill="{P["wood_dark"]}" />',
        f'<rect x="762" y="336" width="126" height="6" fill="{P["wood_top"]}" />',
    ]

    # Oblique floor shadow along angled left side, right wooden side rail, mattress, sheet & blanket
    for dy in range(0, 54, 2):
        lx = 756 + dy
        rx = 888 + dy
        y = 340 + dy

        # Angled floor cast shadow under left side rail
        parts.append(
            f'<rect x="{lx - 6}" y="{396 + dy}" width="10" height="4" '
            f'fill="{P["floor_shadow"]}" fill-opacity="0.7" />'
        )

        # Right wooden side rail outer frame (connects headboard right post to footboard right post)
        rail_h = min(48, 446 - (y + 8))
        parts.append(f'<rect x="{rx}" y="{y + 6}" width="10" height="2" fill="{P["wood_highlight"]}" />')
        if rail_h > 0:
            parts.append(f'<rect x="{rx}" y="{y + 8}" width="10" height="{rail_h}" fill="{P["wood_shadow"]}" />')
            parts.append(f'<rect x="{rx + 8}" y="{y + 8}" width="2" height="{rail_h}" fill="{P["wood_dark"]}" />')

        # Mattress top surface (fitted slate-blue sheet upper half, deep navy folded duvet lower half)
        is_blanket = dy >= 26
        is_trim = 26 <= dy <= 28
        if is_trim:
            top_fill = P["bed_blanket_trim"]
            side_fill = P["bed_blanket_shadow"]
        elif is_blanket:
            top_fill = P["bed_blanket_shadow"] if dy in (34, 42) else P["bed_blanket"]
            side_fill = P["bed_blanket_shadow"]
        else:
            top_fill = P["bed_sheet_light"] if dy in (18, 24) else P["bed_sheet_top"]
            side_fill = P["bed_sheet_side"]

        parts.append(f'<rect x="{lx + 4}" y="{y}" width="128" height="2" fill="{top_fill}" />')

        # Left mattress edge thickness + piping highlight
        parts.append(f'<rect x="{lx + 2}" y="{y}" width="2" height="2" fill="{P["bed_sheet_light"]}" />')
        parts.append(f'<rect x="{lx + 2}" y="{y + 2}" width="2" height="10" fill="{side_fill}" />')

        # Left wooden box frame below mattress (supports 3 under-bed storage drawers)
        parts.append(f'<rect x="{lx}" y="{y + 12}" width="2" height="2" fill="{P["wood_highlight"]}" />')
        parts.append(f'<rect x="{lx}" y="{y + 14}" width="2" height="2" fill="{P["wood_top"]}" />')
        parts.append(f'<rect x="{lx}" y="{y + 16}" width="2" height="36" fill="{P["wood_shadow"]}" />')
        parts.append(f'<rect x="{lx}" y="{y + 52}" width="2" height="4" fill="{P["wood_dark"]}" />')

    # 3 Under-bed storage drawers along the left box frame (matching photo's side drawer structure)
    for d_start in (6, 20, 34):
        for offset in range(0, 12, 2):
            dy = d_start + offset
            lx = 756 + dy
            y = 340 + dy
            parts.append(f'<rect x="{lx}" y="{y + 20}" width="2" height="26" fill="{P["wood_dark"]}" />')
            if 2 <= offset <= 8:
                parts.append(f'<rect x="{lx}" y="{y + 22}" width="2" height="22" fill="{P["wood_top"]}" />')
            else:
                parts.append(f'<rect x="{lx}" y="{y + 22}" width="2" height="22" fill="{P["wood_shadow"]}" />')
            if offset in (4, 6):
                parts.append(f'<rect x="{lx}" y="{y + 30}" width="2" height="4" fill="{P["wood_highlight"]}" />')
                parts.append(f'<rect x="{lx}" y="{y + 34}" width="2" height="2" fill="{P["wood_dark"]}" />')

    # Plump cream pillow tucked neatly near the headboard (clean pillow silhouette with soft shade)
    parts.extend(
        [
            f'<rect x="784" y="342" width="92" height="2" fill="#f5efe4" />',
            f'<rect x="782" y="344" width="96" height="8" fill="{P["bed_pillow"]}" />',
            f'<rect x="784" y="352" width="94" height="2" fill="{P["bed_pillow_shadow"]}" />',
            f'<rect x="786" y="354" width="92" height="2" fill="{P["bed_sheet_side"]}" />',
        ]
    )

    # Front footboard (x=806..952, y=380..452): corner posts, arched top rail, 3 horizontal planks & short feet
    parts.extend(
        [
            f'<rect x="806" y="384" width="10" height="68" fill="{P["wood_top"]}" />',
            f'<rect x="806" y="384" width="2" height="68" fill="{P["wood_highlight"]}" />',
            f'<rect x="814" y="386" width="2" height="58" fill="{P["wood_dark"]}" />',
            f'<rect x="806" y="446" width="10" height="6" fill="{P["wood_dark"]}" />',
            f'<rect x="942" y="384" width="10" height="68" fill="{P["wood_top"]}" />',
            f'<rect x="942" y="384" width="2" height="62" fill="{P["wood_highlight"]}" />',
            f'<rect x="950" y="384" width="2" height="68" fill="{P["wood_shadow"]}" />',
            f'<rect x="942" y="446" width="10" height="6" fill="{P["wood_dark"]}" />',
            f'<rect x="809" y="386" width="2" height="2" fill="{P["wood_dark"]}" />',
            f'<rect x="945" y="386" width="2" height="2" fill="{P["wood_dark"]}" />',
            f'<rect x="856" y="380" width="46" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="834" y="382" width="90" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="816" y="384" width="126" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="816" y="386" width="126" height="2" fill="{P["wood_top"]}" />',
            f'<rect x="816" y="388" width="126" height="2" fill="{P["wood_dark"]}" />',
            f'<rect x="816" y="390" width="126" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="816" y="392" width="126" height="12" fill="{P["wood_top"]}" />',
            f'<rect x="816" y="404" width="126" height="2" fill="{P["wood_dark"]}" />',
            f'<rect x="816" y="406" width="126" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="816" y="408" width="126" height="12" fill="{P["wood_top"]}" />',
            f'<rect x="816" y="420" width="126" height="2" fill="{P["wood_dark"]}" />',
            f'<rect x="816" y="422" width="126" height="2" fill="{P["wood_highlight"]}" />',
            f'<rect x="816" y="424" width="126" height="12" fill="{P["wood_top"]}" />',
            f'<rect x="816" y="436" width="126" height="4" fill="{P["wood_shadow"]}" />',
            f'<rect x="816" y="440" width="126" height="8" fill="{P["floor_shadow"]}" />',
            # Sleeping orange cat curled up ON TOP OF THE BED (resting on blanket at y=380, clear of pillow)
            f'<rect x="828" y="378" width="74" height="4" fill="{P["bed_blanket_shadow"]}" fill-opacity="0.7" />',
            '<g transform="translate(834, 372)">',
            '  <g class="cat-tail-wag">',
            f'    <rect x="-22" y="-4" width="24" height="6" fill="{P["cat_body"]}" />',
            f'    <rect x="-22" y="-4" width="6" height="4" fill="{P["cream"]}" />',
            "  </g>",
            "</g>",
            '<g transform="translate(858, 380)">',
            '  <g class="cat-breathe">',
            f'    <rect x="-24" y="-22" width="48" height="22" fill="{P["cat_body"]}" />',
            f'    <rect x="-18" y="-16" width="28" height="3" fill="{P["cat_stripe"]}" />',
            f'    <rect x="-6" y="-10" width="14" height="3" fill="{P["cat_stripe"]}" />',
            "  </g>",
            "</g>",
            f'<rect x="878" y="352" width="24" height="26" fill="{P["cat_body"]}" />',
            f'<rect x="878" y="346" width="6" height="6" fill="{P["cat_body"]}" />',
            f'<rect x="896" y="346" width="6" height="6" fill="{P["cat_body"]}" />',
            f'<rect x="890" y="362" width="4" height="2" fill="{P["cat_stripe"]}" />',
            f'<rect x="896" y="362" width="4" height="2" fill="{P["cat_stripe"]}" />',
            f'<rect x="895" y="367" width="3" height="2" fill="#d97777" />',
            '<g class="sleep-z-1">',
            f'  <rect x="910" y="324" width="6" height="2" fill="{P["window_star"]}" />',
            f'  <rect x="912" y="326" width="2" height="2" fill="{P["window_star"]}" />',
            f'  <rect x="910" y="328" width="6" height="2" fill="{P["window_star"]}" />',
            "</g>",
            '<g class="sleep-z-2">',
            f'  <rect x="920" y="312" width="8" height="2" fill="{P["window_star"]}" />',
            f'  <rect x="924" y="314" width="2" height="2" fill="{P["window_star"]}" />',
            f'  <rect x="920" y="316" width="8" height="2" fill="{P["window_star"]}" />',
            "</g>",
        ]
    )
    return "\n    ".join(parts)


def _render_clock_shelves_and_cat() -> str:
    """Render animated wall clock, well-stocked programmer bookshelves, and wooden bed with sleeping cat."""
    return "\n    ".join(
        [
            # Wall clock with animated hands (cx=860, cy=73)
            f'<circle cx="862" cy="76" r="30" fill="{P["shadow_ambient"]}" fill-opacity="0.45" />',
            f'<circle cx="860" cy="73" r="30" fill="{P["window_frame"]}" />',
            f'<circle cx="860" cy="73" r="26" fill="{P["cream"]}" />',
            # Hour tick marks (12, 3, 6, 9)
            f'<rect x="859" y="50" width="2" height="4" fill="{P["chair_shadow"]}" />',
            f'<rect x="880" y="72" width="4" height="2" fill="{P["chair_shadow"]}" />',
            f'<rect x="859" y="92" width="2" height="4" fill="{P["chair_shadow"]}" />',
            f'<rect x="836" y="72" width="4" height="2" fill="{P["chair_shadow"]}" />',
            # Animated clock hands pivoted cleanly around (860, 73)
            '<g transform="translate(860, 73)">',
            f'  <g class="clock-hour-hand"><line x1="0" y1="0" x2="-12" y2="-10" stroke="{P["window_frame"]}" stroke-width="3" stroke-linecap="square" /></g>',
            f'  <g class="clock-min-hand"><line x1="0" y1="0" x2="14" y2="-14" stroke="{P["window_frame"]}" stroke-width="2.5" stroke-linecap="square" /></g>',
            f'  <circle cx="0" cy="0" r="2.5" fill="{P["window_frame"]}" />',
            "</g>",
            # Top & bottom right bookshelves with metal L-brackets and cast shadows (x=762..948)
            f'<rect x="778" y="210" width="4" height="10" fill="{P["lamp_pole"]}" />',
            f'<rect x="926" y="210" width="4" height="10" fill="{P["lamp_pole"]}" />',
            f'<rect x="762" y="198" width="186" height="8" fill="{P["wood_top"]}" />',
            f'<rect x="762" y="206" width="186" height="4" fill="{P["wood_shadow"]}" />',
            f'<rect x="764" y="210" width="182" height="4" fill="{P["shadow_ambient"]}" fill-opacity="0.4" />',
            f'<rect x="778" y="291" width="4" height="10" fill="{P["lamp_pole"]}" />',
            f'<rect x="926" y="291" width="4" height="10" fill="{P["lamp_pole"]}" />',
            f'<rect x="762" y="279" width="186" height="8" fill="{P["wood_top"]}" />',
            f'<rect x="762" y="287" width="186" height="4" fill="{P["wood_shadow"]}" />',
            f'<rect x="764" y="291" width="182" height="4" fill="{P["shadow_ambient"]}" fill-opacity="0.4" />',
            # Top shelf: rich technical & programming book collection + cube decor
            f'<rect x="768" y="156" width="26" height="42" fill="{P["book_blue"]}" />',
            f'<rect x="768" y="164" width="26" height="3" fill="#5aa9ff" />',
            f'<rect x="772" y="186" width="18" height="2" fill="{P["lamp_shade"]}" />',
            f'<rect x="797" y="158" width="18" height="40" fill="{P["book_red"]}" />',
            f'<rect x="797" y="166" width="18" height="3" fill="{P["cream"]}" />',
            f'<rect x="818" y="150" width="11" height="48" fill="{P["book_blue"]}" />',
            f'<rect x="832" y="158" width="11" height="40" fill="{P["book_yellow"]}" />',
            f'<rect x="846" y="164" width="13" height="34" fill="{P["book_cream"]}" />',
            f'<rect x="846" y="172" width="13" height="3" fill="{P["wood_shadow"]}" />',
            f'<rect x="862" y="154" width="16" height="44" fill="#2c8a7a" />',
            f'<rect x="862" y="163" width="16" height="2" fill="{P["cream"]}" />',
            # Stacked horizontal reference manuals + Rubik's cube on right side of top shelf
            f'<rect x="888" y="189" width="52" height="9" fill="{P["chair_main"]}" />',
            f'<rect x="892" y="180" width="46" height="9" fill="{P["book_blue"]}" />',
            f'<rect x="904" y="168" width="12" height="12" fill="{P["plaque_border"]}" />',
            f'<rect x="905" y="169" width="3" height="3" fill="{P["book_red"]}" />',
            f'<rect x="909" y="169" width="3" height="3" fill="{P["book_yellow"]}" />',
            f'<rect x="913" y="169" width="2" height="3" fill="#5aa9ff" />',
            f'<rect x="905" y="173" width="3" height="3" fill="{P["plant_leaf"]}" />',
            f'<rect x="909" y="173" width="3" height="3" fill="{P["cream"]}" />',
            f'<rect x="913" y="173" width="2" height="3" fill="{P["book_red"]}" />',
            f'<rect x="905" y="177" width="10" height="2" fill="{P["book_yellow"]}" />',
            # Bottom shelf: Plant 2 + notebooks + retro mini computer dev box + prism trophy
            f'<rect x="812" y="270" width="44" height="9" fill="{P["chair_main"]}" />',
            f'<rect x="815" y="262" width="38" height="8" fill="{P["book_yellow"]}" />',
            f'<rect x="868" y="253" width="28" height="26" fill="{P["mac_edge"]}" />',
            f'<rect x="872" y="257" width="20" height="14" fill="{P["screen_bg"]}" />',
            f'<rect x="874" y="261" width="10" height="2" fill="#73b88d" />',
            f'<rect x="874" y="265" width="14" height="2" fill="#5aa9ff" />',
            f'<rect x="872" y="274" width="4" height="2" fill="#73b88d" />',
            f'<rect x="908" y="255" width="24" height="24" fill="{P["plaque_border"]}" />',
            f'<rect x="911" y="258" width="18" height="18" fill="{P["poster_bg"]}" />',
            f'<rect x="917" y="263" width="6" height="8" fill="{P["lamp_shade"]}" />',
            _render_bed_and_cat(),
        ]
    )


def render_workspace_room_layers(
    config: ProfileConfig,
    theme: WorkspaceTheme = "auto",
    now: datetime | None = None,
) -> dict[str, str]:
    """Render static and animated pixel-art room background and foreground layers around the monitor."""
    is_daytime = resolve_is_daytime(timezone_name=config.timezone, theme=theme, now=now)
    background = "\n    ".join(
        [
            _render_wall_and_floor(),
            _render_window(is_daytime=is_daytime),
            _render_name_plaque_and_wall_decor(config.display_name),
            _render_desk_and_lamp(is_daytime=is_daytime),
            _render_macbook_and_peripherals(),
            _render_external_monitor_shell(),
            _render_clock_shelves_and_cat(),
            _render_indoor_plants(config.include_second_plant),
        ]
    )
    foreground = _render_mug_and_chair()
    _ = WORKSPACE_HEIGHT
    return {"background": background, "foreground": foreground}
