"""Pixel-art room scene generator matching Reference Image 1 + dual-device Mac setup."""

from __future__ import annotations

from src.config import (
    MONITOR_SCREEN_BOX,
    WORKSPACE_HEIGHT,
    WORKSPACE_PALETTE as P,
    WORKSPACE_WIDTH,
    ProfileConfig,
)

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
        if rows is None:
            cursor_x += 4 * px
            continue
        if ch == " ":
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


def _render_wall_and_floor() -> str:
    """Render dark striped wallpaper and wooden plank flooring."""
    parts: list[str] = [
        f'<rect x="0" y="0" width="{WORKSPACE_WIDTH}" height="395" fill="{P["wall_primary"]}" />'
    ]
    for x in range(0, WORKSPACE_WIDTH, 36):
        parts.append(
            f'<rect x="{x + 18}" y="0" width="18" height="395" fill="{P["wall_stripe"]}" />'
        )

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
    for row_top, row_h, joints in zip(row_tops, row_heights, joint_offsets):
        for jx in joints:
            parts.append(
                f'<rect x="{jx}" y="{row_top}" width="2" height="{row_h}" fill="{P["floor_seam"]}" />'
            )
    return "\n    ".join(parts)


def _render_window() -> str:
    """Render cozy 2x2 night window with crescent moon, stars, and wooden sill."""
    return "\n    ".join(
        [
            f'<rect x="36" y="55" width="208" height="202" fill="{P["window_frame"]}" />',
            # 4 night sky panes
            f'<rect x="44" y="63" width="92" height="88" fill="{P["window_sky"]}" />',
            f'<rect x="144" y="63" width="92" height="88" fill="{P["window_sky"]}" />',
            f'<rect x="44" y="159" width="92" height="90" fill="{P["window_sky"]}" />',
            f'<rect x="144" y="159" width="92" height="90" fill="{P["window_sky"]}" />',
            # Subtle pixel stars
            f'<rect x="68" y="92" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect x="168" y="76" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect x="86" y="198" width="4" height="4" fill="{P["window_star"]}" />',
            f'<rect x="196" y="206" width="4" height="4" fill="{P["window_star"]}" />',
            # Pixel L-crescent moon in upper-right pane + star dot
            f'<rect x="184" y="88" width="8" height="24" fill="{P["cream"]}" />',
            f'<rect x="184" y="104" width="24" height="8" fill="{P["cream"]}" />',
            f'<rect x="208" y="120" width="4" height="4" fill="{P["cream"]}" />',
            # Wooden window sill
            f'<rect x="28" y="257" width="224" height="8" fill="{P["wood_top"]}" />',
            f'<rect x="28" y="265" width="224" height="4" fill="{P["wood_shadow"]}" />',
        ]
    )


def _render_name_plaque(display_name: str) -> str:
    """Render framed ESHTIAQ AHMAD plaque centered above the external monitor."""
    # Center plaque directly over external monitor (cx=550)
    plaque_x, plaque_y, plaque_w, plaque_h = 378, 50, 344, 46
    # 12 visible letters + 1 space: width = 12*6*3 - 3 + 4*3 = 225px; exact centering inside 344px
    text_width = 225
    text_x = plaque_x + (plaque_w - text_width) // 2
    text_y = plaque_y + 12
    return "\n    ".join(
        [
            f'<rect x="{plaque_x}" y="{plaque_y}" width="{plaque_w}" height="{plaque_h}" fill="{P["plaque_border"]}" />',
            f'<rect x="{plaque_x + 4}" y="{plaque_y + 4}" width="{plaque_w - 8}" height="{plaque_h - 8}" fill="{P["plaque_bg"]}" />',
            _render_pixel_text(display_name, text_x, text_y, px=3, color=P["plaque_border"]),
        ]
    )


