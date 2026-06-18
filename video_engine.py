"""
video_engine.py — simple slideshow video generator

Functions:
- create_slideshow(output_path, image_paths, durations, audio_path=None, fps=24)
- images_from_generated(images) -> list[str]

Uses moviepy if available, otherwise falls back to imageio-ffmpeg if installed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import List, Optional

from schemas import VideoExperience, VideoStatus
import language_engine


def images_from_generated(images) -> List[str]:
    """Convert a list of GeneratedImage objects or file paths to a list of existing file paths.

    Accepts:
    - list of strings (file paths)
    - list of objects with attribute `image_path`

    Returns a list of paths that exist on disk.
    """
    paths: List[str] = []

    for img in images or []:
        if not img:
            continue
        if isinstance(img, str):
            p = img
        else:
            p = getattr(img, "image_path", None)
        if p and os.path.exists(p):
            paths.append(p)
    return paths


def _normalize_slideshow_inputs(
    image_paths: List[str] | None,
    durations: Optional[List[float]] = None,
) -> tuple[List[str], List[float]]:
    pairs: list[tuple[str, float | None]] = []
    for index, path in enumerate(image_paths or []):
        if not path or not os.path.exists(path):
            continue
        duration = durations[index] if durations and index < len(durations) else None
        pairs.append((path, duration))

    if not pairs:
        raise ValueError("No usable image paths provided")

    normalized_paths = [path for path, _ in pairs]
    normalized_durations = [
        float(duration) if duration and duration > 0 else 3.0
        for _, duration in pairs
    ]
    return normalized_paths, normalized_durations


def _with_duration(clip, duration: float):
    if hasattr(clip, "with_duration"):
        return clip.with_duration(duration)
    return clip.set_duration(duration)


def _with_audio(video, audio):
    if hasattr(video, "with_audio"):
        return video.with_audio(audio)
    return video.set_audio(audio)


def _subclip(clip, start: float, end: float):
    if hasattr(clip, "subclipped"):
        return clip.subclipped(start, end)
    return clip.subclip(start, end)


def _probe_audio_duration(audio_path: Optional[str]) -> float:
    if not audio_path or not os.path.exists(audio_path):
        return 0.0

    try:
        from moviepy.editor import AudioFileClip

        audio = AudioFileClip(audio_path)
        duration = float(audio.duration or 0.0)
        audio.close()
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
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if completed.returncode == 0:
            return max(float(completed.stdout.strip()), 0.0)
    except Exception:
        pass

    return 0.0


def _write_subtitle_files(exp: VideoExperience, output_path: str) -> None:
    if not exp.subtitles:
        return

    base, _ = os.path.splitext(output_path)
    exp.subtitle_path_srt = f"{base}.srt"
    exp.subtitle_path_vtt = f"{base}.vtt"
    os.makedirs(os.path.dirname(exp.subtitle_path_srt) or ".", exist_ok=True)

    with open(exp.subtitle_path_srt, "w", encoding="utf-8") as handle:
        handle.write(_export_selected_language_srt(exp))
    with open(exp.subtitle_path_vtt, "w", encoding="utf-8") as handle:
        handle.write(_export_selected_language_vtt(exp))


def _selected_subtitle_text(cue) -> str:
    speaker = (getattr(cue, "speaker", "") or "").lower()
    wants_tamil = "tamil" in speaker or speaker.endswith(" ta")
    if wants_tamil:
        return getattr(cue, "text_ta", "") or getattr(cue, "text_en", "")
    return getattr(cue, "text_en", "") or getattr(cue, "text_ta", "")


def _export_selected_language_srt(exp: VideoExperience) -> str:
    blocks = []
    for cue in exp.subtitles:
        selected = _selected_subtitle_text(cue).strip()
        if not selected:
            continue
        cue_for_video = cue.model_copy(update={"text_en": selected, "text_ta": ""})
        blocks.append(cue_for_video.to_srt_block())
    return "\n".join(blocks)


def _export_selected_language_vtt(exp: VideoExperience) -> str:
    blocks = []
    for cue in exp.subtitles:
        selected = _selected_subtitle_text(cue).strip()
        if not selected:
            continue
        cue_for_video = cue.model_copy(update={"text_en": selected, "text_ta": ""})
        blocks.append(cue_for_video.to_vtt_block())
    return "WEBVTT\n\n" + "\n".join(blocks)


def _embed_subtitle_track(video_path: str, subtitle_path: str) -> bool:
    if not subtitle_path or not os.path.exists(subtitle_path):
        return False
    if not shutil.which("ffmpeg"):
        return False

    tmp = video_path + ".nosubs.mp4"
    shutil.move(video_path, tmp)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        tmp,
        "-i",
        subtitle_path,
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=tam",
        video_path,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode == 0:
        os.remove(tmp)
        return True

    shutil.move(tmp, video_path)
    return False


def _burn_subtitles(video_path: str, subtitle_path: str) -> bool:
    if os.getenv("DTEC_BURN_SUBTITLES", "1") != "1":
        return False
    if not subtitle_path or not os.path.exists(subtitle_path):
        return False
    if not shutil.which("ffmpeg"):
        return False

    tmp = video_path + ".unburned.mp4"
    shutil.move(video_path, tmp)
    subtitle_filter_path = os.path.abspath(subtitle_path).replace("\\", "/")
    subtitle_filter_path = subtitle_filter_path.replace(":", "\\:")
    style = (
        "FontName=Nirmala UI,"
        "FontSize=22,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&HAA000000,"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=42"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        tmp,
        "-vf",
        f"subtitles='{subtitle_filter_path}':force_style='{style}'",
        "-c:a",
        "copy",
        video_path,
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode == 0:
        os.remove(tmp)
        return True

    shutil.move(tmp, video_path)
    return False


def create_slideshow(
    output_path: str,
    image_paths: List[str],
    durations: Optional[List[float]] = None,
    audio_path: Optional[str] = None,
    fps: int = 24,
) -> str:
    """
    Create a simple slideshow video from image_paths.

    - `durations` is a list of seconds per image. If omitted, each image uses equal duration (default 3s).
    - `audio_path` if provided will be added as background audio (trimmed or looped to match video length).
    - Returns the output path on success.

    Requires `moviepy` for best results. Falls back to `imageio` + `imageio_ffmpeg` if available.
    """
    image_paths, durations = _normalize_slideshow_inputs(image_paths, durations)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # try moviepy first (be defensive about imports and provide a clear error)
    try:
        # Prefer the convenient editor import if available
        try:
            from moviepy.editor import (
                ImageClip,
                AudioFileClip,
                concatenate_videoclips,
                concatenate_audioclips,
            )
        except Exception:
            # Fallback to specific submodules (some distributions don't expose `moviepy.editor`)
            try:
                from moviepy.video.VideoClip import ImageClip
                from moviepy.audio.io.AudioFileClip import AudioFileClip
                from moviepy.video.compositing.CompositeVideoClip import concatenate_videoclips
                from moviepy.audio.AudioClip import concatenate_audioclips
            except Exception:
                # If any import fails, raise ImportError to let caller know
                raise ImportError

        clips = []
        for img_path, dur in zip(image_paths, durations):
            clip = _with_duration(ImageClip(img_path), dur)
            clips.append(clip)

        video = concatenate_videoclips(clips, method="compose")
        audio = None

        if audio_path and os.path.exists(audio_path):
            audio = AudioFileClip(audio_path)
            # if audio shorter than video, loop; if longer, subclip
            if audio.duration > video.duration:
                audio = _subclip(audio, 0, video.duration)
            video = _with_audio(video, audio)

        video.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac", threads=2, logger=None)
        for clip in clips:
            close = getattr(clip, "close", None)
            if close:
                close()
        if audio:
            audio.close()
        close = getattr(video, "close", None)
        if close:
            close()
        return output_path

    except ImportError:
        raise RuntimeError(
            "moviepy is not available. Install with: `pip install moviepy imageio-ffmpeg`"
        )
    except Exception:
        # any other moviepy runtime error — fall through to fallback writer
        pass

    # fallback to imageio-ffmpeg writer
    try:
        from PIL import Image
        import imageio.v2 as imageio
        import numpy as np

        writer = imageio.get_writer(output_path, fps=fps, codec="libx264", ffmpeg_log_level="error")

        for img_path, dur in zip(image_paths, durations):
            frames = max(1, int(round(dur * fps)))
            with Image.open(img_path) as img:
                arr = np.asarray(img.convert("RGB"))
            for _ in range(frames):
                writer.append_data(arr)
        writer.close()

        # add audio using ffmpeg if provided
        if audio_path and os.path.exists(audio_path):
            tmp = output_path + ".tmp.mp4"
            shutil.move(output_path, tmp)
            cmd = (
                "ffmpeg", "-y",
                "-i", tmp,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                output_path,
            )
            completed = subprocess.run(cmd, capture_output=True, text=True)
            if completed.returncode != 0:
                # restore tmp
                shutil.move(tmp, output_path)
                raise RuntimeError("ffmpeg failed to mux audio")
            os.remove(tmp)

        return output_path

    except Exception as e:
        raise RuntimeError("Failed to create slideshow; install moviepy or imageio_ffmpeg") from e

def compose(*args, **kwargs):
    """
    Compatibility wrapper around create_slideshow().

    Accepts:
        compose(output_path, image_paths, ...)
        compose(output_path=..., image_paths=..., ...)
        compose(poem_id=..., output_path=..., image_paths=..., ...)
    """

    pipeline_kwargs = {
        key: kwargs.get(key)
        for key in (
            "poem_id",
            "title_en",
            "title_ta",
            "thinai",
            "images",
            "narration",
            "scenes",
            "analysis",
            "target_language",
        )
    }

    output_path = kwargs.pop("output_path", None)
    image_paths = kwargs.pop("image_paths", None)
    durations = kwargs.pop("durations", None)
    audio_path = kwargs.pop("audio_path", None)
    fps = kwargs.pop("fps", 24)

    if len(args) > 0 and output_path is None:
        output_path = args[0]
    if len(args) > 1 and image_paths is None:
        image_paths = args[1]
    if len(args) > 2 and durations is None:
        durations = args[2]
    if len(args) > 3 and audio_path is None:
        audio_path = args[3]
    if len(args) > 4:
        fps = args[4]

    if pipeline_kwargs["images"] is not None and pipeline_kwargs["narration"] is not None:
        narration = pipeline_kwargs["narration"]
        narration_duration = getattr(narration, "duration_seconds", 0.0) or _probe_audio_duration(
            getattr(narration, "audio_path", None)
        )
        scene_count = max(len(pipeline_kwargs["images"] or []), 1)
        end_padding_seconds = 1.5 if narration_duration else 0.0
        seconds_per_scene = (
            max(4.0, (narration_duration + end_padding_seconds) / scene_count)
            if narration_duration
            else 6.0
        )

        exp = VideoExperience.from_pipeline(
            poem_id=pipeline_kwargs["poem_id"] or 0,
            title_en=pipeline_kwargs["title_en"] or "",
            title_ta=pipeline_kwargs["title_ta"] or "",
            thinai=pipeline_kwargs["thinai"],
            images=pipeline_kwargs["images"] or [],
            narration=narration,
            scenes=pipeline_kwargs["scenes"] or [],
            seconds_per_scene=seconds_per_scene,
        )
        if pipeline_kwargs.get("analysis") is not None:
            exp.subtitles = language_engine.build_multilingual_subtitles(
                pipeline_kwargs["scenes"] or [],
                exp.tracks,
                pipeline_kwargs["analysis"],
                target_language=pipeline_kwargs.get("target_language") or "en",
            )
        image_paths = image_paths or [track.image_path for track in exp.tracks if track.image_path]
        durations = durations or [track.duration_seconds for track in exp.tracks if track.image_path]
        audio_path = audio_path or exp.audio_path
        output_path = output_path or os.path.join(
            "outputs",
            "videos",
            f"poem_{exp.poem_id}_{exp.thinai.value}.mp4",
        )

        started = time.perf_counter()
        try:
            exp.status = VideoStatus.COMPOSING
            _write_subtitle_files(exp, output_path)
            exp.video_path = create_slideshow(
                output_path=output_path,
                image_paths=image_paths,
                durations=durations,
                audio_path=audio_path,
                fps=fps,
            )
            _burn_subtitles(exp.video_path, exp.subtitle_path_srt)
            _embed_subtitle_track(exp.video_path, exp.subtitle_path_srt)
            exp.total_duration = sum(durations or [])
            exp.status = VideoStatus.COMPLETE
            exp.success = True
            exp.error = ""
        except Exception as exc:
            exp.status = VideoStatus.FAILED
            exp.success = False
            exp.error = str(exc)
        finally:
            exp.render_time_sec = time.perf_counter() - started
        return exp

    return create_slideshow(
        output_path=output_path,
        image_paths=image_paths,
        durations=durations,
        audio_path=audio_path,
        fps=fps,
    )
