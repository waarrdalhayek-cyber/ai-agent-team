"""Replicate execution provider for VideoAgent.

This module performs real image-to-video generation. It never purchases credits
or changes billing. Inference is blocked unless the caller explicitly sets
ALLOW_PAID_VIDEO_GENERATION for the current task.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "minimax/video-01"


def _authorized() -> bool:
    return os.environ.get("ALLOW_PAID_VIDEO_GENERATION", "").strip().lower() in {"1", "true", "yes", "on"}


def generate_image_to_video(prompt: str, image_path: str | Path, output_path: str | Path, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    if not os.environ.get("REPLICATE_API_TOKEN"):
        return {"status": "REPLICATE_API_TOKEN_MISSING", "paid_credits_used": False}
    if not _authorized():
        return {
            "status": "FINANCIAL_APPROVAL_REQUIRED",
            "provider": "replicate",
            "model": model,
            "message": "Replicate inference may consume prediction credit. Explicit approval is required before generation.",
            "paid_credits_used": False,
        }

    image_path = Path(image_path)
    if not image_path.is_file():
        return {"status": "IMAGE_NOT_FOUND", "image_path": str(image_path), "paid_credits_used": False}

    try:
        import replicate
    except ImportError:
        return {"status": "REPLICATE_CLIENT_MISSING", "install": "pip install replicate", "paid_credits_used": False}

    try:
        with image_path.open("rb") as image_file:
            output = replicate.run(
                model,
                input={
                    "prompt": prompt,
                    "prompt_optimizer": True,
                    "first_frame_image": image_file,
                },
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(output.read())
        video_url = str(getattr(output, "url", "") or "")
        return {
            "status": "AI_VIDEO_CREATED",
            "provider": "replicate",
            "model": model,
            "output_path": str(output_path),
            "video_url": video_url,
            "paid_credits_used": True,
        }
    except Exception as exc:
        return {
            "status": "REPLICATE_GENERATION_FAILED",
            "provider": "replicate",
            "model": model,
            "error": str(exc),
            "paid_credits_used": True,
        }
