import socket
import time
import colorsys

IP = "127.0.0.1"
PORT = 6454
UNIVERSE = 0
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
CUBE_A = 0
CUBE_B = 152
ZONES = 48

def send(channels):
    packet = (
        b"Art-Net\x00" + bytes([0x00, 0x50]) + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00]) + UNIVERSE.to_bytes(2, "little")
        + len(channels).to_bytes(2, "big") + bytes(channels)
    )
    sock.sendto(packet, (IP, PORT))

def fill_cube(channels, offset, r, g, b):
    for zone in range(ZONES):
        i = offset + zone * 3
        channels[i:i+3] = [r, g, b]

def hold(channels, seconds=3):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        send(channels)
        time.sleep(0.05)

try:
    print("TEST 1: Cube A RED, Cube B OFF")
    frame = [0] * 512
    fill_cube(frame, CUBE_A, 90, 0, 0)
    hold(frame)
    print("TEST 2: Cube A OFF, Cube B BLUE")
    frame = [0] * 512
    fill_cube(frame, CUBE_B, 0, 0, 90)
    hold(frame)
    print("TEST 3: Both cubes GREEN")
    frame = [0] * 512
    fill_cube(frame, CUBE_A, 0, 90, 0)
    fill_cube(frame, CUBE_B, 0, 90, 0)
    hold(frame)
    print("TEST 4: Mirrored rainbow")
    start = time.monotonic()
    while time.monotonic() - start < 12:
        t = time.monotonic() - start
        frame = [0] * 512
        for zone in range(ZONES):
            hue = (zone / ZONES + t * 0.1) % 1
            r, g, b = colorsys.hsv_to_rgb(hue, 1, 0.35)
            colour = [int(r * 255), int(g * 255), int(b * 255)]
            for offset in (CUBE_A, CUBE_B):
                i = offset + zone * 3
                frame[i:i+3] = colour
        send(frame)
        time.sleep(0.04)
    print("Test complete.")
except KeyboardInterrupt:
    print("\nInterrupted.")
finally:
    for _ in range(3):
        send([0] * 512)
        time.sleep(0.05)
    sock.close()