def _render_desk_and_lamp() -> str:
    """Render widened wooden desk and warm desk lamp illuminating the MacBook."""
    return "\n    ".join(
        [
            # Desk surface & legs (x=254..734, y=298..403)
            f'<rect x="270" y="324" width="14" height="79" fill="{P["wood_shadow"]}" />',
            f'<rect x="270" y="324" width="14" height="4" fill="{P["wood_dark"]}" />',
            f'<rect x="704" y="324" width="14" height="79" fill="{P["wood_shadow"]}" />',
            f'<rect x="704" y="324" width="14" height="4" fill="{P["wood_dark"]}" />',
            f'<rect x="254" y="298" width="480" height="16" fill="{P["wood_top"]}" />',
            f'<rect x="262" y="314" width="464" height="10" fill="{P["wood_shadow"]}" />',
            # Desk lamp (far left, warm glow next to MacBook without clipping lid)
            f'<polygon points="260,192 296,192 314,298 256,298" fill="{P["lamp_shade"]}" fill-opacity="0.08" />',
            f'<rect x="268" y="294" width="20" height="4" fill="{P["lamp_pole"]}" />',
            f'<rect x="276" y="192" width="4" height="102" fill="{P["lamp_pole"]}" />',
            f'<rect x="260" y="176" width="36" height="14" fill="{P["lamp_shade"]}" />',
            f'<rect x="260" y="188" width="36" height="4" fill="#d4aa42" />',
        ]
    )


def _render_macbook_and_cable() -> str:
    """Render Apple MacBook laptop on desk connected via cable to the external monitor."""
    return "\n    ".join(
        [
            # Display connection cable (USB-C / DisplayPort from MacBook right edge to monitor stand)
            f'<rect x="398" y="290" width="6" height="5" fill="{P["mac_aluminum"]}" />',
            f'<rect x="404" y="291" width="10" height="3" fill="{P["cable_highlight"]}" />',
            f'<rect x="412" y="293" width="128" height="3" fill="{P["cable"]}" />',
            f'<rect x="538" y="284" width="3" height="12" fill="{P["cable"]}" />',
            # MacBook open lid / display (x=306..390, y=236..288)
            f'<rect x="306" y="236" width="84" height="52" fill="{P["mac_edge"]}" />',
            f'<rect x="308" y="238" width="80" height="48" fill="{P["mac_dark"]}" />',
            f'<rect x="312" y="242" width="72" height="40" fill="{P["mac_screen"]}" />',
            # Subtle static terminal / desktop UI on MacBook (NOT movie credits)
            f'<rect x="316" y="246" width="18" height="3" fill="#64aee9" />',
            f'<rect x="336" y="246" width="4" height="3" fill="#93c8b2" />',
            f'<rect x="316" y="254" width="40" height="2" fill="{P["window_star"]}" />',
            f'<rect x="316" y="260" width="54" height="2" fill="#35527a" />',
            f'<rect x="316" y="266" width="32" height="2" fill="{P["window_star"]}" />',
            f'<rect x="316" y="272" width="46" height="2" fill="#35527a" />',
            # MacBook aluminum unibody base & keyboard deck (x=298..398, y=288..298)
            f'<rect x="298" y="288" width="100" height="6" fill="{P["mac_aluminum"]}" />',
            f'<rect x="312" y="288" width="72" height="2" fill="{P["mac_dark"]}" />',
            f'<rect x="298" y="294" width="100" height="4" fill="{P["mac_edge"]}" />',
            f'<rect x="342" y="294" width="12" height="2" fill="{P["mac_dark"]}" />',
        ]
    )


def _render_external_monitor_shell() -> str:
    """Render external monitor stand, bezel, and backdrop behind the movie-credit screen."""
    sx, sy, sw, sh = MONITOR_SCREEN_BOX
    return "\n    ".join(
        [
            # Monitor stand neck & wide flat base resting on desk (y=298)
            f'<rect x="538" y="286" width="28" height="8" fill="{P["monitor_stand"]}" />',
            f'<rect x="508" y="294" width="88" height="4" fill="{P["monitor_base"]}" />',
            # Outer bezel & inner dark bevel (x=414..686, y=122..286)
            f'<rect x="414" y="122" width="272" height="164" fill="{P["monitor_outer"]}" />',
            f'<rect x="420" y="128" width="260" height="152" fill="{P["monitor_inner"]}" />',
            # Power indicator LED dot on bottom bezel chin
            f'<rect x="668" y="282" width="4" height="2" fill="{P["credit_repo"]}" />',
            # Deep cinema screen backdrop
            f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{P["screen_bg"]}" />',
        ]
    )


