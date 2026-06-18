"""
Pipeline Flow:
  Poem Input
    → [pulavar_ai]    PoemAnalysis
    → [scene_engine]  list[SceneFrame]
    → [image_engine]  list[GeneratedImage]
    → [voice_engine]  NarrationResult
    → [video_engine]  VideoExperience   ← NEW
    → [pipeline]      PipelineResult
"""

from __future__ import annotations
from pydantic import BaseModel, Field, computed_field
from typing import Optional
from enum import Enum
import os


# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════

class Thinai(str, Enum):
    """
    The five classical landscapes (திணை) of Sangam poetry.
    Each landscape carries a specific emotional situation (உரிப்பொருள்).
    """
    KURINJI  = "Kurinji"    # Hills — premarital union
    MULLAI   = "Mullai"     # Forest — patient waiting
    MARUTHAM = "Marutham"   # Farmland — infidelity & quarrel
    NEYTAL   = "Neytal"     # Seashore — separation & longing
    PALAI    = "Palai"      # Desert — separation by travel
    UNKNOWN  = "Unknown"


class Mood(str, Enum):
    """
    Emotional register (மெய்ப்பாடு) detected in the poem.
    Maps to the eight classical Sangam emotions.
    """
    LONGING    = "longing"
    JOY        = "joy"
    SORROW     = "sorrow"
    ANGER      = "anger"
    DEVOTION   = "devotion"
    SERENITY   = "serenity"
    YEARNING   = "yearning"
    MELANCHOLY = "melancholy"
    UNKNOWN    = "unknown"


class SubtitleFormat(str, Enum):
    """
    Supported subtitle/caption export formats for VideoExperience.
    SRT is the most universal; VTT is preferred for web players.
    """
    SRT  = "srt"   # SubRip — works with VLC, ffmpeg, YouTube
    VTT  = "vtt"   # WebVTT — web players, HTML5 <track>
    ASS  = "ass"   # Advanced SubStation Alpha — styling support
    JSON = "json"  # Raw JSON array for custom renderers


class VideoStatus(str, Enum):
    """
    Lifecycle state of a VideoExperience render job.
    Use this to drive progress indicators in the Streamlit UI.
    """
    PENDING    = "pending"     # Queued, not started
    COMPOSING  = "composing"   # Merging scenes + audio
    RENDERING  = "rendering"   # ffmpeg encoding in progress
    COMPLETE   = "complete"    # Output file ready
    FAILED     = "failed"      # Error — see VideoExperience.error


# ═══════════════════════════════════════════════════════════════
# LOOKUP DICTIONARIES
# ═══════════════════════════════════════════════════════════════

THINAI_TAMIL: dict[Thinai, str] = {
    Thinai.KURINJI:  "குறிஞ்சி",
    Thinai.MULLAI:   "முல்லை",
    Thinai.MARUTHAM: "மருதம்",
    Thinai.NEYTAL:   "நெய்தல்",
    Thinai.PALAI:    "பாலை",
    Thinai.UNKNOWN:  "—",
}

THINAI_MEANING: dict[Thinai, str] = {
    Thinai.KURINJI:  "Hills — Premarital union (களவு)",
    Thinai.MULLAI:   "Forest — Patient waiting (இரங்கல்)",
    Thinai.MARUTHAM: "Farmland — Infidelity & quarrel (ஊடல்)",
    Thinai.NEYTAL:   "Seashore — Separation & longing (ஆற்றாமை)",
    Thinai.PALAI:    "Desert — Separation by travel (பிரிவு)",
    Thinai.UNKNOWN:  "Unknown",
}

MOOD_TAMIL: dict[Mood, str] = {
    Mood.LONGING:    "ஏக்கம்",
    Mood.JOY:        "மகிழ்ச்சி",
    Mood.SORROW:     "துயரம்",
    Mood.ANGER:      "கோபம்",
    Mood.DEVOTION:   "பக்தி",
    Mood.SERENITY:   "அமைதி",
    Mood.YEARNING:   "வேட்கை",
    Mood.MELANCHOLY: "வருத்தம்",
    Mood.UNKNOWN:    "—",
}

