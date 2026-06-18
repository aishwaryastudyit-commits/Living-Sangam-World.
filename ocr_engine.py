"""
ocr_engine.py - Camera / Image OCR Engine.

Extracts Tamil/English poem text from uploaded images using Gemini Vision.
"""

from __future__ import annotations

import io
import os
import re
import time

MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
]

MODEL_ENV_VAR = "DTEC_OCR_MODELS"

OCR_PROMPT = """You are a Tamil and English literary OCR assistant.

Look at this image carefully. It may contain:
- A Tamil poem (classical or modern)
- An English poem or translation
- A mix of both Tamil and English text
- A photo of a book page, manuscript, or handwritten poem

Your task:
1. Extract ALL the poem/literary text you can see
2. Preserve line breaks exactly as they appear
3. Do NOT add any explanation, title, or commentary
4. Do NOT translate - output the text exactly as it appears
5. If both Tamil and English are present, output both with a blank line between them

After the extracted text, on a new line write exactly one of:
LANGUAGE: tamil
LANGUAGE: english
LANGUAGE: mixed

Output ONLY the poem text and the LANGUAGE line. Nothing else."""


def extract_text_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[str, str]:
    """
    Extract poem text from an image using Gemini Vision.

    Returns:
        (extracted_text, detected_language)
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not image_bytes:
        raise ValueError("No image bytes received from upload/camera input.")

    if not api_key:
        return _extract_text_with_tesseract(image_bytes)

    models_to_try = _model_candidates(api_key)
    if not models_to_try:
        return _extract_text_with_tesseract(image_bytes)

    last_error: Exception | None = None
    last_actionable_error: Exception | None = None
    for model_name in models_to_try:
        for attempt in range(1, 4):
            try:
                print(f"[ocr] Trying {model_name} (attempt {attempt}/3)...")
                raw = _call_gemini_vision(image_bytes, mime_type, api_key, model_name)
                extracted, lang = _parse_response(raw)
                extracted = _clean_text(extracted)
                if not extracted.strip():
                    raise ValueError("Gemini returned an empty OCR result.")
                print(f"[ocr] {model_name} succeeded. Language: {lang}")
                return extracted, lang
            except Exception as exc:
                last_error = exc
                err = str(exc)
                if any(x in err for x in ("429", "quota", "RESOURCE_EXHAUSTED", "rate")):
                    last_actionable_error = exc
                    print(f"[ocr] {model_name} quota hit, trying next model...")
                    break
                if any(x in err for x in ("503", "UNAVAILABLE", "high demand")):
                    last_actionable_error = exc
                    wait = 5 * attempt
                    print(f"[ocr] {model_name} overloaded, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                if any(x in err for x in ("404", "not found")):
                    print(f"[ocr] {model_name} unavailable, skipping...")
                    break
                last_actionable_error = exc
                print(f"[ocr] {model_name}: {err[:180]}")
                break

    try:
        return _extract_text_with_tesseract(image_bytes)
    except Exception as local_exc:
        detail = last_actionable_error or last_error
        raise RuntimeError(
            "OCR did not extract readable text. "
            f"Gemini detail: {_friendly_error(detail)} "
            f"Local OCR detail: {_friendly_error(local_exc)}"
        ) from local_exc


def _model_candidates(api_key: str) -> list[str]:
    configured = [
        model.strip()
        for model in os.getenv(MODEL_ENV_VAR, "").split(",")
        if model.strip()
    ]
    candidates = _dedupe(configured + MODELS_TO_TRY)
    available = _available_generate_content_models(api_key)
    if not available:
        return candidates
    supported_candidates = [model for model in candidates if _normalize_model_name(model) in available]
    if supported_candidates:
        return supported_candidates
    return _fallback_flash_models(available)


def _available_generate_content_models(api_key: str) -> set[str]:
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        available: set[str] = set()
        for model in genai.list_models():
            methods = set(getattr(model, "supported_generation_methods", []) or [])
            if "generateContent" in methods:
                available.add(_normalize_model_name(getattr(model, "name", "")))
        return available
    except Exception as exc:
        print(f"[ocr] Could not list Gemini models; using configured defaults. {str(exc)[:160]}")
        return set()


def _dedupe(models: list[str]) -> list[str]:
    ordered: list[str] = []
    seen = set()
    for model in models:
        normalized = _normalize_model_name(model)
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)
    return ordered


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


def _friendly_error(error: Exception | None) -> str:
    if error is None:
        return "No model returned text."
    text = str(error) or error.__class__.__name__
    if "404" in text or "not found" in text.lower():
        return "Gemini did not report any available OCR-capable model."
    return text


def _extract_text_with_tesseract(image_bytes: bytes) -> tuple[str, str]:
    """Local OCR fallback for when Gemini is unavailable or returns no text."""
    try:
        import pytesseract
        from PIL import ImageOps
    except ImportError as exc:
        raise RuntimeError("Local OCR is not installed.") from exc

    image = _prepare_image_for_vision(image_bytes)
    image = ImageOps.grayscale(image)
    image = ImageOps.autocontrast(image)

    languages = _tesseract_languages_to_try()
    last_error: Exception | None = None
    for language in languages:
        try:
            print(f"[ocr] Trying local Tesseract OCR ({language})...")
            text = pytesseract.image_to_string(image, lang=language, config="--psm 6")
            text = _clean_text(text)
            if text.strip():
                _, detected = _parse_response(text)
                print(f"[ocr] Local Tesseract succeeded. Language: {detected}")
                return text, detected
            last_error = ValueError("Local OCR returned no text.")
        except Exception as exc:
            last_error = exc
            print(f"[ocr] Local Tesseract ({language}) failed: {str(exc)[:160]}")

    raise RuntimeError(_friendly_tesseract_error(last_error))


def _tesseract_languages_to_try() -> list[str]:
    configured = [
        lang.strip()
        for lang in os.getenv("DTEC_TESSERACT_LANG", "tam+eng").split(",")
        if lang.strip()
    ]
    return _dedupe(configured + ["tam+eng", "eng"])


def _friendly_tesseract_error(error: Exception | None) -> str:
    text = str(error or "") or "Local OCR returned no text."
    lower = text.lower()
    if "tesseract is not installed" in lower or "not installed" in lower:
        return "Local OCR needs the Tesseract app installed."
    if "failed loading language" in lower or "couldn't load any languages" in lower:
        return "Local OCR is missing Tamil/English Tesseract language data."
    return text


def _call_gemini_vision(image_bytes: bytes, mime_type: str, api_key: str, model_name: str) -> str:
    """Call Gemini Vision using the google-generativeai SDK."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    image = _prepare_image_for_vision(image_bytes)
    response = model.generate_content(
        [OCR_PROMPT, image],
        generation_config={"temperature": 0.0},
    )
    text = getattr(response, "text", "") or ""
    if not text and getattr(response, "candidates", None):
        try:
            text = response.candidates[0].content.parts[0].text
        except Exception:
            text = ""
    if not text:
        raise RuntimeError("Gemini Vision returned no text.")
    return text


