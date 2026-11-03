"""Procedural 2D Animated GIF Sprite Generator for Project CYN.

Generates 9 transparent background animated GIFs conforming to Section 2:
1. cyn_idle.gif: Neutral uncanny standing loop, slight breathing sway.
2. cyn_tilt_head.gif: Snaps head 45 degrees to the side.
3. cyn_glitch.gif: Rapid shaking, frame-drop jitter, scanline distortion.
4. cyn_solver_x.gif: Yellow Absolute Solver cross glowing across eyes/visor.
5. cyn_creepy_smile.gif: Unnaturally wide, rigid porcelain smile.
6. cyn_curtsy.gif: Stiff, robotic maid bow / curtsy.
7. cyn_reach.gif: Hand extends forward touching the desktop screen glass.
8. cyn_inspect.gif: Leans down close to inspect code or screen details.
9. cyn_sleep.gif: Slumped forward, eye display shut off (dormant mode).
"""

from __future__ import annotations

import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw

ROOT_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT_DIR / "assets" / "cyn"
WEB_ASSETS_DIR = ROOT_DIR / "web_avatar" / "assets" / "cyn"
ANDROID_ASSETS_DIR = ROOT_DIR / "android_companion" / "app" / "src" / "main" / "assets" / "cyn"

WIDTH = 256
HEIGHT = 256
TOTAL_FRAMES = 10

# Color Palette (Absolute Solver Drone Maid)
AMBER = (255, 204, 0, 255)
AMBER_GLOW = (255, 230, 80, 255)
AMBER_DIM = (160, 120, 0, 255)
CHASSIS_WHITE = (235, 238, 245, 255)
CHASSIS_SHADOW = (180, 185, 195, 255)
VISOR_BLACK = (10, 12, 16, 255)
HAIR_SILVER = (75, 80, 92, 255)
DRESS_BLACK = (24, 26, 32, 255)
APRON_WHITE = (225, 228, 235, 255)
RIBBON_DARK = (16, 18, 22, 255)


