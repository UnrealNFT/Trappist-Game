# Props & cinematique : capsule sci-fi + ruines alien + video de crash
# Usage : python gen_props.py            -> tout
#         python gen_props.py capsule    -> juste la capsule (image + 3d)
#         python gen_props.py ruins      -> arches + obelisque
#         python gen_props.py cine       -> image crash + video mp4
import base64, json, os, sys
from gen_models_v2 import post, get, poll, download, BASE, IMG_MODEL, M3D_MODEL, ROOT, OUT_DIR, CONCEPT_DIR

VIDEO_MODEL = "bytedance/seedance-v1-lite-i2v-480p"  # ~0.016$ / video

PROPS = {
    "capsule": "a crashed sci-fi escape pod capsule, sleek white and dark titanium hull with glowing purple neon strips, "
               "hatch door closed, small thrusters at the back, single object, plain solid dark gray background, "
               "three-quarter view, video game asset, no text",
    "ruin_arch": "an ancient alien civilization stone arch portal, weathered dark basalt stone with glowing violet runes carved in it, "
                 "mossy cracks, single object, plain solid dark gray background, front view, video game asset, no text",
    "obelisk": "an ancient alien obelisk monolith, dark obsidian stone with glowing magenta rune inscriptions, "
               "floating small rock shards around its tip, single object, plain solid dark gray background, front view, video game asset, no text",
}
CRASH_PROMPT = ("cinematic movie still: a sci-fi escape pod capsule streaking down through a blood-pink alien sky, "
                "trailing fire and smoke, towards a dark purple neon alien landscape with twisted purple trees and ancient ruins, "
                "volcano in the distance, dramatic wide shot, epic lighting, video game cinematic")


def gen_image(name, prompt, size="1024*1024"):
    os.makedirs(CONCEPT_DIR, exist_ok=True)
    resp = post(f"{BASE}/{IMG_MODEL}", {"prompt": prompt, "size": size, "output_format": "png", "num_images": 1})
    task_id = (resp.get("data") or {}).get("id") or resp.get("id")
    outputs = poll(task_id, f"{name} (image)")
    dest = os.path.join(CONCEPT_DIR, f"{name}.png")
    download(outputs[0], dest)
    print(f"[concept] {dest}", flush=True)
    return dest


def gen_3d(name):
    img = os.path.join(CONCEPT_DIR, f"{name}.png")
    if not os.path.exists(img):
        gen_image(name, PROPS[name])
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    resp = post(f"{BASE}/{M3D_MODEL}", {
        "image": "data:image/png;base64," + b64,
        "texture": True, "pbr": False,
        "geometry_quality": "detailed", "texture_quality": "detailed",
    })
    task_id = (resp.get("data") or {}).get("id") or resp.get("id")
    print(f"[submit3d] {name}: task {task_id}", flush=True)
    outputs = poll(task_id, f"{name} (3d)")
    url = next((u for u in outputs if ".glb" in u.lower()), outputs[0])
    os.makedirs(OUT_DIR, exist_ok=True)
    dest = os.path.join(OUT_DIR, name + ".glb")
    download(url, dest)
    print(f"[ok] {dest} ({os.path.getsize(dest)//1024} Ko)", flush=True)


def gen_cinematic():
    # 1) image du crash
    img_path = os.path.join(CONCEPT_DIR, "crash.png")
    if not os.path.exists(img_path):
        gen_image("crash", CRASH_PROMPT, size="1536*640")
    # 2) image -> video
    b64 = base64.b64encode(open(img_path, "rb").read()).decode()
    resp = post(f"{BASE}/{VIDEO_MODEL}", {
        "image": "data:image/png;base64," + b64,
        "prompt": "the burning capsule falls from the sky, camera slowly pushes in, smoke and embers drift, epic cinematic motion",
        "duration": 5,
    })
    task_id = (resp.get("data") or {}).get("id") or resp.get("id")
    if not task_id:
        raise RuntimeError(f"video: pas d'id -> {json.dumps(resp)[:300]}")
    print(f"[submitVideo] task {task_id}", flush=True)
    outputs = poll(task_id, "crash video", timeout=1200)
    url = next((u for u in outputs if ".mp4" in u.lower()), outputs[0])
    dest = os.path.join(OUT_DIR, "crash.mp4")
    download(url, dest)
    print(f"[ok] {dest} ({os.path.getsize(dest)//1024} Ko)", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:] or ["all"]
    if "all" in args or "capsule" in args:
        gen_3d("capsule")
    if "all" in args or "ruins" in args:
        for p in ("ruin_arch", "obelisk"):
            try:
                gen_3d(p)
            except Exception as e:
                print(f"[erreur] {p}: {e}", flush=True)
    if "all" in args or "cine" in args:
        try:
            gen_cinematic()
        except Exception as e:
            print(f"[erreur] video: {e}", flush=True)
    print("TERMINE.", flush=True)
