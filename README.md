# LibrePhoneCam

Turn your phone into a webcam for Streamlabs, OBS or anything with a browser source over your own wifi.
No app to install on the phone, no account, no cloud, free and opensource.

*[Version française](README.fr.md)*

## Why

Built for small streamers who cannot drop a few hundred euros on a camera, or
pay a monthly fee for an app that does the same job. You already own a good
camera. It is in your pocket.

## Install

**[Download LibrePhoneCam.exe](../../releases/latest)** and double-click it. That's it.

> Windows will say the publisher is unknown, because the app is not code-signed
> (a certificate costs several hundred euros a year). Click **More info**, then
> **Run anyway**.

## Use it

The app opens with everything you need:

1. **Scan the QR code** with your phone, accept the certificate warning
   ([why?](#the-certificate-warning)), then tap **Start camera**.
2. **Copy the second address** into Streamlabs: `+` > **Browser**, size 1920x1080.

Done. Your phone camera is now a source in your scene.

## Works with

| | |
|---|---|
| **Phones** | iOS and Android |
| **Browsers** | Safari, Chrome, Firefox, Brave |
| **PC** | Windows, Linux |
| **Software** | Streamlabs, OBS, anything with a browser source |

The app is in **English and French**, with a button to switch, and has a **light
and dark theme**.

## How it works

```
   Phone  ────────── video (peer to peer) ──────────►  Streamlabs
     │                                                      │
     └────────► LibrePhoneCam on your PC ◄──────────────────┘
                  (introduces them, then steps aside)
```

Quality is automatic: the page asks your camera what it can do and picks the
best setting it can carry, up to 1080p60.

## Everything stays on your machine

The program connects to **no external server at all**. No account, no sign-up,
no telemetry, no cloud relay, nothing phoning home. The only thing running is a
small web server on your own PC.

The video goes straight from your phone to Streamlabs across your wifi. It never
passes through the app, is never recorded, and never reaches the internet. Unplug
your router from the wall and it still works.

## The certificate warning

Browsers only allow camera access over https, and no authority will issue a
certificate for a home address like `192.168.1.10`. So the app makes its own.
Your phone cannot verify it and says so.

It is safe here: the certificate is created on your PC, stays there, and covers
only your own network. Accept it once and you are done.

## If something goes wrong

**The page will not load on the phone.** Allow the app through Windows Firewall
when prompted, and check that both devices are on the same wifi (phones like to
fall back to mobile data).

**The image is vertical.** Turn the phone sideways before starting the camera.

**Streamlabs shows a black rectangle.** Right-click the source, then **Refresh**.

**The stream stops when you switch apps.** Phones suspend the camera in the
background. Keep the tab in front, and keep the phone plugged in.

## From source

```bash
git clone https://github.com/YOUR-USERNAME/LibrePhoneCam
cd LibrePhoneCam
run.bat          # Windows, or ./run.sh elsewhere. Sets everything up and opens the app.
build.bat        # builds LibrePhoneCam.exe into dist/
```

Any argument turns `run.bat` into a command line version: `run.bat --help`.

```
librephonecam/   the app and the local server
web/             the phone page and the Streamlabs page
tests/           run them directly, no framework needed
build-tools/     icon, PyInstaller spec
```

Contributions welcome.

## License

MIT