# Maps Thinai → suggested color palette hex codes for video overlays
THINAI_COLOR_PALETTE: dict[Thinai, list[str]] = {
    Thinai.KURINJI:  ["#B9B7D9", "#F8F7F3", "#26313F"],
    Thinai.MULLAI:   ["#BFC9BA", "#EEF3EE", "#26313F"],
    Thinai.MARUTHAM: ["#D7C49B", "#FFFCF7", "#26313F"],
    Thinai.NEYTAL:   ["#B9D2DC", "#F3F5F1", "#26313F"],
    Thinai.PALAI:    ["#D8B7A6", "#FFFCF7", "#26313F"],
    Thinai.UNKNOWN:  ["#D9DED6", "#F8F7F3", "#26313F"],
}

# Canonical Tamil labels. These override older mojibake literals above.
THINAI_TAMIL.update(
    {
        Thinai.KURINJI: "குறிஞ்சி",
        Thinai.MULLAI: "முல்லை",
        Thinai.MARUTHAM: "மருதம்",
        Thinai.NEYTAL: "நெய்தல்",
        Thinai.PALAI: "பாலை",
        Thinai.UNKNOWN: "திணை",
    }
)

THINAI_MEANING.update(
    {
        Thinai.KURINJI: "Hills - Premarital union (களவு)",
        Thinai.MULLAI: "Forest - Patient waiting (இரங்கல்)",
        Thinai.MARUTHAM: "Farmland - Infidelity and quarrel (ஊடல்)",
        Thinai.NEYTAL: "Seashore - Separation and longing (ஆற்றாமை)",
        Thinai.PALAI: "Desert - Separation by travel (பிரிவு)",
    }
)

MOOD_TAMIL.update(
    {
        Mood.LONGING: "ஏக்கம்",
        Mood.JOY: "மகிழ்ச்சி",
        Mood.SORROW: "துயரம்",
        Mood.ANGER: "கோபம்",
        Mood.DEVOTION: "பக்தி",
        Mood.SERENITY: "அமைதி",
        Mood.YEARNING: "வேட்கை",
        Mood.MELANCHOLY: "வருத்தம்",
        Mood.UNKNOWN: "தெரியாதது",
    }
)


# ═══════════════════════════════════════════════════════════════
# SHARED SUB-MODELS
# ═══════════════════════════════════════════════════════════════

class MuthalPorul(BaseModel):
    """
    முதற்பொருள் — Time and place elements.
    The 'primary matter' of a Sangam poem: landscape (நிலம்), season (பருவம்), time (பொழுது).
    """
    landscape:       str = ""
    landscape_tamil: str = ""
    season:          str = ""
    season_tamil:    str = ""
    time:            str = ""
    time_tamil:      str = ""


class Character(BaseModel):
    """A named participant in the poem's dramatic situation."""
    name:        str = ""
    name_tamil:  str = ""
    role:        str = ""
    role_tamil:  str = ""
    description: str = ""


class MeaningLine(BaseModel):
    """Line-by-line meaning breakdown with literary annotation."""
    original:        str = ""
    translation:     str = ""
    interpretation:  str = ""
    literary_device: str = ""


class GrammarNote(BaseModel):
    """A classical Tamil grammatical term with definition and in-poem example."""
    term:       str = ""
    term_tamil: str = ""
    definition: str = ""
    example:    str = ""


# ═══════════════════════════════════════════════════════════════
# POEM  —  matches poems.json exactly
# ═══════════════════════════════════════════════════════════════

