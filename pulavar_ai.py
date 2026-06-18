"""
pulavar_ai.py — Literary Brain 🧠
"""
import html
import json
import re

from PIL.ImagePalette import raw
from schemas import (
    PoemAnalysis, Character, MeaningLine, GrammarNote,
    MuthalPorul, Thinai, Mood
)
from gemini_client import get_model


DEFAULT_PROMPT = """
You are Pulavar (புலவர்), a deep scholar of ancient Sangam Tamil literature.
Analyze the following poem and return ONLY a valid JSON object.
No markdown, no code fences, no explanation. Raw JSON only.

Poem:
{poem}

Return this exact JSON structure:
{{
  "summary": "2-3 sentence English summary",
  "summary_tamil": "2-3 sentence Tamil summary",
  "emotion": "Primary emotion in English",
  "emotion_tamil": "Primary emotion in Tamil (e.g. காதல், ஏக்கம், துயரம்)",
  "thinai": "One of: Kurinji, Mullai, Marutham, Neytal, Palai, Unknown",
  "mood": "One of: longing, joy, sorrow, anger, devotion, serenity, yearning, melancholy, unknown",

  "poet": "Poet name in English",
  "poet_tamil": "Poet name in Tamil script",
  "collection": "Collection name in English",
  "collection_tamil": "Collection name in Tamil script",
  "period": "e.g. 300 BCE – 300 CE",
  "akam_puram": "Akam or Puram",

  "thurai": "Situational sub-type in English (e.g. Punarthal — Union of lovers)",
  "thurai_tamil": "Sub-type in Tamil (e.g. புணர்தல்)",
  "speaker": "Who speaks — e.g. Hero (தலைவன்) or Heroine (தலைவி)",
  "listener": "Who is addressed — e.g. Friend (தோழி)",

  "muthal_porul": {{
    "landscape": "Landscape in English",
    "landscape_tamil": "Landscape in Tamil",
    "season": "Season in English",
    "season_tamil": "Season in Tamil",
    "time": "Time of day in English",
    "time_tamil": "Time of day in Tamil"
  }},

  "karu_porul": ["Flora/fauna/object 1 (Tamil)", "Flora/fauna/object 2 (Tamil)"],

  "uri_porul": "The central human emotion/action in English",
  "uri_porul_tamil": "The central human emotion/action in Tamil",

  "meyppadu": "Emotional expression (Meyppadu) in English",
  "meyppadu_tamil": "Emotional expression in Tamil",

  "flora_fauna": "Key plants and animals mentioned",
  "cultural_context": "2-3 sentence cultural context in English",
  "cultural_context_tamil": "2-3 sentence cultural context in Tamil",
  "literary_devices": "Key literary devices used (Ullurai, Uvamai, Uripporul etc.)",

  "word_meanings": {{
    "Tamil word (transliteration)": "English meaning and significance"
  }},

  "grammar_notes": [
    {{
      "term": "Term in English (e.g. Ullurai)",
      "term_tamil": "Term in Tamil (e.g. உள்ளுறை)",
      "definition": "What this term means",
      "example": "How it appears in this poem specifically"
    }}
  ],

  "characters": [
    {{
      "name": "Character name in English",
      "name_tamil": "Character name in Tamil",
      "role": "Role in English",
      "role_tamil": "Role in Tamil (தலைவன் / தலைவி / தோழி / செவிலி)",
      "description": "Brief description"
    }}
  ],

  "meaning_breakdown": [
    {{
      "original": "Exact line or sentence from the poem, preserving Tamil if given",
      "translation": "Decoded plain English meaning of this exact line",
      "interpretation": "Deeper poetic, emotional, and cultural interpretation",
      "literary_device": "Device used if any, such as Ullurai, Uvamai, Thinai imagery"
    }}
  ]
}}

Line-by-line decoded meaning rules:
- Include one meaning_breakdown entry for every meaningful poem line or sentence, in original order.
- Do not collapse the poem into only 1-2 generic phrases.
- If the poem is in Tamil, keep the Tamil line in "original" and decode it in English under "translation".
- In "interpretation", explain what the line reveals emotionally: Muthal, Karu, Uri, Ullurai, Uvamai, Thurai, or Meyppadu when relevant.
- Always return at least 4 grammar_notes when possible.

Grammar terms to always consider for grammar_notes:
- Muthal (முதல்): time and place
- Karu (கரு): flora, fauna, objects that set the scene
- Uri (உரி): the emotion/action central to the Thinai
- Ullurai (உள்ளுறை): embedded inner meaning through nature imagery
- Uvamai (உவமை): simile
- Uripporul (உரிப்பொருள்): the specific emotion belonging to the Thinai
- Meyppadu (மெய்ப்பாடு): the physical/emotional expression shown
- Thurai (துறை): situational sub-classification within the Thinai
"""


def _clean_text(value: str) -> str:
    """
    Remove accidental HTML/markdown fragments from Gemini outputs.
    Handles HTML entities, markdown code fences, and HTML tags.
    """
    if not isinstance(value, str):
        return value

    # Decode HTML entities
    value = html.unescape(value)

    # Remove markdown code fences
    value = re.sub(r"```(?:json)?\s*", "", value)
    value = re.sub(r"```", "", value)

    # Remove specific HTML tags
    value = re.sub(r"</?div[^>]*>", "", value)
    value = re.sub(r"</?span[^>]*>", "", value)
    value = re.sub(r"</?br\s*/?>", "\n", value)
    value = re.sub(r"</?strong>", "", value)
    value = re.sub(r"</?em>", "", value)
    value = re.sub(r"</?p[^>]*>", "", value)
    value = re.sub(r"</?a[^>]*>", "", value)

    # Remove any remaining HTML tags
    value = re.sub(r"<[^>]+>", "", value)

    return value.strip()


