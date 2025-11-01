from fastapi import APIRouter

router = APIRouter(prefix="/meta", tags=["v2/meta"])


@router.get("/models")
async def get_models():
    from config import get_available_models, get_default_model

    available_models = get_available_models()
    default_model = get_default_model()

    return {"models": available_models, "default_model": default_model}


@router.get("/personality-presets")
async def get_personality_presets():
    return {
        "presets": {
            "helpful": {"style": "helpful", "tone": "friendly"},
            "professional": {"style": "expert", "tone": "professional"},
            "casual": {"style": "conversational", "tone": "casual"},
            "creative": {"style": "creative", "tone": "enthusiastic"},
            "concise": {"style": "concise", "tone": "direct"},
        }
    }
