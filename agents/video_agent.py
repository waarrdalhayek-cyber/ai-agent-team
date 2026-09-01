"""Video production specialist for the agent team."""
from __future__ import annotations

import json
import os
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
        if not d.exists(): return None
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
            if lines and lines[-1].strip() == "```": lines = lines[:-1]
            candidates.append("\n".join(lines).strip())
        a, b = raw.find("{"), raw.rfind("}")
        if a != -1 and b > a: candidates.append(raw[a:b+1])
        for c in candidates:
            try:
                v = json.loads(c)
                if isinstance(v, dict): return v
            except json.JSONDecodeError:
                pass
        return {"planner_text": raw, "parser_warning": "Planner response was not valid JSON."}

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
        execution = self._generate_real_test_scene()
        manifest = {
            "status": "PRODUCTION_ATTEMPTED",
            "agent": "video",
            "request": task,
            "plan": plan,
            "available_assets": self._find_assets(),
            "real_video_execution": execution,
            "spending_policy": {
                "paid_generation_authorized": self._paid_generation_authorized(),
                "rule": "Replicate inference is blocked unless explicit financial approval is enabled for this task. Billing changes and purchases are never automated."
            },
        }
        out = Path("outputs/video")
        out.mkdir(parents=True, exist_ok=True)
        manifest_path = out / "production_manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        manifest["manifest_path"] = str(manifest_path)
        return json.dumps(manifest, ensure_ascii=False, indent=2)
