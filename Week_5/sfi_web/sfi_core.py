import hashlib, zlib, wave, struct, json, os
from datetime import datetime

MAGIC = b"SFI1"

# ---------------------------
# Utility
# ---------------------------
def compute_hash(path: str, algo="sha256") -> str:
    """Compute hash of a file."""
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def make_manifest(files: list[str], algo="sha256") -> dict:
    """Create manifest for given files."""
    return {
        "algorithm": algo,
        "created_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": [{"name": os.path.basename(f), "hash": compute_hash(f, algo)} for f in files],
    }

def pack_manifest(manifest: dict) -> bytes:
    data = json.dumps(manifest).encode()
    comp = zlib.compress(data)
    return MAGIC + len(comp).to_bytes(4, "big") + comp

def unpack_manifest(blob: bytes) -> dict:
    if not blob.startswith(MAGIC):
        raise ValueError("No SFI payload found")
    size = int.from_bytes(blob[4:8], "big")
    comp = blob[8:8+size]
    data = zlib.decompress(comp)
    return json.loads(data.decode())

# ---------------------------
# Audio Stego
# ---------------------------
def embed_audio(cover_path: str, out_path: str, files: list[str], algo="sha256"):
    """Embed manifest into a WAV file (LSB stego)."""
    manifest = make_manifest(files, algo)
    payload = pack_manifest(manifest)

    with wave.open(cover_path, "rb") as w:
        params = w.getparams()
        frames = bytearray(list(w.readframes(w.getnframes())))

    if len(payload)*8 > len(frames):
        raise ValueError("Cover file too small for payload")

    for i, byte in enumerate(payload):
        for bit in range(8):
            frames[i*8+bit] &= 0xFE
            frames[i*8+bit] |= (byte >> (7-bit)) & 1

    with wave.open(out_path, "wb") as w:
        w.setparams(params)
        w.writeframes(bytes(frames))

def extract(cover_path: str, out_path: str):
    """Extract manifest from a WAV stego file."""
    with wave.open(cover_path, "rb") as w:
        frames = bytearray(list(w.readframes(w.getnframes())))

    bits = []
    for b in frames:
        bits.append(b & 1)

    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in range(8):
            byte = (byte << 1) | bits[i+bit]
        out.append(byte)
        if out.endswith(MAGIC) and len(out) > 4:  # sanity cut
            break

    try:
        manifest = unpack_manifest(bytes(out))
    except Exception:
        raise ValueError("Could not extract manifest")

    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest

# ---------------------------
# Verification
# ---------------------------
def verify(cover_path: str, files: list[str]) -> dict:
    """Verify file integrity against manifest embedded in cover file."""
    with wave.open(cover_path, "rb") as w:
        frames = bytearray(list(w.readframes(w.getnframes())))

    bits = []
    for b in frames:
        bits.append(b & 1)

    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in range(8):
            byte = (byte << 1) | bits[i+bit]
        out.append(byte)
        if out.startswith(MAGIC) and len(out) > 8:
            try:
                manifest = unpack_manifest(bytes(out))
                break
            except Exception:
                continue
    else:
        raise ValueError("No manifest found in cover")

    algo = manifest["algorithm"]
    results = []
    for f in files:
        current = compute_hash(f, algo)
        stored = next((entry["hash"] for entry in manifest["files"] if entry["name"] == os.path.basename(f)), None)
        results.append({
            "file": f,
            "stored": stored,
            "current": current,
            "ok": stored == current,
        })

    return {"algorithm": algo, "created_utc": manifest["created_utc"], "results": results}
