from fastapi import APIRouter, Query
from typing import List, Optional
from scraper import fetch_anime_list, fetch_anime_details
from config import BASE_URL
from download import router as download_router  # Importamos el router de descarga

router = APIRouter()

@router.get("/anime-list")
def get_anime_list(
    page: int = 1,
    query: Optional[str] = None,
    year: Optional[List[int]] = Query(None),
    type: Optional[List[str]] = Query(None),
    status: Optional[List[int]] = Query(None),
    order: str = Query("default")
):
    params = {"page": page, "order": order}
    if query:
        params["q"] = query.replace(" ", "+")
    if year:
        params.update({f"year%5B%5D": y for y in year})
    if type:
        params.update({f"type%5B%5D": t for t in type})
    if status:
        params.update({f"status%5B%5D": s for s in status})

    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    url = f"{BASE_URL}/browse?{query_string}"

    return {"page": page, "animes": fetch_anime_list(url)}

@router.get("/details")
def get_details(url: str, content_type: str = Query(..., description="Anime, Película, Especial, OVA")):
    return fetch_anime_details(url, content_type)

# Agregar rutas de descarga
router.include_router(download_router)

