import socket
import time

# Experimental sprite animation: user reported poor visual recognizability.
IP = "127.0.0.1"
PORT = 6454
UNIVERSE = 0
WIDTH = 8
HEIGHT = 6
CUBE_OFFSETS = [0, 152]
FPS = 25
WALK_SPEED = 2.0
BRIGHTNESS = 100
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SPRITES = [
    [".###.", "..#..", ".###.", "..#..", ".#.#.", "#...#"],
    [".###.", "..#..", ".###.", "..#..", "..##.", ".#..#"],
    [".###.", "..#..", ".###.", "..#..", ".#.#.", "..#.."],
    [".###.", "..#..", ".###.", "..#..", ".##..", "#..#."],
]

def zone_at(x, y):
    return (HEIGHT - 1 - y) * WIDTH + (WIDTH - 1 - x)

def send_artnet(channels):
    packet = (
        b"Art-Net\x00" + bytes([0x00, 0x50]) + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00]) + UNIVERSE.to_bytes(2, "little")
        + len(channels).to_bytes(2, "big") + bytes(channels)
    )
    sock.sendto(packet, (IP, PORT))

def draw_pixel(frame, x, y, colour):
    if x < 0 or x >= 16 or y < 0 or y >= HEIGHT:
        return
    cube = 0 if x < 8 else 1
    local_x = x % 8
    zone = zone_at(local_x, y)
    offset = CUBE_OFFSETS[cube] + zone * 3
    frame[offset:offset + 3] = colour

def draw_sprite(frame, x_position, pose):
    for y, row in enumerate(SPRITES[pose]):
        for x, pixel in enumerate(row):
            if pixel == "#":
                draw_pixel(frame, x_position + x, y,
                           (0, BRIGHTNESS, BRIGHTNESS))

try:
    print("PHREQED WALKING STICKMAN (experimental). Ctrl+C to stop")
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        position = int(elapsed * WALK_SPEED) % 21 - 5
        pose = int(elapsed * 5) % len(SPRITES)
        frame = [0] * 512
        draw_sprite(frame, position, pose)
        send_artnet(frame)
        time.sleep(1 / FPS)
except KeyboardInterrupt:
    print("\nStopping")
finally:
    for _ in range(5):
        send_artnet([0] * 512)
        time.sleep(0.05)
    sock.close()
