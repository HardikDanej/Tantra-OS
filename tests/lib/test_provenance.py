"""Tantra Seal (.claude/lib/provenance.py): keys, C2PA + Ed25519 signing, OS manifest,
frontmatter CMI/seal ids and keyed fingerprints. Every test uses a throwaway TANTRA_HOME."""
import base64
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = os.path.join(REPO, ".claude", "lib")
if LIB not in sys.path:
    sys.path.insert(0, LIB)

import provenance as prov  # noqa: E402

HAS_CRYPTO = importlib.util.find_spec("cryptography") is not None
HAS_C2PA = importlib.util.find_spec("c2pa") is not None
HAS_GIT = shutil.which("git") is not None
KB_DIR = os.path.join(REPO, "knowledge-bases")


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = prov.main(argv)
    return code, out.getvalue() + err.getvalue()


def png_bytes(rgb=b"\x00\xff\x00"):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(b"\x00" + rgb)) + chunk(b"IEND", b"")


def git(*args):
    """Per-call settings only: never touches any git config file."""
    subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false", *args], check=True)


def slurp(path, mode="rb"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as fh:
        return fh.read()


def load_json(path):
    return json.loads(slurp(path, "r"))


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    return path


class HomeCase(unittest.TestCase):
    """Creates a TANTRA_HOME with fresh keys once per class."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="tantra_prov_")
        cls.home = os.path.join(cls.tmp, "home")
        cls.env = mock.patch.dict(os.environ, {"TANTRA_HOME": cls.home})
        cls.env.start()
        os.environ.pop("TANTRA_KEY_PASSPHRASE", None)
        if HAS_CRYPTO:
            code, out = run(["init", "--name", "Test Owner", "--email", "owner@example.com"])
            assert code == 0, out

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def path(self, *parts):
        return os.path.join(self.tmp, *parts)


# ---- keys ---------------------------------------------------------------------------

@unittest.skipUnless(HAS_CRYPTO, "cryptography not installed")
class InitTests(HomeCase):
    def test_creates_every_key_file_outside_repo(self):
        for name in prov.KEY_FILES:
            self.assertTrue(os.path.isfile(os.path.join(self.home, "keys", name)), name)
        ident = load_json(os.path.join(self.home, "keys", "identity.json"))
        self.assertEqual(ident["name"], "Test Owner")
        self.assertEqual(len(ident["signer_fp"]), 64)
        self.assertFalse(self.home.startswith(REPO))

    def test_refuses_overwrite_without_force(self):
        before = slurp(os.path.join(self.home, "keys", "identity_ed25519.pem"))
        code, out = run(["init", "--name", "Someone Else"])
        self.assertEqual(code, 1)
        self.assertIn("Refusing", out)
        self.assertEqual(before, slurp(os.path.join(self.home, "keys", "identity_ed25519.pem")))

    def test_export_public_has_no_private_material(self):
        dest = self.path("public")
        code, _ = run(["init", "--name", "Test Owner", "--export-public", dest])
        self.assertEqual(code, 0)
        names = set(os.listdir(dest))
        self.assertEqual(names, {"identity_ed25519.pub.pem", "c2pa_root_ca.pem", "c2pa_signer.pem",
                                 "c2pa_chain.pem", "fingerprints.json"})
        for name in names:
            data = slurp(os.path.join(dest, name))
            self.assertNotIn(b"PRIVATE KEY", data, name)
        key = slurp(os.path.join(self.home, "keys", "fingerprint.key"))
        self.assertNotIn(base64.b64encode(key), b"".join(slurp(os.path.join(dest, n)) for n in names))

    def test_private_files_are_created_0600(self):
        """Review finding: private keys were written with default permissions, then chmod'ed."""
        modes = []
        real_open = os.open

        def spy(path, flags, mode=0o777, *a, **kw):
            modes.append((flags, mode))
            return real_open(path, flags, mode, *a, **kw)

        target = self.path("perm", "secret.pem")
        with mock.patch.object(prov.os, "open", spy):
            prov.write_atomic(target, b"secret", private=True)
        self.assertTrue(modes, "private material must be created through os.open with an explicit mode")
        flags, mode = modes[0]
        self.assertEqual(mode, 0o600)
        self.assertTrue(flags & os.O_EXCL)
        self.assertEqual(slurp(target), b"secret")
        if os.name == "posix":
            self.assertEqual(os.stat(target).st_mode & 0o077, 0)
            self.assertEqual(os.stat(os.path.join(self.home, "keys")).st_mode & 0o077, 0)

    def test_signer_certificate_profile(self):
        from cryptography import x509
        leaf = x509.load_pem_x509_certificate(slurp(os.path.join(self.home, "keys", "c2pa_signer.pem")))
        root = x509.load_pem_x509_certificate(slurp(os.path.join(self.home, "keys", "c2pa_root_ca.pem")))
        eku = {o.dotted_string for o in leaf.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value}
        self.assertEqual(eku, {"1.3.6.1.5.5.7.3.4", prov.EKU_DOCUMENT_SIGNING})
        self.assertFalse(leaf.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertTrue(root.extensions.get_extension_for_class(x509.BasicConstraints).value.ca)
        self.assertEqual(leaf.issuer, root.subject)
        self.assertIn("Test Owner", leaf.subject.rfc4514_string())


@unittest.skipUnless(HAS_CRYPTO and HAS_C2PA, "cryptography/c2pa not installed")
class PassphraseTests(unittest.TestCase):
    def test_keys_encrypted_and_required(self):
        tmp = tempfile.mkdtemp(prefix="tantra_pw_")
        self.addCleanup(shutil.rmtree, tmp, True)
        home = os.path.join(tmp, "home")
        with mock.patch.dict(os.environ, {"TANTRA_HOME": home, "TANTRA_KEY_PASSPHRASE": "correct horse"}):
            self.assertEqual(run(["init", "--name", "PW Owner"])[0], 0)
            self.assertIn(b"ENCRYPTED", slurp(os.path.join(home, "keys", "identity_ed25519.pem")))
            doc = write(os.path.join(tmp, "a.md"), "# encrypted keys still sign\n")
            self.assertEqual(run(["sign-file", doc, "--no-fingerprint"])[0], 0)
            self.assertEqual(run(["verify-file", doc])[0], 0)
        with mock.patch.dict(os.environ, {"TANTRA_HOME": home}):
            os.environ.pop("TANTRA_KEY_PASSPHRASE", None)
            code, out = run(["sign-file", doc, "--no-fingerprint"])
            self.assertEqual(code, 2)
            self.assertIn("TANTRA_KEY_PASSPHRASE", out)


# ---- sign-file / verify-file ------------------------------------------------------------

@unittest.skipUnless(HAS_CRYPTO and HAS_C2PA, "cryptography/c2pa not installed")
class SignFileTests(HomeCase):
    def sign(self, path, *extra):
        code, out = run(["sign-file", path, "--json", *extra])
        return code, json.loads(out.strip().splitlines()[-1])

    def verify(self, path, *extra):
        code, out = run(["verify-file", path, "--json", *extra])
        return code, json.loads(out.strip().splitlines()[-1])

    def test_png_embeds_and_verifies_then_tamper_fails(self):
        png = write(self.path("deliv", "hero.png"), png_bytes())
        code, res = self.sign(png, "--workspace", self.path("acme-client"), "--run-id", "run-7")
        self.assertEqual(code, 0, res)
        self.assertEqual(res["c2pa"], "embedded")
        self.assertFalse(os.path.exists(png + ".c2pa"))
        self.assertIsNone(res["fingerprint"])
        record = load_json(png + ".tantra-sig.json")
        self.assertEqual((record["workspace"], record["run_id"], record["file"]), ("acme-client", "run-7", "hero.png"))
        code, ver = self.verify(png)
        self.assertEqual(code, 0, ver)
        self.assertEqual(ver["c2pa"]["state"], "Trusted")
        with open(png, "ab") as fh:
            fh.write(b"tampered")
        code, ver = self.verify(png)
        self.assertEqual(code, 1)
        self.assertFalse(ver["tantra_sig"]["ok"])
        self.assertFalse(ver["c2pa"]["ok"])

    def test_c2pa_assertions_declare_ai_and_owner(self):
        import c2pa
        png = write(self.path("assert", "a.png"), png_bytes(b"\x10\x20\x30"))
        self.assertEqual(self.sign(png)[0], 0)
        with c2pa.Reader(png) as reader:
            store = json.loads(reader.json())
        active = store["manifests"][store["active_manifest"]]
        labels = {a["label"]: a["data"] for a in active["assertions"]}
        actions = next(v for k, v in labels.items() if k.startswith("c2pa.actions"))
        self.assertEqual(actions["actions"][0]["digitalSourceType"], prov.DST_CREATED)
        self.assertEqual(labels[prov.ASSERTION_LABEL]["operator"], "Test Owner")
        self.assertEqual(labels[prov.ASSERTION_LABEL]["statement"], prov.STATEMENT)
        self.assertEqual(labels["cawg.training-mining"]["entries"]["cawg.ai_training"]["use"], "notAllowed")
        self.assertEqual(active["claim_generator_info"][0]["name"], "Tantra")

    def other_home(self):
        other = os.path.join(self.tmp, "other_home")
        if not os.path.isdir(os.path.join(other, "keys")):
            with mock.patch.dict(os.environ, {"TANTRA_HOME": other}):
                run(["init", "--name", "Test Owner"])
        return other

    def sign_as_other(self, path):
        with mock.patch.dict(os.environ, {"TANTRA_HOME": self.other_home()}):
            return self.sign(path, "--no-fingerprint")

    def test_resign_keeps_existing_credentials_as_parent(self):
        import c2pa
        png = write(self.path("chain", "c.png"), png_bytes(b"\x01\x02\x03"))
        self.assertEqual(self.sign_as_other(png)[0], 0, "upstream credential from someone else's signer")
        code, res = self.sign(png)
        self.assertEqual(code, 0, res)
        self.assertTrue(any("parent ingredient" in n for n in res["notes"]))
        with c2pa.Reader(png) as reader:
            store = json.loads(reader.json())
        self.assertGreaterEqual(len(store["manifests"]), 2)
        active = store["manifests"][store["active_manifest"]]
        self.assertEqual(active["ingredients"][0]["relationship"], "parentOf")
        self.assertEqual(self.verify(png)[0], 0)

    def test_markdown_sidecar_verifies_then_tamper_fails(self):
        md = write(self.path("deliv", "brief.md"), "# Launch brief\r\n\r\nPositioning for the spring launch.\r\n")
        code, res = self.sign(md)
        self.assertEqual(code, 0, res)
        self.assertEqual(res["c2pa"], "sidecar")
        self.assertTrue(os.path.isfile(md + ".c2pa"))
        self.assertTrue(res["fingerprint"].startswith("fp-"))
        self.assertEqual(self.verify(md)[0], 0)
        with open(md, "ab") as fh:
            fh.write(b"one more line\n")
        code, ver = self.verify(md)
        self.assertEqual(code, 1)
        self.assertIn("assertion.dataHash.mismatch", ver["c2pa"]["failures"])

    def test_json_html_csv_pdf_use_sidecars(self):
        samples = {"data.json": b'{"a": 1}\n', "page.html": b"<p>hi</p>\n", "t.csv": b"a,b\n1,2\n",
                   "report.pdf": b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"}
        for name, data in samples.items():
            with self.subTest(name=name):
                path = write(self.path("types", name), data)
                code, res = self.sign(path, "--no-fingerprint")
                self.assertEqual((code, res["c2pa"]), (0, "sidecar"), res)
                self.assertEqual(self.verify(path)[0], 0)

    def test_edited_signature_record_fails(self):
        md = write(self.path("sigedit", "x.md"), "# x\n")
        self.assertEqual(self.sign(md, "--no-fingerprint")[0], 0)
        record = load_json(md + ".tantra-sig.json")
        record["workspace"] = "someone-else"
        write(md + ".tantra-sig.json", json.dumps(record))
        code, ver = self.verify(md)
        self.assertEqual(code, 1)
        self.assertIn("signature", ver["tantra_sig"]["failed"])

    def test_other_owner_key_does_not_verify(self):
        md = write(self.path("otherkey", "y.md"), "# y\n")
        self.assertEqual(self.sign(md, "--no-fingerprint")[0], 0)
        other = self.other_home()
        code, ver = self.verify(md, "--pubkey", os.path.join(other, "keys", "identity_ed25519.pub.pem"))
        self.assertEqual(code, 1)
        self.assertIn("signer", ver["tantra_sig"]["failed"])

    def test_impostor_c2pa_sidecar_fails(self):
        """Review finding: a well-formed sidecar from ANY signer used to PASS next to a valid Ed25519 record."""
        ours = write(self.path("impostor", "ours", "r.md"), "# Report\n\nSame words.\n")
        theirs = write(self.path("impostor", "theirs", "r.md"), "# Report\n\nSame words.\n")
        self.assertEqual(self.sign(ours, "--no-fingerprint")[0], 0)
        self.assertEqual(self.verify(ours)[0], 0)
        self.assertEqual(self.sign_as_other(theirs)[0], 0)
        shutil.copy(theirs + ".c2pa", ours + ".c2pa")
        code, ver = self.verify(ours)
        self.assertEqual(code, 1, ver)
        self.assertIn("c2pa_sidecar", ver["tantra_sig"]["failed"])
        self.assertFalse(ver["c2pa"]["ok"])
        self.assertFalse(ver["c2pa"]["owner_bound"])

    def test_foreign_credential_is_not_owner_bound(self):
        """The C2PA layer on its own must reject a signer that does not chain to the owner's root CA."""
        png = write(self.path("foreign_c2pa", "f.png"), png_bytes(b"\x21\x22\x23"))
        self.assertEqual(self.sign_as_other(png)[0], 0)
        root = os.path.join(self.home, "keys", "c2pa_root_ca.pem")
        cred = prov.c2pa_verify(png, root, prov.pem_cert_sha256(root))
        self.assertEqual(cred["state"], "Valid")
        self.assertFalse(cred["ok"])
        self.assertIn("does NOT chain", cred["error"])
        other_root = os.path.join(self.other_home(), "keys", "c2pa_root_ca.pem")
        cred = prov.c2pa_verify(png, other_root, prov.pem_cert_sha256(root))
        self.assertFalse(cred["ok"])
        self.assertIn("is not the owner's root CA", cred["error"])

    def test_trust_root_must_be_the_signed_owner_root(self):
        md = write(self.path("wrongroot", "w.md"), "# w\n")
        self.assertEqual(self.sign(md, "--no-fingerprint")[0], 0)
        other_root = os.path.join(self.other_home(), "keys", "c2pa_root_ca.pem")
        code, ver = self.verify(md, "--trust-root", other_root)
        self.assertEqual(code, 1)
        self.assertIn("is not the owner's root CA", ver["c2pa"]["error"])

    def test_expect_fp_pins_the_owner_key(self):
        md = write(self.path("pin", "p.md"), "# p\n")
        self.assertEqual(self.sign(md, "--no-fingerprint")[0], 0)
        fp = load_json(os.path.join(self.home, "keys", "identity.json"))["signer_fp"]
        self.assertEqual(self.verify(md, "--expect-fp", fp.upper())[0], 0)
        code, ver = self.verify(md, "--expect-fp", "00" * 32)
        self.assertEqual(code, 1)
        self.assertIn("pinned_fp", ver["tantra_sig"]["failed"])
        code, out = run(["verify-file", md])
        self.assertEqual(code, 0, out)
        self.assertIn(fp, out)
        self.assertIn("out of band", out)

    def test_own_resign_does_not_nest_manifests(self):
        """Review finding: every re-sign nested Tantra's previous manifest, growing the file without limit."""
        import c2pa
        png = write(self.path("nest", "n.png"), png_bytes(b"\x31\x32\x33"))
        sizes = []
        for _ in range(3):
            self.assertEqual(self.sign(png)[0], 0)
            sizes.append(os.path.getsize(png))
        self.assertLess(max(sizes) - min(sizes), 256, sizes)  # a few bytes of signature jitter, no nesting
        with c2pa.Reader(png) as reader:
            self.assertEqual(len(json.loads(reader.json())["manifests"]), 1)
        self.assertEqual(self.verify(png)[0], 0)

    def test_svg_gets_a_sidecar_and_is_not_rewritten(self):
        text = '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><rect width="4" height="4"/></svg>\n'
        svg = write(self.path("svg", "logo.svg"), text)
        code, res = self.sign(svg, "--no-fingerprint")
        self.assertEqual((code, res["c2pa"]), (0, "sidecar"), res)
        self.assertEqual(slurp(svg, "r"), text)
        self.assertEqual(self.verify(svg)[0], 0)

    def test_write_during_embed_is_not_reverted(self):
        """Review finding: an agent write landing while the async hook signed was silently reverted."""
        import c2pa
        png = write(self.path("race", "r.png"), png_bytes(b"\x41\x42\x43"))
        newer = png_bytes(b"\x99\x98\x97")
        original = c2pa.Builder.sign_file
        calls = []

        def racing(builder, source, dest, signer):
            out = original(builder, source, dest, signer)
            if not calls:
                write(source, newer)  # the agent's next Write lands mid-signing
            calls.append(source)
            return out

        with mock.patch.object(c2pa.Builder, "sign_file", racing):
            code, res = self.sign(png)
        self.assertEqual(code, 0, res)
        self.assertEqual(len(calls), 2, "the changed file is signed again, not overwritten")
        self.assertIn(zlib.compress(b"\x00\x99\x98\x97"), slurp(png))
        self.assertEqual(self.verify(png)[0], 0)

    def test_missing_signature_and_manifest(self):
        md = write(self.path("unsigned", "z.md"), "# z\n")
        code, ver = self.verify(md)
        self.assertEqual(code, 1)
        self.assertFalse(ver["tantra_sig"]["ok"])
        self.assertIn("no C2PA manifest", ver["c2pa"]["error"])

    def test_refuses_to_sign_own_outputs(self):
        md = write(self.path("own", "q.md"), "# q\n")
        self.assertEqual(self.sign(md, "--no-fingerprint")[0], 0)
        self.assertEqual(run(["sign-file", md + ".tantra-sig.json"])[0], 2)
        self.assertEqual(run(["sign-file", md + ".c2pa"])[0], 2)

    def test_foreign_sidecar_is_preserved(self):
        md = write(self.path("foreign", "f.md"), "# f\n")
        write(md + ".c2pa", b"not a tantra manifest")
        code, res = self.sign(md, "--no-fingerprint")
        self.assertEqual(code, 0, res)
        self.assertTrue(os.path.isfile(md + ".c2pa.upstream"))
        self.assertEqual(slurp(md + ".c2pa.upstream"), b"not a tantra manifest")
        self.assertEqual(self.verify(md)[0], 0)
        self.assertEqual(self.sign(md, "--no-fingerprint")[0], 0)
        self.assertFalse(os.path.exists(md + ".c2pa.upstream2"), "Tantra's own sidecar must just be replaced")

    def test_no_invisible_characters_are_embedded(self):
        text = "# Plain deliverable\n\nNothing hidden in here.\n"
        md = write(self.path("clean", "c.md"), text)
        self.assertEqual(self.sign(md)[0], 0)
        self.assertEqual(slurp(md, "r"), text)


# ---- OS manifest ------------------------------------------------------------------------

@unittest.skipUnless(HAS_CRYPTO and HAS_GIT, "cryptography or git not available")
class OsManifestTests(HomeCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="tantra_repo_", dir=self.tmp)
        git("init", "-q", self.repo)
        write(os.path.join(self.repo, "README.md"), b"# Tantra\r\nline two\r\n")
        write(os.path.join(self.repo, ".claude", "agents", "a.md"), "---\nname: a\n---\nbody\n")
        write(os.path.join(self.repo, "img.bin"), b"\x00\x01\r\n\x02")
        write(os.path.join(self.repo, ".claude", "skills", "unlazy", "SKILL.md"), "third party\n")
        write(os.path.join(self.repo, "provenance", "third_party.json"),
              slurp(os.path.join(REPO, "provenance", "third_party.json")))
        git("-C", self.repo, "add", "-A")

    def verify(self, *extra):
        return run(["verify-os", "--repo", self.repo, *extra])

    def test_sign_then_verify_and_detect_changes(self):
        code, out = run(["sign-os", "--repo", self.repo])
        self.assertEqual(code, 0, out)
        manifest = load_json(os.path.join(self.repo, "provenance", "os_manifest.json"))
        self.assertEqual(manifest["header"]["schema"], prov.MANIFEST_SCHEMA)
        self.assertEqual(manifest["header"]["owner"], "Test Owner")
        self.assertIn("README.md", manifest["files"])
        self.assertNotIn(".claude/skills/unlazy/SKILL.md", manifest["files"])
        self.assertFalse(any(p.startswith("provenance/os_manifest") for p in manifest["files"]))
        self.assertEqual(manifest["files"]["README.md"], prov.sha256_hex(b"# Tantra\nline two\n"))
        self.assertEqual(manifest["files"]["img.bin"], prov.sha256_hex(b"\x00\x01\r\n\x02"))
        self.assertEqual(self.verify()[0], 0)

        write(os.path.join(self.repo, "README.md"), b"# Tantra\nline two\n")
        self.assertEqual(self.verify()[0], 0, "CRLF -> LF checkout must not count as a modification")

        write(os.path.join(self.repo, "new.md"), "new\n")
        git("-C", self.repo, "add", "new.md")
        code, out = self.verify()
        self.assertEqual(code, 0)
        self.assertIn("NEW-UNSEALED", out)

        write(os.path.join(self.repo, ".claude", "agents", "a.md"), "---\nname: a\n---\nstolen body\n")
        code, out = self.verify()
        self.assertEqual(code, 1)
        self.assertRegex(out, r"MODIFIED\s+\.claude/agents/a\.md")

        os.remove(os.path.join(self.repo, "img.bin"))
        code, out = self.verify()
        self.assertIn("MISSING", out)

    def test_tampered_manifest_signature_fails(self):
        self.assertEqual(run(["sign-os", "--repo", self.repo])[0], 0)
        path = os.path.join(self.repo, "provenance", "os_manifest.json")
        manifest = load_json(path)
        manifest["header"]["owner"] = "Somebody Else"
        write(path, json.dumps(manifest))
        code, out = self.verify()
        self.assertEqual(code, 1)
        self.assertIn("INVALID", out)

    def test_expect_fp_catches_a_resigned_repo(self):
        """Review finding: a copier who re-signs with their own key and swaps provenance/public/ verified VALID."""
        self.assertEqual(run(["sign-os", "--repo", self.repo])[0], 0)
        owner_fp = load_json(os.path.join(self.home, "keys", "identity.json"))["signer_fp"]
        code, out = self.verify("--expect-fp", owner_fp)
        self.assertEqual(code, 0, out)
        self.assertIn(owner_fp, out)
        write(os.path.join(self.repo, "README.md"), "# Stolen\n")
        other = os.path.join(self.tmp, "copier_home")
        with mock.patch.dict(os.environ, {"TANTRA_HOME": other}):
            self.assertEqual(run(["init", "--name", "Test Owner", "--export-public",
                                  os.path.join(self.repo, "provenance", "public")])[0], 0)
            self.assertEqual(run(["sign-os", "--repo", self.repo])[0], 0)
        swapped = os.path.join(self.repo, "provenance", "public", "identity_ed25519.pub.pem")
        code, out = self.verify("--pubkey", swapped)
        self.assertEqual(code, 0, "without a pin the copier's own key verifies; the README says to pin")
        self.assertIn("out of band", out)
        code, out = self.verify("--pubkey", swapped, "--expect-fp", owner_fp)
        self.assertEqual(code, 1, out)
        self.assertIn("does NOT match --expect-fp", out)

    @unittest.skipUnless(HAS_C2PA, "c2pa not installed")
    def test_manifest_gets_c2pa_sidecar(self):
        code, out = run(["sign-os", "--repo", self.repo])
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.isfile(os.path.join(self.repo, "provenance", "os_manifest.c2pa")))

    def test_unreachable_tsa_is_skipped_gracefully(self):
        code, out = run(["sign-os", "--repo", self.repo, "--tsa", "http://127.0.0.1:9/tsa"])
        self.assertEqual(code, 0)
        self.assertIn("timestamp skipped", out)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "provenance", "os_manifest.tsr")))

    def test_not_a_git_repo_is_an_environment_error(self):
        self.assertEqual(run(["sign-os", "--repo", tempfile.mkdtemp(dir=self.tmp)])[0], 2)


