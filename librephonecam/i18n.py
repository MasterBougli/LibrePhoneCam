"""Translations for the desktop window."""

from __future__ import annotations

import locale

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "phoneStep": "1 . SCAN WITH YOUR PHONE",
        "phoneHint": (
            "Your browser will warn about the certificate. Open the details\n"
            "and continue to the site. Once is enough."
        ),
        "phoneHintNew": (
            "The certificate was just regenerated, so your phone will ask\n"
            "you to accept it again."
        ),
        "streamStep": "2 . PASTE INTO STREAMLABS",
        "streamHint": (
            "Add a Browser source, size 1920 x 1080. This address also works\n"
            "in any browser on this PC if you just want to check the picture."
        ),
        "copy": "Copy",
        "copied": "Copied",
        "openPreview": "Open preview",
        "otherAddresses": "Other addresses",
        "otherAddressesBody": (
            "Your PC has several network addresses. Docker, WSL, VirtualBox "
            "and VPNs each add one.\n\nIf the QR code does not load on your "
            "phone, try one of these instead:\n\n{addresses}"
        ),
        "starting": "Starting...",
        "waitingPhone": "Waiting for your phone",
        "streaming": "Streaming from {device}, {count} {viewers}",
        "phoneWaiting": "{device} connected, waiting for Streamlabs",
        "viewersWaiting": "{count} {viewers} waiting, scan the QR code",
        "serverStopped": "Server stopped",
        "viewerOne": "viewer",
        "viewerMany": "viewers",
        "errNoNetworkTitle": "No network",
        "errNoNetwork": "{detail}\n\nConnect to wifi and reopen {app}.",
        "errPortTitle": "Port already in use",
        "errPort": (
            "{detail}\n\nAnother program is using it. Close it, or start {app} "
            "from a terminal with --https-port / --http-port."
        ),
        "errStartTitle": "Could not start",
        "themeTip": "Switch between light and dark",
        "langTip": "Passer en français",
    },
    "fr": {
        "phoneStep": "1 . SCANNEZ AVEC VOTRE TÉLÉPHONE",
        "phoneHint": (
            "Votre navigateur va signaler le certificat. Ouvrez les détails\n"
            "et poursuivez vers le site. Une seule fois suffit."
        ),
        "phoneHintNew": (
            "Le certificat vient d'être régénéré : votre téléphone va vous\n"
            "demander de l'accepter à nouveau."
        ),
        "streamStep": "2 . COLLEZ DANS STREAMLABS",
        "streamHint": (
            "Ajoutez une source Navigateur, taille 1920 x 1080. Cette adresse\n"
            "marche aussi dans un navigateur du PC pour vérifier l'image."
        ),
        "copy": "Copier",
        "copied": "Copié",
        "openPreview": "Ouvrir l'aperçu",
        "otherAddresses": "Autres adresses",
        "otherAddressesBody": (
            "Votre PC a plusieurs adresses réseau. Docker, WSL, VirtualBox et "
            "les VPN en ajoutent chacun une.\n\nSi le QR code ne charge pas "
            "sur votre téléphone, essayez une de celles-ci :\n\n{addresses}"
        ),
        "starting": "Démarrage...",
        "waitingPhone": "En attente du téléphone",
        "streaming": "Flux depuis {device}, {count} {viewers}",
        "phoneWaiting": "{device} connecté, en attente de Streamlabs",
        "viewersWaiting": "{count} {viewers} en attente, scannez le QR code",
        "serverStopped": "Serveur arrêté",
        "viewerOne": "spectateur",
        "viewerMany": "spectateurs",
        "errNoNetworkTitle": "Pas de réseau",
        "errNoNetwork": "{detail}\n\nConnectez-vous au wifi et rouvrez {app}.",
        "errPortTitle": "Port déjà utilisé",
        "errPort": (
            "{detail}\n\nUn autre programme l'utilise. Fermez-le, ou lancez "
            "{app} depuis un terminal avec --https-port / --http-port."
        ),
        "errStartTitle": "Démarrage impossible",
        "themeTip": "Basculer clair / sombre",
        "langTip": "Switch to English",
    },
}

LANGUAGES = tuple(STRINGS)


def detect() -> str:
    """Pick a language from the system locale, defaulting to English."""
    try:
        tag = locale.getlocale()[0] or ""
    except ValueError:
        tag = ""
    tag = tag.lower()
    # Windows reports names like "French_France" where POSIX reports "fr_FR".
    return "fr" if tag.startswith("fr") or "french" in tag else "en"


def other(lang: str) -> str:
    return "en" if lang == "fr" else "fr"


def t(lang: str, key: str, **kwargs: object) -> str:
    text = STRINGS.get(lang, STRINGS["en"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
