
"""
scene_generator.py — Image Generation Engine 🖼️
Takes SceneFrames → generates/saves images.
Currently supports: real image providers, curated-cache fallback in app.py,
with hooks for Stable Diffusion / Imagen / DALL-E.

UPGRADED FOR DTEC:
✓ Cache support
✓ Automatic fallback
✓ HuggingFace backend
✓ Existing code preserved
✓ Placeholder available only when explicitly requested
✓ No UI. No analysis. Only image generation.
"""

import os
import hashlib
import shutil
from pathlib import Path

from schemas import SceneFrame, GeneratedImage, Thinai







CHARACTER_MEMORY: dict[str, dict] = {}
def _get_character_signature(scene: SceneFrame) -> str:
    return "|".join(sorted(scene.characters))

def _build_character_consistency(scene: SceneFrame) -> str:
    signature = _get_character_signature(scene)

    if signature not in CHARACTER_MEMORY:
        CHARACTER_MEMORY[signature] = {
            "appearance":
                "traditional Sangam attire, long dark hair, period ornaments"
        }

    return CHARACTER_MEMORY[signature]["appearance"]
    scene.visual_prompt += (
    ", consistent character appearance: "
    + _build_character_consistency(scene)
)
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OUTPUT_DIR = Path("assets/images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = OUTPUT_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "auto")

# Options:
# "auto"
# "placeholder"
# "stability"
# "dalle"
# "huggingface"
# "imagen"


# ─────────────────────────────────────────────
# CACHE HELPERS
# ─────────────────────────────────────────────

def _get_cache_path(scene: SceneFrame) -> Path:
    """
    Generate deterministic cache path based on thinai and prompt.
    Uses poem-specific cache folders to prevent image mixing.
    """

    # Get the thinai value (use lowercase for directory name)
    thinai_folder = scene.thinai.value.lower() if scene.thinai != Thinai.UNKNOWN else "cache"
    
    # Create thinai-specific cache directory
    thinai_cache_dir = CACHE_DIR / thinai_folder
    thinai_cache_dir.mkdir(parents=True, exist_ok=True)

    # Generate hash of the visual prompt
    scene_hash = hashlib.md5(
        scene.visual_prompt.encode("utf-8")
    ).hexdigest()

    return thinai_cache_dir / f"{scene_hash}.png"


def _load_cached_image(scene: SceneFrame) -> GeneratedImage | None:
    """
    Return cached image if available.
    """

    cache_path = _get_cache_path(scene)

    if cache_path.exists():
        print(
            f"[scene_generator] Using cached image "
            f"for scene {scene.scene_id}"
        )

        return GeneratedImage(
            scene_id=scene.scene_id,
            image_path=str(cache_path),
            prompt_used=scene.visual_prompt,
            width=512,
            height=512,
            success=True,
            backend="cache",
        )

    return None


def _save_to_cache(scene: SceneFrame, image_path: str):
    """
    Save generated image to cache.
    """

    if not image_path:
        return

    src = Path(image_path)

    if not src.exists():
        return

    cache_path = _get_cache_path(scene)

    try:
        shutil.copy(src, cache_path)

        print(
            f"[scene_generator] Cached scene "
            f"{scene.scene_id}"
        )

    except Exception as e:
        print(
            f"[scene_generator] Cache save failed: {e}"
        )


# ─────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────

def generate_scene_image(scene: SceneFrame) -> GeneratedImage:
    """
    Generate an image for a single SceneFrame.

    Flow:
    Cache
      ↓
    Stability
      ↓
    HuggingFace
      ↓
    DALL·E
      ↓
    Cache fallback is handled by app.py when providers fail.

    Never raises.
    """

    cached = _load_cached_image(scene)

    if cached:
        return cached

    backend = IMAGE_BACKEND.lower()

    if backend == "auto":

        providers = [
            "gemini",
            "stability",
            "huggingface",
            "dalle",
        ]

    else:

        providers = [backend]

    for provider in providers:

        try:

            print(
                f"[scene_generator] Trying "
                f"{provider} for scene "
                f"{scene.scene_id}"
            )


            if provider == "gemini":            # ← add this block

                result = _generate_gemini(scene)

            elif provider == "stability":        # ← change "if" to "elif" here

                result = _generate_stability(scene)

            elif provider == "huggingface":

                result = _generate_huggingface(scene)

            elif provider == "dalle":

                result = _generate_dalle(scene)

            elif provider == "placeholder":

                result = _generate_placeholder(scene)

            else:

                raise ValueError(f"Unknown image backend: {provider}")

            if result.success:

                _save_to_cache(
                    scene,
                    result.image_path,
                )

                return result

        except Exception as e:

            print(
                f"[scene_generator] "
                f"{provider} failed "
                f"for scene "
                f"{scene.scene_id}: {e}"
            )

    return GeneratedImage.failed(
        scene_id=scene.scene_id,
        error="All image providers failed.",
    )


def generate_all_scenes(
    scenes: list[SceneFrame]
) -> list[GeneratedImage]:
    """
    Generate images for all scenes.

    Always returns a list.
    """

    return [
        generate_scene_image(scene)
        for scene in scenes
    ]


# ─────────────────────────────────────────────
# PLACEHOLDER BACKEND (UNCHANGED)
# ─────────────────────────────────────────────

def _generate_placeholder(
    scene: SceneFrame,
) -> GeneratedImage:
    """
    Generate a simple colored placeholder image
    using Pillow.

    Ensures the pipeline always has something
    to display.
    """

    try:

        from PIL import (
            Image,
            ImageDraw,
            ImageFont,
        )

        prompt_hash = int(
            hashlib.md5(
                scene.visual_prompt.encode()
            ).hexdigest(),
            16,
        )

        PALETTES = [
            (139, 90, 43),
            (34, 85, 34),
            (70, 130, 180),
            (210, 140, 60),
            (100, 60, 120),
            (180, 80, 80),
        ]

        bg_color = (
            PALETTES[
                prompt_hash %
                len(PALETTES)
            ]
        )

        img = Image.new(
            "RGB",
            (512, 512),
            color=bg_color,
        )

        draw = ImageDraw.Draw(img)

        draw.rectangle(
            [20, 20, 492, 492],
            outline=(255, 255, 255, 100),
            width=2,
        )

        title_text = (
            f"Scene {scene.scene_id}"
        )

        if scene.title:

            title_text += (
                f": {scene.title}"
            )

        words = (
            scene.description.split()
        )

        lines = []

        current = ""

        for word in words:

            if len(current + word) < 40:

                current += word + " "

            else:

                lines.append(
                    current.strip()
                )

                current = word + " "

        if current:

            lines.append(current.strip())

        draw.text(
            (30, 40),
            title_text,
            fill=(255, 255, 255),
        )

        y = 80

        for line in lines[:8]:

            draw.text(
                (30, y),
                line,
                fill=(220, 220, 200),
            )

            y += 22

        draw.text(
            (30, 460),
            f"[{scene.mood.value}]",
            fill=(200, 200, 180),
        )

        filename = (
            f"scene_{scene.scene_id}.png"
        )

        filepath = OUTPUT_DIR / filename

        img.save(str(filepath))

        return GeneratedImage(
            scene_id=scene.scene_id,
            image_path=str(filepath),
            prompt_used=scene.visual_prompt,
            width=512,
            height=512,
            success=True,
            backend="placeholder",
        )

    except ImportError:

        return GeneratedImage(
            scene_id=scene.scene_id,
            image_path="",
            prompt_used=scene.visual_prompt,
            success=False,
            error=(
                "Pillow not installed. "
                "Run: pip install Pillow"
            ),
        )
    



def _generate_gemini(scene: SceneFrame) -> GeneratedImage:
    """
    Generate image via Gemini's native image models (Nano Banana family).
    Reuses the same GEMINI_API_KEY as the text analysis pipeline — no extra key needed.
    """

    from gemini_client import get_image_model

    image_bytes = get_image_model().generate_image(scene.visual_prompt)

    filename = f"scene_{scene.scene_id}.png"
    filepath = OUTPUT_DIR / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    return GeneratedImage(
        scene_id=scene.scene_id,
        image_path=str(filepath),
        prompt_used=scene.visual_prompt,
        width=1024,
        height=1024,
        success=True,
        backend="gemini",
    )

# ─────────────────────────────────────────────
# STABILITY AI BACKEND (UNCHANGED)
# ─────────────────────────────────────────────

def _generate_stability(scene: SceneFrame) -> GeneratedImage:
    """
    Generate image via Stability AI API.
    Requires STABILITY_API_KEY environment variable.
    """

    import requests

    api_key = os.getenv("STABILITY_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "STABILITY_API_KEY not set."
        )

    response = requests.post(
        "https://api.stability.ai/v1/generation/"
        "stable-diffusion-xl-1024-v1-0/text-to-image",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "text_prompts": [
                {
                    "text": scene.visual_prompt,
                    "weight": 1.0,
                },
                {
                    "text": (
                        "modern, anachronistic, "
                        "photorealistic"
                    ),
                    "weight": -1.0,
                },
            ],
            "cfg_scale": 7,
            "height": 512,
            "width": 512,
            "samples": 1,
            "steps": 30,
        },
        timeout=60,
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"Stability API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    import base64

    data = response.json()

    image_data = base64.b64decode(
        data["artifacts"][0]["base64"]
    )

    filename = (
        f"scene_{scene.scene_id}.png"
    )

    filepath = OUTPUT_DIR / filename

    with open(filepath, "wb") as f:

        f.write(image_data)

    return GeneratedImage(
        scene_id=scene.scene_id,
        image_path=str(filepath),
        prompt_used=scene.visual_prompt,
        width=512,
        height=512,
        success=True,
        backend="stability",
    )


# ─────────────────────────────────────────────
# DALL·E BACKEND (UNCHANGED)
# ─────────────────────────────────────────────

def _generate_dalle(scene: SceneFrame) -> GeneratedImage:
    """
    Generate image via OpenAI DALL·E 3.
    Requires OPENAI_API_KEY environment variable.
    """

    import requests
    import urllib.request

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY not set."
        )

    response = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "dall-e-3",
            "prompt": scene.visual_prompt,
            "n": 1,
            "size": "1024x1024",
            "response_format": "url",
        },
        timeout=60,
    )

    if response.status_code != 200:

        raise RuntimeError(
            f"DALL-E API error "
            f"{response.status_code}: "
            f"{response.text}"
        )

    data = response.json()

    image_url = data["data"][0]["url"]

    filename = (
        f"scene_{scene.scene_id}.png"
    )

    filepath = OUTPUT_DIR / filename

    urllib.request.urlretrieve(
        image_url,
        str(filepath),
    )

    return GeneratedImage(
        scene_id=scene.scene_id,
        image_path=str(filepath),
        prompt_used=scene.visual_prompt,
        width=1024,
        height=1024,
        success=True,
        backend="dalle",
    )


