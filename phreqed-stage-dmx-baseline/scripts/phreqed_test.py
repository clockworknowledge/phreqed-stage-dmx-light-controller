import socket
import time

ARTNET_IP = "127.0.0.1"
ARTNET_PORT = 6454
UNIVERSE = 0
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_dmx(channels):
    packet = (
        b"Art-Net\x00" + bytes([0x00, 0x50]) + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00]) + UNIVERSE.to_bytes(2, "little")
        + len(channels).to_bytes(2, "big") + bytes(channels)
    )
    sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))

def show_colour(r, g, b):
    channels = [0] * 512
    channels[0:3] = [r, g, b]
    channels[3:6] = [r, g, b]
    send_dmx(channels)

try:
    while True:
        for name, colour in [
            ("RED", (100, 0, 0)),
            ("GREEN", (0, 100, 0)),
            ("BLUE", (0, 0, 100)),
        ]:
            print(name, flush=True)
            for _ in range(20):
                show_colour(*colour)
                time.sleep(0.05)
except KeyboardInterrupt:
    print("\nStopping")
finally:
    show_colour(0, 0, 0)
    sock.close()
