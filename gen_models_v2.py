# Pipeline v2 : concept art (flux-schnell, ~0.003$) -> 3 vues -> Tripo3D multiview-to-3d (0.24$)
# Usage :
#   python gen_models_v2.py images          # genere les planches concept (presque gratuit)
#   python gen_models_v2.py 3d              # convertit en modeles 3D (0.24$ x creature)
#   python gen_models_v2.py full            # les deux
#   python gen_models_v2.py 3d turtle dragon  # seulement certaines creatures
import json, os, sys, time, urllib.request, urllib.error, uuid

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT, "..", ".env")
OUT_DIR = os.path.join(ROOT, "models")
CONCEPT_DIR = os.path.join(ROOT, "concepts")
BASE = "https://api.wavespeed.ai/api/v3"
IMG_MODEL = "wavespeed-ai/flux-schnell"          # ~0.003$ / image
M3D_MODEL = "tripo3d/h3.1/image-to-3d"           # 0.24$ / modele (base64 inline, voir gen_3d)

KEY = None
with open(ENV_PATH, encoding="utf-8") as f:
    for line in f:
        if line.startswith("WAVESPEED_API_KEY="):
            KEY = line.split("=", 1)[1].strip()
if not KEY:
    sys.exit("WAVESPEED_API_KEY introuvable dans " + ENV_PATH)
HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

CREATURES = {
    "turtle":   "a dark mutant turtle creature from an alien planet, obsidian black spiky dome shell with glowing purple neon cracks, magenta glowing eyes, armored legs, apocalyptic fantasy game monster",
    "dragon":   "a dark apocalyptic alien dragon, deep violet and black scales, glowing neon purple wing membranes, sharp obsidian horns, glowing magenta eyes, menacing fantasy game monster",
    "elephant": "a massive mutant alien elephant beast, dark grey-purple armored skin with glowing violet runes, black obsidian tusks, glowing purple eyes, apocalyptic fantasy game monster",
    "phoenix":  "a legendary dark void phoenix, black and deep purple feathers with glowing neon violet fire tips, long elegant tail of purple plasma flames, glowing white eyes, alien fantasy game creature",
}
SHEET = ("3D character turnaround sheet of {desc}, three full-body views side by side "
         "(front view, side view, back view), evenly spaced, same character in all three views, "
         "dark stylized game character, dramatic rim lighting, neon glow accents, "
         "plain solid dark gray background, no text, no labels, no watermark")


def post(url, payload, headers=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=headers or HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def poll(task_id, label, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            resp = get(f"{BASE}/predictions/{task_id}/result")
        except urllib.error.HTTPError:
            resp = get(f"{BASE}/predictions/{task_id}/status")
        data = resp.get("data") or resp
        status = (data.get("status") or "").lower()
        if status == "completed":
            return data.get("outputs") or []
        if status in ("failed", "cancelled", "timeout", "deleted"):
            raise RuntimeError(f"{label}: {status} -> {json.dumps(data)[:300]}")
        time.sleep(4)
    raise RuntimeError(f"{label}: timeout")


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())


def upload_file(path):
    boundary = uuid.uuid4().hex
    with open(path, "rb") as f:
        content = f.read()
    body = (f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(path)}"\r\n'
            f"Content-Type: image/png\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{BASE}/files/upload", data=body, method="POST", headers={
        "Authorization": HEADERS["Authorization"],
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        resp = json.load(r)
    data = resp.get("data") or resp
    url = data.get("url") or data.get("download_url") or (data if isinstance(data, str) else None)
    if not url:
        raise RuntimeError(f"upload: reponse inattendue -> {json.dumps(resp)[:300]}")
    return url


# ---------- etape 1 : planches concept ----------
def gen_concept(name):
    os.makedirs(CONCEPT_DIR, exist_ok=True)
    sheet_path = os.path.join(CONCEPT_DIR, f"{name}.png")
    resp = post(f"{BASE}/{IMG_MODEL}", {
        "prompt": SHEET.format(desc=CREATURES[name]),
        "size": "1536*512",
        "output_format": "png",
        "num_images": 1,
    })
    task_id = (resp.get("data") or {}).get("id") or resp.get("id")
    if not task_id:
        raise RuntimeError(f"{name}: pas d'id -> {json.dumps(resp)[:300]}")
    outputs = poll(task_id, f"{name} (image)")
    download(outputs[0], sheet_path)
    print(f"[concept] {sheet_path}", flush=True)

    # decoupe en 3 vues
    from PIL import Image
    img = Image.open(sheet_path)
    w, h = img.size
    step = w // 3
    views = []
    for i, tag in enumerate(("front", "side", "back")):
        crop = img.crop((i * step, 0, (i + 1) * step, h))
        p = os.path.join(CONCEPT_DIR, f"{name}_{tag}.png")
        crop.save(p)
        views.append(p)
    return views


# ---------- etape 2 : 3D ----------
def gen_3d(name):
    # UNE SEULE vue (3/4 gauche) : envoyer la planche entière donnait 3 créatures soudées dans un mesh
    view = os.path.join(CONCEPT_DIR, f"{name}_front.png")
    if not os.path.exists(view):
        raise RuntimeError(f"{name}: vue manquante, lance d'abord: python gen_models_v2.py images")
    import base64
    b64 = base64.b64encode(open(view, "rb").read()).decode()
    resp = post(f"{BASE}/{M3D_MODEL}", {
        "image": "data:image/png;base64," + b64,
        "texture": True,
        "pbr": False,
        "geometry_quality": "detailed",
        "texture_quality": "detailed",
    })
    task_id = (resp.get("data") or {}).get("id") or resp.get("id")
    if not task_id:
        raise RuntimeError(f"{name}: pas d'id 3D -> {json.dumps(resp)[:300]}")
    print(f"[submit3d] {name}: task {task_id}", flush=True)
    outputs = poll(task_id, f"{name} (3d)")
    os.makedirs(OUT_DIR, exist_ok=True)
    url = next((u for u in outputs if ".glb" in u.lower()), outputs[0])
    dest = os.path.join(OUT_DIR, name + ".glb")
    download(url, dest)
    print(f"[ok] {dest} ({os.path.getsize(dest)//1024} Ko)", flush=True)


def main():
    args = sys.argv[1:]
    mode = args[0] if args and args[0] in ("images", "3d", "full") else "images"
    names = [a for a in args if a in CREATURES] or list(CREATURES)
    if mode in ("images", "full"):
        for n in names:
            try:
                gen_concept(n)
            except Exception as e:
                print(f"[erreur] concept {n}: {e}", flush=True)
    if mode in ("3d", "full"):
        for n in names:
            try:
                gen_3d(n)
            except Exception as e:
                print(f"[erreur] 3d {n}: {e}", flush=True)
    print("TERMINE.", flush=True)


if __name__ == "__main__":
    main()