def create_frame(state_name: str, frame_idx: int, total_frames: int) -> Image.Image:
    """Render a single frame for a given state with true RGBA transparency."""
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    t = frame_idx / total_frames
    phase = t * 2 * math.pi

    # Base transforms
    sway_y = math.sin(phase) * 3.0
    sway_x = math.sin(phase * 0.5) * 1.5
    head_rot = 0.0
    head_offset_x = 0.0
    head_offset_y = 0.0

    # State-specific adjustments
    if state_name == "cyn_idle":
        pass
    elif state_name == "cyn_tilt_head":
        head_rot = 35.0 + math.sin(phase) * 5.0
        head_offset_x = 12.0
        head_offset_y = -4.0
    elif state_name == "cyn_glitch":
        sway_x += random.uniform(-7, 7)
        sway_y += random.uniform(-6, 6)
        head_offset_x += random.uniform(-8, 8)
        head_offset_y += random.uniform(-7, 7)
    elif state_name == "cyn_solver_x":
        sway_y = math.sin(phase) * 1.5
    elif state_name == "cyn_creepy_smile":
        sway_x = math.sin(phase) * 2.0
        head_rot = 12.0 + math.sin(phase) * 3.0
    elif state_name == "cyn_curtsy":
        # Dip down and up
        dip = math.sin(phase) * 12.0
        sway_y += max(0, dip)
    elif state_name == "cyn_reach":
        sway_y = math.sin(phase) * 2.0
    elif state_name == "cyn_inspect":
        sway_y += 14.0 + math.sin(phase) * 2.0
        sway_x += math.sin(phase) * 4.0
    elif state_name == "cyn_sleep":
        sway_y += 18.0
        head_offset_y += 8.0

    cx = WIDTH // 2 + sway_x
    cy = HEIGHT // 2 + sway_y

    # 1. Torso & Maid Dress
    body_y = cy + 42
    # Dress skirt/skirt drape
    skirt_w = 64
    if state_name == "cyn_curtsy":
        skirt_w += 14  # flare skirt outward
    draw.polygon([
        (cx - 30, body_y),
        (cx + 30, body_y),
        (cx + skirt_w, body_y + 80),
        (cx - skirt_w, body_y + 80),
    ], fill=DRESS_BLACK)

    # Apron bib
    draw.polygon([
        (cx - 18, body_y - 2),
        (cx + 18, body_y - 2),
        (cx + 26, body_y + 60),
        (cx - 26, body_y + 60),
    ], fill=APRON_WHITE)

    # Solver Armband on left arm
    draw.rectangle([cx - 38, body_y + 12, cx - 28, body_y + 24], fill=AMBER)

    # 2. Arms & Hands
    if state_name == "cyn_reach":
        # Left arm neutral
        draw.line([(cx - 30, body_y + 6), (cx - 42, body_y + 40)], fill=CHASSIS_WHITE, width=7)
        # Right arm reaching forward toward screen glass (oversized foreground claw)
        reach_t = 0.5 + 0.5 * math.sin(phase)
        claw_x = cx + 32 + reach_t * 12
        claw_y = cy + 18 + reach_t * 6
        draw.line([(cx + 26, body_y + 6), (claw_x, claw_y)], fill=CHASSIS_WHITE, width=9)
        # Metallic fingers touching glass
        for i, off in enumerate([-12, -4, 4, 12]):
            draw.line([(claw_x, claw_y), (claw_x + 14 + i * 2, claw_y - 8 + off)], fill=AMBER, width=3)
        # Glass contact ripple
        draw.ellipse([claw_x + 6, claw_y - 14, claw_x + 28, claw_y + 14], outline=AMBER_GLOW, width=2)
    elif state_name == "cyn_curtsy":
        # Both hands holding skirt sides
        draw.line([(cx - 28, body_y + 8), (cx - skirt_w + 4, body_y + 62)], fill=CHASSIS_WHITE, width=6)
        draw.line([(cx + 28, body_y + 8), (cx + skirt_w - 4, body_y + 62)], fill=CHASSIS_WHITE, width=6)
    else:
        # Default maid idle arms
        draw.line([(cx - 28, body_y + 8), (cx - 36, body_y + 50)], fill=CHASSIS_WHITE, width=6)
        draw.line([(cx + 28, body_y + 8), (cx + 36, body_y + 50)], fill=CHASSIS_WHITE, width=6)
        draw.ellipse([cx - 40, body_y + 46, cx - 32, body_y + 56], fill=CHASSIS_SHADOW)
        draw.ellipse([cx + 32, body_y + 46, cx + 40, body_y + 56], fill=CHASSIS_SHADOW)

    # Collar & Maid Bow
    draw.polygon([(cx - 16, body_y), (cx + 16, body_y), (cx, body_y + 12)], fill=APRON_WHITE)
    draw.polygon([(cx - 8, body_y + 4), (cx + 8, body_y + 4), (cx, body_y + 10)], fill=RIBBON_DARK)

    # 3. Articulated Drone Spine Neck
    neck_x = cx + head_offset_x * 0.4
    neck_y = cy + 24 + head_offset_y * 0.4
    for i in range(3):
        ny = neck_y + i * 5
        draw.rectangle([neck_x - 6, ny, neck_x + 6, ny + 3], fill=CHASSIS_SHADOW)

    # 4. Head, Hair, & Visor (Centered at hx, hy)
    hx = cx + head_offset_x
    hy = cy - 14 + head_offset_y

    # Back hair volume
    draw.ellipse([hx - 48, hy - 46, hx + 48, hy + 46], fill=HAIR_SILVER)

    # Drone Head Chassis (sleek porcelain rounded cube)
    draw.rounded_rectangle([hx - 36, hy - 32, hx + 36, hy + 30], radius=16, fill=CHASSIS_WHITE, outline=CHASSIS_SHADOW, width=2)

    # Maid Headband & Bonnet Frills
    draw.arc([hx - 42, hy - 44, hx + 42, hy - 14], start=180, end=360, fill=APRON_WHITE, width=8)
    for fx in range(int(hx - 38), int(hx + 40), 9):
        draw.ellipse([fx - 4, hy - 40, fx + 4, hy - 32], fill=APRON_WHITE)
    # Bonnet yellow accents
    draw.rectangle([hx - 32, hy - 34, hx - 26, hy - 28], fill=AMBER)
    draw.rectangle([hx + 26, hy - 34, hx + 32, hy - 28], fill=AMBER)

    # Hair bangs & side hair strands
    draw.polygon([(hx - 36, hy - 24), (hx - 12, hy - 6), (hx - 24, hy + 18), (hx - 42, hy + 12)], fill=HAIR_SILVER)
    draw.polygon([(hx + 36, hy - 24), (hx + 12, hy - 6), (hx + 24, hy + 18), (hx + 42, hy + 12)], fill=HAIR_SILVER)
    draw.polygon([(hx - 18, hy - 26), (hx + 6, hy - 10), (hx - 4, hy - 26)], fill=HAIR_SILVER)

    # Hair Ribbons
    draw.polygon([(hx - 38, hy - 14), (hx - 50, hy - 22), (hx - 46, hy - 4)], fill=RIBBON_DARK)
    draw.polygon([(hx + 38, hy - 14), (hx + 50, hy - 22), (hx + 46, hy - 4)], fill=RIBBON_DARK)

    # Black Visor Screen
    vx1, vy1 = hx - 28, hy - 12
    vx2, vy2 = hx + 28, hy + 18
    draw.rounded_rectangle([vx1, vy1, vx2, vy2], radius=10, fill=VISOR_BLACK, outline=(30, 35, 45, 255), width=2)

    # 5. Visor Display Optics (State Specific)
    draw_visor_display(draw, state_name, hx, hy, t, phase)

    # 6. Mouth / Creepy Smile / Expressions
    if state_name == "cyn_creepy_smile":
        # Unnaturally wide sharp porcelain smile
        mx = hx
        my = hy + 23
        draw.arc([mx - 22, my - 6, mx + 22, my + 8], start=10, end=170, fill=CHASSIS_SHADOW, width=2)
        draw.polygon([(mx - 18, my - 1), (mx + 18, my - 1), (mx, my + 7)], fill=(255, 255, 255, 255))
        # Stitch/tooth lines
        for tx in range(int(mx - 14), int(mx + 16), 5):
            draw.line([(tx, my), (tx, my + 4)], fill=(40, 45, 55, 255), width=1)
    elif state_name != "cyn_sleep":
        # Tiny subtle neutral mouth line
        draw.line([(hx - 4, hy + 23), (hx + 4, hy + 23)], fill=(120, 125, 135, 255), width=1)

    # 7. Post-Processing Glitch Scanlines
    if state_name == "cyn_glitch":
        for _ in range(7):
            gy = random.randint(0, HEIGHT - 4)
            gh = random.randint(2, 6)
            gcol = random.choice([
                (255, 204, 0, 180),
                (0, 240, 255, 150),
                (255, 40, 90, 160),
                (255, 255, 255, 220),
            ])
            gx_start = random.randint(0, 40)
            gx_end = random.randint(WIDTH - 50, WIDTH)
            draw.rectangle([gx_start, gy, gx_end, gy + gh], fill=gcol)

    return img


