# partner_api.py
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
import asyncio
import wavespeed

router = APIRouter()

# Clés API partenaires (à mettre en variable d'environnement plus tard)
PARTNER_KEYS = {
    "skylaws-pilot": {"name": "SkyLaws", "balance": 100.0},  # solde en $
}

class PartnerImageIn(BaseModel):
    prompt: str
    model: str = "schnell"  # "schnell" ou "dev"

@router.post("/api/partner/generate/image")
async def partner_generate_image(
    data: PartnerImageIn,
    x_api_key: str = Header(..., alias="X-API-Key")
):
    partner = PARTNER_KEYS.get(x_api_key)
    if not partner:
        raise HTTPException(status_code=401, detail="Invalid API key")

    cost = 0.01 if data.model == "schnell" else 0.04

    if partner["balance"] < cost:
        raise HTTPException(status_code=402, detail="Insufficient partner balance")

    try:
        gen_fn = wavespeed.generate_image_hd if data.model == "dev" else wavespeed.generate_image
        url = await asyncio.get_event_loop().run_in_executor(None, gen_fn, data.prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

    # Débit du solde (en mémoire pour le pilot)
    partner["balance"] -= cost

    return {
        "success": True,
        "url": url,
        "model": data.model,
        "cost": cost,
        "remaining_balance": round(partner["balance"], 2),
    }
