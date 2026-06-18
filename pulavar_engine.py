"""
pulavar_engine.py — Internal processing layer.
Cleans input, formats prompts, standardizes outputs.
No UI. No API calls. No Streamlit.
"""

import re
import json
from schemas import PoemAnalysis, SceneFrame, Thinai, Mood


# ─────────────────────────────────────────────
# TEXT CLEANING
# ─────────────────────────────────────────────

def clean_poem_text(raw: str) -> str:
    """
    Normalize poem input:
    - Strip leading/trailing whitespace
    - Collapse excessive blank lines
    - Preserve Tamil Unicode characters
    - Remove non-printable characters
    """
    if not raw:
        return ""

    # Remove non-printable characters but keep Tamil Unicode (U+0B80–U+0BFF)
    cleaned = re.sub(r"[^\x09\x0A\x0D\x20-\x7E\u0B80-\u0BFF\u200B-\u200D]", "", raw)

    # Normalize line endings
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse 3+ blank lines into 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


def is_tamil(text: str) -> bool:
    """Check if text contains Tamil script characters."""
    return bool(re.search(r"[\u0B80-\u0BFF]", text))


def detect_language(text: str) -> str:
    return "ta" if is_tamil(text) else "en"


# ─────────────────────────────────────────────
# PROMPT BUILDERS
# ─────────────────────────────────────────────

def build_analysis_prompt(poem: str, prompt_template: str) -> str:
    """
    Inject poem into the analysis prompt template.
    Template must contain {poem} placeholder.
    """
    if "{poem}" not in prompt_template:
        raise ValueError("Analysis prompt template must contain {poem} placeholder.")
    return prompt_template.replace("{poem}", poem)


def build_scene_prompt(analysis: PoemAnalysis, prompt_template: str) -> str:
    """
    Inject structured analysis into the scene weaver prompt.
    Template must contain {analysis_json} placeholder.
    """
    if "{analysis_json}" not in prompt_template:
        raise ValueError("Scene prompt template must contain {analysis_json} placeholder.")
    analysis_json = json.dumps(analysis.model_dump(), ensure_ascii=False, indent=2)
    return prompt_template.replace("{analysis_json}", analysis_json)


# ─────────────────────────────────────────────
# OUTPUT STANDARDIZATION
# ─────────────────────────────────────────────

def parse_json_response(raw_response) -> dict:
    """
    Safely extract JSON from LLM response.
    Handles markdown code fences and stray text.
    Returns empty dict on failure — never raises.
    """
    # Guard: must be a string
    if not isinstance(raw_response, str):
        return {}
    if not raw_response.strip():
        return {}

    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw_response).replace("```", "")

    # Find first { ... } block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Find first [ ... ] block (for arrays)
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {}


def parse_analysis_response(raw: str) -> PoemAnalysis:
    """
    Convert raw LLM text → validated PoemAnalysis.
    Falls back to empty object on any failure.
    """
    try:
        data = parse_json_response(raw)
        if not data:
            return PoemAnalysis.empty()

        # Normalize thinai to enum
        thinai_raw = data.get("thinai", "Unknown")
        try:
            data["thinai"] = Thinai(thinai_raw)
        except ValueError:
            data["thinai"] = Thinai.UNKNOWN

        # Normalize mood to enum
        mood_raw = data.get("mood", "unknown")
        try:
            data["mood"] = Mood(mood_raw.lower())
        except ValueError:
            data["mood"] = Mood.UNKNOWN

        return PoemAnalysis(**data)

    except Exception:
        return PoemAnalysis.empty()


def parse_scenes_response(raw: str, analysis: PoemAnalysis | None = None) -> list[SceneFrame]:
    """
    Convert raw LLM text → list of validated SceneFrames.
    Falls back to single empty scene on failure.
    Injects thinai from analysis if available.
    """
    try:
        data = parse_json_response(raw)
        if not data:
            return [SceneFrame.empty()]

        scenes_data = data if isinstance(data, list) else data.get("scenes", [])
        scenes = []
        for i, s in enumerate(scenes_data):
            try:
                mood_raw = s.get("mood", "unknown")
                try:
                    s["mood"] = Mood(mood_raw.lower())
                except ValueError:
                    s["mood"] = Mood.UNKNOWN
                
                # Add thinai from analysis if available
                if analysis and not s.get("thinai"):
                    s["thinai"] = analysis.thinai
                
                scenes.append(SceneFrame(**s))
            except Exception:
                scenes.append(SceneFrame.empty(scene_id=i + 1))

        return scenes if scenes else [SceneFrame.empty()]

    except Exception:
        return [SceneFrame.empty()]


# ─────────────────────────────────────────────
# PROMPT TEMPLATE LOADER
# ─────────────────────────────────────────────

def load_prompt(filepath: str) -> str:
    """Load prompt template from file, return empty string on failure."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


# ─────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────

def validate_pipeline_input(poem: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Empty error message means valid.
    """
    if not poem or not poem.strip():
        return False, "Poem text cannot be empty."
    if len(poem.strip()) < 10:
        return False, "Poem text is too short to analyze."
    if len(poem) > 10_000:
        return False, "Poem text exceeds maximum length (10,000 characters)."
    return True, ""