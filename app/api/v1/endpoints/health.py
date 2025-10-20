from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def ping():
    return {"ping": "pong"}


@router.get("/health")
def health():
    """Health check endpoint pour Docker et monitoring"""
    return {
        "status": "healthy",
        "service": "MPPEEP Dashboard",
        "version": "1.0.0"
    }

    
