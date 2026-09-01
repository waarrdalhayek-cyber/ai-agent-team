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
    def _probe_duration(video: Path) -> float:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        if proc.returncode == 0:
            try:
                return max(float(proc.stdout.strip()), 0.1)
            except ValueError:
                pass
        return 6.0

    @staticmethod
    def _ass_time(seconds: float) -> str:
        seconds = max(seconds, 0.0)
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:05.2f}"

    @staticmethod
    def _ass_escape(text: str) -> str:
        return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")

    def _write_scene1_ass(self, video: Path, lyrics: str, ass_path: Path) -> list[str]:
        """Create proper UTF-8 ASS subtitles so Arabic shaping/RTL is handled by libass."""
        lines = [line.strip() for line in lyrics.splitlines() if line.strip()]
        if not lines:
            lines = ["آداب الحديث"]
        duration = self._probe_duration(video)
        slot = duration / len(lines)
        events = []
        for index, line in enumerate(lines):
            start = index * slot
            end = duration if index == len(lines) - 1 else (index + 1) * slot
            events.append(
                f"Dialogue: 0,{self._ass_time(start)},{self._ass_time(end)},Arabic,,0,0,0,,{self._ass_escape(line)}"
            )
        ass = "\n".join([
            "[Script Info]",
            "ScriptType: v4.00+",
            "PlayResX: 1080",
            "PlayResY: 1920",
            "WrapStyle: 2",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
            "Style: Arabic,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H60000000,1,0,0,0,100,100,0,0,1,3,1,2,60,60,150,1",
            "",
            "[Events]",
            "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
            *events,
            "",
        ])
        ass_path.write_text(ass, encoding="utf-8-sig")
        return lines

    def _finish_test_scene_locally(self) -> dict[str, Any]:
        """Add the existing song and scene-1 Arabic captions without another AI generation."""
        video = Path("outputs/video/replicate_scene_01.mp4")
        audio = self._pick_asset((".mp3", ".wav", ".m4a", ".aac"))
        scenes = self._load_scene_plan()
        if not video.is_file():
            return {"status": "GENERATED_VIDEO_MISSING", "paid_credits_used": False}
        if audio is None:
            return {"status": "AUDIO_ASSET_MISSING", "paid_credits_used": False}

        lyrics = "آداب الحديث"
        if scenes and scenes[0].get("lyrics"):
            lyrics = str(scenes[0]["lyrics"])

        output_dir = Path("outputs/video")
        output_dir.mkdir(parents=True, exist_ok=True)
        ass_path = output_dir / "scene_01_arabic.ass"
        subtitle_lines = self._write_scene1_ass(video, lyrics, ass_path)
        output = output_dir / "replicate_scene_01_finished.mp4"

        subtitle_filter = f"ass='{ass_path.as_posix()}'"
        command = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio),
            "-vf", subtitle_filter,
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
            "subtitle_lines": subtitle_lines,
            "subtitle_mode": "sequential_ass_arabic",
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
