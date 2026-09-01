"""Video production specialist for the agent team."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .base_agent import BaseAgent
from .video_provider import generate_image_to_video

VIDEO_SYSTEM_PROMPT = """You are the Video Production Agent in an autonomous media team.
Understand natural Arabic or English requests for videos. Convert the request into a practical production plan.
Prefer existing assets and safe execution. Never purchase, subscribe, or consume paid video-generation credits unless the user explicitly approved paid generation for this task.
Return JSON only with these keys: title, format, style, duration_seconds, scenes, audio, reference_assets, generation_notes.
For TikTok/short-form requests use vertical 9:16 unless explicitly asked otherwise. Scenes must be concrete visual shots.
"""

class VideoAgent(BaseAgent):
    def __init__(self, model: str = "gpt-4o-mini", client: Any | None = None) -> None:
        super().__init__(name="video_agent", system_prompt=VIDEO_SYSTEM_PROMPT, model=model, client=client)

    @staticmethod
    def _find_assets() -> list[str]:
        d = Path("assets")
        return [str(p) for p in sorted(d.rglob("*")) if p.is_file()] if d.exists() else []

    @staticmethod
    def _paid_generation_authorized() -> bool:
        return os.environ.get("ALLOW_PAID_VIDEO_GENERATION", "").strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _pick_asset(suffixes: tuple[str, ...]) -> Path | None:
        d = Path("assets")
        if not d.exists():
            return None
        return next((p for p in sorted(d.rglob("*")) if p.is_file() and p.suffix.lower() in suffixes), None)

    @staticmethod
    def _load_scene_plan() -> list[dict[str, Any]]:
        try:
            from .video_tools.scene_planner import get_scenes
            return get_scenes()
        except (ImportError, ModuleNotFoundError):
            return []

    @staticmethod
    def _parse_plan(text: str) -> dict[str, Any]:
        raw = text.strip()
        candidates = [raw]
        if raw.startswith("```"):
            lines = raw.splitlines()[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidates.append("\n".join(lines).strip())
        a, b = raw.find("{"), raw.rfind("}")
        if a != -1 and b > a:
            candidates.append(raw[a:b+1])
        for c in candidates:
            try:
                v = json.loads(c)
                if isinstance(v, dict):
                    return v
            except json.JSONDecodeError:
                pass
        return {"planner_text": raw, "parser_warning": "Planner response was not valid JSON."}

    @staticmethod
    def _escape_subtitle_text(text: str) -> str:
        return text.replace("\\", r"\\").replace("'", r"\'").replace(":", r"\:").replace("%", r"\%")

    def _finish_test_scene_locally(self) -> dict[str, Any]:
        """Add the existing song and scene-1 Arabic caption without another AI generation."""
        video = Path("outputs/video/replicate_scene_01.mp4")
        audio = self._pick_asset((".mp3", ".wav", ".m4a", ".aac"))
        scenes = self._load_scene_plan()
        if not video.is_file():
            return {"status": "GENERATED_VIDEO_MISSING", "paid_credits_used": False}
        if audio is None:
            return {"status": "AUDIO_ASSET_MISSING", "paid_credits_used": False}

        caption = "آداب الحديث"
        if scenes and scenes[0].get("lyrics"):
            caption = str(scenes[0]["lyrics"])
        caption = self._escape_subtitle_text(caption).replace("\n", r"\n")

        output = Path("outputs/video/replicate_scene_01_finished.mp4")
        output.parent.mkdir(parents=True, exist_ok=True)
        drawtext = (
            "drawtext="
            f"text='{caption}':"
            "fontfile='C\\:/Windows/Fonts/arial.ttf':"
            "fontcolor=white:fontsize=44:borderw=3:bordercolor=black:"
            "x=(w-text_w)/2:y=h-(text_h*2.2)"
        )
        command = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio),
            "-vf", drawtext,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output),
        ]
        try:
            proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        except FileNotFoundError:
            return {"status": "FFMPEG_MISSING", "paid_credits_used": False}
        if proc.returncode != 0:
            return {
                "status": "LOCAL_FINISH_FAILED",
                "error": proc.stderr[-3000:],
                "paid_credits_used": False,
            }
        return {
            "status": "FINISHED_TEST_SCENE_CREATED",
            "output_path": str(output),
            "source_video": str(video),
            "audio_path": str(audio),
            "caption": scenes[0].get("lyrics") if scenes else "آداب الحديث",
            "paid_credits_used": False,
        }

    def _generate_real_test_scene(self) -> dict[str, Any]:
        image = self._pick_asset((".png", ".jpg", ".jpeg", ".webp"))
        if image is None:
            return {"status": "IMAGE_ASSET_MISSING", "paid_credits_used": False}
        scenes = self._load_scene_plan()
        prompt = "The boy listens respectfully to the older man speaking, gently nodding once. Natural subtle movement, stable characters."
        if scenes and scenes[0].get("prompt"):
            prompt = f"{scenes[0]['prompt']} The boy gently nods once while listening. Natural subtle movement, stable characters, preserve faces and clothing, no new characters, no text."
        return generate_image_to_video(prompt, image, Path("outputs/video/replicate_scene_01.mp4"))

    def run(self, task: str, collaboration_context: str | None = None) -> str:
        plan_text = super().run(task, collaboration_context)
        plan = self._parse_plan(plan_text)
        existing_video = Path("outputs/video/replicate_scene_01.mp4")
        if existing_video.is_file():
            execution = {"status": "REUSING_EXISTING_AI_VIDEO", "output_path": str(existing_video), "paid_credits_used": False}
        else:
            execution = self._generate_real_test_scene()
        local_finish = self._finish_test_scene_locally() if existing_video.is_file() else {"status": "WAITING_FOR_AI_VIDEO", "paid_credits_used": False}
        manifest = {
            "status": "PRODUCTION_ATTEMPTED",
            "agent": "video",
            "request": task,
            "plan": plan,
            "available_assets": self._find_assets(),
            "real_video_execution": execution,
            "local_finish": local_finish,
            "spending_policy": {
                "paid_generation_authorized": self._paid_generation_authorized(),
                "rule": "Replicate inference is blocked unless explicit financial approval is enabled for this task. Existing generated clips are reused without spending."
            },
        }
        out = Path("outputs/video")
        out.mkdir(parents=True, exist_ok=True)
        manifest_path = out / "production_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["manifest_path"] = str(manifest_path)
        return json.dumps(manifest, ensure_ascii=False, indent=2)
