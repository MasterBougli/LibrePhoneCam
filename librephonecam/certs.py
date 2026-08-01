"""Self-signed certificate handling.

Safari refuses `getUserMedia()` on a plain-HTTP origin unless it is localhost,
so reaching the phone over the LAN forces us into TLS. There is no CA that will
issue a certificate for `192.168.x.x`, hence this generator: the phone shows a
one-time "connection is not private" interstitial that the user accepts.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
import json
import ssl
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

# Safari (iOS and macOS) rejects TLS certificates whose total lifetime exceeds
# 398 days, self-signed ones included. Stay comfortably below.
VALIDITY_DAYS = 365

CERT_NAME = "cert.pem"
KEY_NAME = "key.pem"
MANIFEST_NAME = "san.json"


def _build(hosts: list[str]) -> tuple[bytes, bytes]:
    key = ec.generate_private_key(ec.SECP256R1())

    alt_names: list[x509.GeneralName] = []
    for host in hosts:
        try:
            alt_names.append(x509.IPAddress(ipaddress.ip_address(host)))
        except ValueError:
            alt_names.append(x509.DNSName(host))

    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LibrePhoneCam")])
    now = dt.datetime.now(dt.timezone.utc)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        # Backdate slightly so a phone whose clock lags does not reject it.
        .not_valid_before(now - dt.timedelta(hours=1))
        .not_valid_after(now + dt.timedelta(days=VALIDITY_DAYS))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return cert_pem, key_pem


def _is_stale(cert_dir: Path, hosts: list[str]) -> bool:
    """True when the cert is missing, expiring, or no longer covers our IPs.

    The LAN address changes whenever DHCP hands out a new lease, and a
    certificate that does not name the address the phone typed produces a hard
    failure rather than the acceptable interstitial.
    """
    cert_path = cert_dir / CERT_NAME
    manifest = cert_dir / MANIFEST_NAME
    if not (cert_path.exists() and (cert_dir / KEY_NAME).exists() and manifest.exists()):
        return True

    try:
        covered = json.loads(manifest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return True
    if not set(hosts).issubset(set(covered)):
        return True

    try:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
    except (ValueError, OSError):
        return True
    # Renew a week early rather than letting the phone hit an expired cert
    # mid-stream.
    return cert.not_valid_after_utc <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=7)


def ensure_cert(cert_dir: Path, hosts: list[str]) -> tuple[Path, bool]:
    """Return the certificate path, regenerating it if it no longer fits."""
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / CERT_NAME
    key_path = cert_dir / KEY_NAME

    if not _is_stale(cert_dir, hosts):
        return cert_path, False

    cert_pem, key_pem = _build(hosts)
    cert_path.write_bytes(cert_pem)
    key_path.write_bytes(key_pem)
    (cert_dir / MANIFEST_NAME).write_text(json.dumps(hosts), encoding="utf-8")
    return cert_path, True


def ssl_context(cert_dir: Path, hosts: list[str]) -> tuple[ssl.SSLContext, bool]:
    cert_path, regenerated = ensure_cert(cert_dir, hosts)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_path, cert_dir / KEY_NAME)
    return ctx, regenerated
