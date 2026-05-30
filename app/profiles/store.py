import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

VALID_CHANNEL_MODES = {"shorts", "videos"}

def ensure_profile_defaults(profile):
    profile.setdefault("channel_url", "")
    profile.setdefault("channel_mode", "shorts")
    profile.setdefault("last_status", "Idle")
    return profile

def normalize_channel_mode(channel_mode):
    clean = (channel_mode or "shorts").strip().lower()
    if clean not in VALID_CHANNEL_MODES:
        raise ValueError("channel_mode must be 'shorts' or 'videos'")
    return clean

def split_channel_urls(channel_url):
    return [line.strip() for line in (channel_url or "").splitlines() if line.strip()]

def normalize_channel_urls(channel_url):
    return "\n".join(split_channel_urls(channel_url))

def load_profiles(data_path):
    path = Path(data_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [ensure_profile_defaults(profile) for profile in data] if isinstance(data, list) else []

def save_profiles(data_path, profiles):
    path = Path(data_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(profiles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

def create_chrome_profiles(data_path, profiles_dir, count, name_prefix, note, group):
    data_path = Path(data_path)
    profiles_dir = Path(profiles_dir)
    profiles_dir.mkdir(parents=True, exist_ok=True)

    existing = load_profiles(data_path)
    start_index = len(existing) + 1
    created = []
    clean_prefix = (name_prefix or "Profile").strip() or "Profile"

    for offset in range(max(0, int(count))):
        profile_id = uuid.uuid4().hex
        profile_path = profiles_dir / profile_id
        profile_path.mkdir(parents=True, exist_ok=True)
        created.append({
            "id": profile_id,
            "name": f"{clean_prefix} {start_index + offset}",
            "note": note or "",
            "group": group or "",
            "type": "Chrome",
            "profile_path": str(profile_path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "channel_url": "",
            "channel_mode": "shorts",
            "last_status": "Idle",
        })

    profiles = existing + created
    save_profiles(data_path, profiles)
    return profiles

def delete_profile_record(data_path, profile_id):
    profiles = load_profiles(data_path)
    kept = []
    deleted = False

    for profile in profiles:
        if profile.get("id") == profile_id:
            deleted = True
            profile_path = Path(profile.get("profile_path", ""))
            if profile_path.exists() and profile_path.is_dir():
                shutil.rmtree(profile_path)
        else:
            kept.append(profile)

    if deleted:
        save_profiles(data_path, kept)
    return deleted

def update_profile_channel(data_path, profile_id, channel_url, channel_mode):
    return update_profile_fields(
        data_path,
        profile_id,
        channel_url=channel_url,
        channel_mode=channel_mode,
    )

def update_profile_fields(data_path, profile_id, note=None, group=None, channel_url=None, channel_mode=None):
    profiles = load_profiles(data_path)
    changed = False
    clean_mode = normalize_channel_mode(channel_mode) if channel_mode is not None else None
    clean_url = normalize_channel_urls(channel_url) if channel_url is not None else None

    for profile in profiles:
        if profile.get("id") == profile_id:
            if note is not None:
                profile["note"] = str(note).strip()
            if group is not None:
                profile["group"] = str(group).strip()
            if clean_url is not None:
                profile["channel_url"] = clean_url
            if clean_mode is not None:
                profile["channel_mode"] = clean_mode
            changed = True
            break

    if changed:
        save_profiles(data_path, profiles)
    return changed

def update_profile_status(data_path, profile_id, status):
    profiles = load_profiles(data_path)
    changed = False
    for profile in profiles:
        if profile.get("id") == profile_id:
            profile["last_status"] = status or "Idle"
            changed = True
            break
    if changed:
        save_profiles(data_path, profiles)
    return changed

def get_assigned_profiles(data_path):
    return [
        profile for profile in load_profiles(data_path)
        if (profile.get("channel_url") or "").strip()
    ]
