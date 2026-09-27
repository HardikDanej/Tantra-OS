"""
provenance.py
=============
"Tantra Seal": verifiable ownership and provenance for the Tantra marketing
OS (Copyright (c) 2026 Hardik Danej) and for the deliverables it produces.

Why this exists, and why it looks the way it does
-------------------------------------------------
The owner asked for "a SynthID-style text watermark + C2PA" across the OS.
Three verified facts shaped the design:

  * A real SynthID-Text watermark is applied while the model samples tokens
    and needs logits access. Claude Code has no such access, so nothing here
    pretends to be one. Claude's output already carries Anthropic's own
    SynthID-Text-based watermark (no hidden characters, identifies no user).
  * Invisible-Unicode "watermarks" are stripped by one normalisation pass,
    are flagged as ASCII smuggling by security tools, cost hidden tokens on
    every agent load and collide with de-ai-ify / citation_guard. So this
    module NEVER embeds invisible characters anywhere.
  * c2pa-python embeds manifests into images, office files, audio and video,
    but not into Markdown, plain text, HTML, JSON or PDF. Those get a
    detached sidecar (`<file>.c2pa`).

What it builds instead, one layer per claim:

  1. Ed25519 detached signatures (`sign-os`, `sign-file`): prove a file is
     byte-for-byte what the owner's key signed.
  2. C2PA Content Credentials (`sign-file`): an industry-standard, honest
     record that the file was produced with AI assistance under the
     operator's direction, plus a CAWG "do not train / do not mine" notice.
     Upstream credentials (Adobe, OpenAI, Anthropic ...) are kept as the
     parent ingredient, never stripped.
  3. Visible copyright-management information in agent/skill frontmatter
     (`seal-frontmatter`): author, copyright, licence and a keyed seal id
     that only the owner's secret key can produce.
  4. A keyed statistical fingerprint (`fingerprint ...`): the "SynthID-style"
     layer, but detector-side. Registered texts are shingled, keyed with a
     secret HMAC key and winnowed; a suspect text is matched against the
     registry. Nothing is embedded in the text, so there is nothing to strip.

None of this prevents copying. It produces evidence of origin and of
tampering. provenance/README.md states exactly what each layer does and
does not prove.

Key material lives in TANTRA_HOME/keys (default ~/.tantra/keys), never in
the repository. `init --export-public` copies only public material to
provenance/public/ so third parties can verify.

Dependencies: `cryptography` and `c2pa-python` (run this script with the
normal interpreter, not `python -I -S`). The fingerprint and seal-id code
paths are stdlib-only.

Usage:
    python provenance.py init --name "Hardik Danej" [--email E] [--force] [--export-public DIR]
    python provenance.py sign-os   [--repo PATH] [--tsa URL]
    python provenance.py verify-os [--repo PATH] [--pubkey PEM] [--expect-fp SHA256] [--verbose]
    python provenance.py sign-file PATH [--workspace W] [--run-id R] [--no-fingerprint] [--title T] [--json]
    python provenance.py verify-file PATH [--trust-root PEM] [--pubkey PEM] [--expect-fp SHA256] [--json]
    python provenance.py seal-frontmatter [--check] [--cmi-only] [--repo PATH]
    python provenance.py verify-seal NAME_OR_PATH [--seal TS1-...] [--kind agent|skill] [--repo PATH]
    python provenance.py fingerprint register PATH [--label L]
    python provenance.py fingerprint register-os [--repo PATH]
    python provenance.py fingerprint match PATH [--top 5] [--min 0.05] [--json]
    python provenance.py fingerprint list

Exit codes:
    0  success / verification passed
    1  verification failed, --check found issues, or a refused operation
    2  usage or environment error (missing keys, missing dependency, not a git repo)
"""

import argparse
import base64
import datetime
import hashlib
import hmac
import io
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
import unicodedata

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OWNER = "Hardik Danej"
SYSTEM = "Tantra"
ASSERTION_LABEL = "com.hardikdanej.tantra.provenance"
STATEMENT = "Produced with AI assistance under the operator's direction."
DST_CREATED = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
DST_COMPOSITE = "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
EKU_DOCUMENT_SIGNING = "1.3.6.1.5.5.7.3.36"

MANIFEST_SCHEMA = "tantra-os-manifest/1"
OS_MANIFEST_PREFIX = "provenance/os_manifest."
SIG_SUFFIX = ".tantra-sig.json"
SIDECAR_SUFFIX = ".c2pa"

AGENT_CMI = {
    "author": OWNER,
    "copyright": "Copyright (c) 2026 Hardik Danej. All rights reserved.",
    "license": "Proprietary, see LICENSE in the Tantra repository",
}
SKILL_LICENSE = "Proprietary. Copyright (c) 2026 Hardik Danej. All rights reserved."
SEAL_KEY = "tantra-seal"
SEAL_PREFIX = "TS1-"

# SVG is text an agent keeps editing: embedding would rewrite it after every Edit (and put a
# base64 blob into what the agent reads back), so it gets a sidecar like the other text formats.
NEVER_EMBED = {"text/markdown", "text/plain", "text/html", "application/json", "application/pdf", "text/csv",
               "image/svg+xml"}
FINGERPRINT_EXTS = {".md", ".markdown", ".txt", ".html", ".htm", ".json", ".csv"}
OS_FINGERPRINT_EXTS = FINGERPRINT_EXTS | {".py", ".mjs", ".js", ".yaml", ".yml", ".template"}
MIME_BY_EXT = {
    ".md": "text/markdown", ".markdown": "text/markdown", ".txt": "text/plain", ".html": "text/html",
    ".htm": "text/html", ".json": "application/json", ".csv": "text/csv", ".pdf": "application/pdf",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
    ".gif": "image/gif", ".tif": "image/tiff", ".tiff": "image/tiff", ".avif": "image/avif",
    ".heic": "image/heic", ".heif": "image/heif", ".svg": "image/svg+xml",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".odt": "application/vnd.oasis.opendocument.text", ".epub": "application/epub+zip",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".flac": "audio/flac", ".m4a": "audio/mp4",
}

SHINGLE_WORDS = 5
WINNOW_WINDOW = 4
MIN_FPS_FOR_COVERAGE = 8
MIN_QUERY_FPS = 8      # below this a query is a stock phrase, not a document: containment is meaningless
MIN_SHARED_FPS = 3     # one or two shared shingles are common phrases, not evidence of derivation
EMBED_ATTEMPTS = 3
VERDICTS = ((0.5, "strong match"), (0.15, "likely derived"), (0.05, "some overlap"))


class ProvenanceError(Exception):
    """An expected, user-facing failure (missing keys, bad input). Exit code 2."""


class SourceChanged(Exception):
    """The file was rewritten while it was being signed; its new content must not be reverted."""


# ---- small utilities -------------------------------------------------------------

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def is_binary(data):
    return b"\0" in data[:8192]


def content_digest(data):
    """sha256 of LF-normalised bytes for text, raw bytes for binary.

    Git's core.autocrlf rewrites line endings in the working tree, so text is
    hashed as LF to keep the manifest stable across checkouts."""
    if not is_binary(data):
        data = data.replace(b"\r\n", b"\n")
    return sha256_hex(data)


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def write_atomic(path, data, private=False):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp-" + secrets.token_hex(4)
    # Private material is created 0600 from the first byte, never chmod'ed after the fact.
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600 if private else 0o666)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)
    if private:
        restrict(tmp)
    os.replace(tmp, path)


def restrict(path, mode=0o600):
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def private_dir(path):
    os.makedirs(path, mode=0o700, exist_ok=True)
    restrict(path, 0o700)


