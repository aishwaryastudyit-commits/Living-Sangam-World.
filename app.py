import streamlit as st
import json
import os
import inspect
import html
from pathlib import Path
from dotenv import load_dotenv


SCENE_CACHE_DIR = Path("assets/images/scene_cache")

def _build_scene_cache() -> dict[str, str]:
    cache: dict[str, str] = {}

    # Load top-level cache assets first, then nested Kurinji assets.
    for image_path in sorted(SCENE_CACHE_DIR.glob("*.*")):
        if image_path.is_file() and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            cache[image_path.stem.lower().replace(" ", "_")] = str(image_path)

    for image_path in sorted(SCENE_CACHE_DIR.rglob("*.*")):
        if (
            image_path.is_file()
            and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}
            and image_path.parent != SCENE_CACHE_DIR
        ):
            cache[image_path.stem.lower().replace(" ", "_")] = str(image_path)

    return cache

SCENE_CACHE = _build_scene_cache()

load_dotenv()

st.set_page_config(
    page_title="Living Sangam World: AI-Powered Immersive Tamil Poetry Experience",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

from schemas import (
    PipelineResult, PoemAnalysis, SceneFrame, Poem, Thinai, Mood, MuthalPorul,
    GrammarNote, MeaningLine, Character,
    THINAI_TAMIL, THINAI_MEANING, MOOD_TAMIL,
    GeneratedImage, NarrationResult, VideoExperience, VideoStatus, SubtitleFormat,
    THINAI_COLOR_PALETTE,
)
import pulavar_ai
import scene_weaver
import scene_generator
import sangam_voice
import ocr_engine
import language_engine
from scene_weaver import KURINJI_CACHE_KEYS, MULLAI_CACHE_KEYS, MARUTHAM_CACHE_KEYS

THINAI_CACHE_KEYS = {
    Thinai.KURINJI: KURINJI_CACHE_KEYS,
    Thinai.MULLAI: MULLAI_CACHE_KEYS,
    Thinai.MARUTHAM: MARUTHAM_CACHE_KEYS,
    Thinai.NEYTAL: scene_weaver.NEYTAL_CACHE_KEYS,
    Thinai.PALAI: scene_weaver.PALAI_CACHE_KEYS,
}


def ask_pulavar_chat(
    question: str,
    analysis: PoemAnalysis | None,
    target_language: str = "en",
) -> str:
    """Call Pulavar with selected language, while tolerating older loaded modules."""
    signature = inspect.signature(pulavar_ai.ask_pulavar)
    accepts_language = "target_language" in signature.parameters or any(
        param.kind == inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    )
    if accepts_language:
        return pulavar_ai.ask_pulavar(
            question,
            context=analysis,
            target_language=target_language,
        )
    return pulavar_ai.ask_pulavar(question, context=analysis)


SCENE_SLOT_CACHE_KEYS = {
    Thinai.KURINJI: {
        1: ["kurinji_hills", "mountain_path", "waterfall", "kurinji_landscape"],
        2: ["lovers_first_meeting", "lovers_meeting", "heroine_waiting", "hero_gazing_heroine"],
        3: ["moonlit_kurinji", "mountain_pool", "waterfall", "kurinji_landscape"],
    },
    Thinai.MULLAI: {
        1: ["mullai_forest", "monsoon_arrival", "mullai_landscape"],
        2: ["heroine_waiting_dusk", "watching_forest_path", "thozhi_consoling"],
        3: ["hero_returns_twilight", "konrai_reunion", "deer_mullai", "rabbit_jasmine"],
    },
    Thinai.MARUTHAM: {
        1: ["marutham_paddy_fields", "lotus_pond", "marutham_landscape"],
        2: ["marutham_village", "domestic_quarrel", "hero_returning_home"],
        3: ["marutham_reconciliation", "buffalo_lotus_ullurai", "sugarcane_harvest", "lotus_pond"],
    },
    Thinai.NEYTAL: {
        1: ["neytal_landscape", "neital_shoreline", "catamaran_boat"],
        2: ["heroine_seashore_waiting", "waves_longing", "neytalthozhi_consoling"],
        3: ["moonlit_beach", "fisherman_returning", "waves_longing"],
    },
    Thinai.PALAI: {
        1: ["palai_landscape", "dry_waterhole", "blazing_sun"],
        2: ["hero_departure", "desert_travellers", "heroine_separation"],
        3: ["drought_forest", "vulture_sky", "palai_landscape2", "grieving_mother"],
    },
}

# video_engine is optional — gracefully degrade if not yet implemented
try:
    import video_engine
    _VIDEO_ENGINE_AVAILABLE = True
except ImportError:
    _VIDEO_ENGINE_AVAILABLE = False

_api_key_missing = not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))