class Poem(BaseModel):
    """
    A single Sangam poem entry — mirrors the structure of poems.json.
    This is the raw data object; use PoemAnalysis for AI-enriched output.
    """
    id:            int
    title_en:      str = ""
    title_ta:      str = ""
    poem_en:       str = ""
    poem_ta:       str = ""
    thinai:        Thinai = Thinai.UNKNOWN
    thinai_ta:     str = ""
    thurai:        str = ""
    speaker:       str = ""
    listener:      str = ""
    muthal_porul:  Optional[MuthalPorul] = None
    karu_porul:    list[str] = Field(default_factory=list)
    uri_porul:     str = ""
    meyppadu:      str = ""
    word_meanings: dict[str, str] = Field(default_factory=dict)
    author:        str = "Unknown"
    author_ta:     str = ""
    collection:    str = ""
    collection_ta: str = ""
    akam_puram:    str = "Akam"
    akam_puram_ta: str = "அகம்"
    period:        str = ""
    cultural_context: str = ""
    image_prompt:  str = ""

    def display_title(self) -> str:
        """Returns a formatted display title for UI headers."""
        ta = self.title_ta or ""
        en = self.title_en or f"Poem #{self.id}"
        return f"{ta} — {en}" if ta else en

    def thinai_display(self) -> str:
        """Returns 'Kurinji (குறிஞ்சி)' style label for UI badges."""
        ta = THINAI_TAMIL.get(self.thinai, "")
        return f"{self.thinai.value} ({ta})" if ta else self.thinai.value


# ═══════════════════════════════════════════════════════════════
# OCR MODELS  —  used by ocr_engine and Sangam Lens
# ═══════════════════════════════════════════════════════════════

class OCRResult(BaseModel):
    """
    Result of image-to-text extraction via Gemini Vision.
    Supports camera capture and file upload flows in Sangam Lens.
    """
    extracted_text: str = ""
    language:       str = "unknown"   # "tamil", "english", "mixed"
    success:        bool = True
    error:          str = ""

    @classmethod
    def failed(cls, error: str) -> "OCRResult":
        return cls(success=False, error=error)


# ═══════════════════════════════════════════════════════════════
# POEM ANALYSIS  —  output of pulavar_ai.analyze_poem()
# ═══════════════════════════════════════════════════════════════

class PoemAnalysis(BaseModel):
    """
    AI-enriched analysis of a Sangam poem produced by pulavar_ai.
    Contains classification, poetics, literary analysis, and cultural context.

    Hackathon tip: Use analysis.badge_line() for a one-liner summary card.
    """
    # ── Core classification ──────────────────────────────────
    thinai:        Thinai = Thinai.UNKNOWN
    mood:          Mood   = Mood.UNKNOWN
    emotion:       str = ""
    emotion_tamil: str = ""

    # ── Source metadata ──────────────────────────────────────
    poet:             str = ""
    poet_tamil:       str = ""
    collection:       str = ""
    collection_tamil: str = ""
    period:           str = ""
    akam_puram:       str = ""

    # ── Sangam situational poetics ───────────────────────────
    thurai:       str = ""
    thurai_tamil: str = ""
    speaker:      str = ""
    listener:     str = ""

    # ── Three-fold poetics (முப்பொருள்) ─────────────────────
    muthal_porul:    Optional[MuthalPorul] = None
    karu_porul:      list[str] = Field(default_factory=list)
    uri_porul:       str = ""
    uri_porul_tamil: str = ""
    meyppadu:        str = ""
    meyppadu_tamil:  str = ""

    # ── Summary ──────────────────────────────────────────────
    summary:       str = ""
    summary_tamil: str = ""

    # ── Nature elements ──────────────────────────────────────
    flora_fauna: str = ""

    # ── Cultural context ─────────────────────────────────────
    cultural_context:       str = ""
    cultural_context_tamil: str = ""

    # ── Literary analysis ────────────────────────────────────
    literary_devices: str = ""
    grammar_notes:    list[GrammarNote] = Field(default_factory=list)
    word_meanings:    dict[str, str]    = Field(default_factory=dict)

    # ── Characters & meaning ─────────────────────────────────
    characters:        list[Character]   = Field(default_factory=list)
    meaning_breakdown: list[MeaningLine] = Field(default_factory=list)

    # ── OCR source info (set when poem came from camera/image) ──
    ocr_source:   str = ""   # "camera", "upload", or "" if typed
    ocr_language: str = ""   # detected language from OCR

    @classmethod
    def empty(cls) -> "PoemAnalysis":
        return cls(
            summary="Analysis unavailable.",
            emotion="Unknown",
            thinai=Thinai.UNKNOWN,
            mood=Mood.UNKNOWN,
        )

    def badge_line(self) -> str:
        """
        Returns a compact one-liner for hackathon demo cards.
        Example: 'Kurinji (குறிஞ்சி) · longing · Hills — Premarital union'
        """
        thinai_ta = THINAI_TAMIL.get(self.thinai, "")
        meaning   = THINAI_MEANING.get(self.thinai, "")
        return f"{self.thinai.value} ({thinai_ta}) · {self.mood.value} · {meaning}"

    def color_palette(self) -> list[str]:
        """Returns the Thinai-matched hex color palette for this poem's UI/video theme."""
        return THINAI_COLOR_PALETTE.get(self.thinai, THINAI_COLOR_PALETTE[Thinai.UNKNOWN])


