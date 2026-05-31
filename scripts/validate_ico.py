import sys
from pathlib import Path


def is_valid_ico(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False

    if len(data) < 22 or data[:4] != b"\x00\x00\x01\x00":
        return False

    count = int.from_bytes(data[4:6], "little")
    directory_end = 6 + 16 * count
    if count < 1 or count > 20 or len(data) < directory_end:
        return False

    for index in range(count):
        entry = data[6 + index * 16: 22 + index * 16]
        image_size = int.from_bytes(entry[8:12], "little")
        image_offset = int.from_bytes(entry[12:16], "little")
        if image_size < 1 or image_offset < directory_end:
            return False
        if image_offset + image_size > len(data):
            return False

    return True


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        return 2
    return 0 if is_valid_ico(argv[0]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
