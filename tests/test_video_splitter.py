import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_splitter import VideoSplitter


class VideoSplitterTest(unittest.TestCase):
    @patch("video_splitter.subprocess.run")
    def test_split_into_three_equal_parts_with_ffmpeg(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "video.mp4"
            source.write_bytes(b"video")

            def fake_run(command, check, capture_output, text):
                Path(command[-1]).write_bytes(b"part")
                return subprocess.CompletedProcess(command, 0)

            mock_run.side_effect = fake_run

            parts = VideoSplitter(r"C:\ffmpeg\bin\ffmpeg.exe").split_into_equal_parts(source, 900)

            self.assertEqual([part["part_number"] for part in parts], [1, 2, 3])
            self.assertEqual([Path(part["file_path"]).name for part in parts], [
                "video_part_1.mp4",
                "video_part_2.mp4",
                "video_part_3.mp4",
            ])
            self.assertEqual(mock_run.call_count, 3)
            first_command = mock_run.call_args_list[0].args[0]
            self.assertEqual(first_command[0], r"C:\ffmpeg\bin\ffmpeg.exe")
            self.assertIn("-ss", first_command)
            self.assertIn("-t", first_command)
            self.assertIn("-c", first_command)

    @patch("video_splitter.subprocess.run")
    def test_split_falls_back_to_reencode_when_copy_fails(self, mock_run):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "video.mp4"
            source.write_bytes(b"video")
            calls = []

            def fake_run(command, check, capture_output, text):
                calls.append(command)
                if "-c" in command and "copy" in command:
                    raise subprocess.CalledProcessError(1, command, stderr="copy failed")
                Path(command[-1]).write_bytes(b"part")
                return subprocess.CompletedProcess(command, 0)

            mock_run.side_effect = fake_run

            parts = VideoSplitter(r"C:\ffmpeg\bin\ffmpeg.exe").split_into_equal_parts(source, 900)

            self.assertEqual(len(parts), 3)
            self.assertGreater(mock_run.call_count, 3)
            self.assertTrue(any("libx264" in command for command in calls))


if __name__ == "__main__":
    unittest.main()