def draw_visor_display(draw: ImageDraw.ImageDraw, state: str, hx: float, hy: float, t: float, phase: float) -> None:
    """Render the animated digital optical display on the visor."""
    eye_y = hy + 2

    if state == "cyn_idle":
        # Gentle pulsating round drone optics
        pulse = 1.0 + 0.15 * math.sin(phase)
        r = 5.5 * pulse
        # Left eye
        draw.ellipse([hx - 15 - r, eye_y - r, hx - 15 + r, eye_y + r], fill=AMBER)
        draw.ellipse([hx - 15 - r * 0.4, eye_y - r * 0.4, hx - 15 + r * 0.4, eye_y + r * 0.4], fill=AMBER_GLOW)
        # Right eye
        draw.ellipse([hx + 15 - r, eye_y - r, hx + 15 + r, eye_y + r], fill=AMBER)
        draw.ellipse([hx + 15 - r * 0.4, eye_y - r * 0.4, hx + 15 + r * 0.4, eye_y + r * 0.4], fill=AMBER_GLOW)

    elif state == "cyn_tilt_head":
        # Inquiring squint / focused amber rings
        r = 6.0
        draw.ellipse([hx - 15 - r, eye_y - r, hx - 15 + r, eye_y + r], outline=AMBER, width=2)
        draw.ellipse([hx - 15 - 2, eye_y - 2, hx - 15 + 2, eye_y + 2], fill=AMBER_GLOW)
        draw.ellipse([hx + 15 - r, eye_y - r, hx + 15 + r, eye_y + r], outline=AMBER, width=2)
        draw.ellipse([hx + 15 - 2, eye_y - 2, hx + 15 + 2, eye_y + 2], fill=AMBER_GLOW)

    elif state == "cyn_solver_x":
        # Absolute Solver yellow glowing Cross / Spokes
        glow_size = 14 + math.sin(phase) * 2.5
        # Orbital solver ring
        draw.ellipse([hx - glow_size, eye_y - glow_size, hx + glow_size, eye_y + glow_size], outline=AMBER, width=2)
        # Cross spokes (X)
        d = glow_size * 0.72
        draw.line([(hx - d, eye_y - d), (hx + d, eye_y + d)], fill=AMBER_GLOW, width=3)
        draw.line([(hx + d, eye_y - d), (hx - d, eye_y + d)], fill=AMBER_GLOW, width=3)
        # Vertical spine spoke
        draw.line([(hx, eye_y - glow_size * 1.15), (hx, eye_y + glow_size * 1.15)], fill=AMBER, width=2)
        # Central core
        draw.ellipse([hx - 3, eye_y - 3, hx + 3, eye_y + 3], fill=(255, 255, 255, 255))

    elif state == "cyn_creepy_smile":
        # Curved happy visor arcs
        draw.arc([hx - 20, eye_y - 6, hx - 8, eye_y + 6], start=190, end=350, fill=AMBER, width=3)
        draw.arc([hx + 8, eye_y - 6, hx + 20, eye_y + 6], start=190, end=350, fill=AMBER, width=3)

    elif state == "cyn_inspect":
        # Scanning laser bar moving across visor
        scan_y = eye_y - 8 + ((t * 2.5) % 1.0) * 16
        draw.line([(hx - 22, scan_y), (hx + 22, scan_y)], fill=AMBER_GLOW, width=3)
        # Magnified optical reticles
        draw.ellipse([hx - 15 - 8, eye_y - 8, hx - 15 + 8, eye_y + 8], outline=AMBER, width=2)
        draw.ellipse([hx + 15 - 8, eye_y - 8, hx + 15 + 8, eye_y + 8], outline=AMBER, width=2)

    elif state == "cyn_curtsy":
        # Polite downward angled crescents
        draw.arc([hx - 19, eye_y - 3, hx - 9, eye_y + 7], start=20, end=160, fill=AMBER, width=3)
        draw.arc([hx + 9, eye_y - 3, hx + 19, eye_y + 7], start=20, end=160, fill=AMBER, width=3)

    elif state == "cyn_sleep":
        # Power-off sleeping horizontal dashes
        dim_pulse = 0.5 + 0.3 * math.sin(phase)
        c = int(140 * dim_pulse)
        sleep_amber = (c, int(c * 0.8), 0, 200)
        draw.line([(hx - 18, eye_y + 2), (hx - 10, eye_y + 2)], fill=sleep_amber, width=2)
        draw.line([(hx + 10, eye_y + 2), (hx + 18, eye_y + 2)], fill=sleep_amber, width=2)

    elif state == "cyn_glitch":
        # Fragmented glitch lines and shifted eyes
        ox = random.choice([-5, -2, 3, 6])
        oy = random.choice([-3, 0, 4])
        draw.line([(hx - 18 + ox, eye_y + oy), (hx - 8 + ox, eye_y + oy)], fill=(255, 0, 80, 255), width=3)
        draw.line([(hx + 8 - ox, eye_y - oy), (hx + 18 - ox, eye_y - oy)], fill=(0, 255, 255, 255), width=3)
        draw.line([(hx - 14, eye_y - 4), (hx + 14, eye_y + 4)], fill=AMBER, width=2)

    else:
        # Default eyes
        draw.ellipse([hx - 18, eye_y - 4, hx - 10, eye_y + 4], fill=AMBER)
        draw.ellipse([hx + 10, eye_y - 4, hx + 18, eye_y + 4], fill=AMBER)


