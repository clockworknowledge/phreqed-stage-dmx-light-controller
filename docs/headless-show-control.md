# Headless show control

## Recommended control layout

Use two independent control paths:

1. Keep the Ampero connected to the Pi by USB as the performance controller.
   Scene navigation, tap tempo, and blackout then work without Wi-Fi.
2. Put the Pi and phone on a private stage LAN for setup, monitoring, parameter
   editing, and emergency browser control. Do not depend on venue internet or
   venue Wi-Fi.

The strongest production arrangement is a small dedicated router powered with
the lighting rig. Connect the Pi to it by Ethernet and the phone to its private
Wi-Fi. Reserve `10.42.0.2` for the Pi and open `http://10.42.0.2:8080`. The
router does not need an internet connection.

The software also reserves `10.42.0.0/24` for a Pi-hosted access point. In that
arrangement the Pi normally uses `10.42.0.1`, so the controller URL is
`http://10.42.0.1:8080`. Access-point provisioning is intentionally separate
from application installation because changing the Pi's active Wi-Fi profile
can interrupt SSH access.

## Network options

| Option | Show reliability | Trade-off |
| --- | --- | --- |
| Dedicated private router, Pi on Ethernet | Best | One additional powered device |
| Pi-hosted Wi-Fi access point | Good | Built-in Wi-Fi cannot simultaneously be a normal client without extra configuration or a second adapter |
| Phone hotspot | Acceptable backup | Phone hotspots can sleep, change address, or be interrupted by calls/settings |
| Venue Wi-Fi | Backup only | Unknown isolation, congestion, addressing, and credentials |
| Direct Ethernet to a laptop/tablet | Strong wired fallback | Less convenient for a phone and may need an adapter |
| Bluetooth | Pedal/MIDI only for now | The browser controller is HTTP and is not served over Bluetooth |

Do not expose ports 8080 or 9999 to the public internet. Use a WPA2/WPA3 key
for the private network and keep the controller subnets limited to the values
in `/etc/default/phreqed-dmx` and the systemd units.

## Boot behavior

The installed units start in this order:

```text
Linux + USB/audio discovery
        -> headless QLC+
        -> Phreqed browser controller
```

Neither service waits for internet access. Phreqed starts with live capability
available but output stopped. An operator must still open the controller and
press **Start live** before an Art-Net sender is created. If the Ampero is
missing at boot, its reader waits and reconnects when the raw-MIDI device
appears. If the Snowball is missing, the browser starts without audio rather
than becoming unavailable.

Install the controller service on the commissioned Pi:

```bash
cd ~/phreqed-stage-dmx-light-controller
bash scripts/pi-install-show-service.sh
sudoedit /etc/default/phreqed-dmx
sudo reboot
```

The installer synchronizes both systemd units and makes a one-time backup of a
different installed QLC+ unit. It never replaces the commissioned `.qxw`
workspace. Review `systemctl cat qlcplus.service phreqed-dmx.service` before
the reboot if the Pi has any local service customization.

The safe default file permits the current home LAN and reserved stage LAN:

```text
PHREQED_ALLOW_NETWORK=192.168.1.0/24,10.42.0.0/24
```

After reboot, join the selected private network and check:

```bash
systemctl status qlcplus.service phreqed-dmx.service --no-pager
curl -I http://127.0.0.1:9999
curl -I http://127.0.0.1:8080
```

The phone browser is the configuration and override interface. The Ampero is
the no-screen show interface. Keep a tested Ampero blackout action, and retain
QLC+ blackout as the final software safety layer.

## Headless operating checklist

Before applying power, connect the FTDI DMX adapter, Snowball, Ampero, and
Ethernet/private-router cable. Power the router first, then the Pi. Join the
private SSID, open the fixed controller address, confirm audio and pedal status,
select the opening scene, and only then start live output at low brightness.

At shutdown, use browser blackout and stop output before powering down. A
physical shutdown button or small UPS is a worthwhile future addition because
removing Pi power abruptly can corrupt storage and cannot guarantee a final DMX
blackout frame.
