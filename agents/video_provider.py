"""Fal.ai execution provider for VideoAgent.

This module performs real image-to-video generation. It never purchases credits
or changes billing. Paid inference is blocked unless the caller explicitly sets
ALLOW_PAID_VIDEO_GENERATION for the current task.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_MODEL = "fal-ai/minimax/hailuo-2.3-fast/standard/image-to-video"


def _authorized() -> bool:
    return os.environ.get("ALLOW_PAID_VIDEO_GENERATION", "").strip().lower() in {"1", "true", "yes", "on"}


def generate_image_to_video(prompt: str, image_path: str | Path, output_path: str | Path, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    if not os.environ.get("FAL_KEY"):
        return {"status": "FAL_KEY_MISSING", "paid_credits_used": False}
    if not _authorized():
        return {
            "status": "FINANCIAL_APPROVAL_REQUIRED",
            "provider": "fal.ai",
            "model": model,
            "message": "Fal inference can consume paid API credit. Explicit approval is required before generation.",
            "paid_credits_used": False,
        }

    image_path = Path(image_path)
    if not image_path.is_file():
        return {"status": "IMAGE_NOT_FOUND", "image_path": str(image_path), "paid_credits_used": False}

    try:
        import fal_client
    except ImportError:
        return {"status": "FAL_CLIENT_MISSING", "install": "pip install fal-client", "paid_credits_used": False}

    image_url = fal_client.upload_file(str(image_path))
    result = fal_client.subscribe(
        model,
        arguments={"prompt": prompt, "image_url": image_url},
        with_logs=True,
    )
    video = result.get("video") or {}
    video_url = video.get("url")
    if not video_url:
        return {"status": "FAL_GENERATION_FAILED", "provider_result": result, "paid_credits_used": True}

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(video_url, output_path)
    return {
        "status": "AI_VIDEO_CREATED",
        "provider": "fal.ai",
        "model": model,
        "output_path": str(output_path),
        "video_url": video_url,
        "paid_credits_used": True,
    }
