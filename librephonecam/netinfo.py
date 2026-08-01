"""Detection of the LAN addresses the phone will use to reach this machine."""

from __future__ import annotations

import ipaddress
import socket


def _is_usable(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    # Link-local (169.254.x.x / APIPA) means "no DHCP answered"; a phone will
    # never route to it. Loopback is handled separately.
    return not (ip.is_loopback or ip.is_link_local or ip.is_multicast)


def primary_lan_ip() -> str | None:
    """The address of the interface that owns the default route.

    Opening a UDP socket sends no packet, but it makes the OS pick the source
    address it *would* use to reach the internet -- which is the interface the
    phone shares a network with in the overwhelmingly common case.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        addr = sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()
    return addr if _is_usable(addr) else None


def all_lan_ips() -> list[str]:
    """Every routable IPv4 address of this host, best candidate first.

    Machines with Docker, WSL, VirtualBox or a VPN have several. We cannot know
    which one the phone can reach, so they all go in the certificate's SAN list
    and all get printed at startup.
    """
    found: list[str] = []
    primary = primary_lan_ip()
    if primary:
        found.append(primary)

    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except socket.gaierror:
        infos = []
    for info in infos:
        addr = info[4][0]
        if _is_usable(addr) and addr not in found:
            found.append(addr)

    return found
