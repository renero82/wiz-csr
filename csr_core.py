"""Logica di generazione chiave privata + CSR (indipendente dalla GUI)."""
import datetime
import ipaddress
import os
from dataclasses import dataclass, field

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

KEY_TYPES = ["RSA 2048", "RSA 3072", "RSA 4096", "EC P-256", "EC P-384", "EC P-521", "Ed25519"]
HASHES = {"SHA-256": hashes.SHA256, "SHA-384": hashes.SHA384, "SHA-512": hashes.SHA512}

KEY_USAGES = [
    ("digital_signature", "Digital Signature"),
    ("content_commitment", "Non Repudiation"),
    ("key_encipherment", "Key Encipherment"),
    ("data_encipherment", "Data Encipherment"),
    ("key_agreement", "Key Agreement"),
    ("key_cert_sign", "Certificate Sign"),
    ("crl_sign", "CRL Sign"),
]
EXT_KEY_USAGES = [
    (ExtendedKeyUsageOID.SERVER_AUTH, "TLS Server Auth"),
    (ExtendedKeyUsageOID.CLIENT_AUTH, "TLS Client Auth"),
    (ExtendedKeyUsageOID.CODE_SIGNING, "Code Signing"),
    (ExtendedKeyUsageOID.EMAIL_PROTECTION, "Email Protection"),
    (ExtendedKeyUsageOID.TIME_STAMPING, "Time Stamping"),
    (ExtendedKeyUsageOID.OCSP_SIGNING, "OCSP Signing"),
]


@dataclass
class CsrParams:
    common_name: str = ""
    organization: str = ""
    org_unit: str = ""
    country: str = ""
    state: str = ""
    locality: str = ""
    email: str = ""
    key_type: str = "RSA 2048"
    hash_name: str = "SHA-256"
    passphrase: str = ""
    san_dns: list = field(default_factory=list)
    san_ip: list = field(default_factory=list)
    san_email: list = field(default_factory=list)
    san_uri: list = field(default_factory=list)
    key_usages: list = field(default_factory=list)       # nomi attributi KeyUsage
    ext_key_usages: list = field(default_factory=list)   # OID
    is_ca: bool = False
    path_length: int | None = None
    self_signed: bool = False
    validity_days: int = 365


def generate_key(key_type: str):
    if key_type.startswith("RSA"):
        return rsa.generate_private_key(public_exponent=65537, key_size=int(key_type.split()[1]))
    if key_type.startswith("EC"):
        curve = {"P-256": ec.SECP256R1, "P-384": ec.SECP384R1, "P-521": ec.SECP521R1}[key_type.split()[1]]
        return ec.generate_private_key(curve())
    if key_type == "Ed25519":
        return ed25519.Ed25519PrivateKey.generate()
    raise ValueError(f"Tipo di chiave non supportato: {key_type}")


def build_name(p: CsrParams) -> x509.Name:
    attrs = []
    for oid, val in [
        (NameOID.COUNTRY_NAME, p.country),
        (NameOID.STATE_OR_PROVINCE_NAME, p.state),
        (NameOID.LOCALITY_NAME, p.locality),
        (NameOID.ORGANIZATION_NAME, p.organization),
        (NameOID.ORGANIZATIONAL_UNIT_NAME, p.org_unit),
        (NameOID.COMMON_NAME, p.common_name),
        (NameOID.EMAIL_ADDRESS, p.email),
    ]:
        val = val.strip()
        if val:
            attrs.append(x509.NameAttribute(oid, val))
    if not attrs:
        raise ValueError("Specifica almeno un campo del Subject (es. Common Name).")
    return x509.Name(attrs)


def build_extensions(p: CsrParams) -> list:
    """Lista di (estensione, critical) condivisa tra CSR e certificato autofirmato."""
    exts = []
    sans = [x509.DNSName(d) for d in p.san_dns]
    sans += [x509.IPAddress(ipaddress.ip_address(i)) for i in p.san_ip]
    sans += [x509.RFC822Name(e) for e in p.san_email]
    sans += [x509.UniformResourceIdentifier(u) for u in p.san_uri]
    if sans:
        exts.append((x509.SubjectAlternativeName(sans), False))
    if p.key_usages:
        flags = {k: (k in p.key_usages) for k, _ in KEY_USAGES}
        flags["encipher_only"] = flags["decipher_only"] = False
        exts.append((x509.KeyUsage(**flags), True))
    if p.ext_key_usages:
        exts.append((x509.ExtendedKeyUsage(p.ext_key_usages), False))
    if p.is_ca:
        exts.append((x509.BasicConstraints(ca=True, path_length=p.path_length), True))
    return exts