def _render_mug_and_chair() -> str:
    """Render coffee mug on right desk edge and non-occluding foreground chair."""
    return "\n    ".join(
        [
            # Coffee mug with hollow handle and steam right of external monitor (x=694..722)
            f'<rect x="694" y="276" width="22" height="22" fill="{P["mug_cream"]}" />',
            f'<rect x="712" y="276" width="4" height="22" fill="{P["mug_shadow"]}" />',
            f'<rect x="716" y="280" width="6" height="3" fill="{P["mug_cream"]}" />',
            f'<rect x="719" y="283" width="3" height="7" fill="{P["mug_cream"]}" />',
            f'<rect x="716" y="290" width="6" height="3" fill="{P["mug_cream"]}" />',
            # Subtle rising pixel steam
            f'<rect x="700" y="264" width="2" height="6" fill="{P["mug_cream"]}" fill-opacity="0.35" />',
            f'<rect x="708" y="260" width="2" height="8" fill="{P["mug_cream"]}" fill-opacity="0.35" />',
            # T-shaped desk chair positioned cleanly below y=306 (zero monitor overlap)
            f'<rect x="524" y="306" width="56" height="32" fill="{P["chair_main"]}" />',
            f'<rect x="528" y="306" width="48" height="4" fill="{P["chair_highlight"]}" />',
            f'<rect x="514" y="338" width="76" height="14" fill="{P["chair_highlight"]}" />',
            f'<rect x="514" y="348" width="76" height="4" fill="{P["chair_shadow"]}" />',
            f'<rect x="546" y="352" width="12" height="42" fill="{P["chair_main"]}" />',
            f'<rect x="526" y="394" width="52" height="8" fill="{P["chair_shadow"]}" />',
        ]
    )


def _render_indoor_plants(include_second_plant: bool) -> str:
    """Render 1-2 subtle indoor pixel plants without cluttering the Mac setup."""
    parts = [
        # Plant 1: Floor plant beside left of desk (x=114..174, base at y=404)
        f'<rect x="122" y="354" width="42" height="10" fill="{P["plant_pot"]}" />',
        f'<rect x="126" y="364" width="34" height="4" fill="{P["plant_pot_rim"]}" />',
        f'<rect x="126" y="368" width="34" height="36" fill="{P["plant_pot"]}" />',
        f'<rect x="140" y="282" width="6" height="72" fill="{P["plant_leaf"]}" />',
        f'<rect x="146" y="290" width="24" height="10" fill="{P["plant_leaf"]}" />',
        f'<rect x="146" y="300" width="24" height="2" fill="{P["plant_leaf_dark"]}" />',
        f'<rect x="116" y="308" width="24" height="10" fill="{P["plant_leaf"]}" />',
        f'<rect x="116" y="318" width="24" height="2" fill="{P["plant_leaf_dark"]}" />',
        f'<rect x="146" y="324" width="20" height="10" fill="{P["plant_leaf"]}" />',
        f'<rect x="146" y="334" width="20" height="2" fill="{P["plant_leaf_dark"]}" />',
    ]
    if include_second_plant:
        # Plant 2: Small subtle potted succulent on left end of bottom right shelf (y=279)
        parts.extend(
            [
                f'<rect x="780" y="261" width="24" height="4" fill="{P["plant_pot"]}" />',
                f'<rect x="782" y="265" width="20" height="14" fill="{P["plant_pot_rim"]}" />',
                f'<rect x="784" y="267" width="16" height="12" fill="{P["plant_pot"]}" />',
                f'<rect x="788" y="245" width="8" height="16" fill="{P["plant_leaf"]}" />',
                f'<rect x="780" y="251" width="8" height="10" fill="{P["plant_leaf_dark"]}" />',
                f'<rect x="796" y="251" width="8" height="10" fill="{P["plant_leaf"]}" />',
            ]
        )
    return "\n    ".join(parts)