def tantra_home():
    env = os.environ.get("TANTRA_HOME")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), ".tantra")


def keys_dir():
    return os.path.join(tantra_home(), "keys")


def key_path(name):
    return os.path.join(keys_dir(), name)


def registry_path():
    return os.path.join(tantra_home(), "registry", "fingerprints.jsonl")


def git(repo, *args, timeout=60):
    proc = subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=timeout)
    if proc.returncode != 0:
        raise ProvenanceError(f"git {' '.join(args)} failed in {repo}: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


def git_head(repo, short=False):
    try:
        out = git(repo, "rev-parse", "--short" if short else "--verify", "HEAD", timeout=15)
        return out.decode().strip()
    except (ProvenanceError, OSError, subprocess.SubprocessError):
        return None


def generator_version():
    return git_head(REPO_ROOT, short=True) or "dev"


def glob_to_regex(pattern):
    """Translate a gitignore-style glob (`**`, `*`, `?`) into an anchored regex."""
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def load_third_party(repo):
    data = read_json(os.path.join(repo, "provenance", "third_party.json"), {}) or {}
    return [glob_to_regex(e["pattern"]) for e in data.get("exclude", []) if isinstance(e, dict) and e.get("pattern")]


def excluded(relpath, patterns):
    return any(p.match(relpath) for p in patterns)


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


# ---- key material ------------------------------------------------------------------

def crypto():
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, ed25519
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID, ObjectIdentifier
    except ImportError as exc:
        raise ProvenanceError(
            "the 'cryptography' package is required for signing; run this script with the normal "
            f"Python interpreter (not -I -S). ({exc})"
        ) from exc
    return {
        "x509": x509, "hashes": hashes, "serialization": serialization, "ec": ec, "ed25519": ed25519,
        "EKU": ExtendedKeyUsageOID, "NameOID": NameOID, "OID": ObjectIdentifier,
    }


def passphrase():
    value = os.environ.get("TANTRA_KEY_PASSPHRASE")
    return value.encode("utf-8") if value else None


def private_pem(key):
    c = crypto()["serialization"]
    pw = passphrase()
    enc = c.BestAvailableEncryption(pw) if pw else c.NoEncryption()
    return key.private_bytes(c.Encoding.PEM, c.PrivateFormat.PKCS8, enc)


def load_private(path):
    c = crypto()["serialization"]
    if not os.path.isfile(path):
        raise ProvenanceError(f"missing signing key {path}; run `provenance.py init --name \"{OWNER}\"` first")
    try:
        return c.load_pem_private_key(read_bytes(path), password=passphrase())
    except (TypeError, ValueError) as exc:
        raise ProvenanceError(f"cannot load {path}: {exc} (set TANTRA_KEY_PASSPHRASE if the keys are encrypted)") from exc


def plain_private_pem(key):
    c = crypto()["serialization"]
    return key.private_bytes(c.Encoding.PEM, c.PrivateFormat.PKCS8, c.NoEncryption())


def public_fp(public_key):
    c = crypto()["serialization"]
    raw = public_key.public_bytes(c.Encoding.Raw, c.PublicFormat.Raw)
    return sha256_hex(raw)


def load_public(path):
    c = crypto()["serialization"]
    return c.load_pem_public_key(read_bytes(path))


def identity():
    data = read_json(key_path("identity.json"), None)
    if not data:
        raise ProvenanceError(f"no Tantra identity in {keys_dir()}; run `provenance.py init --name \"{OWNER}\"` first")
    return data


def fingerprint_key(required=True):
    path = key_path("fingerprint.key")
    if os.path.isfile(path):
        data = read_bytes(path)
        if len(data) >= 32:
            return data
    if required:
        raise ProvenanceError(f"missing {path}; run `provenance.py init --name \"{OWNER}\"` first")
    return None


KEY_FILES = (
    "identity_ed25519.pem", "identity_ed25519.pub.pem", "fingerprint.key", "c2pa_root_ca.key",
    "c2pa_root_ca.pem", "c2pa_signer.key", "c2pa_signer.pem", "c2pa_chain.pem", "identity.json",
)


def _x509_name(c, common_name):
    NameOID = c["NameOID"]
    return c["x509"].Name([
        c["x509"].NameAttribute(NameOID.COMMON_NAME, common_name),
        c["x509"].NameAttribute(NameOID.ORGANIZATION_NAME, "Tantra"),
    ])


def make_root_ca(c, name):
    x509, hashes = c["x509"], c["hashes"]
    key = c["ec"].generate_private_key(c["ec"].SECP256R1())
    subject = _x509_name(c, f"{name} Tantra Root CA")
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256())
    )
    return key, cert


def make_signer_cert(c, name, email, ca_key, ca_cert):
    x509, hashes = c["x509"], c["hashes"]
    key = c["ec"].generate_private_key(c["ec"].SECP256R1())
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (
        x509.CertificateBuilder().subject_name(_x509_name(c, name)).issuer_name(ca_cert.subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=730))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([c["EKU"].EMAIL_PROTECTION, c["OID"](EKU_DOCUMENT_SIGNING)]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
    )
    if email:
        builder = builder.add_extension(x509.SubjectAlternativeName([x509.RFC822Name(email)]), critical=False)
    return key, builder.sign(ca_key, hashes.SHA256())


def create_keys(name, email):
    c = crypto()
    pem = c["serialization"].Encoding.PEM
    ident = c["ed25519"].Ed25519PrivateKey.generate()
    ca_key, ca_cert = make_root_ca(c, name)
    leaf_key, leaf_cert = make_signer_cert(c, name, email, ca_key, ca_cert)
    pub_pem = ident.public_key().public_bytes(pem, c["serialization"].PublicFormat.SubjectPublicKeyInfo)
    files = {
        "identity_ed25519.pem": (private_pem(ident), True),
        "identity_ed25519.pub.pem": (pub_pem, False),
        "fingerprint.key": (secrets.token_bytes(32), True),
        "c2pa_root_ca.key": (private_pem(ca_key), True),
        "c2pa_root_ca.pem": (ca_cert.public_bytes(pem), False),
        "c2pa_signer.key": (private_pem(leaf_key), True),
        "c2pa_signer.pem": (leaf_cert.public_bytes(pem), False),
        "c2pa_chain.pem": (leaf_cert.public_bytes(pem) + ca_cert.public_bytes(pem), False),
    }
    private_dir(keys_dir())
    for fname, (data, private) in files.items():
        write_atomic(key_path(fname), data, private=private)
    record = {
        "name": name, "email": email or None, "created_at": now_iso(),
        "signer_fp": public_fp(ident.public_key()),
        "root_ca_sha256": sha256_hex(ca_cert.public_bytes(c["serialization"].Encoding.DER)),
        "signer_cert_sha256": sha256_hex(leaf_cert.public_bytes(c["serialization"].Encoding.DER)),
        "encrypted": bool(passphrase()),
    }
    write_atomic(key_path("identity.json"), json.dumps(record, indent=2).encode("utf-8"))
    return record


def export_public(dest):
    ident = identity()
    os.makedirs(dest, exist_ok=True)
    for fname in ("identity_ed25519.pub.pem", "c2pa_root_ca.pem", "c2pa_signer.pem", "c2pa_chain.pem"):
        src = key_path(fname)
        if not os.path.isfile(src):
            raise ProvenanceError(f"missing {src}; re-run init")
        write_atomic(os.path.join(dest, fname), read_bytes(src))
    public = {k: ident.get(k) for k in ("name", "email", "created_at", "signer_fp", "root_ca_sha256", "signer_cert_sha256")}
    public["note"] = "Public verification material for Tantra Seal. Private keys never leave the owner's machine."
    write_atomic(os.path.join(dest, "fingerprints.json"), (json.dumps(public, indent=2) + "\n").encode("utf-8"))
    return sorted(os.listdir(dest))


