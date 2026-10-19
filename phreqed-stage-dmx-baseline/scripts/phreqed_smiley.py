import socket
import time

IP = "127.0.0.1"
PORT = 6454
UNIVERSE = 0
WIDTH = 8
HEIGHT = 6
BRIGHTNESS = 65
SMILEY = [
    "........",
    ".##..##.",
    ".##..##.",
    "........",
    ".#....#.",
    "..####..",
]
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def zone_at(x, y):
    return (HEIGHT - 1 - y) * WIDTH + (WIDTH - 1 - x)

def send_artnet(channels):
    packet = (
        b"Art-Net\x00" + bytes([0x00, 0x50]) + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00]) + UNIVERSE.to_bytes(2, "little")
        + len(channels).to_bytes(2, "big") + bytes(channels)
    )
    sock.sendto(packet, (IP, PORT))

def draw_smiley():
    channels = [0] * 512
    for y, row in enumerate(SMILEY):
        for x, pixel in enumerate(row):
            if pixel == "#":
                zone = zone_at(x, y)
                offset = zone * 3
                channels[offset] = 0
                channels[offset + 1] = BRIGHTNESS
                channels[offset + 2] = BRIGHTNESS
    return channels

try:
    print("PHREQED SMILEY TEST - Cube A only. Ctrl+C to stop")
    frame = draw_smiley()
    while True:
        send_artnet(frame)
        time.sleep(0.05)
except KeyboardInterrupt:
    print("\nStopping")
finally:
    for _ in range(5):
        send_artnet([0] * 512)
        time.sleep(0.05)
    sock.close()