# ── STYLES ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Crimson+Pro:ital,wght@0,300;0,400;1,300&display=swap');
:root {
    --sangam-bg:#F7F7F4;
    --sangam-panel:#FFFFFF;
    --sangam-panel-soft:#F1F3EF;
    --sangam-panel-ai:#FAFAF8;
    --sangam-panel-scene:#F3F1EC;
    --sangam-terracotta:#9A6B55;
    --sangam-terracotta-deep:#5F4A40;
    --sangam-green:#78866B;
    --sangam-bronze:#A58B68;
    --sangam-ink:#262626;
    --sangam-muted:#6B7280;
    --sangam-border:#D9D7D1;
    --thinai-kurinji:#B9B7E5;
    --thinai-mullai:#C6D3B8;
    --thinai-marutham:#E1CFA3;
    --thinai-neytal:#B8D4DF;
    --thinai-palai:#E3B9A6;
    --sangam-dark:var(--sangam-ink);
    --sangam-gold:var(--sangam-bronze);
    --sangam-earth:var(--sangam-terracotta);
}
html,body,[class*="css"]{
    font-family:'Crimson Pro',Georgia,serif;
    background:var(--sangam-bg);
    color:var(--sangam-ink);
}
.stApp{
    background:var(--sangam-bg);
}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif;color:var(--sangam-terracotta-deep);}
h2,h3{
    border-left:4px solid #C8B7A6;
    background:transparent;
    padding:0.25rem 0 0.25rem 0.7rem;
}
.stTextArea textarea{
    background-color:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid var(--sangam-border)!important;
    border-radius:8px!important;
    font-family:'Crimson Pro',Georgia,serif!important;
    font-size:1.1rem!important;
}
.stTextArea textarea:focus{border-color:#A7B29A!important;box-shadow:0 0 0 1px rgba(120,134,107,0.18)!important;}
.stButton>button{
    background:#FFFFFF!important;
    color:var(--sangam-ink)!important;
    font-family:'Playfair Display',Georgia,serif!important;
    font-weight:700!important;
    border:1px solid var(--sangam-border)!important;
    border-radius:8px!important;
    padding:0.6rem 2rem!important;
    letter-spacing:0.02em!important;
    box-shadow:0 1px 3px rgba(15,23,42,0.08)!important;
}
.stButton>button:hover{background:#F1F3EF!important;border-color:#BFC4BA!important;color:#1F2937!important;}
.poem-card{
    background:#FFFDF7;
    border:1px solid #E6D7C6;
    border-radius:10px;
    padding:1.5rem 2rem;
    margin:1rem 0;
    font-style:italic;
    font-size:1.15rem;
    line-height:1.9;
    color:var(--sangam-ink);
    box-shadow:0 4px 14px rgba(95,74,64,0.08);
}
.analysis-card{
    background:#FFFBF3;
    border-left:4px solid #D8BFA5;
    border-top:1px solid #E6D7C6;
    border-right:1px solid #E6D7C6;
    border-bottom:1px solid #E6D7C6;
    padding:1rem 1.5rem;
    margin:0.7rem 0;
    border-radius:0 8px 8px 0;
    box-shadow:0 4px 12px rgba(95,74,64,0.06);
}
.thinai-badge, .word-entry, .track-scene-num, .asset-pill, .video-status-badge {
    background: var(--sangam-gold) !important;
    color: #120E05 !important;   /* near-black text — good contrast on gold */
}
.poetics-label, .meaning-original, .word-ta, .video-header, .subtitle-ta, .asset-pill.ready {
    color: var(--sangam-gold-soft) !important;   /* lighter gold text */
}
.poetics-box{background:#FFFDF7;border:1px solid #E6D7C6;border-radius:8px;padding:1rem 1.2rem;margin:0.4rem 0;}
.poetics-value{color:var(--sangam-dark);margin-top:0.2rem;}
.poetics-value-ta{color:var(--sangam-muted);font-style:italic;font-size:0.95rem;}
.scene-header{font-family:'Playfair Display',serif;color:var(--sangam-terracotta-deep);font-size:1.2rem;border-left:4px solid #C8B7A6;background:var(--sangam-panel-scene);padding:0.5rem 0.8rem;margin-bottom:0.8rem;border-radius:0 8px 8px 0;}
.character-entry{background:#FFFDF7;border:1px solid #E6D7C6;border-radius:8px;padding:0.75rem 1rem;margin:0.4rem 0;}
.meaning-entry{background:#FFFDF7;border-left:3px solid #C9D3BF;padding:0.75rem 1rem;margin:0.5rem 0;}
.meaning-original{font-style:italic;color:#5F4A40;font-size:1.05rem;}
.meaning-translation{color:var(--sangam-dark);margin:0.3rem 0;}
.meaning-interpretation{color:var(--sangam-muted);font-size:0.95rem;}
.word-entry{background:#FBF7EF;border:1px solid #E6D7C6;border-radius:6px;padding:0.4rem 0.8rem;margin:0.2rem 0;display:flex;gap:0.8rem;align-items:baseline;}
.word-ta{color:#5F4A40;font-weight:700;min-width:140px;}
.word-en{color:var(--sangam-dark);font-size:0.95rem;}
.error-card{background:#FCE8E8;border:1px solid #E7A0A0;border-radius:6px;padding:1rem;color:#8A3030;}
.sidebar-title{font-family:'Playfair Display',serif;color:var(--sangam-terracotta-deep);font-size:1.25rem;text-align:center;padding:1rem 0;border-bottom:1px solid var(--sangam-border);line-height:1.25;}
div[data-testid="stSidebar"]{background:#FFFFFF!important;border-right:1px solid var(--sangam-border);}
.stSelectbox>div>div{background-color:var(--sangam-panel)!important;color:var(--sangam-dark)!important;border-color:var(--sangam-border)!important;}
.stTabs [data-baseweb="tab-list"]{background-color:rgba(255,249,240,0.82);border-bottom:1px solid var(--sangam-border);}
.stTabs [data-baseweb="tab"]{color:var(--sangam-muted);font-family:'Playfair Display',serif;}
.stTabs [aria-selected="true"]{color:var(--sangam-ink)!important;border-bottom-color:#C8B7A6!important;}
hr{border-color:var(--sangam-border);}

/* ── VideoExperience styles ── */
.video-header{
    font-family:'Playfair Display',serif;
    color:var(--sangam-terracotta-deep);
    font-size:1.5rem;
    text-align:center;
    letter-spacing:0.1em;
    margin-bottom:0.3rem;
}
.video-subheader{
    text-align:center;
    color:var(--sangam-muted);
    font-style:italic;
    font-size:1rem;
    margin-bottom:1.5rem;
}
.video-status-badge{
    display:inline-block;
    padding:0.2rem 0.9rem;
    border-radius:20px;
    font-family:'Playfair Display',serif;
    font-size:0.85rem;
    font-weight:700;
    letter-spacing:0.06em;
}
.status-pending   { background:#F6F1E8; color:#5F4A40; border:1px solid #D8C8B5; }
.status-composing { background:#EEF5F7; color:#4E6670; border:1px solid #C8DCE3; }
.status-rendering { background:#F1F0FA; color:#5B5A7A; border:1px solid #D8D6EE; }
.status-complete  { background:#EEF2EA; color:#46513E; border:1px solid #C9D3BF; }
.status-failed    { background:#FCE8E8; color:#8A3030; border:1px solid #E7A0A0; }
.subtitle-cue{
    background:var(--sangam-panel);
    border-left:3px solid var(--sangam-gold);
    border-radius:0 6px 6px 0;
    padding:0.5rem 1rem;
    margin:0.3rem 0;
    font-size:0.95rem;
}
.subtitle-time{
    color:var(--sangam-muted);
    font-size:0.8rem;
    font-family:monospace;
    margin-bottom:0.2rem;
}
.subtitle-en{ color:var(--sangam-dark); }
.subtitle-ta{ color:var(--sangam-terracotta); font-style:italic; }
.track-card{
    background:var(--sangam-panel);
    border:1px solid var(--sangam-border);
    border-radius:8px;
    padding:0.75rem 1rem;
    margin:0.4rem 0;
    display:flex;
    align-items:center;
    gap:1rem;
}
.track-scene-num{
    background:#E4E8D7;
    color:var(--sangam-dark);
    border-radius:50%;
    width:28px;
    height:28px;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:700;
    font-size:0.85rem;
    flex-shrink:0;
}
.video-asset-row{
    display:flex;
    gap:0.5rem;
    flex-wrap:wrap;
    margin:0.5rem 0;
}
.asset-pill{
    background:var(--sangam-panel-soft);
    border:1px solid var(--sangam-border);
    border-radius:20px;
    padding:0.2rem 0.7rem;
    font-size:0.82rem;
    color:var(--sangam-muted);
}
.asset-pill.ready{ border-color:var(--sangam-green); color:#43502F; }
.asset-pill.missing{ border-color:#E7A0A0; color:#8A3030; }
@media (prefers-color-scheme: dark) {
    :root {
        --sangam-bg:#111827;
        --sangam-panel:#1F2937;
        --sangam-panel-soft:#263241;
        --sangam-panel-ai:#1B2430;
        --sangam-panel-scene:#263241;
        --sangam-terracotta:#C8B7A6;
        --sangam-terracotta-deep:#E5E7EB;
        --sangam-green:#A7B29A;
        --sangam-bronze:#C8B7A6;
        --sangam-ink:#F9FAFB;
        --sangam-muted:#CBD5E1;
        --sangam-border:#374151;
    }
    .stApp{background:var(--sangam-bg);}
    div[data-testid="stSidebar"]{background:#1F2937!important;}
    .stButton>button{color:#F9FAFB!important;background:#1F2937!important;border-color:#374151!important;}
    .stButton>button:hover{background:#263241!important;border-color:#4B5563!important;}
    .thinai-badge,.word-entry,.track-scene-num{background:#263241;color:#F9FAFB;}
    .asset-pill.ready{color:#DDE7CD;}
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
:root {
    --sangam-bg:#0D1016;
    --sangam-sidebar:#292A33;
    --sangam-panel:#180700;
    --sangam-panel-soft:#20100A;
    --sangam-panel-ai:#120600;
    --sangam-panel-scene:#171B22;
    --sangam-terracotta:#A66F3F;
    --sangam-terracotta-deep:#D8A057;
    --sangam-green:#A58F4C;
    --sangam-bronze:#8D6236;
    --sangam-ink:#F7F4EE;
    --sangam-dark:#FFFFFF;
    --sangam-muted:#A4794B;
    --sangam-border:#4B321F;
    --sangam-gold:#D3A006;
    --sangam-gold-soft:#E4BE43;
    --sangam-earth:#5B2A12;
    --sangam-accent:#FF4B5C;
}
html,body,[class*="css"],.stApp{
    background:var(--sangam-bg)!important;
    color:var(--sangam-ink)!important;
}
h1,h2,h3{
    color:var(--sangam-ink)!important;
    border-left:0!important;
    background:transparent!important;
    padding-left:0!important;
}
.stButton>button{
    background:var(--sangam-gold)!important;
    color:#05070B!important;
    border:1px solid var(--sangam-gold)!important;
    border-radius:6px!important;
    box-shadow:none!important;
}
.stButton>button:hover{
    background:var(--sangam-gold-soft)!important;
    color:#05070B!important;
    border-color:var(--sangam-gold-soft)!important;
}
.stTextArea textarea,
.stSelectbox>div>div{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border-color:var(--sangam-border)!important;
}
.stTextArea textarea:focus{
    border-color:var(--sangam-gold)!important;
    box-shadow:0 0 0 1px rgba(211,160,6,0.35)!important;
}
div[data-testid="stSidebar"]{
    background:var(--sangam-sidebar)!important;
    border-right:1px solid #343541!important;
}
div[data-testid="stSidebar"] *{
    color:var(--sangam-ink)!important;
}
.sidebar-title{
    color:var(--sangam-gold-soft)!important;
    border-bottom:1px solid #50515A!important;
    letter-spacing:0.08em!important;
}
.sidebar-title small{
    color:#B9B1A7!important;
    letter-spacing:0!important;
}
.poetics-box,
.character-entry,
.meaning-entry,
.track-card,
.subtitle-cue{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid var(--sangam-border)!important;
    border-radius:6px!important;
    box-shadow:none!important;
}
.poem-card{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid var(--sangam-gold)!important;
    border-radius:8px!important;
    box-shadow:none!important;
}
.analysis-card{
    background:var(--sangam-panel)!important;
    color:var(--sangam-ink)!important;
    border:1px solid #211006!important;
    border-left:4px solid var(--sangam-gold)!important;
    border-radius:0 6px 6px 0!important;
    box-shadow:none!important;
}
.scene-header{
    background:var(--sangam-panel-scene)!important;
    color:var(--sangam-ink)!important;
    border-left:4px solid var(--sangam-gold)!important;
    border-bottom:1px solid var(--sangam-border)!important;
    border-radius:0 6px 6px 0!important;
    padding:0.45rem 0.75rem!important;
}
.thinai-badge,
.word-entry,
.track-scene-num,
.asset-pill,
.video-status-badge{
    background:var(--sangam-gold)!important;
    color:#120E05!important;
    border:1px solid var(--sangam-gold)!important;
}
.poetics-label,
.meaning-original,
.word-ta,
.video-header,
.subtitle-ta,
.asset-pill.ready{
    color:var(--sangam-gold-soft)!important;
}
.meaning-interpretation,
.poetics-value-ta,
.video-subheader,
.subtitle-time,
.asset-pill{
    color:var(--sangam-muted)!important;
}
.stTabs [data-baseweb="tab-list"]{
    background:#100700!important;
    border-bottom:1px solid var(--sangam-border)!important;
}
.stTabs [data-baseweb="tab"]{
    color:var(--sangam-muted)!important;
}
.stTabs [aria-selected="true"]{
    color:var(--sangam-gold-soft)!important;
    border-bottom-color:var(--sangam-accent)!important;
}
.stRadio label,
.stCheckbox label,
.stToggle label,
.stSelectbox label,
.stTextArea label,
.stFileUploader label,
.stCameraInput label{
    color:var(--sangam-ink)!important;
}
div[data-testid="stExpander"]{
    background:var(--sangam-panel-soft)!important;
    border:1px solid var(--sangam-border)!important;
}
div[data-testid="stChatMessage"]{
    background:var(--sangam-panel-soft)!important;
    color:var(--sangam-ink)!important;
}
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] span{
    color:inherit;
}
hr{border-color:var(--sangam-border)!important;}
.word-ta,
.asset-pill.ready{
    color:#120E05!important;
}
</style>
""", unsafe_allow_html=True)


# ── HELPERS ──────────────────────────────────────────────────────────────────

@st.cache_data
def load_poems() -> list[Poem]:
    try:
        with open("poems.json", "r", encoding="utf-8") as f:
            return [Poem(**p) for p in json.load(f)]
    except Exception as e:
        st.warning(f"Could not load poems.json: {e}")
        return []


def find_library_poem(poem_id: int) -> Poem | None:
    if not poem_id:
        return None
    return next((poem for poem in load_poems() if poem.id == poem_id), None)


def analysis_from_poem(poem: Poem | None, poem_text: str = "") -> PoemAnalysis:
    if poem is None:
        fallback_lines = _meaning_breakdown_from_text(poem_text)
        return PoemAnalysis(
            summary="A compact Sangam-style reading is available in demo mode.",
            emotion="Reflective longing",
            thinai=Thinai.UNKNOWN,
            mood=Mood.LONGING,
            cultural_context="The poem is presented through the Sangam lens of landscape, emotion, and dramatic situation.",
            grammar_notes=_default_grammar_notes(Thinai.UNKNOWN),
            meaning_breakdown=fallback_lines,
        )

    mp = poem.muthal_porul
    muthal = MuthalPorul(
        landscape=mp.landscape if mp else "",
        season=mp.season if mp else "",
        time=mp.time if mp else "",
    ) if mp else None

    return PoemAnalysis(
        summary=(
            poem.cultural_context
            or "This poem binds landscape and emotion in the classical Sangam style."
        ),
        summary_tamil=poem.poem_ta,
        emotion=poem.meyppadu or "Longing",
        thinai=poem.thinai,
        mood=_mood_from_poem(poem),
        poet=poem.author,
        poet_tamil=poem.author_ta,
        collection=poem.collection,
        collection_tamil=poem.collection_ta,
        period=poem.period,
        akam_puram=poem.akam_puram,
        thurai=poem.thurai,
        speaker=poem.speaker,
        listener=poem.listener,
        muthal_porul=muthal,
        karu_porul=poem.karu_porul,
        uri_porul=poem.uri_porul,
        meyppadu=poem.meyppadu,
        cultural_context=poem.cultural_context,
        literary_devices="Thinai imagery, nature-symbolism, and implied emotional parallelism.",
        word_meanings=poem.word_meanings,
        grammar_notes=_grammar_notes_from_poem(poem),
        characters=_characters_from_poem(poem),
        meaning_breakdown=_meaning_breakdown_from_poem(poem),
    )


def _default_grammar_notes(thinai: Thinai) -> list[GrammarNote]:
    thinai_name = thinai.value if thinai != Thinai.UNKNOWN else "the poem"
    return [
        GrammarNote(
            term="Muthal",
            term_tamil="முதல்",
            definition="The time and place frame of a Sangam poem.",
            example=f"In {thinai_name}, landscape is not decoration; it sets the emotional world.",
        ),
        GrammarNote(
            term="Karu",
            term_tamil="கரு",
            definition="The living scene: flowers, animals, occupations, objects, and weather.",
            example="Natural details help the reader infer the speaker's inner state.",
        ),
        GrammarNote(
            term="Uri",
            term_tamil="உரி",
            definition="The central human situation or emotional action.",
            example="The poem's outer image points toward an inner experience of love, waiting, union, or separation.",
        ),
        GrammarNote(
            term="Ullurai",
            term_tamil="உள்ளுறை",
            definition="An embedded inner meaning carried through nature imagery.",
            example="The visible landscape quietly decodes the hidden feeling of the speaker.",
        ),
    ]


def _grammar_notes_from_poem(poem: Poem) -> list[GrammarNote]:
    notes = _default_grammar_notes(poem.thinai)
    if poem.thurai:
        notes.append(
            GrammarNote(
                term="Thurai",
                term_tamil="துறை",
                definition="The specific dramatic situation within a Thinai.",
                example=poem.thurai,
            )
        )
    if poem.meyppadu:
        notes.append(
            GrammarNote(
                term="Meyppadu",
                term_tamil="மெய்ப்பாடு",
                definition="The felt emotional expression made visible in the poem.",
                example=poem.meyppadu,
            )
        )
    return notes


def _characters_from_poem(poem: Poem) -> list[Character]:
    characters: list[Character] = []
    if poem.speaker:
        characters.append(
            Character(
                name=poem.speaker,
                role="Speaker",
                description="The voice through which the poem's emotional situation is revealed.",
            )
        )
    if poem.listener:
        characters.append(
            Character(
                name=poem.listener,
                role="Listener",
                description="The addressed presence who helps frame the poem's dramatic moment.",
            )
        )
    return characters


def _meaning_breakdown_from_text(poem_text: str) -> list[MeaningLine]:
    lines = [line.strip() for line in (poem_text or "").splitlines() if line.strip()]
    return [
        MeaningLine(
            original=line,
            translation=line,
            interpretation="This line contributes to the poem's emotional movement and image pattern.",
            literary_device="Line image",
        )
        for line in lines
    ]


def _meaning_breakdown_from_poem(poem: Poem) -> list[MeaningLine]:
    en_lines = [line.strip() for line in (poem.poem_en or "").splitlines() if line.strip()]
    ta_lines = [line.strip() for line in (poem.poem_ta or "").splitlines() if line.strip()]
    decoded: list[MeaningLine] = []

    for index, line in enumerate(en_lines):
        original = ta_lines[index] if index < len(ta_lines) else line
        decoded.append(
            MeaningLine(
                original=original,
                translation=line,
                interpretation=_line_interpretation(poem, line, index),
                literary_device=_line_device(poem, line),
            )
        )

    return decoded or _meaning_breakdown_from_text(poem.poem_ta or poem.poem_en)


def _line_interpretation(poem: Poem, line: str, index: int) -> str:
    lowered = line.lower()
    if index == 0:
        return f"The opening image establishes {poem.thinai.value} Thinai and prepares the emotional field."
    if any(word in lowered for word in ("like", "as ", "as i", "as my")):
        return "The comparison turns an outer image into a decoded inner feeling."
    if any(word in lowered for word in ("heart", "beloved", "lover", "longing", "waiting", "alone")):
        return "The human emotion comes forward here, revealing the poem's Uri Porul."
    if any(word in lowered for word in ("flower", "wave", "forest", "mountain", "shore", "rain", "sand", "road")):
        return "A natural detail functions as Karu Porul, carrying emotional meaning through landscape."
    return "This sentence advances the poem's dramatic situation and deepens its implied feeling."


def _line_device(poem: Poem, line: str) -> str:
    lowered = line.lower()
    if any(word in lowered for word in ("like", "as ")):
        return "Uvamai / simile"
    if any(word in lowered for word in ("flower", "wave", "forest", "mountain", "shore", "rain", "sand", "road", "heron", "peacock")):
        return "Ullurai / nature-symbolism"
    if poem.thinai != Thinai.UNKNOWN:
        return f"{poem.thinai.value} Thinai imagery"
    return "Poetic image"


def _ensure_deep_analysis_sections(
    analysis: PoemAnalysis,
    poem_text: str = "",
    library_poem: Poem | None = None,
) -> PoemAnalysis:
    """Keep the old rich analysis sections visible even when AI output is sparse."""
    if library_poem:
        if not analysis.grammar_notes:
            analysis.grammar_notes = _grammar_notes_from_poem(library_poem)
        if not analysis.characters:
            analysis.characters = _characters_from_poem(library_poem)
        if not analysis.meaning_breakdown:
            analysis.meaning_breakdown = _meaning_breakdown_from_poem(library_poem)
    else:
        if not analysis.grammar_notes:
            analysis.grammar_notes = _default_grammar_notes(analysis.thinai)
        if not analysis.meaning_breakdown:
            analysis.meaning_breakdown = _meaning_breakdown_from_text(poem_text)

    return analysis


def _mood_from_poem(poem: Poem) -> Mood:
    text = " ".join([poem.uri_porul, poem.meyppadu, poem.cultural_context]).lower()
    if any(word in text for word in ("joy", "union", "secret")):
        return Mood.JOY
    if any(word in text for word in ("waiting", "longing", "separation", "lament")):
        return Mood.LONGING
    if any(word in text for word in ("quarrel", "infidelity", "anger")):
        return Mood.ANGER
    if any(word in text for word in ("desert", "travel", "sorrow")):
        return Mood.SORROW
    return Mood.SERENITY


def demo_scene_frames(analysis: PoemAnalysis) -> list[SceneFrame]:
    thinai = analysis.thinai
    landscape = {
        Thinai.KURINJI: "misty mountain slopes, kurinji flowers, waterfall stone paths",
        Thinai.MULLAI: "rain-washed forest, jasmine vines, mango grove at dusk",
        Thinai.MARUTHAM: "fertile paddy fields, lotus ponds, village courtyards at dawn",
        Thinai.NEYTAL: "windy seashore, fishing boats, waves under a pale sky",
        Thinai.PALAI: "sun-struck wilderness, dry paths, lonely travel roads",
    }.get(thinai, "ancient Tamil landscape")
    color = ", ".join(THINAI_COLOR_PALETTE.get(thinai, THINAI_COLOR_PALETTE[Thinai.UNKNOWN]))

    speaker = (analysis.speaker or "speaker").strip()
    if speaker.lower().startswith("the "):
        speaker = speaker[4:].strip()

    return [
        SceneFrame(
            scene_id=1,
            title=f"{thinai.value} Landscape",
            description=f"The opening frame moves across {landscape}. The light is calm, the air is still, and the land quietly prepares the story.",
            mood=analysis.mood,
            thinai=thinai,
            visual_prompt=f"Ancient Tamil Sangam era {landscape}, cinematic painting, historically grounded clothing, soft atmospheric depth",
            characters=[],
            environment=landscape,
            lighting="soft dawn or dusk light",
            color_palette=color,
        ),
        SceneFrame(
            scene_id=2,
            title="Human Feeling",
            description=f"The {speaker} enters the scene with restrained emotion. The surrounding land stays close, turning silence into presence.",
            mood=analysis.mood,
            thinai=thinai,
            visual_prompt=f"Sangam-era figure in {landscape}, expressive but restrained emotion, classical Tamil poetic atmosphere",
            characters=[speaker],
            environment=landscape,
            lighting="warm side light",
            color_palette=color,
        ),
        SceneFrame(
            scene_id=3,
            title="Poetic Resolution",
            description="The final frame settles on the natural image at the heart of the moment. Landscape, memory, and feeling come together in a quiet close.",
            mood=analysis.mood,
            thinai=thinai,
            visual_prompt=f"Symbolic final frame of {landscape}, ancient Tamil Sangam mood, elegant cinematic composition",
            characters=[],
            environment=landscape,
            lighting="gentle fading light",
            color_palette=color,
        ),
    ]


def experience_scene_frames(
    base_scenes: list[SceneFrame],
    analysis: PoemAnalysis,
) -> list[SceneFrame]:
    """Build a richer visual sequence for the video experience."""
    thinai = analysis.thinai
    color = ", ".join(THINAI_COLOR_PALETTE.get(thinai, THINAI_COLOR_PALETTE[Thinai.UNKNOWN]))
    mood = analysis.mood

    beat_map: dict[Thinai, list[tuple[str, str, str]]] = {
        Thinai.KURINJI: [
            ("Mountain Opening", "Misty Kurinji hills rise around a narrow stone path. Waterfall spray and purple blossoms give the first scene a secret, expectant hush.", "kurinji hills waterfall mountain path"),
            ("Flowered Slope", "Kurinji flowers bend beside a clear mountain pool. The freshness of the slope carries the thrill of love kept private.", "kurinji flower mountain pool"),
            ("First Meeting", "The lovers enter the frame with quiet joy. Their gestures stay restrained, but the hills around them seem newly alive.", "lovers first meeting"),
            ("Moonlit Visit", "Moonlight folds the mountain path into a private world. The night feels close, protective, and full of unsaid feeling.", "moonlit night visit"),
            ("Poetic Echo", "Water, flowers, and silence remain after the lovers pass. The final image lingers like a memory held by the hills.", "waterfall kurinji landscape"),
        ],
        Thinai.MULLAI: [
            ("Forest Dusk", "Rain-washed Mullai forest settles under a slow evening sky. Jasmine vines and wet leaves hold the patience of waiting.", "mullai forest monsoon"),
            ("Ayar Settlement", "Cattle paths curve past small homes at the forest edge. The village moves at the gentle pace of someone expected to return.", "ayar settlement cattle"),
            ("Waiting Path", "The heroine watches the forest path without haste. Her stillness carries trust more strongly than words could.", "heroine waiting forest path"),
            ("Twilight Return", "A returning figure nears the village in soft evening light. The distance between hope and arrival begins to close.", "hero returns twilight"),
            ("Jasmine Rest", "Jasmine, deer, and dusk settle into a calm final frame. The waiting softens into peace.", "jasmine deer mullai"),
        ],
        Thinai.MARUTHAM: [
            ("Paddy Dawn", "Fertile paddy fields open under dawn light. The Marutham village wakes before the private tension comes into view.", "marutham paddy fields"),
            ("Lotus Pond", "Lotus water ripples as cranes step through the shallows. Tenderness remains visible beneath the strain between people.", "lotus pond crane dawn"),
            ("Village Courtyard", "A village courtyard brings the conflict into lived domestic space. Doorways, vessels, and morning light make the scene intimate.", "marutham village courtyard home"),
            ("Domestic Quarrel", "The heroine stands with hurt held carefully in her posture. The room stays restrained, letting silence carry the argument.", "domestic quarrel heroine"),
            ("Return Home", "The hero returns at the edge of the frame. The moment shifts from accusation toward recognition.", "hero returning home"),
            ("Sugarcane Edge", "Sugarcane and wet fields move softly in the wind. The landscape remains alive between the voices.", "sugarcane harvest field"),
            ("Reconciliation", "The village light softens around the final image. Memory and feeling settle without force.", "marutham reconciliation lotus"),
        ],
        Thinai.NEYTAL: [
            ("Seashore Wind", "The shore opens with boats, waves, and pale distance. Salt wind moves through the frame before any voice is heard.", "neytal seashore boats waves"),
            ("Waiting Tide", "The tide rises and falls beside the waiting figure. The horizon keeps separation visible but unreachable.", "shore longing waves"),
            ("Fishing Boats", "Fishing boats move across the water while daily life continues. The heart of the scene remains unsettled on the shore.", "fishing boats sea"),
            ("Pale Horizon", "The far line of the sea holds the eye. Its emptiness gives shape to longing.", "neytal landscape horizon"),
            ("Wave Memory", "Waves return again and again to the sand. The final frame leaves the feeling in motion.", "waves shore"),
        ],
        Thinai.PALAI: [
            ("Dry Road", "The Palai road opens under hard light. Dust, thorn, and distance make separation feel physical.", "palai dry road wilderness"),
            ("Travel Heat", "The journey stretches through sun and thorn. Every step carries both danger and resolve.", "desert travel hardship"),
            ("Lonely Pause", "A single pause on the road holds fear in stillness. The empty land presses close around the traveller.", "wilderness lonely path"),
            ("Distant Figure", "The traveller grows small inside the harsh landscape. Heat and distance swallow the path ahead.", "palai journey"),
            ("Heat Haze", "The final image trembles in the hot distance. Longing remains suspended where the road disappears.", "palai landscape"),
        ],
    }

    beats = beat_map.get(thinai)
    if not beats:
        return base_scenes or demo_scene_frames(analysis)

    scenes: list[SceneFrame] = []
    for index, (title, description, keywords) in enumerate(beats, start=1):
        scenes.append(
            SceneFrame(
                scene_id=index,
                title=title,
                description=description,
                mood=mood,
                thinai=thinai,
                visual_prompt=(
                    f"Ancient Tamil Sangam era {thinai.value} scene, {keywords}, "
                    "cinematic natural light, historically grounded clothing and landscape"
                ),
                characters=[analysis.speaker] if analysis.speaker and index in (3, 4, 5) else [],
                environment=keywords,
                lighting="cinematic dawn, dusk, or soft natural light",
                color_palette=color,
            )
        )

    return scenes


def demo_narration() -> NarrationResult | None:
    path = Path("assets/audio/analysis_narration.mp3")
    if not path.exists():
        return None
    return NarrationResult(
        audio_path=str(path),
        duration_seconds=18.0,
        language="en",
        success=True,
    )


def run_pipeline(
    poem_text: str,
    include_images: bool,
    include_audio: bool,
    include_video: bool,
    poem_id: int = 0,
    demo_mode: bool = False,
    target_language: str = "en",
) -> PipelineResult:
    result = PipelineResult(poem_text=poem_text)
    errors = []
    library_poem = find_library_poem(poem_id)

    if demo_mode:
        result.analysis = analysis_from_poem(library_poem, poem_text)
    else:
        with st.spinner("🧠 Pulavar is reading the poem..."):
            try:
                result.analysis = pulavar_ai.analyze_poem(poem_text)
                if not result.analysis or result.analysis.thinai == Thinai.UNKNOWN:
                    fallback = analysis_from_poem(library_poem, poem_text)
                    if fallback.thinai != Thinai.UNKNOWN:
                        result.analysis = fallback
            except Exception:
                errors.append("Analysis unavailable: using a reliable library reading for this poem.")
                result.analysis = analysis_from_poem(library_poem, poem_text)

    result.analysis = language_engine.improve_analysis_accuracy(
        result.analysis,
        poem_text=poem_text,
        library_poem=library_poem,
    )
    result.analysis = _ensure_deep_analysis_sections(
        result.analysis,
        poem_text=poem_text,
        library_poem=library_poem,
    )

    if demo_mode:
        result.scenes = demo_scene_frames(result.analysis)
    else:
        with st.spinner("🎬 Scene Weaver is composing scenes..."):
            try:
                result.scenes = scene_weaver.extract_scene_frames(result.analysis)
            except Exception:
                errors.append("Scene breakdown unavailable: showing curated Sangam scene frames.")
                result.scenes = demo_scene_frames(result.analysis)

    if not result.scenes:
        result.scenes = demo_scene_frames(result.analysis)

    narration_scenes = (
        experience_scene_frames(result.scenes, result.analysis)[:3]
        if include_video
        else result.scenes
    )

    if include_images and result.scenes:
        if demo_mode:
            result.images = resolve_video_images(result.scenes, [], result.analysis)
        else:
            with st.spinner("🖼️ Generating visual scenes..."):
                try:
                    generated_images = scene_generator.generate_all_scenes(result.scenes)
                    result.images = resolve_video_images(
                        result.scenes,
                        generated_images,
                        result.analysis,
                    )
                except Exception:
                    errors.append("Scene image generation unavailable: using curated image cache.")
                    result.images = resolve_video_images(result.scenes, [], result.analysis)

    if include_audio:
        if (
            demo_mode
            and target_language == "en"
            and os.getenv("DTEC_USE_BUNDLED_NARRATION") == "1"
        ):
            result.narration = demo_narration()
        else:
            with st.spinner("🔊 Sangam Voice is narrating..."):
                try:
                    narrate_fn = getattr(sangam_voice, "narrate_analysis", None)
                    if not narrate_fn:
                        raise AttributeError("narrate_analysis missing in sangam_voice.py")
                    result.narration = narrate_fn(
                        result.analysis,
                        narration_scenes,
                        target_language=target_language,
                    )
                    if result.narration and not result.narration.success:
                        result.narration = demo_narration() or result.narration
                except Exception:
                    errors.append("Narration unavailable: the text and scene experience are still ready.")
                    result.narration = demo_narration()

    # ── Video Experience ─────────────────────────────────────────────────────
    if include_video and _VIDEO_ENGINE_AVAILABLE:
        video_scenes = narration_scenes
        video_images = resolve_video_images(video_scenes, [], result.analysis)

        if not video_images:
            errors.append("Video skipped: no scene images were generated.")
        elif not result.narration or not result.narration.success:
            errors.append("Video skipped: narration is required. Enable voice narration in the sidebar.")
        else:
            with st.spinner("🎥 Composing Sangam Experience video..."):
                try:
                    result.video = video_engine.compose(
                        poem_id=poem_id,
                        title_en=getattr(result.analysis, "collection", "") or "Sangam Poem",
                        title_ta=getattr(result.analysis, "collection_tamil", "") or "",
                        thinai=result.analysis.thinai,
                        scenes=video_scenes,
                        images=video_images,
                        image_paths=[img.image_path for img in video_images],
                        narration=result.narration,
                        analysis=result.analysis,
                        target_language=target_language,
                    )
                    if result.video and not result.video.success:
                        errors.append(f"Video composition failed: {result.video.error}")
                except Exception as e:
                    errors.append(f"Video composition failed: {e}")
                    result.video = VideoExperience.failed(poem_id=poem_id, error=str(e))
    elif include_video and not _VIDEO_ENGINE_AVAILABLE:
        # Build the skeleton so the tab can show a "ready to render" state
        # even before video_engine.py is implemented.
        if result.images and result.narration and result.narration.success:
            result.video = VideoExperience.from_pipeline(
                poem_id=poem_id,
                title_en=getattr(result.analysis, "collection", "") or "Sangam Poem",
                title_ta=getattr(result.analysis, "collection_tamil", "") or "",
                thinai=result.analysis.thinai,
                images=resolve_video_images(narration_scenes, [], result.analysis),
                narration=result.narration,
                scenes=narration_scenes,
            )
            errors.append(
                "video_engine.py not found — VideoExperience skeleton built. "
                "Implement video_engine.compose() to enable ffmpeg rendering."
            )

    result.errors = errors
    result.success = len(errors) == 0
    return result


# ── DISPLAY: HELPERS ─────────────────────────────────────────────────────────

def _box(label: str, value_en: str, value_ta: str = "") -> str:
    ta_part = f'<div class="poetics-value-ta">{value_ta}</div>' if value_ta else ""
    return (
        f'<div class="poetics-box">'
        f'<div class="poetics-label">{label}</div>'
        f'<div class="poetics-value">{value_en}</div>'
        f'{ta_part}</div>'
    )


def _target_language() -> str:
    return language_engine.normalize_language(st.session_state.get("target_language", "en"))


def _ui(text: str, target_language: str | None = None) -> str:
    target_language = target_language or _target_language()
    translated = language_engine.ui_text(text, target_language)
    if translated == text:
        return _local_analysis_translation(text, target_language)
    return translated


def _translate_learning_payload(values: dict[str, str], target_language: str) -> dict[str, str]:
    translate_learning = getattr(language_engine, "translate_learning_json", None)
    if translate_learning:
        return translate_learning(values, target_language)
    if (
        target_language == "ta"
        and os.getenv("DTEC_ENABLE_LIVE_TRANSLATION", "1") == "1"
        and (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))
        and hasattr(language_engine, "_translate_json_cached")
    ):
        payload_json = json.dumps(values, ensure_ascii=False, sort_keys=True)
        try:
            return json.loads(language_engine._translate_json_cached(payload_json, target_language))
        except Exception:
            pass
    return language_engine.translate_json(values, target_language)


def _learning_translation_chunks(values: dict[str, str]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    current: dict[str, str] = {}
    current_chars = 0
    for key, value in values.items():
        value_chars = len(str(value))
        if current and (len(current) >= 8 or current_chars + value_chars > 1400):
            chunks.append(current)
            current = {}
            current_chars = 0
        current[key] = value
        current_chars += value_chars
    if current:
        chunks.append(current)
    return chunks


def _learning_translated_mapping(values: dict[str, str], target_language: str) -> dict[str, str]:
    target_language = language_engine.normalize_language(target_language)
    values = {key: value for key, value in (values or {}).items() if value}
    if target_language == "en" or not values:
        return values

    translated: dict[str, str] = {}
    for chunk in _learning_translation_chunks(values):
        try:
            translated_chunk = _translate_learning_payload(chunk, target_language)
        except Exception:
            translated_chunk = chunk
        translated.update(
            {key: str(translated_chunk.get(key, value)) for key, value in chunk.items()}
        )
    result: dict[str, str] = {}
    for key, value in values.items():
        selected = str(translated.get(key, value))
        if selected.strip() == str(value).strip():
            selected = _local_analysis_translation(str(value), target_language)
        result[key] = selected
    return result


def _learning_translated_text(text: str, target_language: str) -> str:
    translated = _learning_translated_mapping({"text": text or ""}, target_language)
    return translated.get("text", text or "")


def _selected_text(
    text: str,
    target_language: str,
    tamil_text: str = "",
    keep_tamil_note: bool = True,
) -> tuple[str, str]:
    target_language = language_engine.normalize_language(target_language)
    text = text or ""
    tamil_text = tamil_text or ""

    if target_language == "ta":
        return tamil_text or _learning_translated_text(text, target_language), ""
    if target_language == "en":
        return text, tamil_text if keep_tamil_note else ""

    translated = _local_analysis_translation(text, target_language)
    if translated == text:
        translated = _learning_translated_text(text, target_language)
    if not translated or translated.strip() == text.strip():
        translated = _local_analysis_translation(text, target_language)
    return translated, tamil_text if keep_tamil_note and target_language == "en" else ""


def _translated_text(text: str, target_language: str) -> str:
    return _selected_text(text, target_language, keep_tamil_note=False)[0]


def _translated_list(values: list[str], target_language: str) -> list[str]:
    target_language = language_engine.normalize_language(target_language)
    values = [value for value in (values or []) if value]
    if target_language == "en" or not values:
        return values
    payload = {str(index): value for index, value in enumerate(values)}
    translated = _learning_translated_mapping(payload, target_language)
    return [str(translated.get(str(index), value)) for index, value in enumerate(values)]


def _translated_mapping(
    values: dict[str, str],
    target_language: str,
    translate_tamil: bool = False,
) -> dict[str, str]:
    target_language = language_engine.normalize_language(target_language)
    values = {key: value for key, value in (values or {}).items() if value}
    if target_language == "en" or (target_language == "ta" and not translate_tamil) or not values:
        return values
    if translate_tamil:
        translated = _learning_translated_mapping(values, target_language)
    else:
        translated = language_engine.translate_json(values, target_language)
    return {key: str(translated.get(key, value)) for key, value in values.items()}


def _display_box(
    label: str,
    value: str,
    target_language: str,
    tamil_value: str = "",
) -> str:
    selected, note = _selected_text(value, target_language, tamil_value)
    return _box(_ui(label, target_language), html.escape(selected), html.escape(note))


ANALYSIS_DETAIL_LABELS = [
    "Sangam Poetics",
    "Muthal Porul",
    "Time and Place",
    "Landscape",
    "Season",
    "Time",
    "Karu Porul",
    "Flora, Fauna and Objects",
    "Uri Porul",
    "Central Emotion or Action",
    "Meyppadu",
    "Cultural Context",
    "Literary Devices",
    "Grammar Notes",
    "In this poem",
    "Word Meanings",
    "Characters",
    "Meaning Breakdown",
]

LOCAL_ANALYSIS_TRANSLATIONS = {
    "hi": {
        "Poet": "कवि",
        "Collection": "संग्रह",
        "Period": "काल",
        "Thinai": "तिणै",
        "Emotion": "भाव",
        "Mood": "मनोभाव",
        "Thurai": "तुरै",
        "Speaker": "वक्ता",
        "Listener": "श्रोता",
        "Summary": "सारांश",
        "Learner Guide": "सीखने की मार्गदर्शिका",
        "Sangam Poetics": "संगम काव्यशास्त्र",
        "Muthal Porul": "मुतल पोरुल",
        "Time and Place": "समय और स्थान",
        "Landscape": "भूदृश्य",
        "Season": "ऋतु",
        "Time": "समय",
        "Karu Porul": "करु पोरुल",
        "Flora, Fauna and Objects": "वनस्पति, जीव-जंतु और वस्तुएं",
        "Uri Porul": "उरि पोरुल",
        "Central Emotion or Action": "मुख्य भाव या क्रिया",
        "Meyppadu": "मेय्प्पाडु",
        "Cultural Context": "सांस्कृतिक संदर्भ",
        "Literary Devices": "साहित्यिक उपकरण",
        "Grammar Notes": "व्याकरण टिप्पणियां",
        "In this poem": "इस कविता में",
        "Word Meanings": "शब्दार्थ",
        "Characters": "पात्र",
        "Meaning Breakdown": "अर्थ-विवरण",
        "Kurinji": "कुरिंजी",
        "Kapilar": "कपिलर",
        "Kuruntokai": "कुरुंतोकै",
        "joy": "आनंद",
        "Joy": "आनंद",
        "Akam": "अकम",
        "300 BCE – 300 CE": "300 ईसा पूर्व - 300 ईस्वी",
        "300 BCE - 300 CE": "300 ईसा पूर्व - 300 ईस्वी",
        "300 BCE – 300 CE - अकम": "300 ईसा पूर्व - 300 ईस्वी - अकम",
        "300 BCE - 300 CE - अकम": "300 ईसा पूर्व - 300 ईस्वी - अकम",
        "Joy and longing (மகிழ்ச்சி, ஏக்கம்)": "आनंद और लालसा (மகிழ்ச்சி, ஏக்கம்)",
        "Hills - Premarital union (களவு)": "पहाड़ - विवाह से पहले का गुप्त मिलन (களவு)",
        "300 BCE – 300 CE - Akam": "300 ईसा पूर्व - 300 ईस्वी - अकम",
        "300 BCE - 300 CE - Akam": "300 ईसा पूर्व - 300 ईस्वी - अकम",
        "Punarthal (புணர்தல்) — Union of lovers": "पुणर्तल (புணர்தல்) - प्रेमियों का मिलन",
        "Punarthal (புணர்தல்) - Union of lovers": "पुणर्तल (புணர்தல்) - प्रेमियों का मिलन",
        "The Hero (தலைவன்)": "नायक (தலைவன்)",
        "Friend / confidant (தோழி)": "सखी / विश्वासपात्र (தோழி)",
        "Represents secret premarital love set in mountainous landscapes. Kurinji Thinai in Sangam akam poetry always depicts the first stage of love — the secret union before formal marriage.": "यह पर्वतीय भूदृश्य में बसे विवाह-पूर्व गुप्त प्रेम को दिखाता है। संगम अकम कविता में कुरिंजी तिणै प्रेम के पहले चरण, यानी औपचारिक विवाह से पहले के गुप्त मिलन, को दर्शाता है।",
    },
    "te": {
        "Poet": "కవి",
        "Collection": "సంకలనం",
        "Period": "కాలం",
        "Thinai": "తిణై",
        "Emotion": "భావం",
        "Mood": "మనోభావం",
        "Thurai": "తురై",
        "Speaker": "మాట్లాడేవారు",
        "Listener": "వినేవారు",
        "Summary": "సారాంశం",
        "Learner Guide": "అభ్యాస మార్గదర్శిని",
        "Sangam Poetics": "సంగం కవితా శాస్త్రం",
        "Muthal Porul": "ముతల్ పొరుల్",
        "Time and Place": "కాలం మరియు స్థలం",
        "Landscape": "భూభాగం",
        "Season": "ఋతువు",
        "Time": "సమయం",
        "Karu Porul": "కరు పొరుల్",
        "Flora, Fauna and Objects": "చెట్లు, జంతువులు మరియు వస్తువులు",
        "Uri Porul": "ఉరి పొరుల్",
        "Central Emotion or Action": "కేంద్ర భావం లేదా చర్య",
        "Meyppadu": "మెయ్ప్పాడు",
        "Cultural Context": "సాంస్కృతిక సందర్భం",
        "Literary Devices": "సాహిత్య పద్ధతులు",
        "Grammar Notes": "వ్యాకరణ గమనికలు",
        "In this poem": "ఈ కవితలో",
        "Word Meanings": "పదాల అర్థాలు",
        "Characters": "పాత్రలు",
        "Meaning Breakdown": "అర్థ వివరణ",
        "Kurinji": "కురింజి",
        "Kapilar": "కపిలర్",
        "Kuruntokai": "కురుంతొకై",
        "joy": "ఆనందం",
        "Joy": "ఆనందం",
        "Akam": "అకం",
        "300 BCE – 300 CE": "క్రీ.పూ. 300 - క్రీ.శ. 300",
        "300 BCE - 300 CE": "క్రీ.పూ. 300 - క్రీ.శ. 300",
        "300 BCE – 300 CE - అకం": "క్రీ.పూ. 300 - క్రీ.శ. 300 - అకం",
        "300 BCE - 300 CE - అకం": "క్రీ.పూ. 300 - క్రీ.శ. 300 - అకం",
        "Joy and longing (மகிழ்ச்சி, ஏக்கம்)": "ఆనందం మరియు కోరిక (மகிழ்ச்சி, ஏக்கம்)",
        "Hills - Premarital union (களவு)": "పర్వతాలు - వివాహానికి ముందున్న రహస్య కలయిక (களவு)",
        "300 BCE – 300 CE - Akam": "క్రీ.పూ. 300 - క్రీ.శ. 300 - అకం",
        "300 BCE - 300 CE - Akam": "క్రీ.పూ. 300 - క్రీ.శ. 300 - అకం",
        "Punarthal (புணர்தல்) — Union of lovers": "పుణర్తల్ (புணர்தல்) - ప్రేమికుల కలయిక",
        "Punarthal (புணர்தல்) - Union of lovers": "పుణర్తల్ (புணர்தல்) - ప్రేమికుల కలయిక",
        "The Hero (தலைவன்)": "నాయకుడు (தலைவன்)",
        "Friend / confidant (தோழி)": "స్నేహితురాలు / నమ్మకస్తురాలు (தோழி)",
        "Represents secret premarital love set in mountainous landscapes. Kurinji Thinai in Sangam akam poetry always depicts the first stage of love — the secret union before formal marriage.": "పర్వత భూభాగాల్లో జరిగే రహస్య వివాహపూర్వ ప్రేమను ఇది సూచిస్తుంది. సంగం అకం కవిత్వంలో కురింజి తిణై ప్రేమ యొక్క మొదటి దశను, అంటే అధికారిక వివాహానికి ముందున్న రహస్య కలయికను, ఎప్పుడూ చిత్రిస్తుంది.",
        "Mullai": "ముల్లై",
        "Marutham": "మరుతం",
        "Neytal": "నెయ్తల్",
        "Palai": "పాలై",
        "Muthal": "ముతల్",
        "Karu": "కరు",
        "Uri": "ఉరి",
        "Ullurai": "ఉள்ளురై",
        "Thurai": "తురై",
        "Meyppadu": "మెయ్ప్పాడు",
        "Mountains (மலை)": "పర్వతాలు",
        "Cool season / Hemanta (முன்பனிக்காலம்)": "చల్లని ఋతువు / హేమంతం",
        "Misty dawn / Night (யாமம்)": "మంచుతో కూడిన ఉదయం / రాత్రి",
        "Kurinji flowers (குறிஞ்சி மலர்)": "కురింజి పూలు",
        "Waterfall (அருவி)": "జలపాతం",
        "Jasmine tree (மல்லிகை)": "మల్లె చెట్టు",
        "Mountain pool fish (மலைக்குளம் மீன்)": "పర్వత కుంట చేపలు",
        "Hummingbird (தேன்சிட்டு)": "తేనెపిట్ట",
        "The time and place frame of a Sangam poem.": "సంగం కవితలో కాలం మరియు స్థలాన్ని సూచించే ఆధారం.",
        "In Kurinji, landscape is not decoration; it sets the emotional world.": "కురింజిలో భూభాగం అలంకారం కాదు; అది భావ ప్రపంచాన్ని నిర్మిస్తుంది.",
        "The living scene: flowers, animals, occupations, objects, and weather.": "జీవంతమైన దృశ్యం: పూలు, జంతువులు, వృత్తులు, వస్తువులు మరియు వాతావరణం.",
        "Natural details help the reader infer the speaker's inner state.": "ప్రకృతి వివరాలు మాట్లాడేవారి అంతరంగ స్థితిని పాఠకుడు గ్రహించడానికి సహాయపడతాయి.",
        "The central human situation or emotional action.": "కేంద్ర మానవ పరిస్థితి లేదా భావోద్వేగ చర్య.",
        "The poem's outer image points toward an inner experience of love, waiting, union, or separation.": "కవితలోని బాహ్య చిత్రం ప్రేమ, నిరీక్షణ, కలయిక లేదా విరహం వంటి అంతరంగ అనుభవాన్ని సూచిస్తుంది.",
        "An embedded inner meaning carried through nature imagery.": "ప్రకృతి బింబాల ద్వారా మోసుకెళ్లబడే అంతర్లీన అర్థం.",
        "The visible landscape quietly decodes the hidden feeling of the speaker.": "కనిపించే భూభాగం మాట్లాడేవారి దాగిన భావాన్ని మౌనంగా వెల్లడిస్తుంది.",
        "The specific dramatic situation within a Thinai.": "ఒక తిణైలోని నిర్దిష్ట నాటకీయ పరిస్థితి.",
        "The felt emotional expression made visible in the poem.": "కవితలో కనిపించేలా చేయబడిన అనుభూతి భావ వ్యక్తీకరణ.",
        "Joy and longing (மகிழ்ச்சி, ஏக்கம்)": "ఆనందం మరియు కోరిక",
        "Speaker": "మాట్లాడేవారు",
        "Listener": "వినేవారు",
        "The Hero": "నాయకుడు",
        "Friend / confidant": "స్నేహితురాలు / నమ్మకస్తురాలు",
        "The voice through which the poem's emotional situation is revealed.": "కవితలోని భావోద్వేగ పరిస్థితి బయటపడే స్వరం.",
        "The addressed presence who helps frame the poem's dramatic moment.": "కవితలోని నాటకీయ క్షణాన్ని ఆకృతిచేయడంలో సహాయపడే సంభోధిత సన్నిధి.",
        "A mountain flower; also the name of the Thinai": "ఒక పర్వత పువ్వు; అదే తిణై పేరు కూడా.",
        "Are blooming": "వికసిస్తున్నాయి",
        "Mountain": "పర్వతం",
        "Beloved woman": "ప్రియురాలు",
        "Waterfall": "జలపాతం",
        "Eyes": "కళ్లు",
        "Fish — used as a simile for beautiful eyes": "చేప - అందమైన కళ్లకు ఉపమానంగా వాడబడింది",
        "Pool / pond": "కుంట / చెరువు",
        "The Kurinji flowers bloom on the mountain slopes,": "పర్వత వాలుల్లో కురింజి పూలు వికసిస్తున్నాయి,",
        "where the mist hangs low and the waterfall sings.": "అక్కడ మంచు తక్కువగా వేలాడుతూ, జలపాతం పాడుతున్నట్లు ఉంది.",
        "My beloved waits beneath the jasmine tree,": "నా ప్రియురాలు మల్లె చెట్టు కింద ఎదురు చూస్తోంది,",
        "her eyes like the dark fish of the mountain pool.": "ఆమె కళ్లు పర్వత కుంటలోని నల్లని చేపల్లా ఉన్నాయి.",
        "The hummingbird drinks deep from the red-tipped flower,": "తేనెపిట్ట ఎర్రని కొనలున్న పువ్వు నుంచి లోతుగా తేనె తాగుతుంది,",
        "as I drink deep from the sight of her.": "నేను ఆమెను చూసే దృశ్యం నుంచి లోతుగా తాగుతున్నట్లుగా.",
        "The opening image establishes Kurinji Thinai and prepares the emotional field.": "ప్రారంభ చిత్రం కురింజి తిణైను స్థాపించి భావోద్వేగ వాతావరణాన్ని సిద్ధం చేస్తుంది.",
        "This sentence advances the poem's dramatic situation and deepens its implied feeling.": "ఈ వాక్యం కవితలోని నాటకీయ పరిస్థితిని ముందుకు తీసుకెళ్లి దాని అంతర్లీన భావాన్ని మరింత లోతుగా చేస్తుంది.",
        "The human emotion comes forward here, revealing the poem's Uri Porul.": "ఇక్కడ మానవ భావోద్వేగం ముందుకు వచ్చి కవిత యొక్క ఉరి పొరుల్‌ను వెల్లడిస్తుంది.",
        "The comparison turns an outer image into a decoded inner feeling.": "ఈ పోలిక బాహ్య చిత్రాన్ని అర్థమయ్యే అంతరంగ భావంగా మార్చుతుంది.",
        "A natural detail functions as Karu Porul, carrying emotional meaning through landscape.": "ప్రకృతి వివరము కరు పొరుల్‌గా పనిచేస్తూ, భూభాగం ద్వారా భావోద్వేగ అర్థాన్ని మోస్తుంది.",
        "Ullurai / nature-symbolism": "ఉள்ளురై / ప్రకృతి ప్రతీకవాదం",
        "Kurinji Thinai imagery": "కురింజి తిణై బింబాలు",
        "Uvamai / simile": "ఉవమై / ఉపమానం",
        "Thinai imagery, nature-symbolism, and implied emotional parallelism.": "తిణై బింబాలు, ప్రకృతి ప్రతీకవాదం మరియు అంతర్లీన భావోద్వేగ సమాంతరత.",
    }
}


CORE_ANALYSIS_LABEL_TRANSLATIONS = {
    "ml": {
        "Poet": "കവി",
        "Collection": "സമാഹാരം",
        "Period": "കാലഘട്ടം",
        "Thinai": "തിണൈ",
        "Emotion": "വികാരം",
        "Mood": "ഭാവഭൂമി",
        "Thurai": "തുറൈ",
        "Speaker": "സംസാരിക്കുന്നവർ",
        "Listener": "ശ്രോതാവ്",
        "Learner Guide": "പഠന മാർഗ്ഗദർശി",
    },
    "kn": {
        "Poet": "ಕವಿ",
        "Collection": "ಸಂಗ್ರಹ",
        "Period": "ಕಾಲ",
        "Thinai": "ತಿಣೈ",
        "Emotion": "ಭಾವನೆ",
        "Mood": "ಮನೋಭಾವ",
        "Thurai": "ತುರೈ",
        "Speaker": "ಮಾತನಾಡುವವರು",
        "Listener": "ಕೇಳುವವರು",
        "Learner Guide": "ಕಲಿಕಾ ಮಾರ್ಗದರ್ಶಿ",
    },
    "bn": {
        "Poet": "কবি",
        "Collection": "সংকলন",
        "Period": "কালপর্ব",
        "Thinai": "তিণৈ",
        "Emotion": "অনুভূতি",
        "Mood": "ভাব",
        "Thurai": "তুরাই",
        "Speaker": "বক্তা",
        "Listener": "শ্রোতা",
        "Learner Guide": "শিক্ষার্থী নির্দেশিকা",
    },
    "mr": {
        "Poet": "कवी",
        "Collection": "संग्रह",
        "Period": "कालखंड",
        "Thinai": "तिणै",
        "Emotion": "भावना",
        "Mood": "भावस्थिती",
        "Thurai": "तुरै",
        "Speaker": "वक्ता",
        "Listener": "श्रोता",
        "Learner Guide": "शिकण्याची मार्गदर्शिका",
    },
    "gu": {
        "Poet": "કવિ",
        "Collection": "સંગ્રહ",
        "Period": "કાળ",
        "Thinai": "તિણૈ",
        "Emotion": "ભાવ",
        "Mood": "મનોભાવ",
        "Thurai": "તુરૈ",
        "Speaker": "વક્તા",
        "Listener": "શ્રોતા",
        "Learner Guide": "અભ્યાસ માર્ગદર્શિકા",
    },
    "pa": {
        "Poet": "ਕਵੀ",
        "Collection": "ਸੰਗ੍ਰਹਿ",
        "Period": "ਕਾਲ",
        "Thinai": "ਤਿਣੈ",
        "Emotion": "ਭਾਵਨਾ",
        "Mood": "ਮਨੋਭਾਵ",
        "Thurai": "ਤੁਰੈ",
        "Speaker": "ਬੋਲਣ ਵਾਲਾ",
        "Listener": "ਸੁਣਨ ਵਾਲਾ",
        "Learner Guide": "ਸਿੱਖਣ ਮਾਰਗਦਰਸ਼ਿਕਾ",
    },
    "or": {
        "Poet": "କବି",
        "Collection": "ସଂଗ୍ରହ",
        "Period": "କାଳ",
        "Thinai": "ତିଣୈ",
        "Emotion": "ଭାବ",
        "Mood": "ମନୋଭାବ",
        "Thurai": "ତୁରୈ",
        "Speaker": "ବକ୍ତା",
        "Listener": "ଶ୍ରୋତା",
        "Learner Guide": "ଶିକ୍ଷାର୍ଥୀ ମାର୍ଗଦର୍ଶିକା",
    },
}


def _local_analysis_translation(text: str, target_language: str) -> str:
    target_language = language_engine.normalize_language(target_language)
    text = text or ""
    local = LOCAL_ANALYSIS_TRANSLATIONS.get(target_language, {})
    core = CORE_ANALYSIS_LABEL_TRANSLATIONS.get(target_language, {})
    return local.get(text, core.get(text, text))


def _apply_local_analysis_translations(
    values: dict[str, str],
    target_language: str,
) -> dict[str, str]:
    target_language = language_engine.normalize_language(target_language)
    result: dict[str, str] = {}
    for key, value in (values or {}).items():
        result[key] = _local_analysis_translation(str(value), target_language)
    return result


def _translated_analysis_value(text: str, target_language: str) -> str:
    target_language = language_engine.normalize_language(target_language)
    if target_language == "en":
        return text or ""
    local = _local_analysis_translation(text or "", target_language)
    if local != (text or ""):
        return local
    return _learning_translated_text(text or "", target_language)


def _analysis_detail_translations(
    analysis: PoemAnalysis,
    target_language: str,
) -> tuple[dict[str, str], dict[str, str]]:
    target_language = language_engine.normalize_language(target_language)
    labels = {label: _ui(label, target_language) for label in ANALYSIS_DETAIL_LABELS}
    if target_language == "en":
        return labels, {}

    payload: dict[str, str] = {}
    for label in ANALYSIS_DETAIL_LABELS:
        payload[f"label::{label}"] = label

    if analysis.muthal_porul:
        mp = analysis.muthal_porul
        for key, value in (
            ("muthal_landscape", mp.landscape),
            ("muthal_season", mp.season),
            ("muthal_time", mp.time),
        ):
            if value:
                payload[key] = value

    for index, item in enumerate(analysis.karu_porul or []):
        if item:
            payload[f"karu::{index}"] = item

    for index, note in enumerate(analysis.grammar_notes or []):
        if note.term:
            payload[f"grammar_term::{index}"] = note.term
        if note.definition:
            payload[f"grammar_definition::{index}"] = note.definition
        if note.example:
            payload[f"grammar_example::{index}"] = note.example

    for index, meaning in enumerate((analysis.word_meanings or {}).values()):
        if meaning:
            payload[f"word_meaning::{index}"] = str(meaning)

    for index, char in enumerate(analysis.characters or []):
        if char.name:
            payload[f"character_name::{index}"] = char.name
        if char.role:
            payload[f"character_role::{index}"] = char.role
        if char.description:
            payload[f"character_description::{index}"] = char.description

    for index, entry in enumerate(analysis.meaning_breakdown or []):
        if entry.translation:
            payload[f"meaning_translation::{index}"] = entry.translation
        if entry.interpretation:
            payload[f"meaning_interpretation::{index}"] = entry.interpretation
        if entry.literary_device:
            payload[f"meaning_device::{index}"] = entry.literary_device

    translated = _learning_translated_mapping(payload, target_language)
    labels.update(
        {
            label: translated.get(f"label::{label}", labels[label])
            for label in ANALYSIS_DETAIL_LABELS
        }
    )
    return labels, translated


def get_cached_scene_image(
    scene: SceneFrame,
    analysis: PoemAnalysis | None = None,
    exclude_paths: set[str] | None = None,
) -> str | None:
    cache_keys = scene_weaver.select_cache_scene(scene, analysis)
    unique_keys = []
    seen = set()

    thinai = analysis.thinai if analysis and analysis.thinai != Thinai.UNKNOWN else scene.thinai
    for cache_key in SCENE_SLOT_CACHE_KEYS.get(thinai, {}).get(scene.scene_id, []):
        normalized = cache_key.strip().lower()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_keys.append(normalized)

    for cache_key in cache_keys:
        normalized = cache_key.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        unique_keys.append(normalized)

    thinai_pool = set(THINAI_CACHE_KEYS.get(thinai, []))

    available_images: list[str] = []
    checked_paths = set()

    def add_variants_for_key(key: str):
        for suffix in ("", "2", "3", "4"):
            variant = f"{key}{suffix}"
            if variant in SCENE_CACHE:
                path = SCENE_CACHE[variant]
                if path not in checked_paths and Path(path).exists():
                    available_images.append(path)
                    checked_paths.add(path)

    # First pass: same-thinai scene slot and description matches.
    for key in unique_keys:
        if not thinai_pool or key in thinai_pool:
            add_variants_for_key(key)

    # Second pass: same-thinai random cache image before crossing into another thinai.
    if not available_images:
        for key in THINAI_CACHE_KEYS.get(thinai, []):
            add_variants_for_key(key)

    # Final fallback: any exact candidate or generic landscape only if thinai cache is absent.
    if not available_images:
        for key in unique_keys:
            add_variants_for_key(key)
        for key in ("kurinji_landscape", "mullai_landscape", "marutham_landscape", "neytal_landscape", "palai_landscape"):
            add_variants_for_key(key)

    if not available_images:
        return None

    if exclude_paths:
        unused_images = [path for path in available_images if path not in exclude_paths]
        if unused_images:
            available_images = unused_images

    return available_images[0]


def resolve_video_images(
    scenes: list[SceneFrame],
    images: list[GeneratedImage],
    analysis: PoemAnalysis | None = None,
) -> list[GeneratedImage]:
    image_map = {
        img.scene_id: img
        for img in images
        if (
            img.success
            and img.exists_on_disk()
            and getattr(img, "backend", "") != "placeholder"
        )
    }
    video_images: list[GeneratedImage] = []
    used_cached_paths: set[str] = set()

    for scene in scenes:
        image = image_map.get(scene.scene_id)
        if image:
            video_images.append(image)
            continue

        cached_path = get_cached_scene_image(scene, analysis, used_cached_paths)
        if cached_path:
            used_cached_paths.add(cached_path)
            video_images.append(
                GeneratedImage(
                    scene_id=scene.scene_id,
                    image_path=cached_path,
                    prompt_used=scene.visual_prompt,
                    backend="scene-cache",
                )
            )

    return video_images


def stage_notices(result: PipelineResult, stage: str) -> list[str]:
    prefixes = {
        "analysis": ("Analysis unavailable",),
        "scenes": ("Scene breakdown unavailable", "Scene image generation unavailable"),
        "voice": ("Narration unavailable",),
        "video": ("Video skipped", "Video composition failed", "video_engine.py not found"),
    }
    wanted = prefixes.get(stage, ())
    return [err for err in result.errors if err.startswith(wanted)]


def render_stage_notices(result: PipelineResult, stage: str):
    for notice in stage_notices(result, stage):
        message = notice.split(":", 1)[0] if stage == "video" and "failed" in notice.lower() else notice
        st.caption(f"Note: {message}")


# ── DISPLAY: ANALYSIS ────────────────────────────────────────────────────────

def display_analysis(analysis: PoemAnalysis):
    st.markdown("## 🧠 Literary Analysis · இலக்கிய ஆய்வு")

    # OCR source badge
    if analysis.ocr_source:
        lang_label = {"tamil": "🇮🇳 Tamil", "english": "🇬🇧 English", "mixed": "🌐 Tamil + English"}.get(analysis.ocr_language, "")
        st.caption(f"📷 Analyzed from {analysis.ocr_source} image · {lang_label}")

    # Poet / Collection / Period
    if analysis.poet or analysis.collection:
        c1, c2, c3 = st.columns(3)
        with c1:
            if analysis.poet:
                st.markdown(_box("✍️ Poet / புலவர்", analysis.poet, analysis.poet_tamil), unsafe_allow_html=True)
        with c2:
            if analysis.collection:
                st.markdown(_box("📚 Collection / தொகை", analysis.collection, analysis.collection_tamil), unsafe_allow_html=True)
        with c3:
            parts = []
            if analysis.period:
                parts.append(analysis.period)
            if analysis.akam_puram:
                ta = "அகம்" if analysis.akam_puram == "Akam" else "புறம்"
                parts.append(f"{ta} ({analysis.akam_puram})")
            if parts:
                st.markdown(_box("🕰️ Period · காலம்", " · ".join(parts)), unsafe_allow_html=True)

    st.divider()

    # Thinai / Emotion / Mood
    c1, c2, c3 = st.columns(3)
    with c1:
        thinai_ta = THINAI_TAMIL.get(analysis.thinai, "")
        thinai_meaning = THINAI_MEANING.get(analysis.thinai, "")
        st.markdown(
            f"**தினை / Thinai:**<br>"
            f"<span class='thinai-badge'>{analysis.thinai.value} · {thinai_ta}</span><br>"
            f"<small style='color:var(--sangam-muted)'>{thinai_meaning}</small>",
            unsafe_allow_html=True
        )
    with c2:
        emo = analysis.emotion + (f" · {analysis.emotion_tamil}" if analysis.emotion_tamil else "")
        st.markdown(_box("உணர்வு / Emotion", emo), unsafe_allow_html=True)
    with c3:
        mood_ta = MOOD_TAMIL.get(analysis.mood, "")
        st.markdown(_box("மனநிலை / Mood", analysis.mood.value.capitalize(), mood_ta), unsafe_allow_html=True)

    st.divider()

    # Thurai / Speaker / Listener
    if analysis.thurai or analysis.speaker or analysis.listener:
        c1, c2, c3 = st.columns(3)
        with c1:
            if analysis.thurai:
                st.markdown(_box("துறை / Thurai", analysis.thurai, analysis.thurai_tamil), unsafe_allow_html=True)
        with c2:
            if analysis.speaker:
                st.markdown(_box("பேசுவோர் / Speaker", analysis.speaker), unsafe_allow_html=True)
        with c3:
            if analysis.listener:
                st.markdown(_box("கேட்போர் / Listener", analysis.listener), unsafe_allow_html=True)

    # Summary
    if analysis.summary:
        ta_part = f'<br><br><em style="color:var(--sangam-muted)">{analysis.summary_tamil}</em>' if analysis.summary_tamil else ""
        st.markdown(f'<div class="analysis-card"><strong>📖 Summary / சுருக்கம்</strong><br>{analysis.summary}{ta_part}</div>', unsafe_allow_html=True)

    target_language = st.session_state.get("target_language", "en")
    if target_language not in ("en", "ta"):
        learner_note = language_engine.learning_bridge_text(analysis, target_language)
        st.markdown(
            f'<div class="analysis-card"><strong>🌐 {language_engine.language_label(target_language)} Learner Guide</strong><br>{learner_note}</div>',
            unsafe_allow_html=True,
        )

    # Three-fold Poetics
    st.markdown("### 🌿 Sangam Poetics · முப்பொருள்")
    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown("**முதற்பொருள் · Muthal Porul**")
        st.caption("Time & Place")
        if analysis.muthal_porul:
            mp = analysis.muthal_porul
            if mp.landscape:
                st.markdown(f"🗻 **Landscape:** {mp.landscape}" + (f" · {mp.landscape_tamil}" if mp.landscape_tamil else ""))
            if mp.season:
                st.markdown(f"🌦️ **Season:** {mp.season}" + (f" · {mp.season_tamil}" if mp.season_tamil else ""))
            if mp.time:
                st.markdown(f"🕐 **Time:** {mp.time}" + (f" · {mp.time_tamil}" if mp.time_tamil else ""))

    with p2:
        st.markdown("**கருப்பொருள் · Karu Porul**")
        st.caption("Flora, Fauna & Objects")
        for item in analysis.karu_porul:
            st.markdown(f"• {item}")

    with p3:
        st.markdown("**உரிப்பொருள் · Uri Porul**")
        st.caption("Central Emotion/Action")
        if analysis.uri_porul:
            uri = analysis.uri_porul + (f"\n\n*{analysis.uri_porul_tamil}*" if analysis.uri_porul_tamil else "")
            st.info(uri)
        if analysis.meyppadu:
            st.markdown(f"**மெய்ப்பாடு:** {analysis.meyppadu}" + (f" · {analysis.meyppadu_tamil}" if analysis.meyppadu_tamil else ""))

    st.divider()

    # Cultural Context
    if analysis.cultural_context:
        ta_part = f'<br><br><em style="color:var(--sangam-muted)">{analysis.cultural_context_tamil}</em>' if analysis.cultural_context_tamil else ""
        st.markdown(f'<div class="analysis-card"><strong>🏛️ Cultural Context / பண்பாட்டு சூழல்</strong><br>{analysis.cultural_context}{ta_part}</div>', unsafe_allow_html=True)

    # Literary Devices
    if analysis.literary_devices:
        st.markdown(f'<div class="analysis-card"><strong>✦ Literary Devices / இலக்கண கோட்பாடுகள்</strong><br>{analysis.literary_devices}</div>', unsafe_allow_html=True)

    # Grammar Notes
    if analysis.grammar_notes:
        st.markdown("### 📐 Grammar Notes · இலக்கணக் குறிப்புகள்")
        for note in analysis.grammar_notes:
            term = note.term + (f" · {note.term_tamil}" if note.term_tamil else "")
            st.markdown(f'<div class="character-entry"><strong>{term}</strong><br><span style="color:var(--sangam-ink)">{note.definition}</span><br><span style="color:var(--sangam-muted)"><em>In this poem: {note.example}</em></span></div>', unsafe_allow_html=True)

    # Word Meanings
    if analysis.word_meanings:
        st.markdown("### 🔤 Word Meanings · சொற்பொருள்")
        for word, meaning in analysis.word_meanings.items():
            st.markdown(f'<div class="word-entry"><span class="word-ta">{word}</span><span class="word-en">{meaning}</span></div>', unsafe_allow_html=True)

    # Characters
    if analysis.characters:
        st.markdown("### 👤 Characters · கதாபாத்திரங்கள்")
        for char in analysis.characters:
            name = char.name + (f" · {char.name_tamil}" if char.name_tamil else "")
            role = char.role + (f" · {char.role_tamil}" if char.role_tamil else "")
            st.markdown(f'<div class="character-entry"><strong>{name}</strong> — <em>{role}</em><br><span style="color:var(--sangam-muted)">{char.description}</span></div>', unsafe_allow_html=True)

    # Meaning Breakdown
    if analysis.meaning_breakdown:
        st.markdown("### 📜 Meaning Breakdown · பொருள் விளக்கம்")
        for entry in analysis.meaning_breakdown:
            device = f' <span style="color:var(--sangam-muted);font-size:0.85rem">[{entry.literary_device}]</span>' if entry.literary_device else ""
            st.markdown(f'<div class="meaning-entry"><div class="meaning-original">"{entry.original}"{device}</div><div class="meaning-translation">→ {entry.translation}</div><div class="meaning-interpretation">✦ {entry.interpretation}</div></div>', unsafe_allow_html=True)


# ── DISPLAY: SCENES ──────────────────────────────────────────────────────────

def display_analysis(analysis: PoemAnalysis):
    target_language = _target_language()
    display = language_engine.translate_analysis_payload(analysis, target_language)
    detail_labels, detail_text = _analysis_detail_translations(analysis, target_language)
    if target_language != "en":
        display.update(
            _learning_translated_mapping(
                {key: str(value) for key, value in display.items() if value},
                target_language,
            )
        )

    st.markdown(f"## {_ui('Literary Analysis', target_language)}")

    if analysis.ocr_source:
        lang_label = {"tamil": "Tamil", "english": "English", "mixed": "Tamil + English"}.get(analysis.ocr_language, "")
        source = _translated_text(f"Analyzed from {analysis.ocr_source} image", target_language)
        st.caption(f"{source} - {lang_label}")

    if analysis.poet or analysis.collection:
        c1, c2, c3 = st.columns(3)
        with c1:
            if analysis.poet:
                st.markdown(_display_box("Poet", analysis.poet, target_language, analysis.poet_tamil), unsafe_allow_html=True)
        with c2:
            if analysis.collection:
                st.markdown(_display_box("Collection", analysis.collection, target_language, analysis.collection_tamil), unsafe_allow_html=True)
        with c3:
            period_parts = []
            if analysis.period:
                period_parts.append(_translated_text(analysis.period, target_language))
            if analysis.akam_puram:
                akam_puram, _ = _selected_text(
                    analysis.akam_puram,
                    target_language,
                    getattr(analysis, "akam_puram_ta", ""),
                    keep_tamil_note=False,
                )
                period_parts.append(akam_puram)
            if period_parts:
                st.markdown(_box(_ui("Period", target_language), html.escape(" - ".join(period_parts))), unsafe_allow_html=True)

    st.divider()

    c1, c2, c3 = st.columns(3)
    with c1:
        thinai_ta = THINAI_TAMIL.get(analysis.thinai, "")
        thinai_name = _local_analysis_translation(analysis.thinai.value, target_language)
        if target_language == "ta":
            thinai_badge = thinai_ta or analysis.thinai.value
        elif target_language == "en":
            thinai_badge = f"{analysis.thinai.value} - {thinai_ta}" if thinai_ta else analysis.thinai.value
        else:
            thinai_badge = thinai_name
        thinai_meaning = str(display.get("thinai_meaning") or THINAI_MEANING.get(analysis.thinai, ""))
        st.markdown(
            f"**{_ui('Thinai', target_language)}:**<br>"
            f"<span class='thinai-badge'>{html.escape(thinai_badge)}</span><br>"
            f"<small style='color:var(--sangam-muted)'>{html.escape(thinai_meaning)}</small>",
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(_box(_ui("Emotion", target_language), html.escape(str(display.get("emotion", "")))), unsafe_allow_html=True)
    with c3:
        st.markdown(_box(_ui("Mood", target_language), html.escape(str(display.get("mood", "")))), unsafe_allow_html=True)

    st.divider()

    if analysis.thurai or analysis.speaker or analysis.listener:
        c1, c2, c3 = st.columns(3)
        with c1:
            if analysis.thurai:
                st.markdown(_display_box("Thurai", analysis.thurai, target_language, analysis.thurai_tamil), unsafe_allow_html=True)
        with c2:
            if analysis.speaker:
                st.markdown(_display_box("Speaker", analysis.speaker, target_language), unsafe_allow_html=True)
        with c3:
            if analysis.listener:
                st.markdown(_display_box("Listener", analysis.listener, target_language), unsafe_allow_html=True)

    if display.get("summary"):
        st.markdown(
            f'<div class="analysis-card"><strong>{_ui("Summary", target_language)}</strong><br>{html.escape(str(display["summary"]))}</div>',
            unsafe_allow_html=True,
        )

    if target_language not in ("en", "ta"):
        learner_note = _learning_translated_text(
            language_engine.learning_bridge_text(analysis, target_language),
            target_language,
        )
        st.markdown(
            f'<div class="analysis-card"><strong>{language_engine.language_label(target_language)} {_ui("Learner Guide", target_language)}</strong><br>{html.escape(learner_note)}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(f"### {detail_labels['Sangam Poetics']}")
    p1, p2, p3 = st.columns(3)

    with p1:
        st.markdown(f"**{detail_labels['Muthal Porul']}**")
        st.caption(detail_labels["Time and Place"])
        if analysis.muthal_porul:
            mp = analysis.muthal_porul
            for label, key, value, tamil in (
                ("Landscape", "muthal_landscape", mp.landscape, mp.landscape_tamil),
                ("Season", "muthal_season", mp.season, mp.season_tamil),
                ("Time", "muthal_time", mp.time, mp.time_tamil),
            ):
                if value:
                    selected = detail_text.get(key)
                    note = tamil if target_language == "en" and tamil else ""
                    if not selected:
                        selected, note = _selected_text(value, target_language, tamil)
                    st.markdown(f"**{detail_labels[label]}:** {selected}" + (f" - {note}" if note else ""))

    with p2:
        st.markdown(f"**{detail_labels['Karu Porul']}**")
        st.caption(detail_labels["Flora, Fauna and Objects"])
        for index, original_item in enumerate(analysis.karu_porul or []):
            item = detail_text.get(f"karu::{index}", original_item)
            st.markdown(f"- {item}")

    with p3:
        st.markdown(f"**{detail_labels['Uri Porul']}**")
        st.caption(detail_labels["Central Emotion or Action"])
        if display.get("uri_porul"):
            st.info(str(display.get("uri_porul", "")))
        if display.get("meyppadu"):
            st.markdown(f"**{detail_labels['Meyppadu']}:** {display.get('meyppadu')}")

    st.divider()

    if display.get("cultural_context"):
        st.markdown(
            f'<div class="analysis-card"><strong>{detail_labels["Cultural Context"]}</strong><br>{html.escape(str(display["cultural_context"]))}</div>',
            unsafe_allow_html=True,
        )

    if display.get("literary_devices"):
        st.markdown(
            f'<div class="analysis-card"><strong>{detail_labels["Literary Devices"]}</strong><br>{html.escape(str(display["literary_devices"]))}</div>',
            unsafe_allow_html=True,
        )

    if analysis.grammar_notes:
        st.markdown(f"### {detail_labels['Grammar Notes']}")
        for index, note in enumerate(analysis.grammar_notes):
            translated_term = detail_text.get(
                f"grammar_term::{index}",
                _local_analysis_translation(note.term, target_language),
            )
            if target_language in ("en", "ta") and note.term_tamil:
                term = translated_term + f" - {note.term_tamil}"
            else:
                term = translated_term
            definition = detail_text.get(f"grammar_definition::{index}", note.definition)
            example = detail_text.get(f"grammar_example::{index}", note.example)
            st.markdown(
                f'<div class="character-entry"><strong>{html.escape(term)}</strong><br>'
                f'<span style="color:var(--sangam-ink)">{html.escape(definition)}</span><br>'
                f'<span style="color:var(--sangam-muted)"><em>{detail_labels["In this poem"]}: {html.escape(example)}</em></span></div>',
                unsafe_allow_html=True,
            )

    if analysis.word_meanings:
        st.markdown(f"### {detail_labels['Word Meanings']}")
        for index, word in enumerate(analysis.word_meanings.keys()):
            meaning = detail_text.get(f"word_meaning::{index}", str(analysis.word_meanings[word]))
            st.markdown(f'<div class="word-entry"><span class="word-ta">{html.escape(word)}</span><span class="word-en">{html.escape(meaning)}</span></div>', unsafe_allow_html=True)

    if analysis.characters:
        st.markdown(f"### {detail_labels['Characters']}")
        for index, char in enumerate(analysis.characters):
            translated_name = detail_text.get(f"character_name::{index}", char.name)
            name = translated_name + (f" - {char.name_tamil}" if target_language in ("en", "ta") and char.name_tamil else "")
            role = detail_text.get(f"character_role::{index}", char.role)
            if char.role_tamil and target_language == "ta":
                role = char.role_tamil
            if char.role_tamil and target_language == "en":
                role = f"{role} - {char.role_tamil}"
            description = detail_text.get(f"character_description::{index}", char.description)
            st.markdown(
                f'<div class="character-entry"><strong>{html.escape(name)}</strong> - <em>{html.escape(role)}</em><br>'
                f'<span style="color:var(--sangam-muted)">{html.escape(description)}</span></div>',
                unsafe_allow_html=True,
            )

    if analysis.meaning_breakdown:
        st.markdown(f"### {detail_labels['Meaning Breakdown']}")
        for index, entry in enumerate(analysis.meaning_breakdown):
            device_text = detail_text.get(f"meaning_device::{index}", entry.literary_device)
            device = f' <span style="color:var(--sangam-muted);font-size:0.85rem">[{html.escape(device_text)}]</span>' if device_text else ""
            translation = detail_text.get(f"meaning_translation::{index}", entry.translation)
            interpretation = detail_text.get(f"meaning_interpretation::{index}", entry.interpretation)
            st.markdown(
                f'<div class="meaning-entry"><div class="meaning-original">"{html.escape(entry.original)}"{device}</div>'
                f'<div class="meaning-translation">- {html.escape(translation)}</div>'
                f'<div class="meaning-interpretation">* {html.escape(interpretation)}</div></div>',
                unsafe_allow_html=True,
            )


def display_scenes(
    scenes: list[SceneFrame],
    images: list,
    analysis: PoemAnalysis
):
    st.markdown("## 🎬 Scene Breakdown")
    image_map = {img.scene_id: img for img in images} if images else {}

    for scene in scenes:
        with st.expander(f"Scene {scene.scene_id}: {scene.title or scene.description[:50]}...", expanded=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                st.markdown(f'<div class="scene-header">Scene {scene.scene_id} · {scene.mood.value.capitalize()}</div>', unsafe_allow_html=True)
                st.write(scene.description)
                with st.expander("🔍 Advanced Details", expanded=False):
                    st.markdown(f"🌿 Environment: {scene.environment}")
                    st.markdown(f"☀️ Lighting: {scene.lighting}")
                    st.markdown(f"🎨 Palette: {scene.color_palette}")

                    if scene.characters:
                        st.markdown(
                            f"👤 Characters: {', '.join(scene.characters)}"
                        )

                    st.code(scene.visual_prompt)
            with c2:
                img = image_map.get(scene.scene_id)
                image_path = None

                if img and img.success and img.image_path and Path(img.image_path).exists():
                    if getattr(img, "backend", "") == "placeholder":
                        image_path = get_cached_scene_image(scene, analysis) or img.image_path
                    else:
                        image_path = img.image_path

                if not image_path or not Path(image_path).exists():
                    image_path = get_cached_scene_image(scene, analysis)

                if image_path and Path(image_path).exists():
                    try:
                        st.image(
                            image_path,
                            use_container_width=True,
                            caption=f"Scene {scene.scene_id} · {Path(image_path).name}"
                        )
                    except Exception:
                        st.info("Image unavailable.")
                else:
                    st.markdown(
                            '''
                            <div style="
                                background:var(--sangam-panel);
                                border:1px dashed var(--sangam-border);
                                border-radius:8px;
                                padding:3rem;
                                text-align:center;
                                color:var(--sangam-muted);
                            ">
                                🖼️<br>
                                Illustration unavailable
                            </div>
                            ''',
                            unsafe_allow_html=True
                        )

# ── DISPLAY: NARRATION ───────────────────────────────────────────────────────

def display_scenes(
    scenes: list[SceneFrame],
    images: list,
    analysis: PoemAnalysis
):
    target_language = _target_language()
    scene_label = _ui("Scene", target_language)

    st.markdown(f"## {_ui('Scene Breakdown', target_language)}")
    image_map = {img.scene_id: img for img in images} if images else {}

    scene_payload = {}
    for index, scene in enumerate(scenes):
        if scene.title:
            scene_payload[f"title{index}"] = scene.title
        if scene.description:
            scene_payload[f"description{index}"] = scene.description
        if scene.environment:
            scene_payload[f"environment{index}"] = scene.environment
        if scene.lighting:
            scene_payload[f"lighting{index}"] = scene.lighting
        if scene.color_palette:
            scene_payload[f"palette{index}"] = scene.color_palette
        if scene.characters:
            scene_payload[f"characters{index}"] = ", ".join(scene.characters)
    translated_scenes = _translated_mapping(scene_payload, target_language)

    for index, scene in enumerate(scenes):
        caption, tamil_caption = language_engine.scene_caption_text(scene, analysis, target_language)
        title = translated_scenes.get(f"title{index}", scene.title or "")
        description = translated_scenes.get(f"description{index}", scene.description or "")
        expander_title = title or caption or description[:50] or f"{scene_label} {scene.scene_id}"

        with st.expander(f"{scene_label} {scene.scene_id}: {expander_title}...", expanded=True):
            c1, c2 = st.columns([3, 2])
            with c1:
                mood_text = _translated_text(scene.mood.value.capitalize(), target_language)
                st.markdown(
                    f'<div class="scene-header">{scene_label} {scene.scene_id} - {html.escape(mood_text)}</div>',
                    unsafe_allow_html=True,
                )
                if caption:
                    st.write(caption)
                if target_language != "ta" and tamil_caption:
                    st.caption(tamil_caption)
                elif description and description != caption:
                    st.write(description)

                with st.expander(_ui("Advanced Details", target_language), expanded=False):
                    environment = translated_scenes.get(f"environment{index}", scene.environment or "")
                    lighting = translated_scenes.get(f"lighting{index}", scene.lighting or "")
                    palette = translated_scenes.get(f"palette{index}", scene.color_palette or "")
                    characters = translated_scenes.get(f"characters{index}", ", ".join(scene.characters or []))

                    if environment:
                        st.markdown(f"**{_ui('Environment', target_language)}:** {environment}")
                    if lighting:
                        st.markdown(f"**{_ui('Lighting', target_language)}:** {lighting}")
                    if palette:
                        st.markdown(f"**{_ui('Palette', target_language)}:** {palette}")
                    if characters:
                        st.markdown(f"**{_ui('Characters', target_language)}:** {characters}")

                    prompt_label = _ui("Visual Prompt", target_language)
                    st.markdown(f"**{prompt_label}:**")
                    translated_prompt = _translated_text(scene.visual_prompt, target_language)
                    st.code(translated_prompt)

            with c2:
                img = image_map.get(scene.scene_id)
                image_path = None

                if img and img.success and img.image_path and Path(img.image_path).exists():
                    if getattr(img, "backend", "") == "placeholder":
                        image_path = get_cached_scene_image(scene, analysis) or img.image_path
                    else:
                        image_path = img.image_path

                if not image_path or not Path(image_path).exists():
                    image_path = get_cached_scene_image(scene, analysis)

                if image_path and Path(image_path).exists():
                    try:
                        st.image(
                            image_path,
                            use_container_width=True,
                            caption=f"{scene_label} {scene.scene_id} - {Path(image_path).name}",
                        )
                    except Exception:
                        st.info(_ui("Image unavailable", target_language))
                else:
                    st.markdown(
                        f'''
                        <div style="
                            background:var(--sangam-panel);
                            border:1px dashed var(--sangam-border);
                            border-radius:8px;
                            padding:3rem;
                            text-align:center;
                            color:var(--sangam-muted);
                        ">
                            {html.escape(_ui("Illustration unavailable", target_language))}
                        </div>
                        ''',
                        unsafe_allow_html=True,
                    )


def display_narration(narration):
    st.markdown("## 🔊 Sangam Voice")
    if narration and narration.success and narration.audio_path:
        try:
            audio_path = Path(narration.audio_path)
            if audio_path.exists():
                with open(audio_path, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
            else:
                st.info("Narration audio is being prepared for this poem.")
        except Exception:
            st.info("Narration audio could not be played here, but the analysis remains available.")
    elif narration and not narration.success:
        st.markdown(
            '<div class="error-card">🔇 Narration is unavailable for this run.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("Enable narration in the sidebar to hear the poem.")


# ── DISPLAY: VIDEO EXPERIENCE ────────────────────────────────────────────────

def display_narration(narration):
    target_language = _target_language()
    st.markdown(f"## {_ui('Sangam Voice', target_language)}")
    if narration and narration.success and narration.audio_path:
        try:
            audio_path = Path(narration.audio_path)
            if audio_path.exists():
                with open(audio_path, "rb") as f:
                    st.audio(f.read(), format="audio/mp3")
            else:
                st.info(_ui("Narration audio is being prepared for this poem.", target_language))
        except Exception:
            st.info(_ui("Narration audio could not be played here, but the analysis remains available.", target_language))
    elif narration and not narration.success:
        st.markdown(
            f'<div class="error-card">{html.escape(_ui("Narration is unavailable for this run.", target_language))}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info(_ui("Enable narration in the sidebar to hear the poem.", target_language))


def _status_badge(status: VideoStatus) -> str:
    label = status.value.upper()
    css   = f"status-{status.value}"
    return f'<span class="video-status-badge {css}">{label}</span>'


def _asset_pill(label: str, ready: bool) -> str:
    cls = "ready" if ready else "missing"
    icon = "✓" if ready else "✗"
    return f'<span class="asset-pill {cls}">{icon} {label}</span>'


def display_video_experience(result: PipelineResult):
    """
    Renders the 🎥 Sangam Experience tab.

    States handled:
      1. Video disabled in sidebar   → prompt to enable
      2. video_engine not available  → show skeleton + instructions
      3. Video failed                → show error card
      4. Video complete              → play video + subtitles + downloads
      5. Video pending/composing     → show progress info
    """
    st.markdown(
        '<div class="video-header">🎥 Sangam Experience · சங்க அனுபவம்</div>'
        '<div class="video-subheader">All scenes · narration · subtitles — woven into one cinematic poem</div>',
        unsafe_allow_html=True,
    )

    # ── State 1: disabled ────────────────────────────────────────────────────
    if result.video is None:
        st.markdown("""
        <div style='text-align:center;padding:3rem 2rem;background:var(--sangam-panel);
        border:1px dashed var(--sangam-border);border-radius:10px;'>
            <div style='font-size:3rem;margin-bottom:1rem;'>🎥</div>
            <div style='font-family:"Playfair Display",serif;color:var(--sangam-ink);font-size:1.2rem;margin-bottom:0.5rem;'>
                Experience not generated
            </div>
            <div style='color:var(--sangam-muted);font-size:0.95rem;max-width:420px;margin:0 auto;'>
                Enable <strong style='color:var(--sangam-ink)'>Generate Experience video</strong>,
                <strong style='color:var(--sangam-ink)'>Generate scene images</strong>, and
                <strong style='color:var(--sangam-ink)'>Generate voice narration</strong>
                in the sidebar, then re-analyze the poem.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    exp = result.video

    # ── Header row: title + status badge ─────────────────────────────────────
    h_col, s_col = st.columns([4, 1])
    with h_col:
        title = exp.poem_title_en or "Sangam Poem"
        thinai_ta = THINAI_TAMIL.get(exp.thinai, "")
        st.markdown(
            f"**{title}** &nbsp;·&nbsp; "
            f"<span class='thinai-badge'>{exp.thinai.value} · {thinai_ta}</span>",
            unsafe_allow_html=True,
        )
    with s_col:
        st.markdown(_status_badge(exp.status), unsafe_allow_html=True)

    # Asset availability pills
    images_ready  = any(t.image_path and Path(t.image_path).exists() for t in exp.tracks)
    audio_ready   = bool(exp.audio_path) and Path(exp.audio_path).exists()
    subs_ready    = len(exp.subtitles) > 0
    video_ready   = exp.exists_on_disk()

    st.markdown(
        '<div class="video-asset-row">'
        + _asset_pill(f"{len(exp.tracks)} scenes", images_ready)
        + _asset_pill("narration audio", audio_ready)
        + _asset_pill("subtitles", subs_ready)
        + _asset_pill("video file", video_ready)
        + "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── State 3: failed ───────────────────────────────────────────────────────
    if exp.status == VideoStatus.FAILED or not exp.success:
        st.markdown("""
        <div style="
            background:var(--sangam-panel);
            border:1px solid var(--sangam-border);
            border-radius:12px;
            padding:2rem;
            text-align:center;
            color:var(--sangam-muted);
            margin-top:1rem;
        ">
            <div style="font-size:2rem;">🎞️</div>
            <h3>Experience Unavailable</h3>
            <p>
                Scene images could not be assembled into a video for this poem.
            </p>
            <small>
                Analysis, scenes, and narration remain fully available.
            </small>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── State 4: complete — play video ───────────────────────────────────────
    if exp.status == VideoStatus.COMPLETE and video_ready:
        vid_col = st.container()

        with vid_col:
            st.markdown("### ▶ Play")
            with open(exp.video_path, "rb") as vf:
                st.video(vf.read())

            # Thinai color palette swatch
            palette = THINAI_COLOR_PALETTE.get(exp.thinai, [])
            if palette:
                swatches = "".join(
                    f'<span style="display:inline-block;width:24px;height:24px;'
                    f'border-radius:4px;background:{c};margin-right:4px;"></span>'
                    for c in palette
                )
                st.markdown(
                    f'<div style="margin-top:0.5rem;">'
                    f'<small style="color:var(--sangam-muted)">Thinai palette &nbsp;</small>{swatches}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Video metadata
            meta_cols = st.columns(4)
            meta_cols[0].metric("Scenes",      len(exp.tracks))
            meta_cols[1].metric("Duration",    f"{exp.total_duration:.0f}s")
            meta_cols[2].metric("Resolution",  exp.resolution)
            meta_cols[3].metric("Render time", f"{exp.render_time_sec:.1f}s")

        st.caption("Selected-language subtitles are rendered into the video. Subtitle files remain available below.")
        with st.expander("Subtitle files and cue preview", expanded=False):
            _render_subtitles_panel(exp)

        st.divider()
        _render_download_row(exp)
        _render_video_scene_strip(exp, result)
        return

    # ── State 2 / 5: skeleton or in-progress ─────────────────────────────────
    if not _VIDEO_ENGINE_AVAILABLE:
        st.info(
            "**video_engine.py not found.** "
            "The VideoExperience skeleton is built — implement `video_engine.compose()` "
            "to enable ffmpeg rendering. See `schemas.VideoExperience` for the full spec."
        )
    else:
        st.info(f"Video status: **{exp.status.value}** — {exp.progress_summary()}")

    # Show scene strip even without a rendered video
    _render_video_scene_strip(exp, result)

    # Show timeline even without a rendered video
    if exp.tracks:
        st.markdown("### 🎞 Track Timeline")
        for track in exp.tracks:
            scene_title = track.overlay_text or f"Scene {track.scene_id}"
            bar_width   = max(int((track.duration_seconds / max(exp.total_duration, 1)) * 100), 4)
            st.markdown(
                f'<div class="track-card">'
                f'<div class="track-scene-num">{track.scene_id}</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:0.9rem;color:var(--sangam-dark);margin-bottom:0.3rem;">{scene_title}</div>'
                f'<div style="background:var(--sangam-border);border-radius:4px;height:8px;width:100%;">'
                f'<div style="background:var(--sangam-gold);border-radius:4px;height:8px;width:{bar_width}%;"></div>'
                f'</div>'
                f'<div style="font-size:0.78rem;color:var(--sangam-muted);margin-top:0.2rem;">'
                f'{track.start_seconds:.1f}s → {track.end_seconds:.1f}s &nbsp;·&nbsp; '
                f'{track.transition} &nbsp;·&nbsp; '
                f'{"Ken Burns ✓" if track.ken_burns else "static"}'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )

    # SRT preview even without rendered video
    if exp.subtitles:
        _render_subtitles_panel(exp)


def _render_subtitles_panel(exp: VideoExperience):
    """Subtitle viewer with SRT / VTT export tabs."""
    st.markdown("### 📝 Subtitles · வசனங்கள்")

    if not exp.subtitles:
        st.caption("No subtitle cues yet.")
        return

    view_tab, srt_tab, vtt_tab = st.tabs(["👁 Preview", "📄 SRT", "🌐 VTT"])

    with view_tab:
        for cue in exp.subtitles:
            def fmt_ts(s: float) -> str:
                m, sec = divmod(int(s), 60)
                return f"{m:02d}:{sec:02d}.{int((s % 1) * 10)}"

            lines = []
            if cue.text_en: lines.append(f'<div class="subtitle-en">{cue.text_en}</div>')
            if cue.text_ta: lines.append(f'<div class="subtitle-ta">{cue.text_ta}</div>')
            speaker_badge = (
                f'<span style="color:var(--sangam-muted);font-size:0.78rem;">{cue.speaker}</span> &nbsp;'
                if cue.speaker else ""
            )
            st.markdown(
                f'<div class="subtitle-cue">'
                f'<div class="subtitle-time">{speaker_badge}'
                f'{fmt_ts(cue.start_seconds)} → {fmt_ts(cue.end_seconds)}</div>'
                + "".join(lines)
                + "</div>",
                unsafe_allow_html=True,
            )

    with srt_tab:
        srt_content = exp.export_srt()
        st.text_area("SRT content", srt_content, height=300, label_visibility="collapsed")

    with vtt_tab:
        vtt_content = exp.export_vtt()
        st.text_area("VTT content", vtt_content, height=300, label_visibility="collapsed")


def _render_download_row(exp: VideoExperience):
    """Download buttons for video + subtitle files."""
    st.markdown("### ⬇ Downloads")
    dl_cols = st.columns(4)

    with dl_cols[0]:
        if exp.exists_on_disk():
            with open(exp.video_path, "rb") as vf:
                st.download_button(
                    "🎥 Video (.mp4)",
                    data=vf.read(),
                    file_name=Path(exp.video_path).name,
                    mime="video/mp4",
                    use_container_width=True,
                )

    with dl_cols[1]:
        if exp.subtitle_path_srt and Path(exp.subtitle_path_srt).exists():
            with open(exp.subtitle_path_srt, "rb") as sf:
                st.download_button(
                    "📄 Subtitles (.srt)",
                    data=sf.read(),
                    file_name=Path(exp.subtitle_path_srt).name,
                    mime="text/plain",
                    use_container_width=True,
                )
        elif exp.subtitles:
            st.download_button(
                "📄 Subtitles (.srt)",
                data=exp.export_srt().encode("utf-8"),
                file_name=f"poem_{exp.poem_id}.srt",
                mime="text/plain",
                use_container_width=True,
            )

    with dl_cols[2]:
        if exp.subtitle_path_vtt and Path(exp.subtitle_path_vtt).exists():
            with open(exp.subtitle_path_vtt, "rb") as vf:
                st.download_button(
                    "🌐 Subtitles (.vtt)",
                    data=vf.read(),
                    file_name=Path(exp.subtitle_path_vtt).name,
                    mime="text/vtt",
                    use_container_width=True,
                )
        elif exp.subtitles:
            st.download_button(
                "🌐 Subtitles (.vtt)",
                data=exp.export_vtt().encode("utf-8"),
                file_name=f"poem_{exp.poem_id}.vtt",
                mime="text/vtt",
                use_container_width=True,
            )

    with dl_cols[3]:
        if exp.thumbnail_path and Path(exp.thumbnail_path).exists():
            with open(exp.thumbnail_path, "rb") as tf:
                st.download_button(
                    "🖼 Thumbnail",
                    data=tf.read(),
                    file_name=Path(exp.thumbnail_path).name,
                    mime="image/jpeg",
                    use_container_width=True,
                )


def _render_video_scene_strip(exp: VideoExperience, result: PipelineResult):
    """
    Horizontal filmstrip of scene thumbnails with track timing labels.
    Shown regardless of whether the video is rendered.
    """
    if not exp.tracks:
        return

    st.markdown("### 🎞 Scene Strip")
    image_map = {img.scene_id: img for img in result.images} if result.images else {}
    scene_map = {s.scene_id: s for s in result.scenes} if result.scenes else {}

    cols = st.columns(len(exp.tracks))
    for col, track in zip(cols, exp.tracks):
        with col:
            # Resolve image: prefer track path → generated image → cached fallback
            img_path = None
            if track.image_path and Path(track.image_path).exists():
                img_path = track.image_path
            else:
                gen_img = image_map.get(track.scene_id)
                if gen_img and gen_img.success and gen_img.image_path and Path(gen_img.image_path).exists():
                    img_path = gen_img.image_path
                else:
                    scene = scene_map.get(track.scene_id)
                    if scene:
                        img_path = get_cached_scene_image(scene, result.analysis)

            if img_path and Path(img_path).exists():
                st.image(img_path, use_container_width=True)
            else:
                st.markdown(
                    '<div style="background:var(--sangam-panel);border:1px dashed var(--sangam-border);'
                    'border-radius:6px;padding:1.5rem;text-align:center;'
                    'color:var(--sangam-muted);font-size:0.8rem;">🖼️</div>',
                    unsafe_allow_html=True,
                )

            label = track.overlay_text or f"Scene {track.scene_id}"
            st.caption(f"{label}\n{track.start_seconds:.0f}s–{track.end_seconds:.0f}s")


# ── DISPLAY: CHATBOT ─────────────────────────────────────────────────────────

def display_chatbot(analysis: PoemAnalysis | None):
    st.markdown("## 🗣️ Ask Pulavar")
    st.caption("Ask the ancient scholar anything about Sangam poetry, culture, or this poem.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input("Ask Pulavar a question...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Pulavar reflects..."):
                response = ask_pulavar_chat(
                    user_input,
                    analysis=analysis,
                    target_language=st.session_state.get("target_language", "en"),
                )
            st.write(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})


# ── SIDEBAR ──────────────────────────────────────────────────────────────────

def display_chatbot(analysis: PoemAnalysis | None):
    target_language = _target_language()
    st.markdown(f"## {_ui('Ask Pulavar', target_language)}")
    st.caption(_ui("Ask the ancient scholar anything about Sangam poetry, culture, or this poem.", target_language))

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_input = st.chat_input(_ui("Ask Pulavar a question...", target_language))
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            with st.spinner(_ui("Pulavar reflects...", target_language)):
                response = ask_pulavar_chat(
                    user_input,
                    analysis=analysis,
                    target_language=target_language,
                )
            st.write(response)
        st.session_state.chat_history.append({"role": "assistant", "content": response})


def render_sidebar():
    with st.sidebar:
        st.markdown(
            "<div class='sidebar-title'>Living Sangam World<br><small>AI-Powered Immersive Tamil Poetry Experience</small></div>",
            unsafe_allow_html=True,
        )
        st.markdown("")

        poem_source = st.radio(
            "Poem source",
            ["✍️ Type / Paste", "📚 Library", "📷 Camera / Image"],
            index=1,
            horizontal=False,
        )

        poem_text = ""
        poem_id   = 0   # track selected poem id for output file naming

        # ── MODE 1: Type / Paste ─────────────────────────────
        if poem_source == "✍️ Type / Paste":
            poem_text = st.text_area(
                "Enter Sangam poem", height=200,
                placeholder="Paste Tamil or English poem here...",
            )

        # ── MODE 2: Library ──────────────────────────────────
        elif poem_source == "📚 Library":
            poems = load_poems()
            if poems:
                titles = [f"{p.id}. {p.title_en} · {p.title_ta} ({p.thinai.value})" for p in poems]
                idx = st.selectbox("Select a poem", range(len(poems)), format_func=lambda i: titles[i])
                p = poems[idx]
                poem_text = p.poem_en
                poem_id   = p.id

                show_tamil = st.toggle("Show Tamil version", value=False)
                display_poem = p.poem_ta if (show_tamil and p.poem_ta) else p.poem_en
                st.markdown(f'<div class="poem-card">{display_poem.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)

                meta = []
                if p.author_ta:    meta.append(f"✍️ {p.author} · {p.author_ta}")
                if p.collection_ta: meta.append(f"📚 {p.collection} · {p.collection_ta}")
                if meta: st.caption(" | ".join(meta))

                with st.expander("📐 Poetic Structure"):
                    if p.thurai:   st.markdown(f"**துறை / Thurai:** {p.thurai}")
                    if p.speaker:  st.markdown(f"**Speaker:** {p.speaker}  |  **Listener:** {p.listener}")
                    if p.muthal_porul:
                        mp = p.muthal_porul
                        st.markdown(f"**முதல்:** {mp.landscape}, {mp.season}, {mp.time}")
                    if p.karu_porul: st.markdown(f"**கரு:** {', '.join(p.karu_porul[:3])}")
                    if p.uri_porul:  st.markdown(f"**உரி:** {p.uri_porul}")
                    if p.meyppadu:   st.markdown(f"**மெய்ப்பாடு:** {p.meyppadu}")

                if p.word_meanings:
                    with st.expander("🔤 Word Meanings"):
                        for word, meaning in p.word_meanings.items():
                            st.markdown(f"**{word}** — {meaning}")
            else:
                st.warning("No poems found in poems.json")

        # ── MODE 3: Camera / Image OCR ───────────────────────
        elif poem_source == "📷 Camera / Image":
            st.markdown(
                "<small style='color:var(--sangam-muted)'>Take a photo of a poem — from a book, "
                "manuscript, or handwritten note — and we'll read the text for you.</small>",
                unsafe_allow_html=True
            )
            st.markdown("")

            camera_image = st.camera_input("📸 Take a photo")
            st.markdown("<div style='text-align:center;color:var(--sangam-muted);font-size:0.85rem'>— or —</div>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "📁 Upload an image", type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed"
            )

            image_source = camera_image or uploaded_file

            if image_source is not None:
                st.image(image_source, caption="Image to scan", use_container_width=True)

                if st.button("🔍 Extract Poem Text", use_container_width=True):
                    with st.spinner("📖 Reading the image with Gemini Vision..."):
                        try:
                            img_bytes, mime_type = ocr_engine.image_bytes_from_upload(image_source)
                            extracted, lang = ocr_engine.extract_text_from_image(img_bytes, mime_type)
                            if extracted.strip():
                                st.session_state["ocr_text"] = extracted
                                st.session_state["ocr_lang"] = lang
                                st.session_state["ocr_source"] = "camera" if camera_image else "upload"
                                st.success(f"✅ Text extracted! ({lang.capitalize()} detected)")
                            else:
                                st.warning("No text found. Try a clearer photo.")
                        except Exception as exc:
                            reason = str(exc) or exc.__class__.__name__
                            if "GEMINI_API_KEY" in reason or "GOOGLE_API_KEY" in reason:
                                st.error("OCR is not configured yet. Add GEMINI_API_KEY to your .env file or install local Tesseract OCR, then restart the app.")
                            elif "empty" in reason.lower() or "readable image" in reason.lower():
                                st.error("OCR could not read this image file. Try uploading a JPG/PNG photo again.")
                            elif "tesseract" in reason.lower() or "language data" in reason.lower():
                                st.error("OCR needs one working reader. Gemini failed, and local Tesseract OCR is not fully installed.")
                                st.caption(f"OCR detail: {reason[:320]}")
                            elif "did not extract readable text" in reason.lower() or "returned no text" in reason.lower():
                                st.error("OCR ran, but it did not find readable poem text in this image.")
                                st.caption(f"OCR detail: {reason[:320]}")
                            elif "quota" in reason.lower() or "overloaded" in reason.lower() or "unavailable" in reason.lower():
                                st.error("OCR is temporarily unavailable. Gemini is busy or out of quota.")
                                st.caption(f"OCR detail: {reason[:320]}")
                            else:
                                st.error("OCR failed before text could be extracted.")
                                if "All OCR models failed" in reason:
                                    st.caption("OCR detail: Gemini OCR models were unavailable or overloaded. Try again shortly.")
                                else:
                                    st.caption(f"OCR detail: {reason[:240]}")

            if st.session_state.get("ocr_text"):
                lang = st.session_state.get("ocr_lang", "unknown")
                lang_label = {"tamil": "🇮🇳 Tamil", "english": "🇬🇧 English", "mixed": "🌐 Tamil + English"}.get(lang, "")
                st.markdown(f"**Extracted text** {lang_label}")
                edited = st.text_area(
                    "Edit if needed",
                    value=st.session_state["ocr_text"],
                    height=180, label_visibility="collapsed",
                )
                poem_text = edited
                if st.button("🗑️ Clear", use_container_width=False):
                    for key in ["ocr_text", "ocr_lang", "ocr_source"]:
                        st.session_state.pop(key, None)
                    st.rerun()
            else:
                st.markdown(
                    "<div style='background:var(--sangam-panel);border:1px dashed var(--sangam-border);border-radius:8px;"
                    "padding:1.5rem;text-align:center;color:var(--sangam-muted);margin-top:0.5rem;'>"
                    "📷 Take or upload a photo above<br>"
                    "<small>Works with books, screens, or handwritten poems</small></div>",
                    unsafe_allow_html=True
                )

        # ── Options & Run ────────────────────────────────────
        st.divider()
        st.markdown("### ⚙️ Options")
        demo_mode = st.toggle(
            "Demo judging mode",
            value=True,
            help="Uses curated library analysis, cached scene images, and bundled narration for a reliable live demo.",
        )
        st.markdown("### Learning")
        language_options = language_engine.language_choices()
        target_language = st.selectbox(
            "Narration and subtitle language",
            options=[code for code, _ in language_options],
            index=1,
            format_func=language_engine.language_label,
            help="Tamil terms stay visible; narration and learner captions follow this language.",
        )
        include_images = st.toggle("Generate scene images",    value=True)
        include_audio  = st.toggle("Generate voice narration", value=demo_mode)

        # Video toggle — only shown when both images and audio can be active
        include_video  = st.toggle(
            "Generate Experience video 🎥",
            value=False,
            help=(
                "Composes all scene images + narration + subtitles into a single .mp4 per poem. "
                "Requires scene images AND voice narration to be enabled. "
                "Uses ffmpeg via video_engine.py."
            ),
        )

        if include_video and not include_images:
            st.caption("⚠️ Scene images must be enabled for video.")
        if include_video and not include_audio:
            st.caption("⚠️ Voice narration must be enabled for video.")

        st.divider()
        run_btn = st.button("✦ Analyze Poem", use_container_width=True)
        st.caption("Living Sangam World: AI-Powered Immersive Tamil Poetry Experience")

    return poem_text, poem_id, include_images, include_audio, include_video, demo_mode, target_language, run_btn


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    st.markdown("""
        <h1 style='text-align:center;font-size:2.6rem;letter-spacing:0;
        color:var(--sangam-gold-soft);padding:1rem 0 0.2rem;'>
            Living Sangam World
        </h1>
        <p style='text-align:center;color:var(--sangam-muted);font-family:"Playfair Display",serif;
        font-size:1rem;letter-spacing:0.35em;margin-bottom:2rem;text-transform:uppercase;'>
            AI-Powered Immersive Tamil Poetry Experience
        </p>
    """, unsafe_allow_html=True)

    if _api_key_missing:
        st.error("⚠️ **GEMINI_API_KEY not found.** Add it to your `.env` file.")

    poem_text, poem_id, include_images, include_audio, include_video, demo_mode, target_language, run_btn = render_sidebar()
    st.session_state["target_language"] = target_language

    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None

    if run_btn:
        if not poem_text or not poem_text.strip():
            st.error(_ui("Please enter a poem to analyze.", target_language))
        else:
            result = run_pipeline(
                poem_text.strip(),
                include_images,
                include_audio,
                include_video,
                poem_id=poem_id,
                demo_mode=demo_mode,
                target_language=target_language,
            )
            # Tag the analysis with OCR source if it came from camera/image
            if st.session_state.get("ocr_source"):
                result.analysis.ocr_source   = st.session_state["ocr_source"]
                result.analysis.ocr_language = st.session_state.get("ocr_lang", "")
            st.session_state.pipeline_result = result

    result = st.session_state.pipeline_result

    if result is None:
        st.markdown("""
        <div style='text-align:center;padding:4rem 2rem;'>
            <div style='font-size:4rem;margin-bottom:1rem;'>🌿</div>
            <div style='font-family:"Playfair Display",serif;font-size:1.4rem;color:var(--sangam-ink);margin-bottom:1rem;'>
                Enter a Sangam poem to begin
            </div>
            <div style='font-size:1rem;color:var(--sangam-muted);max-width:500px;margin:0 auto;font-style:italic;'>
                "As the kurinji flower blooms on the mountain slopes,<br>
                so does the meaning of ancient verse unfold<br>
                to those who look deeply."
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📜 Analysis",
        "🎬 Scenes",
        "🔊 Voice",
        "🎥 Experience",
        "🗣️ Ask Pulavar",
    ])
    with tab1:
        render_stage_notices(result, "analysis")
        display_analysis(result.analysis)
    with tab2:
        render_stage_notices(result, "scenes")
        display_scenes(result.scenes, result.images, result.analysis)
    with tab3:
        render_stage_notices(result, "voice")
        display_narration(result.narration)
    with tab4:
        render_stage_notices(result, "video")
        display_video_experience(result)
    with tab5: display_chatbot(result.analysis)


def main():
    st.markdown("""
        <h1 style='text-align:center;font-size:2.6rem;letter-spacing:0;
        color:var(--sangam-gold-soft);padding:1rem 0 0.2rem;'>
            Living Sangam World
        </h1>
        <p style='text-align:center;color:var(--sangam-muted);font-family:"Playfair Display",serif;
        font-size:1rem;letter-spacing:0.35em;margin-bottom:2rem;text-transform:uppercase;'>
            AI-Powered Immersive Tamil Poetry Experience
        </p>
    """, unsafe_allow_html=True)

    if _api_key_missing:
        st.error("GEMINI_API_KEY not found. Add it to your `.env` file.")

    poem_text, poem_id, include_images, include_audio, include_video, demo_mode, target_language, run_btn = render_sidebar()
    st.session_state["target_language"] = target_language

    if "pipeline_result" not in st.session_state:
        st.session_state.pipeline_result = None

    if run_btn:
        if not poem_text or not poem_text.strip():
            st.error(_ui("Please enter a poem to analyze.", target_language))
        else:
            result = run_pipeline(
                poem_text.strip(),
                include_images,
                include_audio,
                include_video,
                poem_id=poem_id,
                demo_mode=demo_mode,
                target_language=target_language,
            )
            if st.session_state.get("ocr_source"):
                result.analysis.ocr_source = st.session_state["ocr_source"]
                result.analysis.ocr_language = st.session_state.get("ocr_lang", "")
            st.session_state.pipeline_result = result

    result = st.session_state.pipeline_result

    if result is None:
        empty_title = _ui("Enter a Sangam poem to begin", target_language)
        empty_copy = _translated_text(
            "As the kurinji flower blooms on the mountain slopes, so does the meaning of ancient verse unfold to those who look deeply.",
            target_language,
        )
        st.markdown(
            f"""
            <div style='text-align:center;padding:4rem 2rem;'>
                <div style='font-family:"Playfair Display",serif;font-size:1.4rem;color:var(--sangam-ink);margin-bottom:1rem;'>
                    {html.escape(empty_title)}
                </div>
                <div style='font-size:1rem;color:var(--sangam-muted);max-width:500px;margin:0 auto;font-style:italic;'>
                    {html.escape(empty_copy)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        _ui("Analysis", target_language),
        _ui("Scenes", target_language),
        _ui("Voice", target_language),
        _ui("Experience", target_language),
        _ui("Ask Pulavar", target_language),
    ])
    with tab1:
        render_stage_notices(result, "analysis")
        display_analysis(result.analysis)
    with tab2:
        render_stage_notices(result, "scenes")
        display_scenes(result.scenes, result.images, result.analysis)
    with tab3:
        render_stage_notices(result, "voice")
        display_narration(result.narration)
    with tab4:
        render_stage_notices(result, "video")
        display_video_experience(result)
    with tab5:
        display_chatbot(result.analysis)


if __name__ == "__main__":
    main()
