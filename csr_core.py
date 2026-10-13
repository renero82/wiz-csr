"""Logica di generazione chiave privata + CSR (indipendente dalla GUI)."""
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


def build_csr(p: CsrParams, key):
    if p.country.strip() and len(p.country.strip()) != 2:
        raise ValueError("Il Country deve essere un codice di 2 lettere (es. IT).")
    builder = x509.CertificateSigningRequestBuilder().subject_name(build_name(p))

    sans = [x509.DNSName(d) for d in p.san_dns]
    sans += [x509.IPAddress(ipaddress.ip_address(i)) for i in p.san_ip]
    sans += [x509.RFC822Name(e) for e in p.san_email]
    sans += [x509.UniformResourceIdentifier(u) for u in p.san_uri]
    if sans:
        builder = builder.add_extension(x509.SubjectAlternativeName(sans), critical=False)

    if p.key_usages:
        flags = {k: (k in p.key_usages) for k, _ in KEY_USAGES}
        flags["encipher_only"] = flags["decipher_only"] = False
        builder = builder.add_extension(x509.KeyUsage(**flags), critical=True)
    if p.ext_key_usages:
        builder = builder.add_extension(x509.ExtendedKeyUsage(p.ext_key_usages), critical=False)
    if p.is_ca:
        builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=p.path_length), critical=True)

    algo = None if isinstance(key, ed25519.Ed25519PrivateKey) else HASHES[p.hash_name]()
    return builder.sign(key, algo)


def _safe_name(name: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "-_." else "_" for c in name.strip())
    return cleaned.strip("._") or "certificato"


def generate_and_save(p: CsrParams, out_dir: str, base_name: str = ""):
    """Genera chiave + CSR e li salva in out_dir. Ritorna (key_path, csr_path, csr_pem)."""
    if not out_dir or not os.path.isdir(out_dir):
        raise ValueError("Scegli una cartella di destinazione valida.")
    base = _safe_name(base_name or p.common_name or "certificato")
    key_path = os.path.join(out_dir, base + ".key")
    csr_path = os.path.join(out_dir, base + ".csr")
    for path in (key_path, csr_path):
        if os.path.exists(path):
            raise FileExistsError(f"Il file esiste già: {path}")

    key = generate_key(p.key_type)
    csr = build_csr(p, key)

    enc = (serialization.BestAvailableEncryption(p.passphrase.encode())
           if p.passphrase else serialization.NoEncryption())
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, enc)
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)

    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key_pem)
    with open(csr_path, "wb") as f:
        f.write(csr_pem)
    return key_path, csr_path, csr_pem.decode()