# ═══════════════════════════════════════════════════════════════
# SCENE FRAME
# ═══════════════════════════════════════════════════════════════

class SceneFrame(BaseModel):
    """
    A single visual scene extracted from the poem for image generation.
    One poem typically yields 3–5 SceneFrames.
    """
    scene_id:      int
    title:         str = ""
    description:   str = ""
    mood:          Mood = Mood.UNKNOWN
    thinai:        Thinai = Thinai.UNKNOWN
    visual_prompt: str = ""
    characters:    list[str] = Field(default_factory=list)
    environment:   str = ""
    lighting:      str = ""
    color_palette: str = ""

    @classmethod
    def empty(cls, scene_id: int = 1) -> "SceneFrame":
        return cls(
            scene_id=scene_id,
            description="Scene unavailable.",
            visual_prompt="Ancient Tamil Sangam era landscape, cinematic painting.",
        )


# ═══════════════════════════════════════════════════════════════
# GENERATED IMAGE
# ═══════════════════════════════════════════════════════════════

class GeneratedImage(BaseModel):
    """
    Output of the image generation engine for a single SceneFrame.
    `image_path` is an absolute path to the saved file on disk.
    """
    scene_id:    int
    image_path:  str = ""
    prompt_used: str = ""
    width:       int = 512
    height:      int = 512
    success:     bool = True
    backend:     str = ""   # e.g. "gemini-imagen", "stability-ai", "placeholder"
    error:       str = ""

    @classmethod
    def failed(cls, scene_id: int, error: str) -> "GeneratedImage":
        return cls(scene_id=scene_id, image_path="", success=False, error=error)

    def exists_on_disk(self) -> bool:
        """Returns True if image_path points to a real file."""
        return bool(self.image_path) and os.path.isfile(self.image_path)


# ═══════════════════════════════════════════════════════════════
# NARRATION RESULT
# ═══════════════════════════════════════════════════════════════

class NarrationResult(BaseModel):
    """
    Output of the voice narration engine.
    `audio_path` is an absolute path to the saved audio file.
    """
    audio_path:       str   = ""
    duration_seconds: float = 0.0
    language:         str   = "en"   # "en", "ta", or "ta+en" for bilingual
    success:          bool  = True
    error:            str   = ""

    @classmethod
    def failed(cls, error: str) -> "NarrationResult":
        return cls(audio_path="", success=False, error=error)

    def exists_on_disk(self) -> bool:
        """Returns True if audio_path points to a real file."""
        return bool(self.audio_path) and os.path.isfile(self.audio_path)


# ═══════════════════════════════════════════════════════════════
# VIDEO EXPERIENCE  —  NEW
# ═══════════════════════════════════════════════════════════════

