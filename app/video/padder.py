import subprocess
from pathlib import Path

def _run_ffmpeg(command):
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class VideoPadder:
    def __init__(self, ffmpeg_path=r"C:\ffmpeg\bin\ffmpeg.exe"):
        self.ffmpeg_path = str(ffmpeg_path)

    def pad_last_frame_to_duration(self, video_path, duration_seconds, target_seconds=61):
        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(str(source))

        duration = float(duration_seconds or 0)
        target = float(target_seconds or 61)
        if duration <= 0:
            raise ValueError("duration_seconds must be greater than 0")
        if duration >= target:
            return str(source)

        output_dir = source.parent / f"{source.stem}_padded"
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_path = output_dir / f"{source.stem}_last_frame.jpg"
        output_path = output_dir / f"{source.stem}_padded_{int(target)}s.mp4"

        self._extract_last_frame(source, frame_path, duration)
        self._render_padded_video(source, frame_path, output_path, target - duration, target)
        if not output_path.exists():
            raise FileNotFoundError(str(output_path))
        return str(output_path)

    def _extract_last_frame(self, source, frame_path, duration):
        last_error = None
        for seek_at in self._last_frame_seek_candidates(duration):
            if frame_path.exists():
                frame_path.unlink()
            command = [
                self.ffmpeg_path,
                "-y",
                "-ss",
                f"{seek_at:.3f}",
                "-i",
                str(source),
                "-frames:v",
                "1",
                str(frame_path),
            ]
            try:
                _run_ffmpeg(command)
            except subprocess.CalledProcessError as error:
                last_error = error
                continue
            if frame_path.exists():
                return

        if last_error is not None:
            raise last_error
        raise FileNotFoundError(str(frame_path))

    def _last_frame_seek_candidates(self, duration):
        duration = max(0.0, float(duration or 0))
        candidates = []
        seen = set()
        for offset in (0.1, 1.0, 2.0, 3.0, 5.0):
            seek_at = max(0.0, duration - offset)
            key = f"{seek_at:.3f}"
            if key not in seen:
                candidates.append(seek_at)
                seen.add(key)
        return candidates

    def _render_padded_video(self, source, frame_path, output_path, pad_seconds, target_seconds):
        command = self._build_audio_command(source, frame_path, output_path, pad_seconds, target_seconds)
        try:
            _run_ffmpeg(command)
            return
        except subprocess.CalledProcessError:
            fallback = self._build_no_audio_command(source, frame_path, output_path, pad_seconds, target_seconds)
            _run_ffmpeg(fallback)

    def _build_audio_command(self, source, frame_path, output_path, pad_seconds, target_seconds):
        return [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(source),
            "-loop",
            "1",
            "-t",
            f"{pad_seconds:.3f}",
            "-i",
            str(frame_path),
            "-f",
            "lavfi",
            "-t",
            f"{pad_seconds:.3f}",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-filter_complex",
            "[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v0];"
            "[0:a]asetpts=PTS-STARTPTS[a0];"
            "[1:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v1];"
            "[2:a]asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            f"{target_seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(output_path),
        ]

    def _build_no_audio_command(self, source, frame_path, output_path, pad_seconds, target_seconds):
        return [
            self.ffmpeg_path,
            "-y",
            "-i",
            str(source),
            "-loop",
            "1",
            "-t",
            f"{pad_seconds:.3f}",
            "-i",
            str(frame_path),
            "-filter_complex",
            "[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v0];"
            "[1:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v1];"
            "[v0][v1]concat=n=2:v=1:a=0[v]",
            "-map",
            "[v]",
            "-an",
            "-t",
            f"{target_seconds:.3f}",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            str(output_path),
        ]