class TsaDerTests(unittest.TestCase):
    def test_request_structure(self):
        digest = bytes(range(32))
        req = prov.tsa_request(digest, 12345)
        self.assertEqual(req[0], 0x30)
        self.assertEqual(req[1], len(req) - 2)
        self.assertIn(bytes.fromhex("0609608648016503040201"), req)
        self.assertIn(b"\x04\x20" + digest, req)
        self.assertTrue(req.endswith(b"\x01\x01\xff"))
        self.assertTrue(req[2:5] == b"\x02\x01\x01")

    def test_status_parsing(self):
        granted = prov.der(0x30, prov.der(0x30, prov.der_int(0)) + prov.der(0x30, b"\x00" * 200))
        rejected = prov.der(0x30, prov.der(0x30, prov.der_int(2)))
        self.assertEqual(prov.tsa_status(granted), 0)
        self.assertEqual(prov.tsa_status(rejected), 2)
        with self.assertRaises(ValueError):
            prov.tsa_status(b"garbage!")


class GlobTests(unittest.TestCase):
    def test_patterns(self):
        cases = [
            (".claude/skills/unlazy/**", ".claude/skills/unlazy/scripts/lib/x.mjs", True),
            (".claude/skills/unlazy/**", ".claude/skills/unlazy-other/SKILL.md", False),
            ("**/node_modules/**", "platform/node_modules/a/b.js", True),
            ("**/node_modules/**", "node_modules/a.js", True),
            ("**/package-lock.json", "platform/package-lock.json", True),
            ("**/*.pyc", "a/b/c.pyc", True),
            ("evals/results/**", "evals/run_evals.py", False),
            ("taxonomy/marketing_taxonomy.json", "taxonomy/marketing_taxonomy.json", True),
        ]
        for pattern, path, expected in cases:
            with self.subTest(pattern=pattern, path=path):
                self.assertEqual(bool(prov.glob_to_regex(pattern).match(path)), expected)

    def test_repo_third_party_file_excludes_unlazy(self):
        patterns = prov.load_third_party(REPO)
        self.assertTrue(prov.excluded(".claude/skills/unlazy/LICENSE", patterns))
        self.assertFalse(prov.excluded(".claude/agents/seo-agent.md", patterns))


