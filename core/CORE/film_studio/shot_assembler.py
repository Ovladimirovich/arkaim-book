"""Film Studio — сборка видео из шотов через ffmpeg."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

from .schemas import FilmProject, SceneShot, ShotVersion, ShotStatus, ProjectStatus

log = logging.getLogger("film_studio.assembler")

_DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
_OUTPUT_DIR = _DATA_DIR / "film_output"


class AssemblyStatus:
    IDLE = "idle"
    PREPARING = "preparing"
    ASSEMBLING = "assembling"
    COMPLETE = "complete"
    FAILED = "failed"


class ShotAssembler:
    """Сборка видео из шотов проекта через ffmpeg."""

    def __init__(self):
        self._tasks: dict[str, dict] = {}

    def _get_asset_path(self, asset_id: str) -> Path | None:
        """Получить путь к файлу ассета по ID."""
        base = _DATA_DIR / "visual_assets"
        for ext in ("png", "jpg", "webp", "mp4"):
            fpath = base / f"{asset_id}.{ext}"
            if fpath.exists():
                return fpath
            fpath = base / "images" / f"{asset_id}.{ext}"
            if fpath.exists():
                return fpath
            fpath = base / "videos" / f"{asset_id}.{ext}"
            if fpath.exists():
                return fpath
        # Legacy fallback
        fpath = _DATA_DIR / "visual_assets" / "videos" / f"{asset_id}.mp4"
        if fpath.exists():
            return fpath
        return None

    def _collect_active_shots(self, project: FilmProject) -> list[dict]:
        """Собрать все активные завершённые шоты проекта в порядке сцен."""
        shots = []
        for scene in sorted(project.scenes, key=lambda s: s.order):
            for version in scene.versions:
                if version.is_active and version.status == ShotStatus.COMPLETED and version.asset_id:
                    asset_path = self._get_asset_path(version.asset_id)
                    if asset_path:
                        shots.append({
                            "shot_id": version.id,
                            "asset_id": version.asset_id,
                            "asset_path": asset_path,
                            "duration_sec": version.duration_sec,
                            "scene_id": scene.scene_id,
                            "scene_order": scene.order,
                            "movement": version.camera.motion.value if hasattr(version.camera, 'motion') else "static",
                        })
        return shots

    async def assemble(
        self,
        project: FilmProject,
        fps: int = 24,
    ) -> dict:
        """Собрать видео из активных шотов проекта.

        Returns:
            dict с полями: status, output_path, duration_sec, shot_count, error
        """
        project_dir = _OUTPUT_DIR / project.id
        project_dir.mkdir(parents=True, exist_ok=True)

        output_path = project_dir / "output.mp4"
        status_entry = {
            "status": AssemblyStatus.PREPARING,
            "output_path": str(output_path),
            "duration_sec": 0,
            "shot_count": 0,
            "error": None,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._tasks[project.id] = status_entry

        try:
            shots = self._collect_active_shots(project)
            if not shots:
                status_entry["status"] = AssemblyStatus.FAILED
                status_entry["error"] = "Нет активных шотов для сборки"
                return status_entry

            status_entry["shot_count"] = len(shots)

            # Check ffmpeg
            if not shutil.which("ffmpeg"):
                status_entry["status"] = AssemblyStatus.FAILED
                status_entry["error"] = "ffmpeg не установлен"
                return status_entry

            status_entry["status"] = AssemblyStatus.ASSEMBLING

            # Build video from images using ffmpeg concat
            total_duration = sum(s["duration_sec"] for s in shots)
            status_entry["duration_sec"] = total_duration

            await self._assemble_with_effects(shots, output_path, fps)

            status_entry["status"] = AssemblyStatus.COMPLETE
            status_entry["output_path"] = str(output_path)
            log.info("assembly_done project=%s shots=%d duration=%.1f",
                     project.id, len(shots), total_duration)

        except Exception as e:
            log.error("assembly_failed project=%s error=%s", project.id, e)
            status_entry["status"] = AssemblyStatus.FAILED
            status_entry["error"] = str(e)

        return status_entry

    async def _assemble_concat(
        self,
        shots: list[dict],
        output_path: Path,
        fps: int,
    ):
        """Собрать видео через concat demuxer с изображениями."""
        with tempfile.TemporaryDirectory(prefix="film_assemble_") as tmpdir:
            tmp = Path(tmpdir)

            # Create individual video segments from each image
            concat_entries = []
            for i, shot in enumerate(shots):
                segment_path = tmp / f"segment_{i:04d}.mp4"
                duration = shot["duration_sec"]
                asset_path = shot["asset_path"]

                # Create video segment from image
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(asset_path),
                    "-c:v", "libx264",
                    "-t", str(duration),
                    "-pix_fmt", "yuv420p",
                    "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={fps}",
                    "-r", str(fps),
                    str(segment_path),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    raise RuntimeError(f"ffmpeg segment failed: {stderr.decode()[:500]}")

                concat_entries.append(f"file '{segment_path}'")

            # Write concat list
            concat_file = tmp / "concat.txt"
            concat_file.write_text("\n".join(concat_entries), encoding="utf-8")

            # Concat all segments
            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_path),
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg concat failed: {stderr.decode()[:500]}")

    def get_status(self, project_id: str) -> dict | None:
        """Получить статус сборки проекта."""
        return self._tasks.get(project_id)

    def clear_status(self, project_id: str):
        """Очистить статус сборки."""
        self._tasks.pop(project_id, None)



    def _get_ken_burns_filter(self, movement_type: str, duration: float, fps: int) -> str:
        """Получить ffmpeg filter для Ken Burns эффекта."""
        total_frames = max(1, int(duration * fps))
        
        if movement_type == "slow_dolly_in":
            return f"zoompan=z='min(zoom+0.0015,1.15)':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "slow_dolly_out":
            return f"zoompan=z='if(eq(on,1),1.15,max(zoom-0.0015,1.0))':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "slow_pan":
            return f"zoompan=z='1.1':x='if(eq(on,1),0,min(x+2,192))':y='(ih-oh)/2':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "crane_up":
            return f"zoompan=z='if(eq(on,1),1.2,max(zoom-0.002,1.0))':x='(iw-iw/zoom)/2':y='if(eq(on,1),(ih-ih/zoom)/2,max(y-1,0))':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "orbit":
            return f"zoompan=z='1.05+0.05*sin(2*PI*on/{total_frames})':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "slow_zoom_in":
            return f"zoompan=z='min(zoom+0.0015,1.3)':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "slow_zoom_out":
            return f"zoompan=z='if(eq(on,1),1.3,max(zoom-0.0015,1.0))':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "tracking":
            return f"zoompan=z='1.1':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
        elif movement_type == "follow":
            return f"zoompan=z='1.1':x='if(eq(on,1),0,min(x+1,iw))':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}"
        else:
            return f"zoompan=z='1':d={total_frames}:s=1920x1080:fps={fps}"

    async def _assemble_with_effects(
        self,
        shots: list[dict],
        output_path: Path,
        fps: int,
        crossfade_sec: float = 0.5,
    ):
        """Собрать видео с Ken Burns эффектами и кроссфейдами."""
        with tempfile.TemporaryDirectory(prefix="film_assemble_") as tmpdir:
            tmp = Path(tmpdir)
            
            segment_paths = []
            for i, shot in enumerate(shots):
                segment_path = tmp / f"segment_{i:04d}.mp4"
                duration = shot["duration_sec"]
                asset_path = shot["asset_path"]
                movement = shot.get("movement", "static")
                
                kb_filter = self._get_ken_burns_filter(movement, duration, fps)
                
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(asset_path),
                    "-vf", f"{kb_filter},scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264",
                    "-t", str(duration),
                    "-pix_fmt", "yuv420p",
                    "-r", str(fps),
                    str(segment_path),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    log.warning("ken_burns_segment_%d_failed: %s", i, stderr.decode()[:200])
                    await self._create_simple_segment(asset_path, segment_path, duration, fps)
                
                segment_paths.append(segment_path)
            
            if len(segment_paths) < 2:
                shutil.copy2(segment_paths[0], output_path)
                return
            
            current_input = segment_paths[0]
            cumulative_duration = shots[0]["duration_sec"]
            for i in range(1, len(segment_paths)):
                next_segment = segment_paths[i]
                is_last = (i == len(segment_paths) - 1)
                out_path = output_path if is_last else tmp / f"xfade_{i:04d}.mp4"

                offset = max(0, cumulative_duration - crossfade_sec)
                
                cmd = [
                    "ffmpeg", "-y",
                    "-i", str(current_input),
                    "-i", str(next_segment),
                    "-filter_complex",
                    f"[0:v][1:v]xfade=transition=fade:duration={crossfade_sec}:offset={offset},format=yuv420p",
                    "-c:v", "libx264",
                    "-r", str(fps),
                    "-movflags", "+faststart",
                    str(out_path),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    log.warning("xfade_%d_failed: %s", i, stderr.decode()[:200])
                    shutil.copy2(next_segment, out_path)
                
                current_input = out_path
                cumulative_duration = cumulative_duration + shots[i]["duration_sec"] - crossfade_sec

    async def _create_simple_segment(
        self,
        asset_path: Path,
        output_path: Path,
        duration: float,
        fps: int,
    ):
        """Создать простой сегмент без эффектов (fallback)."""
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(asset_path),
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-vf", f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps={fps}",
            "-r", str(fps),
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg simple segment failed: {stderr.decode()[:500]}")
# Singleton
assembler = ShotAssembler()



