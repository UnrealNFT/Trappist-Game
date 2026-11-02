# Genere les creatures du jeu via WaveSpeed / Tripo3D (text-to-3d)
# Lit WAVESPEED_API_KEY depuis le .env (jamais affichee). Sortie : models/*.glb
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT, "..", ".env")
OUT_DIR = os.path.join(ROOT, "models")
BASE = "https://api.wavespeed.ai/api/v3"
MODEL = "tripo3d/h3.1/text-to-3d"  # 0.12$ / generation

KEY = None
with open(ENV_PATH, encoding="utf-8") as f:
    for line in f:
        if line.startswith("WAVESPEED_API_KEY="):
            KEY = line.split("=", 1)[1].strip()
if not KEY:
    sys.exit("WAVESPEED_API_KEY introuvable dans " + ENV_PATH)

HEADERS = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

STYLE = ("low-poly stylized cartoon game character, cute fantasy creature mascot, "
         "big friendly eyes, vibrant flat colors, smooth simple shapes, "
         "T-pose or neutral standing pose, full body, centered")
NEG = "realistic, photorealistic, dark, horror, scary, high-poly, complex background, text, watermark"

CREATURES = {
    "turtle":   "cute round turtle creature with a big teal dome shell and chubby legs, " + STYLE,
    "dragon":   "cute green dragon with big spread wings, small horns and a long tail, " + STYLE,
    "elephant": "cute strong purple elephant warrior with big round ears and white tusks, " + STYLE,
    "phoenix":  "legendary phoenix bird with orange and gold fire feathers, spread wings and long tail, " + STYLE,
}


def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r)


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def submit(name, prompt):
    body = {
        "prompt": prompt,
        "negative_prompt": NEG,
        "texture": True,
        "pbr": False,
        "face_limit": 8000,
        "geometry_quality": "standard",
        "texture_quality": "standard",
    }
    resp = post(f"{BASE}/{MODEL}", body)
    data = resp.get("data") or {}
    task_id = data.get("id") or resp.get("id")
    if not task_id:
        raise RuntimeError(f"{name}: pas d'id de tache -> {json.dumps(resp)[:300]}")
    print(f"[submit] {name}: task {task_id}", flush=True)
    return task_id


def poll(name, task_id, timeout=900):
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
            raise RuntimeError(f"{name}: generation {status} -> {json.dumps(data)[:300]}")
        time.sleep(5)
    raise RuntimeError(f"{name}: timeout de polling")


def download(name, outputs):
    os.makedirs(OUT_DIR, exist_ok=True)
    url = next((u for u in outputs if ".glb" in u.lower()), outputs[0])
    dest = os.path.join(OUT_DIR, name + ".glb")
    print(f"[download] {name} <- {url[:90]}...", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
        f.write(r.read())
    print(f"[ok] {dest} ({os.path.getsize(dest)//1024} Ko)", flush=True)


def main():
    only = sys.argv[1:] or list(CREATURES)
    tasks = {}
    for name in only:
        try:
            tasks[name] = submit(name, CREATURES[name])
        except Exception as e:
            print(f"[erreur] submit {name}: {e}", flush=True)
    for name, tid in tasks.items():
        try:
            outputs = poll(name, tid)
            print(f"[done] {name}: {len(outputs)} output(s)", flush=True)
            download(name, outputs)
        except Exception as e:
            print(f"[erreur] {name}: {e}", flush=True)
    print("TERMINE.", flush=True)


if __name__ == "__main__":
    main()
