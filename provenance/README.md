# Tantra Seal — provenance for Tantra and its deliverables

Tantra is proprietary software, Copyright (c) 2026 Hardik Danej (see `LICENSE` and `NOTICE`).
Tantra Seal is the set of checks that show where a Tantra file or deliverable came from and whether
it has been changed since. Everything runs through one script:

```
python .claude/lib/provenance.py <command> ...
```

It needs the `cryptography` and `c2pa-python` packages. Run it with your normal Python, not `python -I -S`.

## Why there is no hidden text watermark

The original request was a "SynthID-style text watermark + C2PA". Some facts ruled out the obvious version:

- **Real SynthID-Text needs the model's token probabilities.** It is applied while the model samples
  tokens. Claude Code does not expose those, so no script here can apply it. Claude's output already
  carries Anthropic's own SynthID-Text-based watermark. That watermark uses no hidden characters and
  identifies no user.
- **Invisible-character marks are a liability.** Zero-width characters and similar tricks disappear
  after one normalisation pass. Security tools also flag them as "ASCII smuggling". They add hidden
  tokens to every agent load, and they conflict with Tantra's own `de-ai-ify` and `citation_guard`.
  Tantra Seal does not embed invisible characters anywhere.

The "SynthID-style" part is handled from the detector's side instead, with keyed fingerprints (layer 4).
Nothing gets hidden in the text, so there is nothing for anyone to strip.

## The four layers: what each one proves and what it doesn't

| Layer | Command | What it proves | What it does NOT prove |
|---|---|---|---|
| 1. Ed25519 signatures | `sign-os`, `verify-os`, `sign-file`, `verify-file` | A file is byte-for-byte what the owner's key signed, **provided the verifier checks that key's fingerprint against one obtained out of band** (see below). `os_manifest.json` lists a SHA-256 for every first-party tracked file, and one signature covers the whole list. | Who wrote the content first, or that nobody copied it. A copy with the signature removed is just an unsigned file. A copier can re-sign with their own key, so a signature checked against a key taken from the same copy proves nothing. |
| 2. C2PA Content Credentials | `sign-file`, `verify-file` | A tamper-evident record that the file was produced with AI assistance under the operator's direction (`digitalSourceType` = `trainedAlgorithmicMedia`), which system produced it, and a CAWG "no AI training / no data mining" notice. Existing credentials from other tools (Adobe, OpenAI, Anthropic and so on) are kept as the parent ingredient. `verify-file` passes the credential only if its signer chains to the owner's root CA, and that root's SHA-256 is named in the Ed25519-signed `.tantra-sig.json` (which also pins the exact sidecar bytes). | Legal ownership. C2PA records provenance "without limiting its use". Metadata can be stripped, and a sidecar can be separated from its file. The certificate is self-issued, so other validators report **Valid** but `signingCredential.untrusted` unless they are given the owner's root CA. |
| 3. Copyright notices in frontmatter | `seal-frontmatter`, `verify-seal` | Every first-party agent and skill carries visible author, copyright and licence lines (copyright-management information in the 17 USC 1202 sense), plus a `tantra-seal` id. Only the owner's secret key can produce that id. | That a file without the lines isn't Tantra's. Removing them breaches the licence and, when done knowingly to enable or conceal infringement, may also violate 17 USC 1202. Nothing technically stops it. |
| 4. Keyed fingerprints | `fingerprint register / register-os / match / list` | That a suspect text is derived from a registered document: identical, reformatted, excerpted or lightly edited. The shingles are keyed with the owner's secret HMAC key, so nobody else can compute or game them. | Anything about text that isn't in the registry. A full paraphrase defeats it, the same limit Google states for SynthID. Very short text (a sentence or a stock phrase) gets no verdict. It is evidence, not proof of authorship. |

**No watermark prevents copying.** The layers give evidence of origin and of tampering. That evidence
supports licence enforcement. It does not replace it.

## One-time setup (owner)

```
python .claude/lib/provenance.py init --name "Hardik Danej" --email you@example.com --export-public provenance/public
```

- Keys are created in `~/.tantra/keys/` (or `$TANTRA_HOME/keys/`), never in the repo:
  `identity_ed25519.pem` (+ `.pub.pem`), `fingerprint.key`, `c2pa_root_ca.{key,pem}`,
  `c2pa_signer.{key,pem}`, `c2pa_chain.pem` and `identity.json`.
- To encrypt the private keys, set `TANTRA_KEY_PASSPHRASE` before `init`. The same variable must
  then be set whenever you sign.
- `--export-public` writes only public material: the Ed25519 public key, the root and signer
  certificates, and `fingerprints.json`. Commit `provenance/public/` so other people can verify.
- **Publish the Ed25519 signer fingerprint** (`init` prints it; it is also `signer_fp` in
  `fingerprints.json`) somewhere a copier can't edit: your website, your LinkedIn profile, a signed
  git tag or release notes. Verifiers compare against that published value, not against the repo.
- `init` won't overwrite existing keys unless you pass `--force`. With existing keys and
  `--export-public`, it only re-exports the public files.

**Back up `~/.tantra/keys/` offline**, for example on an encrypted USB drive. If you lose it, new
signatures can't be linked to old ones, and the fingerprint registry can't be matched any more.
If the keys leak, anyone can sign as you. Run `init --force` and publish the new public material.

Then seal the OS:

