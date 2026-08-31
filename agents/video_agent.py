"""Video production specialist for the agent team.

The VideoAgent plans short-form videos and can execute a zero-cost local FFmpeg
production path when suitable local assets are available. Paid generation remains
blocked unless explicitly authorized.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .base_agent import BaseAgent


VIDEO_SYSTEM_PROMPT = """You are the Video Production Agent in an autonomous media team.
Understand natural Arabic or English requests for videos. Convert the request into a practical production plan.
Prefer existing assets, free credits, and local tools before paid generation.
Never purchase, subscribe, or consume paid video-generation credits unless the user explicitly approved paid generation for this task.
Return JSON only with these keys: title, format, style, duration_seconds, scenes, audio, reference_assets, generation_notes.
For TikTok/short-form requests use vertical 9:16 unless the user explicitly asks otherwise.
Scenes must be concrete visual shots, not general advice.
"""


class VideoAgent(BaseAgent):
    """Plans video production and executes safe local rendering when possible."""

    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None) -> None:
        super().__init__(
            name="video_agent",
            system_prompt=VIDEO_SYSTEM_PROMPT,
            model=model,
            client=client,
        )

    @staticmethod
    def _find_assets() -> list[str]:
        asset_dir = Path("assets")
        if not asset_dir.exists():
            return []
        return [str(path) for path in sorted(asset_dir.rglob("*")) if path.is_file()]

    @staticmethod
    def _paid_generation_authorized() -> bool:
        return os.environ.get("ALLOW_PAID_VIDEO_GENERATION", "").strip().lower() in {
            "1", "true", "yes", "on"
        }

    @staticmethod
    def _ffmpeg_path() -> str | None:
        return shutil.which("ffmpeg")

    @staticmethod
    def _pick_asset(suffixes: tuple[str, ...]) -> Path | None:
        asset_dir = Path("assets")
        if not asset_dir.exists():
            return None
        for path in sorted(asset_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in suffixes:
                return path
        return None

    @staticmethod
    def _load_scene_plan() -> list[dict[str, Any]]:
        try:
            from .video_tools.scene_planner import get_scenes
        except (ImportError, ModuleNotFoundError):
            return []
        return get_scenes()

    def _render_local_preview(self) -> dict[str, Any]:
        """Create a real MP4 locally with FFmpeg without consuming paid credits.

        This is deliberately a preview/fallback renderer. It uses the local reference
        image as the visual source and adds a gentle zoom/pan motion in vertical 9:16,
        synchronized to the local audio. The scene plan is attached to the execution
        result for the next stage, where true scene-by-scene visuals can replace this
        fallback without changing the agent contract.
        """
        ffmpeg = self._ffmpeg_path()
        image = self._pick_asset((".png", ".jpg", ".jpeg", ".webp"))
        audio = self._pick_asset((".mp3", ".wav", ".m4a", ".aac"))
        scenes = self._load_scene_plan()

        missing: list[str] = []
        if not ffmpeg:
            missing.append("ffmpeg")
        if image is None:
            missing.append("image_asset")
        if audio is None:
            missing.append("audio_asset")

        if missing:
            return {
                "status": "LOCAL_RENDER_UNAVAILABLE",
                "missing": missing,
                "scene_count": len(scenes),
            }

        output_dir = Path("outputs/video")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "local_preview.mp4"

        # TikTok-friendly 1080x1920 output with subtle motion so the result is an
        # actual moving video rather than a completely static image.
        video_filter = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "zoompan=z='min(zoom+0.0008,1.12)':d=1:s=1080x1920:fps=30"
        )

        command = [
            ffmpeg,
            "-y",
            "-loop", "1",
            "-i", str(image),
            "-i", str(audio),
            "-vf", video_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "21",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )

        if completed.returncode != 0:
            return {
                "status": "LOCAL_RENDER_FAILED",
                "returncode": completed.returncode,
                "stderr_tail": completed.stderr[-3000:],
                "scene_count": len(scenes),
            }

        return {
            "status": "LOCAL_PREVIEW_CREATED",
            "output_path": str(output_path),
            "visual_mode": "animated_reference_image",
            "format": "vertical_9_16",
            "scene_count": len(scenes),
            "scene_plan_loaded": bool(scenes),
            "paid_credits_used": False,
        }

    def run(self, task: str, collaboration_context: str | None = None) -> str:
        plan_text = super().run(task, collaboration_context)
        try:
            plan = json.loads(plan_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("VideoAgent planner returned invalid JSON.") from exc

        local_execution = self._render_local_preview()

        manifest = {
            "status": "PRODUCTION_ATTEMPTED",
            "agent": "video",
            "request": task,
            "plan": plan,
            "available_assets": self._find_assets(),
            "local_execution": local_execution,
            "spending_policy": {
                "priority": ["existing_assets", "free_credits", "local_tools", "paid_provider"],
                "paid_generation_authorized": self._paid_generation_authorized(),
                "rule": "Paid generation is blocked unless explicitly authorized.",
            },
        }

        output_dir = Path("outputs/video")
        output_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = output_dir / "production_manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifest["manifest_path"] = str(manifest_path)

        return json.dumps(manifest, ensure_ascii=False, indent=2)