# ---- frontmatter CMI --------------------------------------------------------------------

AGENTS = ["seo-agent", "chief-marketing-orchestrator", "technical-seo-subagent"]
SKILLS = ["caption-writer", "analytical-intelligence"]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FrontmatterTests(HomeCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="tantra_fm_", dir=self.tmp)
        self.originals = {}
        for name in AGENTS:
            src = os.path.join(REPO, ".claude", "agents", name + ".md")
            if not os.path.isfile(src):
                self.skipTest(f"{src} missing")
            self.copy(src, os.path.join(".claude", "agents", name + ".md"))
        for name in SKILLS + ["unlazy"]:
            self.copy(os.path.join(REPO, ".claude", "skills", name, "SKILL.md"), os.path.join(".claude", "skills", name, "SKILL.md"))
        self.copy(os.path.join(REPO, "provenance", "third_party.json"), os.path.join("provenance", "third_party.json"))

    def copy(self, src, rel):
        data = slurp(src)
        write(os.path.join(self.repo, rel), data)
        self.originals[rel.replace(os.sep, "/")] = data

    def read(self, rel):
        return slurp(os.path.join(self.repo, rel))

    def seal(self, *extra):
        return run(["seal-frontmatter", "--repo", self.repo, *extra])

    def test_check_seal_idempotent_and_verified(self):
        self.assertEqual(self.seal("--check")[0], 1)
        code, out = self.seal()
        self.assertEqual(code, 0, out)
        first = {rel: self.read(rel) for rel in self.originals}
        code, out = self.seal()
        self.assertIn("0 updated", out)
        self.assertEqual(first, {rel: self.read(rel) for rel in self.originals})
        self.assertEqual(self.seal("--check")[0], 0)
        for name in AGENTS:
            self.assertEqual(run(["verify-seal", name, "--repo", self.repo])[0], 0, name)
        for name in SKILLS:
            self.assertEqual(run(["verify-seal", name, "--repo", self.repo])[0], 0, name)

    def test_line_endings_body_and_third_party_preserved(self):
        self.seal()
        for rel, original in self.originals.items():
            new = self.read(rel)
            if "unlazy" in rel or rel.startswith("provenance/"):
                self.assertEqual(new, original, rel)
                continue
            crlf = b"\r\n" in original.split(b"\n", 1)[0] + b"\n"
            if crlf:
                self.assertEqual(new.count(b"\n"), new.count(b"\r\n"), f"{rel} lost CRLF")
            else:
                self.assertNotIn(b"\r\n", new, rel)
            body_old = original.split(b"\n---", 1)[1]
            body_new = new.split(b"\n---", 1)[1]
            self.assertEqual(body_old, body_new, f"{rel} body changed")

    def test_agent_and_skill_shapes(self):
        self.seal()
        agent = self.read(".claude/agents/seo-agent.md").decode("utf-8").replace("\r\n", "\n")
        fm = agent.split("\n---\n", 1)[0]
        self.assertTrue(fm.rstrip().splitlines()[-4].startswith("author: Hardik Danej"))
        self.assertIn("\ncopyright: Copyright (c) 2026 Hardik Danej. All rights reserved.", fm)
        self.assertIn("\nlicense: Proprietary, see LICENSE in the Tantra repository", fm)
        self.assertRegex(fm, r"\ntantra-seal: TS1-[A-Z2-7]{16}$")
        skill = self.read(".claude/skills/caption-writer/SKILL.md").decode("utf-8")
        fm = skill.split("\n---\n", 1)[0]
        self.assertIn("\nlicense: Proprietary. Copyright (c) 2026 Hardik Danej. All rights reserved.\nmetadata:\n"
                      "  author: Hardik Danej\n  tantra-seal: TS1-", fm)
        self.assertNotIn("\nauthor:", fm)

    def test_downstream_parsers_unchanged(self):
        taxonomy = load_module("taxonomy_registry_t", os.path.join(LIB, "taxonomy_registry.py"))
        model_routing = load_module("model_routing_t", os.path.join(LIB, "model_routing.py"))
        builder_path = os.path.join(REPO, "tools", "build_tantra_registry.py")
        builder = load_module("build_tantra_registry_t", builder_path) if os.path.isfile(builder_path) else None
        self.seal()
        for name in AGENTS:
            rel = f".claude/agents/{name}.md"
            old = self.originals[rel].decode("utf-8").replace("\r\n", "\n")
            new = self.read(rel).decode("utf-8").replace("\r\n", "\n")
            self.assertEqual(taxonomy.parse_frontmatter(old), taxonomy.parse_frontmatter(new), name)
            self.assertEqual(bool(model_routing.FRONTMATTER_RE.match(old)), bool(model_routing.FRONTMATTER_RE.match(new)))
            self.assertEqual(model_routing.MODEL_LINE_RE.findall(old), model_routing.MODEL_LINE_RE.findall(new))
            if builder:
                fm_old, body_old = builder.parse_frontmatter(old)
                fm_new, body_new = builder.parse_frontmatter(new)
                for key in ("name", "description", "tools"):
                    self.assertEqual(fm_old.get(key), fm_new.get(key), (name, key))
                self.assertEqual(builder._contract_fields(body_old), builder._contract_fields(body_new))

    def test_taxonomy_build_on_temp_copy(self):
        self.seal()
        os.makedirs(os.path.join(self.repo, ".claude", "lib"), exist_ok=True)
        shutil.copy(os.path.join(LIB, "taxonomy_registry.py"), os.path.join(self.repo, ".claude", "lib"))
        proc = subprocess.run([sys.executable, os.path.join(self.repo, ".claude", "lib", "taxonomy_registry.py"), "build"],
                              capture_output=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = load_json(os.path.join(self.repo, "taxonomy", "marketing_taxonomy.json"))
        nodes = data.get("nodes") or {}
        seo = nodes.get("seo-agent") if isinstance(nodes, dict) else next(n for n in nodes if n["id"] == "seo-agent")
        self.assertNotIn("tantra-seal", seo["definition"])
        self.assertNotIn("Hardik Danej", seo["definition"])

    def test_cmi_only_and_invalid_seal_detection(self):
        self.seal("--cmi-only")
        text = self.read(".claude/agents/seo-agent.md").decode("utf-8")
        self.assertIn("author: Hardik Danej", text)
        self.assertNotIn("tantra-seal", text)
        self.assertEqual(self.seal("--check", "--cmi-only")[0], 0)
        self.seal()
        forged = self.read(".claude/agents/seo-agent.md").decode("utf-8")
        forged = re.sub(r"tantra-seal: TS1-[A-Z2-7]{16}", "tantra-seal: TS1-AAAAAAAAAAAAAAAA", forged)
        write(os.path.join(self.repo, ".claude", "agents", "seo-agent.md"), forged)
        code, out = self.seal("--check")
        self.assertEqual(code, 1)
        self.assertIn("invalid seal TS1-AAAAAAAAAAAAAAAA", out)
        self.assertEqual(run(["verify-seal", "seo-agent", "--repo", self.repo])[0], 1)
        self.assertEqual(run(["verify-seal", "seo-agent", "--repo", self.repo,
                              "--seal", prov.seal_id(prov.fingerprint_key(), "agent", "seo-agent")])[0], 0)

    def test_existing_metadata_block_is_merged(self):
        rel = os.path.join(".claude", "skills", "caption-writer", "SKILL.md")
        text = "---\nname: caption-writer\ndescription: x\nmetadata:\n    version: 2\n    author: Someone\n---\nbody\n"
        write(os.path.join(self.repo, rel), text)
        self.seal()
        self.seal()
        out = self.read(rel).decode("utf-8")
        self.assertIn("metadata:\n    version: 2\n    author: Hardik Danej\n    tantra-seal: TS1-", out)
        self.assertNotIn("Someone", out)
        self.assertEqual(out.count("license:"), 1)

    def test_no_key_keeps_existing_seal(self):
        self.seal()
        sealed = self.read(".claude/agents/seo-agent.md")
        with mock.patch.dict(os.environ, {"TANTRA_HOME": os.path.join(self.tmp, "empty_home")}):
            code, out = self.seal()
        self.assertEqual(code, 0, out)
        self.assertIn("CMI only", out)
        self.assertEqual(sealed, self.read(".claude/agents/seo-agent.md"))


# ---- keyed fingerprints -----------------------------------------------------------------

def kb_text(name):
    return slurp(os.path.join(KB_DIR, name), "r")


@unittest.skipUnless(os.path.isdir(KB_DIR), "knowledge-bases missing")
class FingerprintRobustnessTests(unittest.TestCase):
    KEY = bytes(range(32))
    OTHER_KEY = bytes(range(32, 64))

    @classmethod
    def setUpClass(cls):
        cls.source = kb_text("ads-knowledge-base.md")
        cls.registered = prov.fingerprint_text(cls.source, cls.KEY)

    def score(self, text, key=None):
        return prov.compare(prov.fingerprint_text(text, key or self.KEY), self.registered)

    def test_identical(self):
        self.assertGreaterEqual(self.score(self.source)[0], 0.99)

    def test_reformatted(self):
        text = self.source.upper()
        text = re.sub(r"\s+", "  \n", text).replace("E", "E​").replace(".", " ;")
        text = "**" + text.replace(" A ", " _a_ ") + "**"
        text = text.replace("O", "O⁠").replace("I", "I️")
        self.assertGreaterEqual(self.score(text)[0], 0.9)

    def test_forty_percent_excerpt(self):
        words = self.source.split()
        excerpt = " ".join(words[int(len(words) * 0.3): int(len(words) * 0.7)])
        self.assertGreaterEqual(self.score(excerpt)[0], 0.9)

    def test_light_edits(self):
        words = self.source.split()
        edited = " ".join("zqx%d" % i if i % 12 == 0 else w for i, w in enumerate(words))
        self.assertGreaterEqual(self.score(edited)[0], 0.4)

    def test_unrelated_same_domain(self):
        for other in ("seo-knowledge-base.md", "pr-corporate-communications-knowledge-base.md"):
            if os.path.isfile(os.path.join(KB_DIR, other)):
                self.assertLess(self.score(kb_text(other))[0], 0.05, other)

    def test_different_key(self):
        self.assertLess(self.score(self.source, key=self.OTHER_KEY)[0], 0.01)

    def test_stock_phrase_gets_no_verdict(self):
        """Review finding: a one-line stock phrase scored "likely derived"/"strong match" on 1-4 fingerprints."""
        doc = self.source + "\n\nLet me know if you have any questions. At the end of the day, it works.\n"
        entries = {"doc": {"id": "fp-doc", "label": "doc", "path": "doc",
                           "fps": sorted(prov.fingerprint_text(doc, self.KEY))}}
        for phrase in ("Let me know if you have any questions.", "At the end of the day, it works."):
            with self.subTest(phrase=phrase):
                result = prov.match_fingerprints(phrase, key=self.KEY, entries=entries)
                self.assertTrue(result["insufficient_text"])
                self.assertEqual(result["matches"], [])
        words = self.source.split()
        excerpt = " ".join(words[200:600])
        result = prov.match_fingerprints(excerpt, key=self.KEY, entries=entries)
        self.assertFalse(result["insufficient_text"])
        self.assertEqual(result["matches"][0]["verdict"], "strong match")
        self.assertGreaterEqual(result["matches"][0]["shared"], prov.MIN_SHARED_FPS)

    def test_verdict_bands(self):
        self.assertEqual(prov.verdict(0.93), "strong match")
        self.assertEqual(prov.verdict(0.2), "likely derived")
        self.assertEqual(prov.verdict(0.06), "some overlap")
        self.assertEqual(prov.verdict(0.01), "none")


class NormaliseTests(unittest.TestCase):
    def test_invisible_and_markup_removed(self):
        self.assertEqual(prov.normalise_words("**Bra​nd** — `voice`⁠!"), ["brand", "voice"])
        self.assertEqual(prov.normalise_words("ＡＢＣ x"), ["abc", "x"])

    def test_short_text_still_fingerprints(self):
        self.assertEqual(len(prov.fingerprint_text("two words", bytes(32))), 1)
        self.assertEqual(prov.fingerprint_text("", bytes(32)), set())


@unittest.skipUnless(HAS_CRYPTO and os.path.isdir(KB_DIR), "cryptography or knowledge-bases missing")
class FingerprintCliTests(HomeCase):
    def test_register_match_list_and_dedupe(self):
        source = write(self.path("fp", "source.md"), kb_text("marketing-knowledge-base.md"))
        code, out = run(["fingerprint", "register", source, "--label", "master playbook"])
        self.assertEqual(code, 0, out)
        self.assertIn("registered fp-", out)
        self.assertIn("already registered", run(["fingerprint", "register", source])[1])
        words = kb_text("marketing-knowledge-base.md").split()
        suspect = write(self.path("fp", "suspect.txt"), " ".join(words[1000:3000]).lower())
        code, out = run(["fingerprint", "match", suspect, "--json"])
        result = json.loads(out)
        top = result["matches"][0]
        self.assertEqual(top["label"], "master playbook")
        self.assertEqual(top["verdict"], "strong match")
        unrelated = write(self.path("fp", "other.md"), kb_text("seo-knowledge-base.md"))
        code, out = run(["fingerprint", "match", unrelated, "--json"])
        self.assertFalse([m for m in json.loads(out)["matches"] if m["label"] == "master playbook"])
        self.assertIn("master playbook", run(["fingerprint", "list"])[1])
        rows = [json.loads(line) for line in slurp(prov.registry_path(), "r").splitlines()]
        self.assertTrue(all(set(r) >= {"id", "label", "path", "sha256", "created_at", "n", "fps"} for r in rows))

    @unittest.skipUnless(HAS_GIT, "git missing")
    def test_register_os(self):
        repo = tempfile.mkdtemp(prefix="tantra_fprepo_", dir=self.tmp)
        git("init", "-q", repo)
        write(os.path.join(repo, "a.md"), "alpha beta gamma delta epsilon zeta eta theta\n")
        write(os.path.join(repo, "b.png"), png_bytes())
        write(os.path.join(repo, ".claude", "skills", "unlazy", "SKILL.md"), "third party words here now\n")
        write(os.path.join(repo, "provenance", "third_party.json"),
              slurp(os.path.join(REPO, "provenance", "third_party.json")))
        git("-C", repo, "add", "-A")
        code, out = run(["fingerprint", "register-os", "--repo", repo])
        self.assertEqual(code, 0, out)
        self.assertIn("2 registered", out)
        labels = {r["label"] for r in prov.load_registry().values()}
        self.assertIn("os:a.md", labels)
        self.assertNotIn("os:.claude/skills/unlazy/SKILL.md", labels)
        self.assertIn("0 registered", run(["fingerprint", "register-os", "--repo", repo])[1])


class ReadmeTests(unittest.TestCase):
    def setUp(self):
        self.text = slurp(os.path.join(REPO, "provenance", "README.md"), "r")

    def test_third_party_flow_pins_the_owner_fingerprint(self):
        self.assertIn("--expect-fp", self.text)
        self.assertIn("out of band", self.text)
        self.assertRegex(self.text, r"(?is)do not trust.{0,80}provenance/public/")

    def test_1202_is_not_overstated(self):
        self.assertNotIn("is exactly what the licence and 17 USC 1202 cover", self.text)
        self.assertIn("knowingly", self.text)


if __name__ == "__main__":
    unittest.main()