def _extract_json(text: str) -> str:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text).strip()
    match = re.search(r'(\{[\s\S]*\})', text)
    return match.group(1).strip() if match else text


def _parse_thinai(v: str) -> Thinai:
    return {t.value.lower(): t for t in Thinai}.get(str(v).strip().lower(), Thinai.UNKNOWN)


def _parse_mood(v: str) -> Mood:
    return {m.value.lower(): m for m in Mood}.get(str(v).strip().lower(), Mood.UNKNOWN)


def analyze_poem(poem: str) -> PoemAnalysis:
    if not poem or not poem.strip():
        return PoemAnalysis.empty()

    prompt = DEFAULT_PROMPT.replace("{poem}", poem.strip())

    try:
        response = get_model().generate_content(prompt)
        raw = response.text
        print("\n===== GEMINI RAW =====")
        print(raw)
        print("======================\n")
    except Exception as e:
        print(f"[pulavar_ai] LLM failed: {e}")
        return PoemAnalysis.empty()

    try:
        data = json.loads(_extract_json(raw))

        for key, value in data.items():
            if isinstance(value, str):
                data[key] = _clean_text(value)

        mp = data.get("muthal_porul", {})
        muthal = MuthalPorul(
            landscape=mp.get("landscape", ""),
            landscape_tamil=mp.get("landscape_tamil", ""),
            season=mp.get("season", ""),
            season_tamil=mp.get("season_tamil", ""),
            time=mp.get("time", ""),
            time_tamil=mp.get("time_tamil", ""),
        ) if mp else None

        return PoemAnalysis(
            summary=data.get("summary", ""),
            summary_tamil=data.get("summary_tamil", ""),
            emotion=data.get("emotion", ""),
            emotion_tamil=data.get("emotion_tamil", ""),
            thinai=_parse_thinai(data.get("thinai", "Unknown")),
            mood=_parse_mood(data.get("mood", "unknown")),
            poet=data.get("poet", ""),
            poet_tamil=data.get("poet_tamil", ""),
            collection=data.get("collection", ""),
            collection_tamil=data.get("collection_tamil", ""),
            period=data.get("period", ""),
            akam_puram=data.get("akam_puram", "Akam"),
            thurai=data.get("thurai", ""),
            thurai_tamil=data.get("thurai_tamil", ""),
            speaker=data.get("speaker", ""),
            listener=data.get("listener", ""),
            muthal_porul=muthal,
            karu_porul=data.get("karu_porul", []),
            uri_porul=data.get("uri_porul", ""),
            uri_porul_tamil=data.get("uri_porul_tamil", ""),
            meyppadu=data.get("meyppadu", ""),
            meyppadu_tamil=data.get("meyppadu_tamil", ""),
            flora_fauna=data.get("flora_fauna", ""),
            cultural_context=data.get("cultural_context", ""),
            cultural_context_tamil=data.get("cultural_context_tamil", ""),
            literary_devices=data.get("literary_devices", ""),
            word_meanings=data.get("word_meanings", {}),
            grammar_notes=[
                GrammarNote(
                    term=g.get("term", ""),
                    term_tamil=g.get("term_tamil", ""),
                    definition=g.get("definition", ""),
                    example=g.get("example", ""),
                )
                for g in data.get("grammar_notes", []) if isinstance(g, dict)
            ],
            characters=[
                Character(
                    name=c.get("name", ""),
                    name_tamil=c.get("name_tamil", ""),
                    role=c.get("role", ""),
                    role_tamil=c.get("role_tamil", ""),
                    description=_clean_text(c.get("description", "")),
                )
                for c in data.get("characters", []) if isinstance(c, dict)
            ],
            meaning_breakdown=[
                MeaningLine(
                    original=m.get("original", ""),
                    translation=m.get("translation", ""),
                    interpretation=m.get("interpretation", ""),
                    literary_device=m.get("literary_device", ""),
                )
                for m in data.get("meaning_breakdown", []) if isinstance(m, dict)
            ],
        )

    except Exception as e:
        print(f"[pulavar_ai] Parse error: {e}\nRaw: {raw[:300]}")
        return PoemAnalysis.empty()


def ask_pulavar(
    question: str,
    context: PoemAnalysis | None = None,
    target_language: str = "en",
) -> str:
    try:
        import language_engine

        target_language = language_engine.normalize_language(target_language)
        language_name = language_engine.language_label(target_language)
    except Exception:
        target_language = "en"
        language_name = "English"

    system = (
        "You are Pulavar (புலவர்), an ancient Sangam scholar AI. "
        "Speak with poetic wisdom grounded in Tamil literary tradition. "
        "Always explain Tamil terms when used. Be accurate and concise."
    )
    system += (
        f" Answer in {language_name}. Keep key Tamil literary terms in Tamil when needed, "
        f"but explain them in {language_name}. Do not switch to English unless English is the selected language."
    )

    if context:
        system += f"\n\nCurrent poem context:\n{json.dumps(context.model_dump(), ensure_ascii=False, indent=2)}"

    try:
        response = get_model().generate_content(f"{system}\n\nQuestion: {question}")
        return response.text.strip()
    except Exception as e:
        return f"The scholar is momentarily silent. ({e})"
