# 🛸 Trappist Legend — NÉBULA

**Le jeu de démonstration de [trappist.land](https://trappist.land)** : la génération IA *dans* le jeu, en direct.

Un FPS d'exploration sur **Nébula**, la lune pourpre de Trappist : capture des créatures IA (Turtlian 🐢, Elephantian 🐘, Phenixian 🔥, Dragon 🐉), entraîne-les, fusionne-les en **cartes d'arène uniques générées par IA**, et bats-toi en duels de cartes façon *Legendary Species*.

> Explore → Capture → Entraîne → Fusionne (IA) → Duel d'arène. Chaque carte fusionnée est une œuvre unique générée par WaveSpeed/FLUX.

## ✨ Features

- **FPS 3D** (Three.js) : monde ouvert nocturne, créatures territoriales avec movesets propres (charges, esquives, souffle de feu du dragon 🔥), captures au filet (stock limité, recharges rares au sol), extraction à la capsule — meurs et tu perds ton butin non sécurisé
- **Progression** : niveaux pilote + niveaux par créature (XP en expédition *et* en arène) — deux joueurs n'ont jamais le même deck
- **🧬 Fusion IA** : sacrifie 3-6 cartes d'une espèce → l'IA dessine une variante unique (mutations, poses, décors aléatoires) · re-fusions illimitées par rangs (II, III, IV…)
- **⚔️ Arène** : duels 20 cartes, 1v1 simultané à carte cachée, cycle d'espèces (🐢>🐉>🔥>🐘>🐢), tie-break au niveau, XP de combat pour tes cartes
- **💳 Casper Network** : connexion Casper Wallet, débit de crédits [trappist.land](https://trappist.land) pour les générations (1 token = 1 image), JcJ en ligne asynchrone
- 🌍 FR/EN

## 🚀 Lancer le jeu en local

```bash
# prérequis : Python 3.10+ · une clé WaveSpeed dans ../.env (WAVESPEED_API_KEY=...)
pip install Pillow requests
python serve.py 8000
# -> http://localhost:8000/nebula.html
```

Sans clé WaveSpeed, tout fonctionne hors génération de fusions.

## 🏗️ Architecture

| Pièce | Rôle |
|---|---|
| `nebula.html` | le jeu complet (Three.js + logique, zéro build) |
| `serve.py` | serveur statique local + proxy fusion IA + proxy backend trappist.land (CORS-safe) |
| `netlify.toml` | déploiement statique + proxy `/api/tc/*` → backend Render (même origine, zéro CORS) |
| `nebula_game.py` | extension à copier dans le backend [TrappistAI](https://github.com/UnrealNFT/TrappistAI) (`backend/`) : fusion payante (`/api/game/fuse`) + JcJ en ligne (`/api/arena/*`) |
| `gen_*.py` | pipeline de génération des assets (modèles 3D Tripo, concepts FLUX) |

Backend live : `trappistai-backend.onrender.com` (Render) · Site : trappist.land (Netlify) · Jeu : play.trappist.land (Netlify, ce repo)

## 🌐 Déploiement

**Netlify (ce repo → play.trappist.land)** : Add new site → Import from GitHub → `UnrealNFT/Trappist-Game` → aucun build, publish `.` → DNS : `play.trappist.land` CNAME vers le site Netlify. Auto-deploy à chaque push. ✅

**Render (backend TrappistAI)** : copier `nebula_game.py` dans `backend/`, ajouter dans `main.py` :
```python
import nebula_game
app.include_router(nebula_game.router)
```
Push → redéploiement auto. Active : fusion payante en ligne (débit tokens réel) + arène JcJ (decks, adversaires, leaderboard).

## 🔐 Secrets

Aucune clé dans ce repo : `WAVESPEED_API_KEY` se lit depuis `../.env` (hors repo, jamais commité).

---

*Nébula est une lune de l'écosystème Trappist — le futur de la génération IA jouable.* 🌙