```
python .claude/lib/provenance.py seal-frontmatter            # author/copyright/licence + seal ids in agents and skills
python .claude/lib/provenance.py sign-os                     # provenance/os_manifest.{json,sig,c2pa}
python .claude/lib/provenance.py fingerprint register-os     # registers first-party text in ~/.tantra/registry
```

`sign-os --tsa <RFC 3161 URL>` also saves a trusted timestamp (`os_manifest.tsr`). It needs a network
connection and is skipped quietly when offline. Re-run `seal-frontmatter` and `sign-os` after you
change agents or skills, and before a release.

## Deliverables (automatic)

Inside a client workspace, when Tantra is active, the `seal_guard` hook signs every file written
under `deliverables/`. It runs `provenance.py sign-file <file> --workspace <ws>` in the background
and produces:

- raster images, Office files, audio and video: C2PA embedded in the file. Re-signing replaces
  Tantra's own earlier credential instead of nesting it, so the file doesn't grow with every edit;
  if the file changes while it is being signed, the newer content is kept and signed again;
- Markdown, text, HTML, JSON, CSV and PDF: a `<file>.c2pa` sidecar (these formats can't carry an
  embedded manifest). SVG also gets a sidecar, so an SVG the agent is still editing is never
  rewritten behind its back;
- always: a `<file>.tantra-sig.json` Ed25519 record (hash, size, signer, time, workspace name, run id,
  the owner's C2PA root CA and signer certificate hashes, and the sidecar's hash);
- text files are also registered in the fingerprint registry.

The workspace is recorded by folder name only, never by full local path. To switch the hook off or
change the folders, edit `~/.tantra/config.json`:

```json
{"seal": {"enabled": true, "dirs": ["deliverables"], "timeout_s": 90}}
```

Signing by hand: `python .claude/lib/provenance.py sign-file path/to/file [--title T] [--run-id R]`.

## How a third party verifies

**First, get the owner's Ed25519 signer fingerprint out of band**: from the owner directly or from a
place a copier can't edit (the owner's website, LinkedIn profile, a signed git tag). Do not trust the
key, certificates or `fingerprints.json` in `provenance/public/` of the copy you are checking on their
own: anyone who changes files can re-sign them with their own key and swap that folder, and the
check would still say VALID. The pin (`--expect-fp`) is what ties the result to the owner.

They need the file, its `.tantra-sig.json` (and `.c2pa` sidecar, if there is one) and the public
material (from `provenance/public/` or from the owner):

```
python .claude/lib/provenance.py verify-file report.md \
    --pubkey provenance/public/identity_ed25519.pub.pem \
    --trust-root provenance/public/c2pa_root_ca.pem \
    --expect-fp <owner's published signer fingerprint>
```

The command exits 0 only if the Ed25519 signature passes, the verifying key matches `--expect-fp`,
and the C2PA manifest's signer chains to the owner's root CA. The root CA itself is checked against
the SHA-256 in the signed record, so a swapped root or a Content Credential from anyone else fails.
Without `--expect-fp` the command prints the verifying key's fingerprint so it can be compared by
hand. Other C2PA tools (for example `c2patool` or contentcredentials.org/verify) can also read the
credentials; without the owner's root CA they show "Valid" but untrusted, which on its own says
nothing about who signed.

To verify the OS itself:
`python .claude/lib/provenance.py verify-os --pubkey provenance/public/identity_ed25519.pub.pem --expect-fp <fingerprint>`.
Each file is reported as OK, MODIFIED, MISSING or NEW-UNSEALED. The check passes only if the
signature is valid, the key matches the pinned fingerprint, and nothing is MODIFIED or MISSING. The
owner name in the manifest is whatever the signer wrote; only the pinned fingerprint identifies them.

To check a seal id found somewhere else: `python .claude/lib/provenance.py verify-seal seo-agent --seal TS1-XXXXXXXXXXXXXXXX`.
Only the owner can run this, because it needs `fingerprint.key`.

To check a suspect text: `python .claude/lib/provenance.py fingerprint match suspect.txt`. This is also
owner-only. Verdicts: ≥ 0.50 "strong match", ≥ 0.15 "likely derived", ≥ 0.05 "some overlap". A
document is only scored when it shares at least 3 fingerprints with the suspect text, and containment
only counts when the suspect text has at least 8 fingerprints (roughly 30+ words). Shorter input is
reported as "insufficient text", because a single stock phrase would otherwise "match" anything that
uses it. Each match shows the number of shared fingerprints next to the ratios.

## Publicly trusted certificates (owner's decision, costs money)

The C2PA signer certificate comes from the owner's private root CA. Public validators therefore show
`signingCredential.untrusted`. Getting on the C2PA trust list means buying a certificate from a listed
CA and/or joining the C2PA conformance program. Tantra never does this automatically. It is an opt-in
paid step for the owner to decide on. After buying one, point `c2pa_signer.{key,pem}` and
`c2pa_chain.pem` at the new material.

## Git commit signing (recommended; commands only)

Signed commits show that the repository history came from you. Tantra doesn't change your git config.
To turn it on yourself:

```
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519_wptantra_signing.pub
git config --global commit.gpgsign true
git config --global tag.gpgsign true
git config --global gpg.ssh.allowedSignersFile ~/.ssh/allowed_signers
git log --show-signature -1
```

## Excluded paths

`provenance/third_party.json` lists paths that are never sealed as Hardik's work. These are
third-party components (the MIT-licensed `unlazy` skill by Leonxlnx, and `node_modules`) and
generated or runtime files (registries, lockfiles, caches, eval results).
