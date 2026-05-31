import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.video.padder import VideoPadder


class VideoPadderTest(unittest.TestCase):
    @patch("app.video.padder.subprocess.run")
    def test_pad_last_frame_to_sixty_one_seconds_with_ffmpeg(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "short.mp4"
            source.write_bytes(b"video")

            def fake_run(command, check, capture_output, text, creationflags=0):
                Path(command[-1]).write_bytes(b"output")
                return subprocess.CompletedProcess(command, 0)

            mock_run.side_effect = fake_run

            result = VideoPadder(r"C:\ffmpeg\bin\ffmpeg.exe").pad_last_frame_to_duration(source, 55, 61)

            self.assertEqual(Path(result).name, "short_padded_61s.mp4")
            self.assertEqual(mock_run.call_count, 2)
            frame_command = mock_run.call_args_list[0].args[0]
            render_command = mock_run.call_args_list[1].args[0]
            self.assertEqual(frame_command[0], r"C:\ffmpeg\bin\ffmpeg.exe")
            self.assertEqual(mock_run.call_args_list[0].kwargs["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.assertIn("-frames:v", frame_command)
            self.assertIn("-loop", render_command)
            self.assertIn("-filter_complex", render_command)
            self.assertIn("concat=n=2:v=1:a=1", " ".join(render_command))
            self.assertIn("61.000", render_command)

    @patch("app.video.padder.subprocess.run")
    def test_does_not_pad_when_duration_already_reaches_target(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "short.mp4"
            source.write_bytes(b"video")

            result = VideoPadder().pad_last_frame_to_duration(source, 61, 61)

            self.assertEqual(result, str(source))
            mock_run.assert_not_called()

    @patch("app.video.padder.subprocess.run")
    def test_extract_last_frame_falls_back_when_seek_near_end_fails(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "short.mp4"
            source.write_bytes(b"video")

            def fake_run(command, check, capture_output, text, creationflags=0):
                if "-frames:v" in command:
                    seek_at = command[command.index("-ss") + 1]
                    if seek_at == "59.900":
                        raise subprocess.CalledProcessError(4294967274, command, stderr="invalid seek")
                    Path(command[-1]).write_bytes(b"frame")
                    return subprocess.CompletedProcess(command, 0)
                Path(command[-1]).write_bytes(b"output")
                return subprocess.CompletedProcess(command, 0)

            mock_run.side_effect = fake_run

            result = VideoPadder(r"C:\ffmpeg\bin\ffmpeg.exe").pad_last_frame_to_duration(source, 60, 61)

            self.assertEqual(Path(result).name, "short_padded_61s.mp4")
            frame_commands = [call.args[0] for call in mock_run.call_args_list if "-frames:v" in call.args[0]]
            self.assertEqual([command[command.index("-ss") + 1] for command in frame_commands], ["59.900", "59.000"])


if __name__ == "__main__":
    unittest.main()
