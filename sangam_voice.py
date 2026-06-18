"""
sangam_voice.py — Audio Narration Engine 🔊
Converts summary or scene text to speech.
Saves to assets/audio/. Returns NarrationResult.
No UI. No analysis. Only narration generation.
"""

import os
import hashlib
import subprocess
import shutil
from pathlib import Path
from schemas import NarrationResult, SceneFrame, PoemAnalysis
import language_engine

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

OUTPUT_DIR = Path("assets/audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TTS_BACKEND = os.getenv("TTS_BACKEND", "gtts")
# Options: "gtts" | "elevenlabs" | "openai"


# ─────────────────────────────────────────────
# TEXT BUILDERS
# ─────────────────────────────────────────────

def _clean_join(parts: list[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def _build_analysis_narration(
    analysis: PoemAnalysis,
    scenes: list[SceneFrame] | None = None,
) -> str:
    """Build a warm Tamil pulavar-style narration script."""
    thinai = analysis.thinai.value if analysis.thinai else "Sangam"
    landscape = (
        analysis.muthal_porul.landscape
        if analysis.muthal_porul and analysis.muthal_porul.landscape
        else "தமிழர் நிலம்"
    )

    parts = [
        "வணக்கம். இப்போது நாம் சங்க இலக்கியத்தின் ஓர் உயிருள்ள உலகிற்குள் மெதுவாக செல்கிறோம்.",
        f"இந்தப் பாடல் {thinai} திணையின் மனநிலையை தாங்குகிறது.",
        f"இங்கே நிலம் வெறும் பின்னணி அல்ல; {landscape} மனித உள்ளத்தின் குரலாக மாறுகிறது.",
    ]

    if analysis.summary_tamil:
        parts.append(f"பாடலின் மைய உணர்வு இதுதான்: {analysis.summary_tamil}")
    elif analysis.summary:
        parts.append(f"பாடல் சொல்வது இதுதான்: {analysis.summary}")

    if analysis.emotion or analysis.meyppadu:
        parts.append(
            f"இதன் மெய்ப்பாடு {analysis.emotion or analysis.meyppadu}; ஆனால் அது கத்தாமல், அமைதியாக நம் மனத்தில் அமர்கிறது."
        )

    if analysis.uri_porul:
        parts.append(f"உரிப்பொருள் நோக்கில், {analysis.uri_porul}")

    for scene in scenes or []:
        scene_line = _clean_join([scene.title, scene.description])
        if scene_line:
            parts.append(
                f"காட்சி {scene.scene_id}: {scene_line} இந்தப் படம் கவிதையின் உள்ளொளியை கண்களுக்கு தருகிறது."
            )

    parts.extend(
        [
            "ஒரு புலவர் பேசுவது போல நினைத்துப் பாருங்கள்: இயற்கை முதலில் பேசுகிறது; மனிதர் பின்னர் பதில் அளிக்கிறார்.",
            "மலர், நீர், மேகம், பாதை, காத்திருப்பு இவை அனைத்தும் இங்கே இலக்கியக் குறியீடுகளாக நிற்கின்றன.",
            "அதனால் இந்த அனுபவம் ஒரு விளக்கம் மட்டும் அல்ல; பாடல், காட்சி, குரல் மூன்றும் ஒன்றாக சேரும் சிறிய சங்கப் பயணம்.",
        ]
    )

    return _clean_join(parts)

def _build_scene_narration(scene: SceneFrame) -> str:
    """Build narration script from a single scene."""
    parts = []
    if scene.title:
        parts.append(f"Scene {scene.scene_id}: {scene.title}.")
    parts.append(scene.description)
    if scene.environment:
        parts.append(f"The setting: {scene.environment}.")
    return " ".join(parts)


def _estimate_duration_seconds(text: str, language: str = "en") -> float:
    chars = len(text or "")
    words = len((text or "").split())
    if language == "ta":
        return max(24.0, chars / 11.0)
    return max(18.0, words / 2.35)


def _probe_audio_duration(filepath: Path, text: str, language: str) -> float:
    try:
        from moviepy.editor import AudioFileClip

        clip = AudioFileClip(str(filepath))
        duration = float(clip.duration or 0.0)
        clip.close()
        if duration > 0:
            return duration
    except Exception:
        pass

    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(filepath),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode == 0:
            duration = float(completed.stdout.strip())
            if duration > 0:
                return duration
    except Exception:
        pass

    return _estimate_duration_seconds(text, language)


def _pad_audio_tail(filepath: Path, seconds: float = 0.7) -> None:
    """Add a short silence tail so the final spoken word is not clipped."""
    if seconds <= 0 or not filepath.exists() or not shutil.which("ffmpeg"):
        return

    tmp = filepath.with_name(f"{filepath.stem}_tailpad{filepath.suffix}")
    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(filepath),
                "-af",
                f"apad=pad_dur={seconds}",
                "-c:a",
                "libmp3lame",
                str(tmp),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode == 0 and tmp.exists():
            os.replace(tmp, filepath)
    except Exception:
        pass
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass


# ─────────────────────────────────────────────
# MAIN FUNCTIONS
# ─────────────────────────────────────────────

def generate_voice_narration(
    text: str,
    filename: str = "narration",
    language: str = "en",
) -> NarrationResult:
    """
    Convert text to speech. Save to assets/audio/.
    Returns NarrationResult. Never raises.

    Args:
        text: Text to narrate.
        filename: Base filename (without extension).
        language: Language code ("en", "ta", etc.).
    """
    if not text or not text.strip():
        return NarrationResult.failed("Empty text provided for narration.")

    backend = TTS_BACKEND.lower()

    try:
        if backend == "elevenlabs":
            return _narrate_elevenlabs(text, filename, language)
        elif backend == "openai":
            return _narrate_openai(text, filename)
        else:
            return _narrate_gtts(text, filename, language)
    except Exception as e:
        print(f"[sangam_voice] Narration failed: {e}")
        return NarrationResult.failed(str(e))


def narrate_analysis(
    analysis: PoemAnalysis,
    scenes: list[SceneFrame] | None = None,
    target_language: str = "en",
) -> NarrationResult:
    """Narrate a full poem analysis."""
    narration_language = language_engine.normalize_language(target_language)
    script = language_engine.build_learning_script(
        analysis,
        scenes=scenes,
        target_language=narration_language,
    )
    return generate_voice_narration(
        script,
        filename=f"analysis_narration_{narration_language}",
        language=narration_language,
    )


def narrate_scene(scene: SceneFrame) -> NarrationResult:
    """Narrate a single scene."""
    script = _build_scene_narration(scene)
    return generate_voice_narration(
        script,
        filename=f"scene_{scene.scene_id}_narration",
    )


# ─────────────────────────────────────────────
# GTTS BACKEND (default, free)
# ─────────────────────────────────────────────

def _narrate_gtts(text: str, filename: str, language: str = "en") -> NarrationResult:
    """
    Google Text-to-Speech (free, no API key needed).
    Falls back to English if Tamil not supported.
    """
    try:
        from gtts import gTTS
        from gtts.lang import tts_langs
    except ImportError:
        raise ImportError("gTTS not installed. Run: pip install gtts")

    lang = language_engine.gtts_language(language)
    try:
        supported_langs = tts_langs()
        if lang not in supported_langs:
            lang = "en"
    except Exception:
        pass

    filepath = OUTPUT_DIR / f"{filename}.mp3"

    pulavar_slow = os.getenv("DTEC_PULAVAR_SLOW", "1") == "1"
    tts = gTTS(text=text, lang=lang, slow=pulavar_slow)
    tts.save(str(filepath))
    _pad_audio_tail(filepath)

    return NarrationResult(
        audio_path=str(filepath),
        duration_seconds=_probe_audio_duration(filepath, text, lang),
        language=lang,
        success=True,
    )


# ─────────────────────────────────────────────
# ELEVENLABS BACKEND
# ─────────────────────────────────────────────

def _narrate_elevenlabs(text: str, filename: str, language: str = "en") -> NarrationResult:
    """
    ElevenLabs high-quality TTS.
    Requires ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID.
    """
    import requests

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    if not api_key:
        raise EnvironmentError("ELEVENLABS_API_KEY not set.")

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.72,
                "similarity_boost": 0.78,
                "style": 0.35,
                "use_speaker_boost": True,
            },
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs error {response.status_code}: {response.text}")

    filepath = OUTPUT_DIR / f"{filename}.mp3"
    with open(filepath, "wb") as f:
        f.write(response.content)
    _pad_audio_tail(filepath)

    return NarrationResult(
        audio_path=str(filepath),
        duration_seconds=_probe_audio_duration(filepath, text, language),
        language=language,
        success=True,
    )


# ─────────────────────────────────────────────
# OPENAI TTS BACKEND
# ─────────────────────────────────────────────

def _narrate_openai(text: str, filename: str) -> NarrationResult:
    """
    OpenAI TTS (tts-1 model).
    Requires OPENAI_API_KEY.
    """
    import requests

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    response = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "tts-1",
            "input": text,
            "voice": "onyx",
            "speed": 0.85,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(f"OpenAI TTS error {response.status_code}: {response.text}")

    filepath = OUTPUT_DIR / f"{filename}.mp3"
    with open(filepath, "wb") as f:
        f.write(response.content)
    _pad_audio_tail(filepath)

    return NarrationResult(
        audio_path=str(filepath),
        duration_seconds=_probe_audio_duration(filepath, text, "en"),
        language="en",
        success=True,
    )
 