def _prepare_image_for_vision(image_bytes: bytes):
    """Open and normalize images from camera/upload before sending to Gemini."""
    from PIL import Image, ImageOps

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.load()
    except Exception as exc:
        raise ValueError("Uploaded file is not a readable image.") from exc

    return image


def _parse_response(raw: str) -> tuple[str, str]:
    """Split Gemini response into (poem_text, language)."""
    raw = (raw or "").strip()
    lang = "unknown"

    lang_match = re.search(r"LANGUAGE:\s*(tamil|english|mixed)", raw, re.IGNORECASE)
    if lang_match:
        lang = lang_match.group(1).lower()
        raw = raw[: lang_match.start()].strip()

    if lang == "unknown":
        tamil_chars = len(re.findall(r"[\u0B80-\u0BFF]", raw))
        english_chars = len(re.findall(r"[A-Za-z]", raw))
        if tamil_chars > 10 and english_chars > 10:
            lang = "mixed"
        elif tamil_chars > 10:
            lang = "tamil"
        else:
            lang = "english"

    return raw, lang


def _clean_text(text: str) -> str:
    lines = (text or "").splitlines()
    cleaned = [line.strip() for line in lines]
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return "\n".join(cleaned)


def image_bytes_from_upload(uploaded_file) -> tuple[bytes, str]:
    """Convert a Streamlit UploadedFile/CameraInput to (bytes, mime_type)."""
    if hasattr(uploaded_file, "getvalue"):
        img_bytes = uploaded_file.getvalue()
    else:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        img_bytes = uploaded_file.read()

    if not img_bytes:
        raise ValueError("Image upload was empty.")

    name = (getattr(uploaded_file, "name", "") or "").lower()
    mime = getattr(uploaded_file, "type", "") or ""
    if not mime:
        if name.endswith(".png"):
            mime = "image/png"
        elif name.endswith(".webp"):
            mime = "image/webp"
        else:
            mime = "image/jpeg"
    return img_bytes, mime