class SubtitleEntry(BaseModel):
    """
    A single timed subtitle cue.
    Used to build SRT / VTT / ASS / JSON caption files for VideoExperience.

    Timestamps are in seconds (floats) for easy ffmpeg integration.
    """
    index:          int    = 1         # 1-based cue number (required for SRT)
    start_seconds:  float  = 0.0       # Cue in-point
    end_seconds:    float  = 3.0       # Cue out-point
    text_en:        str    = ""        # English caption line
    text_ta:        str    = ""        # Tamil caption line (Unicode)
    speaker:        str    = ""        # Optional: "Hero", "Heroine", "Narrator"
    scene_id:       int    = 1         # Which SceneFrame this cue belongs to

    def to_srt_block(self) -> str:
        """
        Renders this cue as an SRT block string.
        Example:
            1
            00:00:00,000 --> 00:00:03,500
            She waits by the seashore, the waves her only witness.
        """
        def fmt(s: float) -> str:
            h  = int(s // 3600)
            m  = int((s % 3600) // 60)
            sc = int(s % 60)
            ms = int(round((s - int(s)) * 1000))
            return f"{h:02d}:{m:02d}:{sc:02d},{ms:03d}"

        lines = []
        if self.text_en:
            lines.append(self.text_en)
        if self.text_ta:
            lines.append(self.text_ta)

        body = "\n".join(lines) or "(no text)"
        return f"{self.index}\n{fmt(self.start_seconds)} --> {fmt(self.end_seconds)}\n{body}\n"

    def to_vtt_block(self) -> str:
        """
        Renders this cue as a WebVTT block string.
        Example:
            00:00:00.000 --> 00:00:03.500
            She waits by the seashore, the waves her only witness.
        """
        def fmt(s: float) -> str:
            h  = int(s // 3600)
            m  = int((s % 3600) // 60)
            sc = int(s % 60)
            ms = int(round((s - int(s)) * 1000))
            return f"{h:02d}:{m:02d}:{sc:02d}.{ms:03d}"

        lines = []
        if self.text_en:
            lines.append(self.text_en)
        if self.text_ta:
            lines.append(self.text_ta)

        body = "\n".join(lines) or "(no text)"
        return f"{fmt(self.start_seconds)} --> {fmt(self.end_seconds)}\n{body}\n"


class VideoTrack(BaseModel):
    """
    Describes one image-to-video clip segment derived from a SceneFrame.
    The video engine stitches all tracks into the final VideoExperience output.

    Duration = how long this scene's image is held on screen.
    Transition = visual effect between this track and the next.
    """
    scene_id:          int    = 1
    image_path:        str    = ""          # Source image for this track
    start_seconds:     float  = 0.0         # Absolute start in the final video
    duration_seconds:  float  = 5.0         # How long to display this scene
    transition:        str    = "crossfade" # "crossfade", "fade_black", "cut", "zoom_in"
    ken_burns:         bool   = True        # Apply subtle Ken Burns pan/zoom effect
    overlay_text:      str    = ""          # Optional title card text (e.g. scene title)

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds


class VideoExperience(BaseModel):
    """
   
    The final cinematic output for a single poem analysis.
    Combines all SceneFrame images + NarrationResult audio + SubtitleEntry list
    into one video file per poem.

    How to build one:
        from video_engine import VideoComposer
        exp = VideoComposer(result).compose()   # returns VideoExperience

    Output path convention:
        outputs/videos/poem_{poem_id}_{thinai}.mp4

    Subtitle files are written alongside the video:
        outputs/videos/poem_{poem_id}.srt
        outputs/videos/poem_{poem_id}.vtt
    """

    # ── Identity ─────────────────────────────────────────────
    poem_id:        int    = 0
    poem_title_en:  str    = ""
    poem_title_ta:  str    = ""
    thinai:         Thinai = Thinai.UNKNOWN

    # ── Source assets ────────────────────────────────────────
    tracks:         list[VideoTrack]    = Field(default_factory=list)
    audio_path:     str                 = ""   # NarrationResult.audio_path
    subtitles:      list[SubtitleEntry] = Field(default_factory=list)

    # ── Output ───────────────────────────────────────────────
    video_path:         str          = ""   # Final rendered .mp4 path
    subtitle_path_srt:  str          = ""   # .srt file path
    subtitle_path_vtt:  str          = ""   # .vtt file path
    thumbnail_path:     str          = ""   # First-frame or best-scene thumbnail

    # ── Video parameters ─────────────────────────────────────
    resolution:         str   = "1920x1080"  # "1280x720", "1920x1080", "3840x2160"
    fps:                int   = 24
    total_duration:     float = 0.0          # Computed by video_engine after render
    subtitle_format:    SubtitleFormat = SubtitleFormat.SRT

    # ── Render metadata ──────────────────────────────────────
    status:          VideoStatus = VideoStatus.PENDING
    render_engine:   str         = "ffmpeg"     # "ffmpeg", "moviepy", "mock"
    render_time_sec: float       = 0.0          # Wall-clock seconds taken to render
    success:         bool        = True
    error:           str         = ""

    # ── Theme ────────────────────────────────────────────────
    color_theme:        list[str] = Field(default_factory=list)  # From THINAI_COLOR_PALETTE
    background_music:   str       = ""  # Optional ambient BGM audio path
    bgm_volume:         float     = 0.15  # 0.0–1.0; kept low under narration

    @classmethod
    def failed(cls, poem_id: int, error: str) -> "VideoExperience":
        """Create a failed VideoExperience for error propagation in PipelineResult."""
        return cls(poem_id=poem_id, success=False, error=error, status=VideoStatus.FAILED)

    @classmethod
    def from_pipeline(
        cls,
        poem_id:   int,
        title_en:  str,
        title_ta:  str,
        thinai:    Thinai,
        images:    list[GeneratedImage],
        narration: NarrationResult,
        scenes:    list[SceneFrame],
        seconds_per_scene: float = 10.0,
    ) -> "VideoExperience":
        """
        Factory method: builds a VideoExperience skeleton from pipeline outputs.
        Call this in video_engine before handing off to the ffmpeg compositor.

        Args:
            poem_id:           Poem ID for output file naming.
            title_en / ta:     Poem titles for title card overlay.
            thinai:            Used to set color theme.
            images:            GeneratedImage list (one per scene).
            narration:         NarrationResult with the audio path.
            scenes:            SceneFrame list for titles and metadata.
            seconds_per_scene: How long each image is held (default 6s).

        Returns:
            VideoExperience with tracks pre-populated, ready for render.
        """
        if narration and narration.duration_seconds and images:
            target_duration = float(narration.duration_seconds)
            seconds_per_scene = target_duration / max(len(images), 1)

        tracks: list[VideoTrack] = []
        subtitles: list[SubtitleEntry] = []
        cursor = 0.0

        scene_map = {s.scene_id: s for s in scenes}

        for img in images:
            if not img.success:
                continue
            scene = scene_map.get(img.scene_id)
            track = VideoTrack(
                scene_id=img.scene_id,
                image_path=img.image_path,
                start_seconds=cursor,
                duration_seconds=seconds_per_scene,
                overlay_text=scene.title if scene else "",
            )
            tracks.append(track)
            if scene:
                text_en = " ".join(
                    part.strip()
                    for part in (scene.title, scene.description)
                    if part and part.strip()
                )
                text_ta = (
                    f"{THINAI_TAMIL.get(thinai, '')} நிலத்தின் உணர்வு இங்கே விரிகிறது."
                    if THINAI_TAMIL.get(thinai, "")
                    else ""
                )
                subtitles.append(
                    SubtitleEntry(
                        index=len(subtitles) + 1,
                        start_seconds=cursor,
                        end_seconds=cursor + seconds_per_scene,
                        text_en=text_en,
                        text_ta=text_ta,
                        speaker="Pulavar",
                        scene_id=img.scene_id,
                    )
                )
            cursor += seconds_per_scene

        return cls(
            poem_id=poem_id,
            poem_title_en=title_en,
            poem_title_ta=title_ta,
            thinai=thinai,
            tracks=tracks,
            audio_path=narration.audio_path if narration.success else "",
            subtitles=subtitles,
            total_duration=cursor,
            color_theme=THINAI_COLOR_PALETTE.get(thinai, []),
            status=VideoStatus.PENDING,
        )

    def export_srt(self) -> str:
        """
        Generates a complete SRT subtitle string from self.subtitles.
        Write this to subtitle_path_srt.

        Usage:
            srt_content = experience.export_srt()
            with open(experience.subtitle_path_srt, "w", encoding="utf-8") as f:
                f.write(srt_content)
        """
        blocks = [s.to_srt_block() for s in self.subtitles]
        return "\n".join(blocks)

    def export_vtt(self) -> str:
        """
        Generates a complete WebVTT subtitle string from self.subtitles.
        Write this to subtitle_path_vtt.
        """
        header = "WEBVTT\n\n"
        blocks = [s.to_vtt_block() for s in self.subtitles]
        return header + "\n".join(blocks)

    def is_ready_to_render(self) -> bool:
        """
        Returns True if all required assets are present for ffmpeg composition.
        Call before triggering the render step in video_engine.
        """
        images_ok = all(
            t.image_path and os.path.isfile(t.image_path)
            for t in self.tracks
        )
        audio_ok = bool(self.audio_path) and os.path.isfile(self.audio_path)
        return images_ok and audio_ok and len(self.tracks) > 0

    def progress_summary(self) -> str:
        """
        Returns a one-line status string for Streamlit progress displays.
        Example: '[COMPOSING] poem_42_Neytal — 4 scenes · 24s · 1920x1080'
        """
        n      = len(self.tracks)
        dur    = f"{self.total_duration:.0f}s"
        title  = self.poem_title_en or f"poem_{self.poem_id}"
        thinai = self.thinai.value
        return f"[{self.status.value.upper()}] {title}_{thinai} — {n} scenes · {dur} · {self.resolution}"

    def exists_on_disk(self) -> bool:
        """Returns True if the rendered video file is present."""
        return bool(self.video_path) and os.path.isfile(self.video_path)


# ═══════════════════════════════════════════════════════════════
# PIPELINE RESULT
# ═══════════════════════════════════════════════════════════════

class PipelineResult(BaseModel):
    """
    Top-level container returned by the full DTEC pipeline.
    Holds every intermediate and final output for one poem run.

    Fields added in Hackathon Edition:
        video  — VideoExperience (the final cinematic output)
    """
    poem_text: str
    analysis:  PoemAnalysis             = Field(default_factory=PoemAnalysis.empty)
    scenes:    list[SceneFrame]         = Field(default_factory=list)
    images:    list[GeneratedImage]     = Field(default_factory=list)
    narration: Optional[NarrationResult] = None
    video:     Optional[VideoExperience] = None   # ← NEW: cinematic experience
    ocr:       Optional[OCRResult]       = None
    success:   bool                     = True
    errors:    list[str]                = Field(default_factory=list)

    def has_video(self) -> bool:
        """True if a rendered VideoExperience with a real output file exists."""
        return self.video is not None and self.video.exists_on_disk()

    def summary_card(self) -> dict:
        """
        Returns a flat dict useful for hackathon demo dashboards and st.metric() calls.
        Example:
            card = result.summary_card()
            st.metric("Thinai", card["thinai"])
        """
        a = self.analysis
        return {
            "thinai":        a.thinai.value,
            "thinai_ta":     THINAI_TAMIL.get(a.thinai, ""),
            "mood":          a.mood.value,
            "mood_ta":       MOOD_TAMIL.get(a.mood, ""),
            "emotion":       a.emotion,
            "poet":          a.poet,
            "collection":    a.collection,
            "scene_count":   len(self.scenes),
            "image_count":   sum(1 for i in self.images if i.success),
            "has_audio":     self.narration is not None and self.narration.success,
            "has_video":     self.has_video(),
            "video_path":    self.video.video_path if self.video else "",
            "video_status":  self.video.status.value if self.video else "none",
            "errors":        self.errors,
            "success":       self.success,
        }
