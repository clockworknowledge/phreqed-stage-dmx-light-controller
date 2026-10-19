import socket
import time

ARTNET_IP = "127.0.0.1"
ARTNET_PORT = 6454
UNIVERSE = 0
NUM_ZONES = 48
BRIGHTNESS = 90
HOLD_SECONDS = 1.5
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_dmx(channels):
    packet = (
        b"Art-Net\x00" + bytes([0x00, 0x50]) + bytes([0x00, 0x0E])
        + bytes([0x00, 0x00]) + UNIVERSE.to_bytes(2, "little")
        + len(channels).to_bytes(2, "big") + bytes(channels)
    )
    sock.sendto(packet, (ARTNET_IP, ARTNET_PORT))

def show_zone(zone):
    channels = [0] * 512
    offset = zone * 3
    channels[offset] = BRIGHTNESS
    return channels

def transmit_for(channels, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        send_dmx(channels)
        time.sleep(0.05)

try:
    print("Phreqed LF4808 Zone Mapper. Ctrl+C to stop.")
    while True:
        for zone in range(NUM_ZONES):
            print(f"Zone {zone + 1:02d} DMX {zone * 3 + 1}-{zone * 3 + 3}", flush=True)
            transmit_for(show_zone(zone), HOLD_SECONDS)
except KeyboardInterrupt:
    print("\nStopping zone mapper.")
finally:
    send_dmx([0] * 512)
    sock.close()
