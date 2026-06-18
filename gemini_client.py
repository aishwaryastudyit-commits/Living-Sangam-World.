"""
gemini_client.py — Centralized Gemini client.
Single place to initialize and get the model.
All modules import from here — no duplicate genai.configure() calls.
"""

import os
import time
import base64   # ← add this

IMAGE_MODELS_TO_TRY = [
    "gemini-2.5-flash-image",   # GA, cheapest, most stable — try first
    "gemini-3.1-flash-image",   # "Nano Banana 2" — newer, also GA
    "gemini-3-pro-image",       # "Nano Banana Pro" — best quality, priciest, last resort
]


def _model_candidates(env_name: str, defaults: list[str]) -> list[str]:
    configured = [
        model.strip()
        for model in os.getenv(env_name, "").split(",")
        if model.strip()
    ]
    candidates = configured + defaults
    ordered: list[str] = []
    seen = set()
    for model in candidates:
        if model not in seen:
            ordered.append(model)
            seen.add(model)
    return ordered


class _SmartImageModel:
    """
    Image-generation counterpart to _SmartModel.
    Tries multiple Gemini image models with retry, same API key.
    Returns raw PNG bytes on success.
    """

    def generate_image(self, prompt: str) -> bytes:
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Run: pip install google-generativeai")

        genai.configure(api_key=_get_api_key())
        last_error = None

        for model_name in IMAGE_MODELS_TO_TRY:
            for attempt in range(1, 3):
                try:
                    print(f"[gemini-image] Trying {model_name} (attempt {attempt}/2)...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            response_modalities=["IMAGE"],
                        ),
                    )
                    for part in response.candidates[0].content.parts:
                        if getattr(part, "inline_data", None) and part.inline_data.data:
                            print(f"[gemini-image] ✅ {model_name} succeeded.")
                            return base64.b64decode(part.inline_data.data)
                    raise RuntimeError("No image data in response.")
                except Exception as e:
                    last_error = e
                    err = str(e)
                    if _is_invalid_api_key_error(err):
                        global _api_key
                        _api_key = None
                        raise EnvironmentError(_invalid_api_key_message()) from e
                    if any(x in err for x in ["503", "UNAVAILABLE", "high demand"]):
                        wait = 5 * attempt
                        print(f"[gemini-image] ⏳ Overloaded, waiting {wait}s...")
                        time.sleep(wait)
                    elif any(x in err for x in ["429", "quota", "rate"]):
                        print(f"[gemini-image] ⚠️ Quota hit on {model_name}, trying next model...")
                        break
                    elif any(x in err for x in ["404", "not found"]):
                        print(f"[gemini-image] ⚠️ {model_name} unavailable, skipping...")
                        break
                    else:
                        print(f"[gemini-image] 🚨 Unexpected error: {err[:150]}")
                        break

        raise RuntimeError(f"All Gemini image models failed. Last error: {last_error}")


def get_image_model() -> _SmartImageModel:
    """Returns a smart image-generation wrapper. Same pattern as get_model(), just for images."""
    return _SmartImageModel()
# Free tier models in order of stability — most reliable first
MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
]

_api_key = None


def _clean_api_key(value: str | None) -> str:
    cleaned = str(value or "").strip().strip('"').strip("'").strip()
    if cleaned.startswith("`") and cleaned.endswith("`"):
        cleaned = cleaned.strip("`").strip()
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    lowered = cleaned.lower()
    if (
        not cleaned
        or lowered.startswith("paste_your_")
        or lowered in {"none", "null", "your_api_key_here", "your_key_here"}
        or "paste_your" in lowered
    ):
        return ""
    return cleaned


def _get_api_key():
    global _api_key
    if _api_key is None:
        _api_key = _clean_api_key(os.getenv("GEMINI_API_KEY")) or _clean_api_key(os.getenv("GOOGLE_API_KEY"))
        if not _api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not found. "
                "Add it to your .env file: GEMINI_API_KEY=your_key_here"
            )
    return _api_key


def _is_invalid_api_key_error(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return "api_key_invalid" in lowered or "api key not valid" in lowered or "api key invalid" in lowered


def _invalid_api_key_message() -> str:
    return (
        "Gemini API key is invalid. In Streamlit Cloud, set only "
        'GEMINI_API_KEY = "your_real_google_ai_studio_key" in Secrets, '
        "then reboot the app. Do not use paste_your_* placeholders or Bearer prefixes."
    )


class _SmartModel:
    """
    Drop-in replacement for GenerativeModel.
    Tries multiple models with retry — existing code needs zero changes.
    """
    def generate_content(self, prompt: str):
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("Run: pip install google-generativeai")

        genai.configure(api_key=_get_api_key())
        last_error = None
        models_to_try = _available_text_model_candidates(genai)
        if not models_to_try:
            raise RuntimeError("No Gemini text models are available for generateContent.")

        for model_name in models_to_try:
            for attempt in range(1, 4):
                try:
                    print(f"[gemini] Trying {model_name} (attempt {attempt}/3)...")
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    print(f"[gemini] ✅ {model_name} succeeded.")
                    return response
                except Exception as e:
                    last_error = e
                    err = str(e)
                    if _is_invalid_api_key_error(err):
                        global _api_key
                        _api_key = None
                        raise EnvironmentError(_invalid_api_key_message()) from e
                    if any(x in err for x in ["503", "UNAVAILABLE", "high demand"]):
                        wait = 5 * attempt
                        print(f"[gemini] ⏳ Overloaded, waiting {wait}s...")
                        time.sleep(wait)
                    elif any(x in err for x in ["429", "quota", "rate"]):
                        print(f"[gemini] ⚠️ Quota hit on {model_name}, trying next...")
                        break  # try next model immediately
                    elif any(x in err for x in ["404", "not found"]):
                        print(f"[gemini] ⚠️ {model_name} unavailable, skipping...")
                        break
                    else:
                        print(f"[gemini] 🚨 Unexpected error: {err[:150]}")
                        break

        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def get_model() -> _SmartModel:
    """
    Returns a smart model wrapper.
    Drop-in for genai.GenerativeModel — same .generate_content() interface.
    """
    return _SmartModel()


def _available_text_model_candidates(genai) -> list[str]:
    candidates = _model_candidates("DTEC_GEMINI_MODELS", MODELS_TO_TRY)
    try:
        available = set()
        for model in genai.list_models():
            methods = set(getattr(model, "supported_generation_methods", []) or [])
            if "generateContent" in methods:
                available.add(_normalize_model_name(getattr(model, "name", "")))
        if available:
            supported_candidates = [model for model in candidates if _normalize_model_name(model) in available]
            if supported_candidates:
                return supported_candidates
            return _fallback_flash_models(available)
    except Exception as exc:
        print(f"[gemini] Could not list Gemini models; using configured defaults. {str(exc)[:150]}")
    return candidates


def _normalize_model_name(model_name: str) -> str:
    return (model_name or "").strip().removeprefix("models/")


def _fallback_flash_models(available: set[str]) -> list[str]:
    flash_models = [
        model for model in available
        if "gemini" in model and "flash" in model and "-image" not in model
    ]
    return sorted(flash_models, key=_model_sort_key)


def _model_sort_key(model_name: str) -> tuple[int, str]:
    if "2.5" in model_name:
        return (0, model_name)
    if "2.0" in model_name:
        return (1, model_name)
    return (2, model_name)
