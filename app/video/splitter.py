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


class VideoSplitter:
    def __init__(self, ffmpeg_path=r"C:\ffmpeg\bin\ffmpeg.exe"):
        self.ffmpeg_path = str(ffmpeg_path)

    def split_into_equal_parts(self, video_path, duration_seconds, parts=3):
        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(str(source))
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be greater than 0")

        output_dir = source.parent / f"{source.stem}_parts"
        output_dir.mkdir(parents=True, exist_ok=True)
        part_duration = float(duration_seconds) / parts
        results = []

        for index in range(parts):
            part_number = index + 1
            start_at = part_duration * index
            segment_duration = duration_seconds - start_at if part_number == parts else part_duration
            output_path = output_dir / f"{source.stem}_part_{part_number}.mp4"
            self._run_segment(source, output_path, start_at, segment_duration)
            if not output_path.exists():
                raise FileNotFoundError(str(output_path))
            results.append({"part_number": part_number, "file_path": str(output_path)})

        return results

    def _run_segment(self, source, output_path, start_at, segment_duration):
        copy_command = self._build_copy_command(source, output_path, start_at, segment_duration)
        try:
            _run_ffmpeg(copy_command)
            return
        except subprocess.CalledProcessError:
            reencode_command = self._build_reencode_command(source, output_path, start_at, segment_duration)
            _run_ffmpeg(reencode_command)

    def _base_command(self, source, output_path, start_at, segment_duration):
        return [
            self.ffmpeg_path,
            "-y",
            "-ss",
            f"{start_at:.3f}",
            "-i",
            str(source),
            "-t",
            f"{segment_duration:.3f}",
            "-avoid_negative_ts",
            "make_zero",
        ]

    def _build_copy_command(self, source, output_path, start_at, segment_duration):
        return self._base_command(source, output_path, start_at, segment_duration) + [
            "-c",
            "copy",
            str(output_path),
        ]

    def _build_reencode_command(self, source, output_path, start_at, segment_duration):
        return self._base_command(source, output_path, start_at, segment_duration) + [
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