def _sign_algo(p: CsrParams, key):
    return None if isinstance(key, ed25519.Ed25519PrivateKey) else HASHES[p.hash_name]()


def build_csr(p: CsrParams, key):
    if p.country.strip() and len(p.country.strip()) != 2:
        raise ValueError("Il Country deve essere un codice di 2 lettere (es. IT).")
    builder = x509.CertificateSigningRequestBuilder().subject_name(build_name(p))
    for ext, critical in build_extensions(p):
        builder = builder.add_extension(ext, critical=critical)
    return builder.sign(key, _sign_algo(p, key))


def build_self_signed(p: CsrParams, key):
    if p.validity_days < 1:
        raise ValueError("La validità deve essere di almeno 1 giorno.")
    name = build_name(p)
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (x509.CertificateBuilder()
               .subject_name(name).issuer_name(name)
               .public_key(key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(now - datetime.timedelta(minutes=5))
               .not_valid_after(now + datetime.timedelta(days=p.validity_days))
               .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False))
    for ext, critical in build_extensions(p):
        builder = builder.add_extension(ext, critical=critical)
    return builder.sign(key, _sign_algo(p, key))


def _summary(p: CsrParams, files: list) -> str:
    out = [f"Generato il: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
           f"Subject: {build_name(p).rfc4514_string()}",
           f"Chiave: {p.key_type}" + (f", hash {p.hash_name}" if p.key_type != "Ed25519" else ""),
           f"Chiave cifrata con passphrase: {'sì' if p.passphrase else 'no'}"]
    for label, vals in (("SAN DNS", p.san_dns), ("SAN IP", p.san_ip),
                        ("SAN Email", p.san_email), ("SAN URI", p.san_uri)):
        if vals:
            out.append(f"{label}: {', '.join(vals)}")
    if p.key_usages:
        out.append("Key Usage: " + ", ".join(l for k, l in KEY_USAGES if k in p.key_usages))
    if p.ext_key_usages:
        out.append("Extended Key Usage: " + ", ".join(l for o, l in EXT_KEY_USAGES if o in p.ext_key_usages))
    if p.is_ca:
        out.append(f"CA: sì (path length: {p.path_length if p.path_length is not None else 'illimitata'})")
    if p.self_signed:
        out.append(f"Autofirmato, validità: {p.validity_days} giorni")
    out.append("File: " + ", ".join(files))
    return "\n".join(out) + "\n"


def _safe_name(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in name.strip())
    return cleaned.strip("._") or "certificato"


def generate_and_save(p: CsrParams, out_dir: str, base_name: str = ""):
    """Genera chiave + CSR (+ certificato autofirmato) in una sottocartella ordinata di out_dir.

    Ritorna un dict con i percorsi (folder, key, csr, crt|None) e i PEM (csr_pem, crt_pem|None).
    """
    if not out_dir or not os.path.isdir(out_dir):
        raise ValueError("Scegli una cartella di destinazione valida.")
    base = _safe_name(base_name or p.common_name or "certificato")

    key = generate_key(p.key_type)
    csr = build_csr(p, key)
    crt = build_self_signed(p, key) if p.self_signed else None

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = os.path.join(out_dir, f"{base}_{stamp}")
    n = 1
    while os.path.exists(folder):
        n += 1
        folder = os.path.join(out_dir, f"{base}_{stamp}-{n}")
    os.makedirs(folder)

    enc = (serialization.BestAvailableEncryption(p.passphrase.encode())
           if p.passphrase else serialization.NoEncryption())
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, enc)
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)
    crt_pem = crt.public_bytes(serialization.Encoding.PEM) if crt else None

    paths = {"folder": folder, "key": os.path.join(folder, base + ".key"),
             "csr": os.path.join(folder, base + ".csr"), "crt": None}
    fd = os.open(paths["key"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key_pem)
    with open(paths["csr"], "wb") as f:
        f.write(csr_pem)
    if crt_pem:
        paths["crt"] = os.path.join(folder, base + ".crt")
        with open(paths["crt"], "wb") as f:
            f.write(crt_pem)
    names = [os.path.basename(v) for k, v in paths.items() if k != "folder" and v]
    with open(os.path.join(folder, "info.txt"), "w", encoding="utf-8") as f:
        f.write(_summary(p, names + ["info.txt"]))
    return {**paths, "csr_pem": csr_pem.decode(), "crt_pem": crt_pem.decode() if crt_pem else None}