def save_animated_gif(frames: list[Image.Image], output_path: Path, duration_ms: int = 110) -> None:
    """Save frames into an optimized animated GIF with transparent background."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert frames to palette mode preserving transparent color
    paletted_frames = []
    for f in frames:
        # Create an empty palette image with alpha preserved
        alpha = f.split()[3]
        # Mask out completely transparent pixels
        p_frame = f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        # Add transparent color index
        mask = Image.eval(alpha, lambda a: 255 if a <= 128 else 0)
        p_frame.paste(255, mask)
        paletted_frames.append(p_frame)

    paletted_frames[0].save(
        output_path,
        save_all=True,
        append_images=paletted_frames[1:],
        duration=duration_ms,
        loop=0,
        transparency=255,
        disposal=2,
    )
    print(f"Generated: {output_path.name} -> {output_path}")


def main():
    states = [
        "cyn_idle",
        "cyn_tilt_head",
        "cyn_glitch",
        "cyn_solver_x",
        "cyn_creepy_smile",
        "cyn_curtsy",
        "cyn_reach",
        "cyn_inspect",
        "cyn_sleep",
    ]

    print(f"Generating 9 CYN 2D Animated Transparent GIFs ({WIDTH}x{HEIGHT})...")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    WEB_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    ANDROID_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for state in states:
        frames = [create_frame(state, i, TOTAL_FRAMES) for i in range(TOTAL_FRAMES)]
        out_file = ASSETS_DIR / f"{state}.gif"
        save_animated_gif(frames, out_file)

        # Copy to web_avatar assets and android companion assets
        import shutil
        shutil.copy(out_file, WEB_ASSETS_DIR / f"{state}.gif")
        shutil.copy(out_file, ANDROID_ASSETS_DIR / f"{state}.gif")

    print("\nAll 9 CYN 2D Animated GIFs generated and synchronized across all target platforms successfully!")


if __name__ == "__main__":
    main()
