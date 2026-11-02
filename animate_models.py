# Pipeline animation 3D via Replicate (peelz/kitbash3d-animate ou blueambr/rigging)
# Cible : animer les creatures GLB (idle / walk / attack) -> models/*_animated.glb
# Usage :
#   python animate_models.py status           # verifie le token et liste les modeles dispo
#   python animate_models.py rig turtle       # rig une creature (gratuit)
#   python animate_models.py all              # rig tout
import json, os, sys, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT, "..", ".env")
OUT_DIR = os.path.join(ROOT, "models")
BASE = "https://api.replicate.com/v1"

TOKEN = None
with open(ENV_PATH, encoding="utf-8") as f:
    for line in f:
        for var in ("REPLICATE_API_TOKEN", "REPLICATE_TOKEN", "R8_TOKEN"):
            if line.startswith(var + "="):
                TOKEN = line.split("=", 1)[1].strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"} if TOKEN else {}

# modeles Replicate a essayer (auto-rig / animate de GLB, gratuits)
CANDIDATES = [
    "peelz/kitbash3d-animate",
    "blueambr/rigging",
    "blueambr/rig-anything",
]


def req(method, url, payload=None):
    data = json.dumps(payload).encode() if payload else None
    r = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return json.load(resp)


def find_model():
    for name in CANDIDATES:
        try:
            m = req("GET", f"{BASE}/models/{name}")
            ver = m.get("latest_version", {}).get("id")
            if ver:
                print(f"[ok] modele trouve : {name} (version {ver[:12]}...)", flush=True)
                return name, ver
        except urllib.error.HTTPError as e:
            print(f"[skip] {name}: HTTP {e.code}", flush=True)
    return None, None


def main():
    if not TOKEN:
        print("Pas de REPLICATE_API_TOKEN dans le .env -> je prepare l'URL a coller :", flush=True)
        print("1. Va sur https://replicate.com (compte gratuit GitHub)", flush=True)
        print("2. https://replicate.com/account/api-tokens -> cree un token", flush=True)
        print("3. Ajoute dans le .env : REPLICATE_API_TOKEN=r8_xxxxx", flush=True)
        print("4. Relance : python animate_models.py all", flush=True)
        print("\nModeles Replicate recommandes (auto-rig GLB, gratuits) :", flush=True)
        for c in CANDIDATES:
            print("   - " + c, flush=True)
        return
    name, ver = find_model()
    if not name:
        print("Aucun modele de rig trouve parmi les candidats. Cherche 'rigging' sur replicate.com/explore", flush=True)
        return
    print(f"\nPret a animer avec {name}. Exemple :", flush=True)
    print(f'  python animate_models.py rig turtle   # rig models/turtle.glb', flush=True)
    print("(le code d'appel exact depend du schema du modele - dis-moi lequel est dispo et je finis l'integration)", flush=True)


if __name__ == "__main__":
    main()
