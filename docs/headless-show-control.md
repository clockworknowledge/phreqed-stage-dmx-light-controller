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

## Pi-hosted stage Wi-Fi and iPhone control

The Pi-hosted option works like a small private Wi-Fi router: the iPhone joins
the Pi's SSID directly. Internet service is neither required nor provided. In
iPhone **Settings > Wi-Fi**, select `Phreqed-Stage`, enter the private WPA2
password, leave **Auto-Join** enabled, and retain the connection if iOS reports
that it has no internet. Then open Safari at `http://10.42.0.1:8080`. **Add to
Home Screen** is optional. Private Wi-Fi Address may remain enabled because
Phreqed authorizes the subnet, not a phone MAC address. The phone may continue
to use cellular data for internet traffic.

Provision the NetworkManager profile from an Ethernet SSH session or a local
console. Do not activate or disable it from SSH carried by `wlan0`; the helper
detects and refuses that path. It prompts for the key without putting it in
shell history, does not commit the key to Git, and separates configuration,
testing, and boot enablement:

```bash
cd ~/phreqed-stage-dmx-light-controller
bash scripts/pi-stage-hotspot.sh configure
bash scripts/pi-stage-hotspot.sh status
bash scripts/pi-stage-hotspot.sh activate
```

Join the SSID from the iPhone, verify the browser, then enable the tested
profile for unattended boots:

```bash
bash scripts/pi-stage-hotspot.sh enable
sudo reboot
```

For the first local-console activation, the repository also includes a short
wrapper. Configure the hotspot over SSH as above, move to the Pi's attached
keyboard/screen, and run:

```bash
cd ~/phreqed-stage-dmx-light-controller
bash local_network.sh
```

It activates the existing profile through the guarded helper, prints network
status, runs the safe-startup/stage-LAN readiness checks, and displays the
iPhone controller URL. It does not configure a password, enable the profile at
boot, or enable fixture output. The same SSH-path protection remains active, so
it refuses to replace `wlan0` when that interface carries the current session.

The Pi's built-in Wi-Fi becomes the access point and is no longer a client of
home or venue Wi-Fi. SSH from the iPhone-connected network uses
`mmorley@10.42.0.1`. To return it to normal Wi-Fi-client operation, use an
Ethernet/local session and run:

```bash
bash scripts/pi-stage-hotspot.sh disable
```

QLC+'s web interface is also reachable at `http://10.42.0.1:9999`; it is an
operator/recovery surface, not a public service. Use a unique stage Wi-Fi key
and do not share that network with an audience. A dedicated travel router with
Pi Ethernet remains preferred when the extra device and power connection are
acceptable, because it preserves Wi-Fi for other use and provides a separately
replaceable network component.

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

The installer creates `/dev/snd/phreqed-ampero-midi` from the Ampero's USB
identity, avoiding ALSA card-number changes such as `midiC3D0` becoming
`midiC2D0` after a reboot.

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
curl -fsS http://127.0.0.1:8080/api/state | python3 -m json.tool
```

The repository also supplies a read-only consolidated check. Immediately after
a cold boot, and after pressing one mapped Ampero switch, run:

```bash
.venv/bin/python scripts/show-readiness.py \
  --startup-defaults --require-stage-lan --require-audio --require-foot-event
```

It fails if output is already active, if Manual/inactive/stopped startup
defaults were lost, if a required peripheral is unhealthy, or if neither
commissioned stage address is present. A MIDI event proves the input path is
alive; the bank acceptance tool is what proves all five mappings.

The phone browser is the configuration and override interface. The Ampero is
the no-screen show interface. Keep a tested Ampero blackout action, and retain
QLC+ blackout as the final software safety layer.

## Headless operating checklist

Before applying power, connect the FTDI DMX adapter, Snowball, Ampero, and
Ethernet/private-router cable. Power the router first, then the Pi. Join the
private SSID, open the fixed controller address, confirm audio and pedal status,
select the opening scene, and only then start live output at low brightness.

When the optional browser shutdown capability has been installed and enabled,
use **Shut down Pi**, type `SHUTDOWN`, and wait for Pi activity to stop before
removing power. The controller first stops the timeline and requests fixture
blackout before systemd performs a normal power-off. If that control is not
enabled or the browser is unavailable, use browser blackout plus Stop output
and then the physical Pi switch. A small UPS remains worthwhile because sudden
power loss can corrupt storage and cannot guarantee a final DMX blackout frame.
