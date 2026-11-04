# Serveur local du jeu : statique SANS cache navigateur + API de fusion IA
# (POST /api/fuse lance la génération WaveSpeed de la CARTE 2D d'arène (image concept + vignette),
#  GET /api/fuse_status?id=... pour suivre la tâche)
# Proxy trappist.land (backend Render) : le navigateur ne peut pas l'appeler directement (CORS),
# donc le jeu passe par ici serveur-à-serveur. Un wallet Casper connecté = débit RÉEL de tokens trappist.
import http.server, socketserver, sys, json, os, threading, uuid, random
import urllib.request
from urllib.parse import urlparse, parse_qs

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from gen_models_v2 import post, poll, download, BASE, IMG_MODEL
from gen_v4 import ASSETS

# flux-dev pour les fusions : plus détaillé et créatif que schnell (~0.025$/image)
IMG_FUSION = "wavespeed-ai/flux-dev"

# backend trappist.land (Render) : crédits RÉELS des joueurs (1 token = 1 image, comme sur le site)
TC_API = os.getenv("TRAPPIST_API", "https://trappistai-backend.onrender.com")

def tc_get(path, timeout=30):
    req = urllib.request.Request(TC_API + path, headers={"User-Agent": "nebula-game"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def tc_post(path, payload, timeout=180):
    req = urllib.request.Request(TC_API + path, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "nebula-game"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def tc_balance(wallet):
    try:
        d = tc_get("/api/user/" + wallet + "/balance")
        return int(d.get("tokens") or 0), None
    except Exception as e:
        return 0, str(e)[:200]

# mutations physiques, poses et décors tirés au hasard : chaque fusion est une créature UNIQUE
TRAITS = [
    "asymmetric glowing battle scars", "glowing tribal tattoos across the body",
    "crystal horns and spine spikes", "a spiked mace-like tail", "an extra pair of small arms",
    "bioluminescent dotted patterns", "scavenged metal armor implants", "tribal bone jewelry and piercings",
    "cracked obsidian armor patches", "crackling electricity arcs around the claws",
    "floating rock shards orbiting the body", "venom-dripping oversized fangs",
    "a majestic feathered crest", "rune-carved glowing shell plates", "a blazing fiery mane",
    "ice frost covering the shoulders", "smoke pouring from the nostrils", "one huge mutated muscular arm",
]
POSES = [
    "roaring triumphantly at the sky", "charging forward aggressively", "rearing up on its hind legs",
    "crouched low ready to pounce", "striking a heroic battle stance", "mid-leap attack pose",
    "standing proudly on a rock", "unleashing its battle cry",
]
SETTINGS = [
    "on a volcanic ridge at dusk", "inside a glowing purple crystal cave",
    "on the purple moon surface under a giant green planet in the sky",
    "in a neon-lit alien arena", "in a bioluminescent alien swamp", "on a floating rock island in a nebula sky",
]

# clé de jeu -> clé d'asset v4 + nom affiché
FUSION_BASE = {
    "turtle":   ("turtlian", "Turtlian"),
    "elephant": ("elephantian", "Elephantian"),
    "phoenix":  ("phoenixian", "Phenixian"),
    "dragon":   ("dragonian", "Dragon"),
}
# thèmes de variante (le hasard choisit) : fragment de prompt, suffixe de nom, couleur
THEMES = [
    ("golden royal armor plates, glowing gold runes, majestic champion", "Prime", "#ffd36b"),
    ("purple crystal growths all over the body, glowing amethyst shards", "Cristal", "#c55aff"),
    ("pale silver-white lunar skin, icy blue bioluminescent glow", "Lunaire", "#bfe8ff"),
    ("molten lava veins, glowing orange cracks, ember particles", "Magma", "#ff7a3c"),
    ("spectral ghostly translucent body, cyan ethereal glow", "Spectral", "#40f0ff"),
    ("pitch black void skin, glowing crimson cracks and eyes", "Obsidienne", "#ff3355"),
]

JOBS = {}

# re-fusion (fusion de variantes déjà fusionnées, à l'infini) : descriptif visuel par rang
TIER_STYLE = {
    2: "mega evolved form, larger and even more elaborate",
    3: "ancient colossal alpha form, extremely elaborate",
    4: "godlike mythical form, majestic and divine",
}
ROMAN = ["II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
def tier_style(t):
    return TIER_STYLE.get(t, "transcendent cosmic deity form, unimaginably elaborate")

def run_fusion(job, species, tier=1, theme_idx=None, wallet=None):
    try:
        asset, disp = FUSION_BASE[species]
        tier = max(1, min(10, int(tier or 1)))
        # une re-fusion garde l'identité (thème + couleur) de la lignée ; une fusion simple tire un thème au hasard
        if tier > 1 and theme_idx is not None and 0 <= int(theme_idx) < len(THEMES):
            theme_idx = int(theme_idx)
        else:
            theme_idx = random.randrange(len(THEMES))
        frag, suffix, color = THEMES[theme_idx]
        key = "fx_" + job[:8]
        os.makedirs(os.path.join(ROOT, "concepts", "fusions"), exist_ok=True)

        JOBS[job]["step"] = "concept"
        # prompt unique à chaque fusion : espèce + thème (+ rang) + 2 mutations + pose + décor + graine aléatoire
        parts = [ASSETS[asset], frag]
        if tier > 1:
            parts.append(tier_style(tier))
        parts += random.sample(TRAITS, 2) + [random.choice(POSES), random.choice(SETTINGS),
                 "unique legendary fusion creature, vibrant detailed concept art"]
        prompt = ", ".join(parts)
        out = None
        charged = False
        newbal = None
        if wallet:
            # joueur connecté (Casper Wallet) : la génération passe par le backend trappist.land
            # -> débit RÉEL d'1 token (le backend ne débite qu'après une génération réussie)
            bal, berr = tc_balance(wallet)
            if berr is None and bal < 1:
                JOBS[job].update(status="error", step=None,
                                 error="Crédits trappist insuffisants (1 requis) — recharge sur trappist.land")
                return
            try:
                d = tc_post("/api/generate/image", {"walletAddress": wallet, "prompt": prompt})
                if d.get("url"):
                    out = [d["url"]]
                    charged = True
                    newbal = (bal - 1) if berr is None else None
            except urllib.error.HTTPError as e:
                if e.code == 402:  # insuffisant : pas de débit, on arrête là
                    JOBS[job].update(status="error", step=None,
                                     error="Crédits trappist insuffisants (1 requis) — recharge sur trappist.land")
                    return
            except Exception:
                pass  # backend injoignable -> secours local ci-dessous (non débité)
        if out is None:
            try:
                r = post(f"{BASE}/{IMG_FUSION}", {"prompt": prompt, "size": "1024*1024",
                                                  "output_format": "png", "num_images": 1,
                                                  "seed": random.randint(1, 2**31 - 1)})
                tid = (r.get("data") or {}).get("id") or r.get("id")
                out = poll(tid, f"fusion {species} (concept)")
            except Exception:
                # secours : schnell (plus simple) si flux-dev est indisponible
                r = post(f"{BASE}/{IMG_MODEL}", {"prompt": prompt,
                                                 "size": "1024*1024", "output_format": "png", "num_images": 1})
                tid = (r.get("data") or {}).get("id") or r.get("id")
                out = poll(tid, f"fusion {species} (concept)")
        png = os.path.join(ROOT, "concepts", "fusions", key + ".png")
        download(out[0], png)

        # vignette carte 320x320 (comme les autres cartes) — la fusion est une carte 2D d'arène, pas de 3D
        from PIL import Image
        im = Image.open(png).convert("RGB").resize((320, 320), Image.LANCZOS)
        im.save(os.path.join(ROOT, "concepts", "cards", key + ".jpg"), quality=90)

        spName = f"{disp} {suffix}" + (f" {ROMAN[tier - 2]}" if tier > 1 else "")
        JOBS[job].update(status="done", step=None, key=key,
                         art=f"concepts/cards/{key}.jpg",
                         spName=spName, color=color, tier=tier, themeIdx=theme_idx,
                         charged=charged, balance=newbal)
    except Exception as e:
        JOBS[job].update(status="error", step=None, error=str(e)[:300])

class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if urlparse(self.path).path == "/api/fuse":
            try:
                n = int(self.headers.get('Content-Length') or 0)
                data = json.loads(self.rfile.read(n) or b"{}")
                sp = data.get("species")
                if sp not in FUSION_BASE:
                    return self._json({"error": "espece inconnue"}, 400)
                job = uuid.uuid4().hex
                JOBS[job] = {"status": "working", "step": "concept"}
                threading.Thread(target=run_fusion, args=(job, sp, data.get("tier", 1), data.get("themeIdx"),
                                                          data.get("wallet") or None),
                                 daemon=True).start()
                return self._json({"job": job})
            except Exception as e:
                return self._json({"error": str(e)[:300]}, 500)
        # proxy trappist.land : /api/tc/<chemin> -> TC_API/api/<chemin> (serveur-à-serveur, pas de CORS)
        if urlparse(self.path).path.startswith("/api/tc/"):
            p = self.path.replace("/api/tc", "/api", 1)
            try:
                n = int(self.headers.get('Content-Length') or 0)
                data = json.loads(self.rfile.read(n) or b"{}")
                return self._json(tc_post(p, data, timeout=240))
            except urllib.error.HTTPError as e:
                return self._json({"error": e.read()[:250].decode('utf-8', 'ignore')}, e.code)
            except Exception as e:
                return self._json({"error": str(e)[:250]}, 502)

        # ========== PARTNER API (SkyLaws) ==========
        if urlparse(self.path).path == "/api/partner/generate/image":
            try:
                n = int(self.headers.get('Content-Length') or 0)
                data = json.loads(self.rfile.read(n) or b"{}")
                api_key = self.headers.get("X-API-Key", "")

                # Clé API → wallet lié (remplace par le vrai wallet de SkyLaws)
                PARTNER_WALLETS = {
                    "skylaws-pilot": "METTRE_LE_WALLET_ICI",
                }

                wallet = PARTNER_WALLETS.get(api_key)
                if not wallet:
                    return self._json({"error": "Invalid API key"}, 401)

                model = data.get("model", "schnell")
                tokens_needed = 1 if model == "schnell" else 2

                # Vérifier le vrai solde
                bal, err = tc_balance(wallet)
                if err or bal < tokens_needed:
                    return self._json({"error": "Insufficient tokens", "balance": bal}, 402)

                prompt = data.get("prompt", "").strip()
                if not prompt:
                    return self._json({"error": "prompt required"}, 400)

                # Génération
                model_id = "wavespeed-ai/flux-dev" if model == "dev" else IMG_MODEL
                r = post(f"{BASE}/{model_id}", {
                    "prompt": prompt,
                    "size": "1024*1024",
                    "output_format": "png",
                    "num_images": 1,
                    "seed": random.randint(1, 2**31 - 1),
                })
                tid = (r.get("data") or {}).get("id") or r.get("id")
                out = poll(tid, "partner image")
                url = out[0] if out else None

                if not url:
                    return self._json({"error": "Generation failed"}, 500)

                # Débit réel via le backend TrappistAI
                try:
                    tc_post("/api/generate/image", {"walletAddress": wallet, "prompt": prompt})
                except Exception:
                    pass

                return self._json({
                    "success": True,
                    "url": url,
                    "model": model,
                    "tokens_used": tokens_needed,
                    "remaining_balance": bal - tokens_needed,
                })
            except Exception as e:
                return self._json({"error": str(e)[:300]}, 500)

        self.send_error(404)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/fuse_status":
            job = JOBS.get(parse_qs(u.query).get("id", [""])[0])
            return self._json(job or {"status": "error", "error": "job inconnu"}, 200 if job else 404)
        # proxy trappist.land : /api/tc/<chemin> -> TC_API/api/<chemin>
        if u.path.startswith("/api/tc/"):
            p = self.path.replace("/api/tc", "/api", 1)
            try:
                return self._json(tc_get(p, timeout=45))
            except urllib.error.HTTPError as e:
                return self._json({"error": e.read()[:250].decode('utf-8', 'ignore')}, e.code)
            except Exception as e:
                return self._json({"error": str(e)[:250]}, 502)
        super().do_GET()

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer(('', port), Handler) as httpd:
    print(f'Phénix Legends -> http://localhost:{port}/nebula.html', flush=True)
    httpd.serve_forever()
