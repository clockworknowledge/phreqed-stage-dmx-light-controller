import socket
import time
import math
import colorsys
import select
import sys
import termios
import tty

# PHREQED VISUAL ENGINE v2
# Two Betopper LF4808 fixtures in 152-channel mode
# Cube A: A001, Cube B: A153

IP = "127.0.0.1"
PORT = 6454
UNIVERSE = 0
WIDTH = 8
HEIGHT = 6
ZONES = WIDTH * HEIGHT
FPS = 25
CUBE_A = 0
CUBE_B = 152
brightness = 0.35
speed = 1.0
mode = "MIRROR"
effect_a = 1
effect_b = 2
blackout = False
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def clamp(value):
    return max(0, min(255, int(value)))

def rgb(h, s=1.0, v=1.0):
    return colorsys.hsv_to_rgb(h % 1.0, s, v)

def zone_at(x, y):
    # Front view: zone 1 at bottom-right
    return (HEIGHT - 1 - y) * WIDTH + (WIDTH - 1 - x)

def send_artnet(channels):
    packet = (
        b"Art-Net\x00"
        + bytes([0x00, 0x50])
        + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00])
        + UNIVERSE.to_bytes(2, "little")
        + len(channels).to_bytes(2, "big")
        + bytes(channels)
    )
    sock.sendto(packet, (IP, PORT))

def plasma(x, y, t):
    a = math.sin(x * 0.85 + t)
    b = math.sin(y * 1.1 - t * 0.8)
    c = math.sin((x + y) * 0.65 + t * 0.5)
    hue = (a + b + c) / 6 + 0.5
    return rgb(hue)

def tunnel(x, y, t):
    cx = (WIDTH - 1) / 2
    cy = (HEIGHT - 1) / 2
    distance = math.hypot(x - cx, y - cy)
    wave = math.sin(distance * 2.5 - t * 4)
    hue = (distance * 0.12 - t * 0.12) % 1
    intensity = 0.15 + 0.85 * ((wave + 1) / 2)
    return rgb(hue, 1.0, intensity)

def pulse(x, y, t):
    intensity = ((math.sin(t * 3) + 1) / 2) ** 3
    hue = (t * 0.035) % 1
    return rgb(hue, 1.0, intensity)

def chase(x, y, t):
    position = y * WIDTH + x
    head = int(t * 10) % ZONES
    distance = (head - position) % ZONES
    if distance < 7:
        intensity = (1 - distance / 7) ** 2
        hue = (t * 0.05 + position / ZONES) % 1
        return rgb(hue, 1.0, intensity)
    return (0, 0, 0)

def cross_cube(x, y, t, cube):
    # Virtual 16x6 display: Cube A left, Cube B right
    global_x = x if cube == 0 else x + WIDTH
    position = y * (WIDTH * 2) + global_x
    total = ZONES * 2
    head = int(t * 15) % total
    distance = (head - position) % total
    if distance < 10:
        intensity = (1 - distance / 10) ** 2
        hue = (t * 0.06 + position / total) % 1
        return rgb(hue, 1.0, intensity)
    return (0, 0, 0)

EFFECTS = {
    1: ("PLASMA", plasma),
    2: ("TUNNEL", tunnel),
    3: ("PULSE", pulse),
    4: ("CHASE", chase),
}

def render_cube(channels, offset, effect_num, t, hue_offset=0.0, cube=0):
    for y in range(HEIGHT):
        for x in range(WIDTH):
            zone = zone_at(x, y)
            if effect_num == 5:
                r, g, b = cross_cube(x, y, t, cube)
            else:
                r, g, b = EFFECTS[effect_num][1](x, y, t)
            if hue_offset:
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                r, g, b = rgb(h + hue_offset, s, v)
            i = offset + zone * 3
            channels[i] = clamp(r * brightness * 255)
            channels[i + 1] = clamp(g * brightness * 255)
            channels[i + 2] = clamp(b * brightness * 255)

def render(t):
    channels = [0] * 512
    if blackout:
        return channels
    if effect_a == 5:
        render_cube(channels, CUBE_A, 5, t, cube=0)
        render_cube(channels, CUBE_B, 5, t, cube=1)
    elif mode == "MIRROR":
        render_cube(channels, CUBE_A, effect_a, t)
        render_cube(channels, CUBE_B, effect_a, t)
    elif mode == "COMPLEMENTARY":
        render_cube(channels, CUBE_A, effect_a, t)
        render_cube(channels, CUBE_B, effect_a, t + 1.5, hue_offset=0.5, cube=1)
    elif mode == "INDEPENDENT":
        render_cube(channels, CUBE_A, effect_a, t)
        render_cube(channels, CUBE_B, effect_b, t, cube=1)
    return channels

def effect_name(number):
    return "CROSS-CUBE" if number == 5 else EFFECTS[number][0]

def status():
    print(
        f"\rMode: {mode:14s} | A: {effect_name(effect_a):11s} "
        f"| B: {effect_name(effect_b):8s} "
        f"| Brightness: {brightness:.0%} | Speed: {speed:.1f}x "
        f"| {'BLACKOUT' if blackout else 'LIVE'}     ",
        end="", flush=True,
    )

def main():
    global mode, effect_a, effect_b, brightness, speed, blackout
    print("PHREQED VISUAL ENGINE v2")
    print("1-4 Effects | 5 Cross-cube")
    print("m Mirror | c Complementary | i Independent")
    print("n Next Cube B effect")
    print("+/- Brightness | [/] Speed")
    print("Space Blackout | q Quit")
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)
    animation_time = 0.0
    previous = time.monotonic()
    try:
        status()
        while True:
            now = time.monotonic()
            dt = min(now - previous, 0.1)
            previous = now
            animation_time += dt * speed
            if select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.read(1)
                if key in "12345":
                    effect_a = int(key)
                    status()
                elif key == "m":
                    mode = "MIRROR"
                    status()
                elif key == "c":
                    mode = "COMPLEMENTARY"
                    status()
                elif key == "i":
                    mode = "INDEPENDENT"
                    if effect_a == 5:
                        effect_a = 1
                    status()
                elif key == "n":
                    effect_b = (effect_b % 4) + 1
                    status()
                elif key in "+=":
                    brightness = min(1.0, brightness + 0.05)
                    status()
                elif key == "-":
                    brightness = max(0.0, brightness - 0.05)
                    status()
                elif key == "]":
                    speed = min(5.0, speed + 0.2)
                    status()
                elif key == "[":
                    speed = max(0.2, speed - 0.2)
                    status()
                elif key == " ":
                    blackout = not blackout
                    status()
                elif key.lower() == "q":
                    break
            send_artnet(render(animation_time))
            time.sleep(1 / FPS)
    finally:
        for _ in range(5):
            send_artnet([0] * 512)
            time.sleep(0.05)
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        sock.close()
        print("\nPhreqed Visual Engine stopped.")

if __name__ == "__main__":
    main()