def _render_clock_shelves_and_cat() -> str:
    """Render wall clock, two bookshelves with language books, and sleeping cat."""
    return "\n    ".join(
        [
            # Wall clock (top right, cx=860, cy=73, r=27)
            f'<circle cx="860" cy="73" r="30" fill="{P["window_frame"]}" />',
            f'<circle cx="860" cy="73" r="26" fill="{P["cream"]}" />',
            f'<line x1="860" y1="73" x2="848" y2="63" stroke="{P["window_frame"]}" stroke-width="3" stroke-linecap="square" />',
            f'<line x1="860" y1="73" x2="874" y2="59" stroke="{P["window_frame"]}" stroke-width="3" stroke-linecap="square" />',
            # Top & bottom right bookshelves (x=762..948)
            f'<rect x="762" y="198" width="186" height="8" fill="{P["wood_top"]}" />',
            f'<rect x="762" y="206" width="186" height="4" fill="{P["wood_shadow"]}" />',
            f'<rect x="762" y="279" width="186" height="8" fill="{P["wood_top"]}" />',
            f'<rect x="762" y="287" width="186" height="4" fill="{P["wood_shadow"]}" />',
            # 4 language books on top shelf
            f'<rect x="768" y="156" width="30" height="42" fill="{P["book_blue"]}" />',
            f'<rect x="768" y="164" width="30" height="3" fill="#4f8fc4" />',
            f'<rect x="802" y="158" width="18" height="40" fill="{P["book_red"]}" />',
            f'<rect x="824" y="150" width="10" height="48" fill="{P["book_blue"]}" />',
            f'<rect x="838" y="158" width="10" height="40" fill="{P["book_yellow"]}" />',
            f'<rect x="852" y="166" width="12" height="32" fill="{P["book_cream"]}" />',
            # Sleeping orange cat on right floor (x=770..872, resting at y=404)
            f'<rect x="764" y="388" width="26" height="8" fill="{P["cat_body"]}" />',
            f'<rect x="790" y="376" width="56" height="28" fill="{P["cat_body"]}" />',
            f'<rect x="798" y="384" width="34" height="4" fill="{P["cat_stripe"]}" />',
            # Cat head & pixel ears
            f'<rect x="846" y="366" width="26" height="30" fill="{P["cat_body"]}" />',
            f'<rect x="846" y="358" width="8" height="8" fill="{P["cat_body"]}" />',
            f'<rect x="864" y="358" width="8" height="8" fill="{P["cat_body"]}" />',
            f'<rect x="866" y="378" width="4" height="4" fill="{P["cat_stripe"]}" />',
            # Subtle sleep 'z' pixel glyph above cat
            f'<rect x="894" y="330" width="8" height="2" fill="{P["wall_stripe"]}" />',
            f'<rect x="898" y="332" width="4" height="2" fill="{P["wall_stripe"]}" />',
            f'<rect x="894" y="334" width="8" height="2" fill="{P["wall_stripe"]}" />',
        ]
    )


def render_workspace_room_layers(config: ProfileConfig) -> dict[str, str]:
    """Render static pixel-art room background and foreground layers around the monitor."""
    background = "\n    ".join(
        [
            _render_wall_and_floor(),
            _render_window(),
            _render_name_plaque(config.display_name),
            _render_desk_and_lamp(),
            _render_macbook_and_cable(),
            _render_external_monitor_shell(),
            _render_clock_shelves_and_cat(),
            _render_indoor_plants(config.include_second_plant),
        ]
    )
    foreground = _render_mug_and_chair()
    _ = WORKSPACE_HEIGHT
    return {"background": background, "foreground": foreground}