def cmd_init(args):
    existing = [f for f in KEY_FILES if os.path.exists(key_path(f))]
    if existing and not args.force:
        if args.export_public:
            names = export_public(args.export_public)
            print(f"Keys already exist in {keys_dir()}; exported public material only: {', '.join(names)}")
            return 0
        print(f"Refusing to overwrite existing keys in {keys_dir()} ({', '.join(existing)}). "
              "Pass --force to replace them; anything signed with the old keys will then only verify "
              "against the old public key.", file=sys.stderr)
        return 1
    record = create_keys(args.name, args.email)
    print(f"Created Tantra signing identity for {record['name']} in {keys_dir()}")
    print(f"  Ed25519 signer fingerprint: {record['signer_fp']}")
    print(f"  C2PA root CA sha256:        {record['root_ca_sha256']}")
    print("  Private keys are " + ("encrypted with TANTRA_KEY_PASSPHRASE." if record["encrypted"]
                                   else "NOT passphrase-encrypted (set TANTRA_KEY_PASSPHRASE before init to encrypt)."))
    print("  Back up this folder offline; losing it means new signatures cannot be linked to old ones.")
    if args.export_public:
        names = export_public(args.export_public)
        print(f"  Public material exported to {args.export_public}: {', '.join(names)}")
    return 0


# ---- Ed25519 signatures ------------------------------------------------------------

