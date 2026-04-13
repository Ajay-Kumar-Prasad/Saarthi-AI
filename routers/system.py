from fastapi import APIRouter


router = APIRouter(tags=["system"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "saarthi-ai"}
