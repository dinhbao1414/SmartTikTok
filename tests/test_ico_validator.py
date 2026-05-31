import tempfile
import unittest
from pathlib import Path

from scripts.validate_ico import is_valid_ico


class IcoValidatorTest(unittest.TestCase):
    def test_accepts_basic_ico_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            icon_path = Path(temp_dir) / "valid.ico"
            payload = b"\x00\x00\x00\x00"
            header = b"\x00\x00\x01\x00\x01\x00"
            entry = bytes([1, 1, 0, 0]) + (1).to_bytes(2, "little") + (32).to_bytes(2, "little")
            entry += len(payload).to_bytes(4, "little") + (22).to_bytes(4, "little")
            icon_path.write_bytes(header + entry + payload)

            self.assertTrue(is_valid_ico(icon_path))

    def test_rejects_jpeg_renamed_to_ico(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            icon_path = Path(temp_dir) / "output.ico"
            icon_path.write_bytes(b"\xff\xd8\xff\xe1" + b"\x00" * 32)

            self.assertFalse(is_valid_ico(icon_path))


if __name__ == "__main__":
    unittest.main()