def resolve_pubkey(explicit, repo=None):
    candidates = [explicit] if explicit else [
        key_path("identity_ed25519.pub.pem"),
        os.path.join(repo or REPO_ROOT, "provenance", "public", "identity_ed25519.pub.pem"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path, load_public(path)
    raise ProvenanceError("no public key found; pass --pubkey PEM (e.g. provenance/public/identity_ed25519.pub.pem)")


def normalise_fp(value):
    return re.sub(r"[^0-9a-f]", "", (value or "").lower()) or None


def pin_status(pub, expect_fp):
    """(fingerprint, pinned): pinned is None when no --expect-fp was given, else whether it matches."""
    fp = public_fp(pub)
    expect = normalise_fp(expect_fp)
    return fp, (None if expect is None else hmac.compare_digest(fp, expect))


PIN_HINT = ("compare it with the owner's fingerprint obtained out of band (not from the copy being verified), "
            "or pass --expect-fp")


def ed_verify(pub, data, sig_b64):
    try:
        pub.verify(base64.b64decode(sig_b64), data)
        return True
    except Exception:  # noqa: BLE001 - InvalidSignature or malformed base64 both mean "not valid"
        return False


# ---- OS manifest -------------------------------------------------------------------

def tracked_files(repo):
    raw = git(repo, "ls-files", "-z")
    return sorted(p for p in raw.decode("utf-8", errors="surrogateescape").split("\0") if p)


def sealable_files(repo):
    patterns = load_third_party(repo)
    return [p for p in tracked_files(repo) if not p.startswith(OS_MANIFEST_PREFIX) and not excluded(p, patterns)]


def build_os_manifest(repo, signer_fp, owner):
    files, missing = {}, []
    for rel in sealable_files(repo):
        path = os.path.join(repo, rel)
        if os.path.isfile(path):
            files[rel] = content_digest(read_bytes(path))
        else:
            missing.append(rel)
    header = {
        "schema": MANIFEST_SCHEMA, "owner": owner, "system": SYSTEM, "git_head": git_head(repo),
        "created_at": now_iso(), "file_count": len(files), "signer_fp": signer_fp,
    }
    return {"header": header, "files": files}, missing


def der(tag, content):
    n = len(content)
    if n < 0x80:
        length = bytes([n])
    else:
        enc = n.to_bytes((n.bit_length() + 7) // 8, "big")
        length = bytes([0x80 | len(enc)]) + enc
    return bytes([tag]) + length + content


def der_int(value):
    return der(0x02, value.to_bytes(value.bit_length() // 8 + 1, "big"))


def tsa_request(digest, nonce):
    """DER TimeStampReq (RFC 3161) for a sha256 digest, asking for the TSA certificate."""
    sha256_alg = der(0x30, der(0x06, bytes.fromhex("608648016503040201")) + der(0x05, b""))
    imprint = der(0x30, sha256_alg + der(0x04, digest))
    return der(0x30, der_int(1) + imprint + der_int(nonce) + der(0x01, b"\xff"))


def tsa_status(response):
    """PKIStatus from a TimeStampResp: 0 granted, 1 grantedWithMods, else rejected."""
    try:
        if response[0] != 0x30:
            raise ValueError("not a DER TimeStampResp")
        i = 2 if response[1] < 0x80 else 2 + (response[1] & 0x7F)
        if response[i] != 0x30:
            raise ValueError("missing PKIStatusInfo")
        j = i + 2 if response[i + 1] < 0x80 else i + 2 + (response[i + 1] & 0x7F)
        if response[j] != 0x02 or response[j + 1] == 0:
            raise ValueError("missing PKIStatus")
        return int.from_bytes(response[j + 2: j + 2 + response[j + 1]], "big")
    except IndexError as exc:
        raise ValueError("truncated TimeStampResp") from exc


def request_timestamp(url, data, out_path):
    import urllib.request

    body = tsa_request(hashlib.sha256(data).digest(), secrets.randbits(63))
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/timestamp-query"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            reply = resp.read()
        status = tsa_status(reply)
    except Exception as exc:  # noqa: BLE001 - offline or TSA error: the timestamp is optional
        return f"RFC 3161 timestamp skipped ({type(exc).__name__}: {exc})"
    if status not in (0, 1):
        return f"RFC 3161 timestamp rejected by {url} (PKIStatus {status})"
    write_atomic(out_path, reply)
    return f"RFC 3161 timestamp saved to {out_path} (verify with `openssl ts -verify`)"


def cmd_sign_os(args):
    repo = os.path.abspath(args.repo)
    ident = identity()
    key = load_private(key_path("identity_ed25519.pem"))
    manifest, missing = build_os_manifest(repo, public_fp(key.public_key()), ident["name"])
    data = canonical(manifest)
    out_dir = os.path.join(repo, "provenance")
    json_path = os.path.join(out_dir, "os_manifest.json")
    write_atomic(json_path, (json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8"))
    write_atomic(os.path.join(out_dir, "os_manifest.sig"), (base64.b64encode(key.sign(data)).decode("ascii") + "\n").encode())
    print(f"Signed OS manifest: {manifest['header']['file_count']} files, git_head {manifest['header']['git_head']}")
    print(f"  {json_path}\n  {os.path.join(out_dir, 'os_manifest.sig')}")
    for rel in missing:
        print(f"  note: tracked but missing on disk, not sealed: {rel}")
    if args.tsa:
        print("  " + request_timestamp(args.tsa, data, os.path.join(out_dir, "os_manifest.tsr")))
    print("  " + c2pa_sign_manifest_sidecar(json_path, os.path.join(out_dir, "os_manifest.c2pa")))
    return 0


def c2pa_sign_manifest_sidecar(json_path, out_path):
    try:
        manifest_bytes = c2pa_sign(json_path, title="Tantra OS manifest", workspace=None, run_id=None,
                                   force_sidecar=True)[1]
    except ProvenanceError as exc:
        return f"C2PA sidecar skipped: {exc}"
    write_atomic(out_path, manifest_bytes)
    return f"C2PA sidecar: {out_path}"


def load_signed_manifest(repo):
    base = os.path.join(repo, "provenance")
    manifest = read_json(os.path.join(base, "os_manifest.json"))
    if not isinstance(manifest, dict) or "files" not in manifest:
        raise ProvenanceError(f"no OS manifest at {base}/os_manifest.json; run sign-os first")
    try:
        sig = read_bytes(os.path.join(base, "os_manifest.sig")).decode("ascii").strip()
    except OSError as exc:
        raise ProvenanceError(f"missing {base}/os_manifest.sig") from exc
    return manifest, sig


def diff_os(repo, manifest):
    current = set(sealable_files(repo))
    recorded = manifest.get("files", {})
    rows = []
    for rel in sorted(current | set(recorded)):
        path = os.path.join(repo, rel)
        if rel not in recorded:
            rows.append((rel, "NEW-UNSEALED"))
        elif not os.path.isfile(path):
            rows.append((rel, "MISSING"))
        elif content_digest(read_bytes(path)) != recorded[rel]:
            rows.append((rel, "MODIFIED"))
        else:
            rows.append((rel, "OK"))
    return rows


def cmd_verify_os(args):
    repo = os.path.abspath(args.repo)
    manifest, sig = load_signed_manifest(repo)
    key_file, pub = resolve_pubkey(args.pubkey, repo)
    sig_ok = ed_verify(pub, canonical(manifest), sig)
    header = manifest.get("header", {})
    fp, pinned = pin_status(pub, args.expect_fp)
    fp_note = "" if header.get("signer_fp") == fp else " (manifest names a different signer key)"
    print(f"Signature: {'VALID' if sig_ok else 'INVALID'} (key {key_file}){fp_note}")
    if pinned is None:
        print(f"Signer key fingerprint: {fp} - {PIN_HINT}")
    else:
        print(f"Signer key fingerprint: {fp} - {'matches' if pinned else 'does NOT match'} --expect-fp")
    print(f"Manifest: owner {header.get('owner')} (as written by the signer), created {header.get('created_at')}, "
          f"git_head {header.get('git_head')}")
    rows = diff_os(repo, manifest)
    counts = {}
    for rel, status in rows:
        counts[status] = counts.get(status, 0) + 1
        if status != "OK" or args.verbose:
            print(f"  {status:<13} {rel}")
    print("Files: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    return 0 if sig_ok and pinned is not False and not counts.get("MODIFIED") and not counts.get("MISSING") else 1


# ---- C2PA --------------------------------------------------------------------------

def c2pa_lib():
    try:
        import c2pa
    except ImportError as exc:
        raise ProvenanceError(f"c2pa-python is not installed ({exc})") from exc
    return c2pa


def mime_for(path):
    ext = os.path.splitext(path)[1].lower()
    return MIME_BY_EXT.get(ext) or mimetypes.guess_type(path)[0] or "application/octet-stream"


def sidecar_format(path):
    mime = mime_for(path)
    return mime if mime.startswith("text/") or mime == "application/json" else "application/octet-stream"


def embeddable(c2pa, path):
    mime = mime_for(path)
    return mime not in NEVER_EMBED and mime in set(c2pa.Builder.get_supported_mime_types())


def c2pa_context(c2pa, settings):
    try:
        return c2pa.Context.from_dict(settings)
    except Exception:  # noqa: BLE001 - older SDKs have no Context; defaults still work
        return None


def c2pa_signer(c2pa):
    chain = key_path("c2pa_chain.pem")
    if not os.path.isfile(chain):
        raise ProvenanceError(f"missing {chain}; run init")
    key = plain_private_pem(load_private(key_path("c2pa_signer.key")))
    return c2pa.Signer.from_info(c2pa.C2paSignerInfo(b"es256", read_bytes(chain), key, None))


def provenance_assertions(workspace, run_id):
    info = {
        "operator": identity().get("name", OWNER), "system": "Tantra marketing OS",
        "workspace": workspace, "run_id": run_id, "signed_at": now_iso(), "statement": STATEMENT,
    }
    training = {"entries": {k: {"use": "notAllowed"} for k in
                            ("cawg.ai_training", "cawg.ai_generative_training", "cawg.data_mining")}}
    return [{"label": ASSERTION_LABEL, "data": info}, {"label": "cawg.training-mining", "data": training}]


def manifest_definition(title, fmt, workspace, run_id, created):
    assertions = provenance_assertions(workspace, run_id)
    if created:
        actions = {"actions": [{"action": "c2pa.created", "digitalSourceType": DST_CREATED}]}
        assertions.insert(0, {"label": "c2pa.actions", "data": actions})
    return {
        "claim_generator_info": [{"name": SYSTEM, "version": generator_version()}],
        "title": title, "format": fmt, "assertions": assertions,
    }


def active_manifest(reader):
    store = json.loads(reader.json())
    return store["manifests"][store["active_manifest"]]


def generator_name(manifest):
    return ((manifest.get("claim_generator_info") or [{}])[0]).get("name", "")


def own_signer_serial():
    try:
        cert = crypto()["x509"].load_pem_x509_certificate(read_bytes(key_path("c2pa_signer.pem")))
        return str(cert.serial_number)
    except (OSError, ValueError, ProvenanceError):
        return None


def existing_manifest(c2pa, path):
    """(has_manifest, readable, own). Unreadable manifests are never overwritten in place.

    own: the active manifest was made by this owner's own Tantra signer and carries no ingredient,
    so re-signing replaces it instead of nesting it (nesting grew the file on every write). Anyone
    else's credential, including another Tantra owner's, is kept as the parent ingredient."""
    try:
        reader = c2pa.Reader.try_create(path)
    except Exception:  # noqa: BLE001 - corrupt or unsupported: treat as "do not touch"
        return False, False, False
    if reader is None:
        return False, True, False
    own = False
    try:
        active = active_manifest(reader)
        serial = str((active.get("signature_info") or {}).get("cert_serial_number") or "")
        own = (generator_name(active) == SYSTEM and not active.get("ingredients")
               and bool(serial) and serial == own_signer_serial())
    except Exception:  # noqa: BLE001 - unknown shape: keep it as a parent
        own = False
    finally:
        try:
            reader.close()
        except Exception:  # noqa: BLE001
            pass
    return True, True, own


def c2pa_sign(path, title, workspace, run_id, force_sidecar=False):
    """Sign `path`. Returns (mode, sidecar_bytes_or_None, notes). mode: embedded | sidecar."""
    c2pa = c2pa_lib()
    signer = c2pa_signer(c2pa)
    ctx = c2pa_context(c2pa, {"builder": {"thumbnail": {"enabled": False}}})
    notes = []
    if not force_sidecar and embeddable(c2pa, path):
        for _ in range(EMBED_ATTEMPTS):
            has_parent, readable, own = existing_manifest(c2pa, path)
            if not readable:
                break
            try:
                return "embedded", None, notes + embed_in_place(c2pa, ctx, signer, path, title, workspace, run_id,
                                                                has_parent and not own)
            except SourceChanged:
                continue
        else:
            raise ProvenanceError("the file kept changing while it was being signed; it was left exactly as last "
                                  "written and the next write will sign it")
        notes.append("existing C2PA data could not be read, so it was left untouched and a sidecar was written")
    fmt = sidecar_format(path)
    builder = c2pa.Builder(manifest_definition(title, fmt, workspace, run_id, created=True), ctx)
    builder.set_no_embed()
    with open(path, "rb") as src:
        manifest_bytes = builder.sign(signer, fmt, src, io.BytesIO())
    return "sidecar", manifest_bytes, notes


def embed_in_place(c2pa, ctx, signer, path, title, workspace, run_id, has_parent):
    builder = c2pa.Builder(manifest_definition(title, mime_for(path), workspace, run_id, created=not has_parent), ctx)
    notes = []
    if has_parent:
        builder.set_intent(c2pa.C2paBuilderIntent.EDIT)
        builder.add_action({"action": "c2pa.edited", "digitalSourceType": DST_COMPOSITE})
        notes.append("existing Content Credentials kept as the parent ingredient")
    folder, base = os.path.split(os.path.abspath(path))
    stem, ext = os.path.splitext(base)
    tmp = os.path.join(folder, f".{stem}.tantra-tmp-{secrets.token_hex(3)}{ext}")
    before = sha256_hex(read_bytes(path))
    try:
        builder.sign_file(path, tmp, signer)
        # The hook is async: a Write/Edit that landed while we signed must win, never be reverted.
        if sha256_hex(read_bytes(path)) != before:
            raise SourceChanged(path)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return notes


def preserve_foreign_sidecar(c2pa, path, sidecar):
    """Keep a sidecar some other tool wrote; Tantra's own old sidecars are simply replaced."""
    if not os.path.isfile(sidecar):
        return None
    generator = ""
    try:
        with open(path, "rb") as fh, c2pa.Reader(sidecar_format(path), fh, manifest_data=read_bytes(sidecar)) as r:
            generator = generator_name(active_manifest(r))
    except Exception:  # noqa: BLE001 - unreadable sidecars are preserved too
        generator = ""
    if generator == SYSTEM:
        return None
    keep = sidecar + ".upstream"
    n = 1
    while os.path.exists(keep):
        n += 1
        keep = f"{sidecar}.upstream{n}"
    os.replace(sidecar, keep)
    return keep


def pem_cert_sha256(path):
    """sha256 of the DER bytes of the first certificate in a PEM file (the form identity.json records)."""
    try:
        text = read_bytes(path).decode("ascii", errors="replace")
    except OSError:
        return None
    m = re.search(r"-----BEGIN CERTIFICATE-----(.+?)-----END CERTIFICATE-----", text, re.S)
    if not m:
        return None
    try:
        return sha256_hex(base64.b64decode("".join(m.group(1).split())))
    except ValueError:
        return None


def c2pa_verify(path, trust_root, owner_root_sha256):
    """Return a dict: {ok, mode, state, trusted, owner_bound, failures, error}.

    A structurally valid manifest is not enough: anyone can make one with their own certificate.
    ok also requires the active manifest's signer to chain to the owner's root CA, i.e. state
    "Trusted" with that root as the ONLY trust anchor, where the root is the one whose sha256 the
    owner's Ed25519-signed record names (owner_root_sha256)."""
    base = {"ok": False, "mode": None, "state": None, "trusted": False, "owner_bound": False, "failures": [],
            "trust_root_sha256": pem_cert_sha256(trust_root) if trust_root else None}
    try:
        c2pa = c2pa_lib()
    except ProvenanceError as exc:
        return dict(base, error=str(exc))
    settings = {"trust": {"trust_anchors": read_bytes(trust_root).decode("ascii")}} if trust_root else {}
    ctx = c2pa_context(c2pa, settings) if settings else None
    sidecar = path + SIDECAR_SUFFIX
    try:
        reader, mode = None, None
        if embeddable(c2pa, path):
            reader = c2pa.Reader.try_create(path, context=ctx)
            mode = "embedded"
        if reader is None and os.path.isfile(sidecar):
            with open(path, "rb") as fh:
                reader = c2pa.Reader(sidecar_format(path), fh, manifest_data=read_bytes(sidecar), context=ctx)
            mode = "sidecar"
        if reader is None:
            return dict(base, error="no C2PA manifest (embedded or sidecar) found")
        with reader:
            state = reader.get_validation_state()
            results = reader.get_validation_results() or {}
    except Exception as exc:  # noqa: BLE001 - a tampered asset can fail to parse at all
        return dict(base, mode="unknown", state="Error", error=f"{type(exc).__name__}: {exc}")
    failures = [f.get("code") for f in (results.get("activeManifest") or {}).get("failure", [])]
    trusted = state == "Trusted"
    error = None
    if state not in ("Valid", "Trusted"):
        error = f"state {state}"
    elif not owner_root_sha256:
        error = ("cannot tie the C2PA signer to the owner: no Ed25519-verified signature record names the "
                 "owner's root CA")
    elif not trust_root:
        error = "the owner's root CA is not available; pass --trust-root PEM"
    elif base["trust_root_sha256"] != owner_root_sha256:
        error = (f"--trust-root {base['trust_root_sha256']} is not the owner's root CA "
                 f"({owner_root_sha256}, named in the signed record)")
    elif not trusted:
        error = (f"state {state}: the C2PA signer does NOT chain to the owner's root CA "
                 "(a foreign or substituted Content Credential)")
    return dict(base, ok=error is None, mode=mode, state=state, trusted=trusted, owner_bound=error is None,
                failures=failures, error=error)


def pick_trust_root(explicit, owner_root_sha256):
    """The explicit root, else the first known root whose sha256 is the owner's (else the first that exists).
    A root found on disk is only a candidate: c2pa_verify accepts it only if its sha256 is the signed one."""
    if explicit:
        return explicit
    candidates = (key_path("c2pa_root_ca.pem"), os.path.join(REPO_ROOT, "provenance", "public", "c2pa_root_ca.pem"))
    existing = [p for p in candidates if os.path.isfile(p)]
    for p in existing:
        if owner_root_sha256 and pem_cert_sha256(p) == owner_root_sha256:
            return p
    return existing[0] if existing else None


# ---- sign-file / verify-file -------------------------------------------------------

def sig_record(path, workspace, run_id, c2pa_mode, signer_fp, ident=None):
    """The Ed25519-signed record. It also names the owner's C2PA root CA and signer certificate and,
    for sidecars, the exact sidecar bytes, so a swapped-in Content Credential cannot pass."""
    data = read_bytes(path)
    ident = ident or {}
    record = {
        "v": 1, "file": os.path.basename(path), "sha256": sha256_hex(data), "size": len(data),
        "signer_fp": signer_fp, "signed_at": now_iso(), "workspace": workspace, "run_id": run_id,
        "c2pa": c2pa_mode, "c2pa_root_sha256": ident.get("root_ca_sha256"),
        "c2pa_signer_sha256": ident.get("signer_cert_sha256"),
    }
    sidecar = path + SIDECAR_SUFFIX
    if c2pa_mode == "sidecar" and os.path.isfile(sidecar):
        record["c2pa_sidecar_sha256"] = sha256_hex(read_bytes(sidecar))
    return record


def sign_file(path, workspace=None, run_id=None, fingerprint=True, title=None):
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        raise ProvenanceError(f"no such file: {path}")
    if path.endswith(SIG_SUFFIX) or path.endswith(SIDECAR_SUFFIX):
        raise ProvenanceError("refusing to sign a Tantra signature or C2PA sidecar file")
    ident = identity()
    ws_label = os.path.basename(os.path.normpath(workspace)) if workspace else None
    title = title or os.path.basename(path)
    result = {"ok": True, "file": path, "notes": [], "c2pa": "failed", "c2pa_error": None}
    try:
        c2pa = c2pa_lib()
        kept = preserve_foreign_sidecar(c2pa, path, path + SIDECAR_SUFFIX) if not embeddable(c2pa, path) else None
        if kept:
            result["notes"].append(f"another tool's C2PA sidecar was preserved as {os.path.basename(kept)}")
        mode, sidecar_bytes, notes = c2pa_sign(path, title, ws_label, run_id)
        if sidecar_bytes is not None:
            write_atomic(path + SIDECAR_SUFFIX, sidecar_bytes)
        result["c2pa"] = mode
        result["notes"].extend(notes)
    except Exception as exc:  # noqa: BLE001 - the Ed25519 layer still runs
        result["ok"] = False
        result["c2pa_error"] = f"{type(exc).__name__}: {exc}"
    key = load_private(key_path("identity_ed25519.pem"))
    fp = public_fp(key.public_key())
    record = sig_record(path, ws_label, run_id, result["c2pa"], fp, ident)
    record["sig"] = base64.b64encode(key.sign(canonical(record))).decode("ascii")
    write_atomic(path + SIG_SUFFIX, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    result.update(sha256=record["sha256"], sig_path=path + SIG_SUFFIX, signer_fp=fp, fingerprint=None)
    if fingerprint and os.path.splitext(path)[1].lower() in FINGERPRINT_EXTS:
        entry = register_fingerprint(path, label=title)
        result["fingerprint"] = entry["id"] if entry else None
    return result


def verify_sig(path, pubkey, expect_fp=None):
    sig_path = path + SIG_SUFFIX
    record = read_json(sig_path)
    if not isinstance(record, dict) or "sig" not in record:
        return {"ok": False, "error": f"missing or unreadable {os.path.basename(sig_path)}"}
    key_file, pub = resolve_pubkey(pubkey)
    fp, pinned = pin_status(pub, expect_fp)
    body = {k: v for k, v in record.items() if k != "sig"}
    data = read_bytes(path)
    checks = {
        "signature": ed_verify(pub, canonical(body), record["sig"]),
        "sha256": sha256_hex(data) == record.get("sha256"),
        "size": len(data) == record.get("size"),
        "signer": record.get("signer_fp") == fp,
    }
    if pinned is not None:
        checks["pinned_fp"] = pinned
    if record.get("c2pa_sidecar_sha256"):
        sidecar = path + SIDECAR_SUFFIX
        checks["c2pa_sidecar"] = os.path.isfile(sidecar) and sha256_hex(read_bytes(sidecar)) == record["c2pa_sidecar_sha256"]
    failed = [k for k, v in checks.items() if not v]
    return {"ok": not failed, "failed": failed, "key": key_file, "key_fp": fp, "pinned": pinned, "record": body,
            "error": ("failed checks: " + ", ".join(failed)) if failed else None}


def owner_root_from(sig):
    """The owner's root CA sha256, trusted only from a record whose Ed25519 signature verified."""
    if not sig.get("record") or {"signature", "signer", "pinned_fp"} & set(sig.get("failed") or []):
        return None
    rec = sig["record"]
    if rec.get("c2pa_root_sha256"):
        return rec["c2pa_root_sha256"]
    local = read_json(key_path("identity.json"), None) or {}  # records made before the root was recorded
    return local.get("root_ca_sha256") if local.get("signer_fp") == rec.get("signer_fp") else None


def cmd_sign_file(args):
    result = sign_file(args.path, args.workspace, args.run_id, not args.no_fingerprint, args.title)
    if args.json:
        print(json.dumps(result, ensure_ascii=True))
    else:
        print(f"Signed {result['file']}")
        print(f"  sha256 {result['sha256']}  signature {result['sig_path']}")
        print(f"  C2PA: {result['c2pa']}" + (f" ({result['c2pa_error']})" if result["c2pa_error"] else ""))
        if result["fingerprint"]:
            print(f"  fingerprint registered: {result['fingerprint']}")
        for note in result["notes"]:
            print(f"  note: {note}")
    return 0 if result["ok"] else 1


def cmd_verify_file(args):
    path = os.path.abspath(args.path)
    if not os.path.isfile(path):
        raise ProvenanceError(f"no such file: {path}")
    sig = verify_sig(path, args.pubkey, args.expect_fp)
    owner_root = owner_root_from(sig)
    trust_root = pick_trust_root(args.trust_root, owner_root)
    cred = c2pa_verify(path, trust_root, owner_root)
    ok = sig["ok"] and cred["ok"]
    if args.json:
        print(json.dumps({"ok": ok, "tantra_sig": sig, "c2pa": cred, "trust_root": trust_root}, ensure_ascii=True, default=str))
        return 0 if ok else 1
    print(f"File: {path}")
    print(f"  Tantra signature: {'PASS' if sig['ok'] else 'FAIL'}" + (f" - {sig['error']}" if sig.get("error") else ""))
    if sig.get("key_fp"):
        pin = PIN_HINT if sig["pinned"] is None else ("matches --expect-fp" if sig["pinned"] else "does NOT match --expect-fp")
        print(f"    verifying key fingerprint {sig['key_fp']} - {pin}")
    if sig.get("record"):
        rec = sig["record"]
        print(f"    signed_at {rec.get('signed_at')}, signer {rec.get('signer_fp')}, workspace {rec.get('workspace')}")
    detail = cred["error"] or f"state {cred['state']}, signer chains to the owner's root CA {cred['trust_root_sha256']}"
    print(f"  C2PA ({cred['mode'] or 'none'}): {'PASS' if cred['ok'] else 'FAIL'} - {detail}")
    if cred["failures"]:
        print(f"    validation codes: {', '.join(c for c in cred['failures'] if c)}")
    return 0 if ok else 1


# ---- frontmatter CMI + seal ids ----------------------------------------------------

def seal_id(key, kind, name):
    digest = hmac.new(key, f"{kind}:{name}".encode("utf-8"), hashlib.sha256).digest()
    return SEAL_PREFIX + base64.b32encode(digest).decode("ascii")[:16]


def split_frontmatter(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return lines[0], lines[1:i], lines[i:]
    return None


def top_key(line):
    m = re.match(r"^([A-Za-z0-9_-]+):", line)
    return m.group(1) if m else None


def fm_value(fm_lines, key):
    for line in fm_lines:
        if top_key(line) == key:
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def metadata_block(fm_lines):
    """(start, end) of the `metadata:` map (end exclusive), or None."""
    for i, line in enumerate(fm_lines):
        if top_key(line) == "metadata":
            end = i + 1
            while end < len(fm_lines) and fm_lines[end][:1] in (" ", "\t") and fm_lines[end].strip():
                end += 1
            return i, end
    return None


def child_key(line):
    m = re.match(r"^\s+([A-Za-z0-9_-]+):", line)
    return m.group(1) if m else None


def sealed_agent_lines(fm, eol, seal):
    keep = [ln for ln in fm if top_key(ln) not in (*AGENT_CMI, SEAL_KEY)]
    existing = [ln for ln in fm if top_key(ln) == SEAL_KEY]
    added = [f"{k}: {v}{eol}" for k, v in AGENT_CMI.items()]
    added += [f"{SEAL_KEY}: {seal}{eol}"] if seal else existing[-1:]
    return keep + added


def sealed_skill_lines(fm, eol, seal):
    block = metadata_block(fm)
    if block and fm[block[0]].split(":", 1)[1].strip():
        raise ProvenanceError("inline `metadata:` value is not supported; convert it to a block map")
    children = fm[block[0] + 1: block[1]] if block else []
    indent = re.match(r"^(\s+)", children[0]).group(1) if children else "  "
    existing = [c for c in children if child_key(c) == SEAL_KEY]
    kept_children = [c for c in children if child_key(c) not in ("author", SEAL_KEY)]
    ours = [f"{indent}author: {OWNER}{eol}"]
    ours += [f"{indent}{SEAL_KEY}: {seal}{eol}"] if seal else existing[-1:]
    head, tail = (fm[: block[0] + 1], fm[block[1]:]) if block else (list(fm) + [f"metadata:{eol}"], [])
    body = [ln for ln in head + kept_children + ours + tail if top_key(ln) != "license"]
    at = next(i for i, ln in enumerate(body) if top_key(ln) == "metadata")
    return body[:at] + [f"license: {SKILL_LICENSE}{eol}"] + body[at:]


def seal_text(text, kind, name, key, cmi_only):
    bom = "﻿" if text.startswith("﻿") else ""
    parts = split_frontmatter(text[len(bom):])
    if parts is None:
        raise ProvenanceError("no YAML frontmatter")
    opener, fm, closer = parts
    eol = "\r\n" if opener.endswith("\r\n") else "\n"
    seal = seal_id(key, kind, name) if key and not cmi_only else None
    new_fm = sealed_agent_lines(fm, eol, seal) if kind == "agent" else sealed_skill_lines(fm, eol, seal)
    return bom + opener + "".join(new_fm) + "".join(closer)


def cmi_targets(repo):
    patterns = load_third_party(repo)
    targets = []
    agents = os.path.join(repo, ".claude", "agents")
    skills = os.path.join(repo, ".claude", "skills")
    if os.path.isdir(agents):
        targets += [("agent", os.path.join(agents, f)) for f in sorted(os.listdir(agents)) if f.endswith(".md")]
    if os.path.isdir(skills):
        for d in sorted(os.listdir(skills)):
            path = os.path.join(skills, d, "SKILL.md")
            if os.path.isfile(path):
                targets.append(("skill", path))
    out, skipped = [], []
    for kind, path in targets:
        rel = os.path.relpath(path, repo).replace(os.sep, "/")
        (skipped if excluded(rel, patterns) else out).append((kind, path, rel))
    return out, skipped


def doc_name(kind, path, fm_text):
    parts = split_frontmatter(fm_text.lstrip("﻿"))
    name = fm_value(parts[1], "name") if parts else None
    if name:
        return name
    return os.path.splitext(os.path.basename(path))[0] if kind == "agent" else os.path.basename(os.path.dirname(path))


def read_seal(kind, text):
    parts = split_frontmatter(text.lstrip("﻿"))
    if not parts:
        return None
    fm = parts[1]
    if kind == "agent":
        return fm_value(fm, SEAL_KEY)
    block = metadata_block(fm)
    if not block:
        return None
    for line in fm[block[0] + 1: block[1]]:
        if child_key(line) == SEAL_KEY:
            return line.split(":", 1)[1].strip()
    return None


def cmd_seal_frontmatter(args):
    repo = os.path.abspath(args.repo)
    key = fingerprint_key(required=False)
    if not key and not args.cmi_only:
        print(f"note: no fingerprint.key in {keys_dir()}; writing CMI only, existing seal ids are left as they are.")
    targets, skipped = cmi_targets(repo)
    changed, issues = [], []
    for kind, path, rel in targets:
        raw = read_bytes(path).decode("utf-8")
        try:
            new = seal_text(raw, kind, doc_name(kind, path, raw), key, args.cmi_only)
        except ProvenanceError as exc:
            issues.append(f"{rel}: {exc}")
            continue
        if new == raw:
            continue
        if args.check:
            issues.append(f"{rel}: {describe_gap(kind, raw, new)}")
        else:
            write_atomic(path, new.encode("utf-8"))
            changed.append(rel)
    summary = f"{len(issues)} with issues" if args.check else f"{len(changed)} updated, {len(issues)} with issues"
    print(f"seal-frontmatter: {len(targets)} first-party files, {summary}, {len(skipped)} third-party skipped")
    for line in changed + issues:
        print(f"  {line}")
    return 1 if issues else 0


def describe_gap(kind, raw, new):
    old_seal, new_seal = read_seal(kind, raw), read_seal(kind, new)
    if new_seal and old_seal and old_seal != new_seal:
        return f"invalid seal {old_seal}"
    if new_seal and not old_seal:
        return "seal missing" + ("" if AGENT_CMI["author"] in raw else "; CMI missing")
    return "CMI missing or outdated"


def cmd_verify_seal(args):
    repo = os.path.abspath(args.repo)
    target = args.target
    if os.path.isfile(target):
        path = os.path.abspath(target)
        kind = args.kind or ("skill" if os.path.basename(path) == "SKILL.md" else "agent")
    else:
        kind = args.kind or ("agent" if os.path.isfile(os.path.join(repo, ".claude", "agents", target + ".md")) else "skill")
        path = (os.path.join(repo, ".claude", "agents", target + ".md") if kind == "agent"
                else os.path.join(repo, ".claude", "skills", target, "SKILL.md"))
    raw = read_bytes(path).decode("utf-8") if os.path.isfile(path) else ""
    name = doc_name(kind, path, raw) if raw else target
    found = args.seal or (read_seal(kind, raw) if raw else None)
    if not found:
        print(f"{kind} {name}: no tantra-seal found (pass --seal ID to check an id seen elsewhere)")
        return 1
    expected = seal_id(fingerprint_key(), kind, name)
    ok = hmac.compare_digest(found, expected)
    print(f"{kind} {name}: seal {found} is {'VALID - issued by this owner key' if ok else 'NOT VALID for this owner key'}")
    return 0 if ok else 1


# ---- keyed fingerprints ("SynthID-style", detector-side) ---------------------------

IGNORABLE_RANGES = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
    (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
    (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)


def ignorable(ch):
    cp = ord(ch)
    return unicodedata.category(ch) == "Cf" or any(lo <= cp <= hi for lo, hi in IGNORABLE_RANGES)


def normalise_words(text):
    """NFKC, casefold, drop default-ignorables, punctuation/symbols -> space, split."""
    out = []
    for ch in unicodedata.normalize("NFKC", text).casefold():
        if ignorable(ch):
            continue
        cat = unicodedata.category(ch)
        out.append(" " if cat[0] in "PSZC" or ch.isspace() else ch)
    return "".join(out).split()


def shingle_hashes(words, key):
    if not words:
        return []
    size = min(SHINGLE_WORDS, len(words))
    grams = (" ".join(words[i:i + size]) for i in range(len(words) - size + 1))
    return [int.from_bytes(hmac.new(key, g.encode("utf-8"), hashlib.sha256).digest()[:8], "big") for g in grams]


def winnow(hashes, window=WINNOW_WINDOW):
    if len(hashes) <= window:
        return set(hashes)
    picked = set()
    for i in range(len(hashes) - window + 1):
        chunk = hashes[i:i + window]
        low = min(chunk)
        picked.add(i + max(j for j, h in enumerate(chunk) if h == low))
    return {hashes[i] for i in picked}


def fingerprint_text(text, key):
    return {format(h, "016x") for h in winnow(shingle_hashes(normalise_words(text), key))}


def read_text(path):
    return read_bytes(path).decode("utf-8", errors="replace")


def load_registry():
    entries = {}
    path = registry_path()
    if not os.path.isfile(path):
        return entries
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and row.get("fps") is not None:
                entries[row.get("path") or row.get("id")] = row
    return entries


def register_fingerprint(path, label=None, key=None, entries=None):
    """Append a fingerprint entry unless this exact content is already registered for this path."""
    path = os.path.abspath(path)
    key = key or fingerprint_key()
    data = read_bytes(path)
    digest = sha256_hex(data)
    entries = load_registry() if entries is None else entries
    prior = entries.get(path)
    if prior and prior.get("sha256") == digest:
        return None
    fps = sorted(fingerprint_text(data.decode("utf-8", errors="replace"), key))
    row = {"id": "fp-" + digest[:16], "label": label or os.path.basename(path), "path": path, "sha256": digest,
           "created_at": now_iso(), "n": len(fps), "fps": fps}
    os.makedirs(os.path.dirname(registry_path()), exist_ok=True)
    with open(registry_path(), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    entries[path] = row
    return row


def verdict(score):
    for threshold, label in VERDICTS:
        if score >= threshold:
            return label
    return "none"


def compare(query, registered):
    """containment = |Q&R|/|Q|, coverage = |Q&R|/|R|, resemblance = Jaccard."""
    if not query or not registered:
        return 0.0, 0.0, 0.0
    inter = len(query & registered)
    containment = inter / len(query)
    coverage = inter / len(registered)
    resemblance = inter / len(query | registered)
    return containment, coverage, resemblance


def match_fingerprints(text, key=None, entries=None, top=5, minimum=0.05):
    """Rank registered documents against `text`.

    A verdict needs real evidence: at least MIN_SHARED_FPS shared fingerprints, and containment only
    counts for a query of at least MIN_QUERY_FPS fingerprints. Without these floors one stock phrase
    ("at the end of the day") scores containment 1.0 against any document that uses it."""
    key = key or fingerprint_key()
    query = fingerprint_text(text, key)
    rows = []
    for entry in (load_registry() if entries is None else entries).values():
        registered = set(entry.get("fps") or [])
        shared = len(query & registered)
        if shared < MIN_SHARED_FPS:
            continue
        containment, coverage, resemblance = compare(query, registered)
        score = max(containment if len(query) >= MIN_QUERY_FPS else 0.0,
                    coverage if len(registered) >= MIN_FPS_FOR_COVERAGE else 0.0)
        if score >= minimum:
            rows.append({"id": entry.get("id"), "label": entry.get("label"), "path": entry.get("path"),
                         "shared": shared, "containment": round(containment, 4), "coverage": round(coverage, 4),
                         "resemblance": round(resemblance, 4), "score": round(score, 4), "verdict": verdict(score)})
    rows.sort(key=lambda r: r["score"], reverse=True)
    return {"query_fps": len(query), "insufficient_text": len(query) < MIN_QUERY_FPS, "matches": rows[:top]}


def cmd_fp_register(args):
    row = register_fingerprint(args.path, args.label)
    print(f"registered {row['id']} ({row['n']} fingerprints) {row['path']}" if row
          else f"already registered with identical content: {os.path.abspath(args.path)}")
    return 0


def cmd_fp_register_os(args):
    repo = os.path.abspath(args.repo)
    key = fingerprint_key()
    entries = load_registry()
    added = skipped = 0
    for rel in sealable_files(repo):
        path = os.path.join(repo, rel)
        if os.path.splitext(rel)[1].lower() not in OS_FINGERPRINT_EXTS or not os.path.isfile(path):
            continue
        if register_fingerprint(path, label="os:" + rel, key=key, entries=entries):
            added += 1
        else:
            skipped += 1
    print(f"fingerprint register-os: {added} registered, {skipped} unchanged (registry {registry_path()})")
    return 0


def cmd_fp_match(args):
    result = match_fingerprints(read_text(args.path), top=args.top, minimum=args.min)
    if args.json:
        print(json.dumps(result, ensure_ascii=True))
        return 0
    print(f"{args.path}: {result['query_fps']} fingerprints; matches at or above {args.min}:")
    if result["insufficient_text"]:
        print(f"  note: insufficient text (fewer than {MIN_QUERY_FPS} fingerprints); only a short registered "
              "document it covers can match")
    if not result["matches"]:
        print("  none")
    for r in result["matches"]:
        print(f"  {r['verdict']:<15} shared {r['shared']} containment {r['containment']:.2f} coverage {r['coverage']:.2f} "
              f"resemblance {r['resemblance']:.2f}  {r['label']}  ({r['path']})")
    return 0


def cmd_fp_list(args):
    entries = load_registry()
    print(f"{len(entries)} registered document(s) in {registry_path()}")
    for e in sorted(entries.values(), key=lambda r: r.get("created_at", "")):
        print(f"  {e.get('id')}  n={e.get('n'):<6} {e.get('created_at')}  {e.get('label')}")
    return 0


# ---- CLI ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(prog="provenance.py", description="Tantra Seal: signatures, C2PA and keyed fingerprints.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create the owner's signing keys under TANTRA_HOME/keys")
    s.add_argument("--name", required=True)
    s.add_argument("--email")
    s.add_argument("--force", action="store_true")
    s.add_argument("--export-public", metavar="DIR")
    s.set_defaults(func=cmd_init)

    s = sub.add_parser("sign-os", help="sign a manifest of every first-party tracked file")
    s.add_argument("--repo", default=REPO_ROOT)
    s.add_argument("--tsa", metavar="URL")
    s.set_defaults(func=cmd_sign_os)

    s = sub.add_parser("verify-os", help="verify the OS manifest signature and every file")
    s.add_argument("--repo", default=REPO_ROOT)
    s.add_argument("--pubkey")
    s.add_argument("--expect-fp", metavar="SHA256", help="owner's Ed25519 key fingerprint, obtained out of band")
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=cmd_verify_os)

    s = sub.add_parser("sign-file", help="C2PA + Ed25519 sign one deliverable")
    s.add_argument("path")
    s.add_argument("--workspace")
    s.add_argument("--run-id")
    s.add_argument("--no-fingerprint", action="store_true")
    s.add_argument("--title")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_sign_file)

    s = sub.add_parser("verify-file", help="verify a signed deliverable")
    s.add_argument("path")
    s.add_argument("--trust-root")
    s.add_argument("--pubkey")
    s.add_argument("--expect-fp", metavar="SHA256", help="owner's Ed25519 key fingerprint, obtained out of band")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_verify_file)

    s = sub.add_parser("seal-frontmatter", help="write copyright-management info + seal ids into agent/skill frontmatter")
    s.add_argument("--check", action="store_true")
    s.add_argument("--cmi-only", action="store_true")
    s.add_argument("--repo", default=REPO_ROOT)
    s.set_defaults(func=cmd_seal_frontmatter)

    s = sub.add_parser("verify-seal", help="check one agent/skill seal id against the owner key")
    s.add_argument("target", metavar="NAME_OR_PATH")
    s.add_argument("--seal")
    s.add_argument("--kind", choices=["agent", "skill"])
    s.add_argument("--repo", default=REPO_ROOT)
    s.set_defaults(func=cmd_verify_seal)

    fp = sub.add_parser("fingerprint", help="keyed text fingerprints (detector-side, nothing embedded)")
    fsub = fp.add_subparsers(dest="fpcmd", required=True)
    s = fsub.add_parser("register")
    s.add_argument("path")
    s.add_argument("--label")
    s.set_defaults(func=cmd_fp_register)
    s = fsub.add_parser("register-os")
    s.add_argument("--repo", default=REPO_ROOT)
    s.set_defaults(func=cmd_fp_register_os)
    s = fsub.add_parser("match")
    s.add_argument("path")
    s.add_argument("--top", type=int, default=5)
    s.add_argument("--min", type=float, default=0.05)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_fp_match)
    s = fsub.add_parser("list")
    s.set_defaults(func=cmd_fp_list)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ProvenanceError as exc:
        print(f"provenance: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
