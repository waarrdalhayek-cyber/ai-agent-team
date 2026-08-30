"""Video production specialist for the agent team.

The VideoAgent is intentionally provider-agnostic at this stage. It understands a
natural-language video request, creates an executable production manifest, checks
available local/free inputs, and refuses to spend paid generation credits unless
explicitly authorized. Provider adapters can be added without changing the
orchestrator contract.
"""

from __future__ import annotations

import json
import os
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
    """Plans video production and prepares execution without hidden spending."""

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

    def run(self, task: str, collaboration_context: str | None = None) -> str:
        plan_text = super().run(task, collaboration_context)
        try:
            plan = json.loads(plan_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("VideoAgent planner returned invalid JSON.") from exc

        manifest = {
            "status": "READY_FOR_PRODUCTION",
            "agent": "video",
            "request": task,
            "plan": plan,
            "available_assets": self._find_assets(),
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
