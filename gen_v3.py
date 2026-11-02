# V3 "Odyssée" : arme FPS, arbre alien, ruine low-poly + vidéo d'ATTERRISSAGE mystérieux
# Usage : python gen_v3.py           -> tout
#         python gen_v3.py props     -> arme + arbre + ruine (3D)
#         python gen_v3.py cine      -> image + vidéo d'atterrissage
import base64, json, os, sys
import gen_props as gp
from gen_models_v2 import post, poll, download, BASE, OUT_DIR, CONCEPT_DIR

BG = "single object, isolated, plain solid dark gray background, three-quarter view, video game asset, no text"
gp.PROPS.update({
    "weapon": "a futuristic alien sci-fi energy blaster pistol held in first person, sleek dark gunmetal and obsidian body, "
              "glowing purple neon energy core and coils, small capture-net launcher module under the barrel, " + BG,
    "alien_tree": "a stylized low poly alien tree with a twisted dark charcoal trunk and a large canopy of glowing violet purple leaves, "
                  "small glowing magenta fruits hanging, " + BG,
    "ruin_lowpoly": "a low poly stylized ancient alien temple ruin, broken stone columns and a collapsed wall, dark weathered stone "
                    "with faintly glowing purple runes, mossy, " + BG,
})
LAND_PROMPT = ("cinematic movie still, dusk: a mysterious sleek sci-fi capsule descending slowly with soft blue retro thrusters firing, "
               "about to land gently on a dark purple alien planet, blood-pink sky with a giant ringed planet, twisted trees with glowing "
               "violet leaves, ancient ruins in the mist, dust swirling below the capsule, the hatch is closed, nobody knows who is inside, "
               "mysterious atmosphere, wide shot, video game cinematic")


def gen_landing():
    img = os.path.join(CONCEPT_DIR, "landing.png")
    if not os.path.exists(img):
        gp.gen_image("landing", LAND_PROMPT, size="1536*640")
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    resp = post(f"{BASE}/{gp.VIDEO_MODEL}", {
        "image": "data:image/png;base64," + b64,
        "prompt": "the capsule slowly descends and lands gently on the ground, thrusters glow, dust and purple mist swirl around it, "
                  "camera slowly pushes in, mysterious calm cinematic motion, no explosion",
        "duration": 5,
    })
    task_id = (resp.get("data") or {}).get("id") or resp.get("id")
    if not task_id:
        raise RuntimeError(f"video: pas d'id -> {json.dumps(resp)[:300]}")
    print(f"[submitVideo] task {task_id}", flush=True)
    out = poll(task_id, "landing video", timeout=1200)
    url = next((u for u in out if ".mp4" in u.lower()), out[0])
    dest = os.path.join(OUT_DIR, "landing.mp4")
    download(url, dest)
    print(f"[ok] {dest} ({os.path.getsize(dest)//1024} Ko)", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    if "all" in args or "cine" in args:
        try: gen_landing()
        except Exception as e: print(f"[erreur] video: {e}", flush=True)
    if "all" in args or "props" in args:
        for p in ("weapon", "alien_tree", "ruin_lowpoly"):
            try: gp.gen_3d(p)
            except Exception as e: print(f"[erreur] {p}: {e}", flush=True)
    print("TERMINE.", flush=True)
