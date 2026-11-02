# V4 : créatures mascottes bipèdes / en vol + 3 arbres + 3 ruines (concept flux-schnell fond noir -> Tripo 3D)
# Usage : python gen_v4.py concepts          -> images seulement (~0.003$ chacune)
#         python gen_v4.py 3d [noms...]       -> 3D Tripo (soumis en parallèle) + optimisation auto
#         python gen_v4.py post [noms...]     -> optimisation seule (décimation + Draco)
import base64, json, os, subprocess, sys, time
from gen_models_v2 import post, poll, download, BASE, IMG_MODEL, M3D_MODEL, OUT_DIR, CONCEPT_DIR

READY = ("single subject centered, isolated on pure black background, entire object visible, no ground, no shadow, "
         "clean readable silhouette, stylized high quality video game asset, ready for 3D modeling, no text, no watermark")
CREATURE = ("full body, front view facing the viewer, symmetrical A-pose with arms slightly away from the body, "
            "dark fantasy alien style, obsidian and deep purple palette with glowing violet neon accents, " + READY)
FLYING = ("in flight, wings fully spread wide, seen from the front facing the viewer, symmetrical, "
          "dark fantasy alien style, black and deep purple palette with glowing violet fire accents, " + READY)

ASSETS = {
    # créatures (mascottes humanoïdes bipèdes)
    "turtlian":    "a bipedal humanoid turtle warrior mascot standing upright on two strong legs, spiked dark obsidian shell on its back, "
                   "muscular arms, wise determined face, glowing purple cracks on the shell, " + CREATURE,
    "elephantian": "a bipedal humanoid elephant warrior mascot standing upright on two legs, big ears, long trunk, curved ivory tusks "
                   "glowing violet at the tips, tribal stone armor plates, " + CREATURE,
    "reptilian":   "STRICT T-POSE character reference sheet: a menacing black-scaled reptilian alien predator standing upright, "
                   "BOTH ARMS HELD STRAIGHT OUT HORIZONTALLY to the sides at shoulder height in a perfect T-pose, palms down, legs apart, "
                   "long muscular tail extended behind, sleek glossy jet-black obsidian scales with subtle iridescent purple sheen, "
                   "sharp dorsal spikes running from skull to tail tip, predatory lizard head with glowing crimson eyes and short snout, "
                   "lean athletic hunter build, full body, front view, realistic dark fantasy style, black and charcoal palette only, " + READY,
    # créatures volantes
    "phoenixian":  "a majestic phoenix bird in flight, wings fully spread wide, golden orange and red fiery feathers, long flaming tail "
                   "of fire, glowing yellow highlights, seen from the front facing the viewer, symmetrical, epic fantasy style, " + READY,
    "weapon":      "a futuristic post-apocalyptic alien energy blaster gun HELD by a muscular glowing BLUE alien forearm and hand, "
                   "bright blue skin arm with dark veins gripping the handle firmly, scratched dark gunmetal and rusted armor plates, exposed cables, "
                   "glowing cyan and magenta neon energy coils, glowing energy core chamber, side view, " + READY,
    "dragonian":   "a powerful dark dragon with huge bat-like wings, obsidian scales, horned head, long tail " + FLYING,
    # 3 arbres violets
    "tree_canopy": "a large stylized alien tree with a thick twisted dark bark trunk and roots, huge round canopy of glowing violet "
                   "purple leaves, small glowing magenta fruits, " + READY,
    "tree_willow": "a stylized alien weeping willow tree, gnarled dark trunk, long drooping branches covered with glowing lavender "
                   "and violet leaves, " + READY,
    "tree_crystal": "a stylized alien tree whose branches end in glowing purple crystal clusters instead of leaves, dark spiral "
                    "trunk, violet bioluminescent veins, " + READY,
    # 3 ruines low poly
    "ruin_temple": "low poly stylized ancient alien temple ruin, broken stone columns on a cracked stone platform, collapsed roof "
                   "fragments, faintly glowing purple runes, " + READY,
    "ruin_gate":   "low poly stylized ancient alien stone gateway arch ruin, massive weathered blocks, carved glowing violet glyphs, "
                   "moss and cracks, " + READY,
    "ruin_tower":  "low poly stylized ruined ancient alien watchtower, half collapsed round stone tower with a broken spiral top, "
                   "glowing purple runes, scattered blocks at its base, " + READY,
}
# décimation : ratio de triangles conservés (Tripo sort ~2M triangles)
DECIMATE = {"turtlian": .05, "elephantian": .05, "reptilian": .15, "phoenixian": .05, "dragonian": .05, "weapon": .03,
            "tree_canopy": .01, "tree_willow": .01, "tree_crystal": .01,
            "ruin_temple": .015, "ruin_gate": .015, "ruin_tower": .015}


def concept(name):
    os.makedirs(CONCEPT_DIR, exist_ok=True)
    dest = os.path.join(CONCEPT_DIR, f"v4_{name}.png")
    if os.path.exists(dest):
        print(f"[skip] {dest}", flush=True); return dest
    r = post(f"{BASE}/{IMG_MODEL}", {"prompt": ASSETS[name], "size": "1024*1024", "output_format": "png", "num_images": 1})
    tid = (r.get("data") or {}).get("id") or r.get("id")
    out = poll(tid, f"{name} (image)")
    download(out[0], dest)
    print(f"[concept] {dest}", flush=True)
    return dest


def submit3d(name):
    img = os.path.join(CONCEPT_DIR, f"v4_{name}.png")
    if not os.path.exists(img):
        concept(name)
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    r = post(f"{BASE}/{M3D_MODEL}", {"image": "data:image/png;base64," + b64, "texture": True, "pbr": False,
                                     "geometry_quality": "detailed", "texture_quality": "detailed"})
    tid = (r.get("data") or {}).get("id") or r.get("id")
    if not tid:
        raise RuntimeError(json.dumps(r)[:300])
    print(f"[submit3d] {name}: {tid}", flush=True)
    return tid


def optimize(name):
    src = os.path.join(OUT_DIR, f"{name}.glb")
    tmp = os.path.join(OUT_DIR, f"{name}.s.glb")
    sh = os.name == "nt"
    subprocess.run(["gltf-transform", "simplify", src, tmp, "--ratio", str(DECIMATE[name]), "--error", "0.002"], check=True, shell=sh)
    subprocess.run(["gltf-pipeline", "-i", tmp, "-o", src, "--draco.compressionLevel", "10"], check=True, shell=sh)
    os.remove(tmp)
    print(f"[opt] {src} ({os.path.getsize(src)//1024} Ko)", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "concepts"
    names = [a for a in sys.argv[2:] if a in ASSETS] or list(ASSETS)
    if mode == "concepts":
        for n in names:
            try: concept(n)
            except Exception as e: print(f"[erreur] {n}: {e}", flush=True)
    elif mode == "3d":
        tasks = {}
        for n in names:  # tout soumettre d'abord : Tripo travaille en parallèle
            try: tasks[n] = submit3d(n)
            except Exception as e: print(f"[erreur] submit {n}: {e}", flush=True)
        for n, tid in tasks.items():
            try:
                out = poll(tid, f"{n} (3d)")
                url = next((u for u in out if ".glb" in u.lower()), out[0])
                download(url, os.path.join(OUT_DIR, f"{n}.glb"))
                optimize(n)
            except Exception as e: print(f"[erreur] 3d {n}: {e}", flush=True)
    elif mode == "post":
        for n in names:
            try: optimize(n)
            except Exception as e: print(f"[erreur] post {n}: {e}", flush=True)
    print("TERMINE.", flush=True)
