import socket
import time
import math
import colorsys

IP = "127.0.0.1"
PORT = 6454
UNIVERSE = 0
WIDTH = 8
HEIGHT = 6
BRIGHTNESS = 0.35
FPS = 25
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_frame(data):
    packet = (
        b"Art-Net\x00" + bytes([0x00, 0x50]) + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00]) + UNIVERSE.to_bytes(2, "little")
        + len(data).to_bytes(2, "big") + bytes(data)
    )
    sock.sendto(packet, (IP, PORT))

def zone_at(x, y):
    return (HEIGHT - 1 - y) * WIDTH + (WIDTH - 1 - x)

try:
    print("Phreqed psychedelic wave running. Ctrl+C to stop.")
    start = time.monotonic()
    while True:
        t = time.monotonic() - start
        channels = [0] * 512
        for y in range(HEIGHT):
            for x in range(WIDTH):
                zone = zone_at(x, y)
                wave = math.sin(x * 0.75 + y * 0.5 - t * 2)
                hue = (t * 0.08 + x / WIDTH * 0.6
                       + y / HEIGHT * 0.3 + wave * 0.08) % 1
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, BRIGHTNESS)
                offset = zone * 3
                channels[offset] = int(r * 255)
                channels[offset + 1] = int(g * 255)
                channels[offset + 2] = int(b * 255)
        send_frame(channels)
        time.sleep(1 / FPS)
except KeyboardInterrupt:
    print("\nStopping.")
finally:
    send_frame([0] * 512)
    sock.close()
