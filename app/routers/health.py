from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_class=ORJSONResponse)
async def health():
    return {"status": "ok", "service": "pocket-option-market-intelligence"}