# ─────────────────────────────────────────────
# HUGGING FACE BACKEND (NEW)
# ─────────────────────────────────────────────

def _generate_huggingface(
    scene: SceneFrame,
) -> GeneratedImage:
    """
    Generate image using Hugging Face
    Inference API.

    Requires:
        HF_TOKEN

    Default model:
        stabilityai/stable-diffusion-xl-base-1.0
    """

    import requests

    api_key = os.getenv("HF_TOKEN")

    if not api_key:
        raise EnvironmentError(
            "HF_TOKEN not set."
        )

    API_URL = (
        "https://api-inference.huggingface.co/"
        "models/"
        "stabilityai/"
        "stable-diffusion-xl-base-1.0"
    )

    response = requests.post(
        API_URL,
        headers={
            "Authorization":
                f"Bearer {api_key}"
        },
        json={
            "inputs":
                scene.visual_prompt
        },
        timeout=120,
    )

    if response.status_code != 200:

        try:

            error_data = response.json()

        except Exception:

            error_data = response.text

        raise RuntimeError(
            f"HuggingFace error "
            f"{response.status_code}: "
            f"{error_data}"
        )

    filename = (
        f"scene_{scene.scene_id}.png"
    )

    filepath = OUTPUT_DIR / filename

    with open(filepath, "wb") as f:

        f.write(response.content)

    return GeneratedImage(
        scene_id=scene.scene_id,
        image_path=str(filepath),
        prompt_used=scene.visual_prompt,
        width=512,
        height=512,
        success=True,
        backend="huggingface",
    )


# ─────────────────────────────────────────────
# END OF FILE
# ─────────────────────────────────────────────
