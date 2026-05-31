import shutil
from pathlib import Path

TIKTOK_UPLOAD_CACHE_DIRS = (
    Path("Default") / "IndexedDB" / "https_www.tiktok.com_0.indexeddb.blob",
)


def _directory_size(path):
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += child.stat().st_size
            except OSError:
                pass
    return total


def clean_tiktok_upload_cache(profile_path):
    profile_root = Path(profile_path)
    deleted_bytes = 0
    deleted_paths = []
    errors = []

    for relative_path in TIKTOK_UPLOAD_CACHE_DIRS:
        cache_path = profile_root / relative_path
        if not cache_path.exists():
            continue
        try:
            deleted_bytes += _directory_size(cache_path)
            shutil.rmtree(cache_path)
            deleted_paths.append(str(cache_path))
        except OSError as error:
            errors.append(f"{cache_path}: {error}")

    return {
        "deleted_bytes": deleted_bytes,
        "deleted_paths": deleted_paths,
        "errors": errors,
    }
