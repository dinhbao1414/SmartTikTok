import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.paths import PROFILES_PATH
from app.profiles.store import load_profiles
from app.tiktok.uploader import TikTokUploader


DEFAULT_VIDEO = r"C:\Users\thedu\Downloads\0528(1).mp4"


def find_profile(profile_id="", profile_path=""):
    profiles = load_profiles(PROFILES_PATH)
    if profile_path:
        return Path(profile_path)
    if profile_id:
        for profile in profiles:
            if profile.get("id") == profile_id:
                return Path(profile["profile_path"])
        raise SystemExit(f"Profile id not found: {profile_id}")
    if not profiles:
        raise SystemExit(f"No profiles found in {PROFILES_PATH}")
    return Path(profiles[0]["profile_path"])


def main():
    parser = argparse.ArgumentParser(description="Test TikTok scheduled upload with an existing Chrome profile.")
    parser.add_argument("--video", default=DEFAULT_VIDEO)
    parser.add_argument("--profile-id", default="")
    parser.add_argument("--profile-path", default="")
    parser.add_argument("--day", type=int, default=30)
    parser.add_argument("--month", type=int, default=None)
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--hour", type=int, default=9)
    parser.add_argument("--minute", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--confirm-post", action="store_true")
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        raise SystemExit(f"Video not found: {video_path}")
    if not args.confirm_post:
        raise SystemExit(
            "This script will click Post/Schedule on TikTok. "
            "Rerun with --confirm-post to continue."
        )

    profile_path = find_profile(args.profile_id, args.profile_path)
    uploader = TikTokUploader(wait_seconds=2, close_delay_seconds=10)
    result = uploader.upload_scheduled(
        profile_path=profile_path,
        video_path=video_path,
        schedule_day=args.day,
        schedule_month=args.month,
        schedule_year=args.year,
        schedule_hour=args.hour,
        schedule_minute=args.minute,
        title=video_path.stem,
        timeout=args.timeout,
    )
    print(result)


if __name__ == "__main__":
    main()
