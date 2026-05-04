import os
import sys
import gzip
import shutil
import argparse
import requests
from datetime import datetime, timedelta, timezone
from tqdm import tqdm

BASE_URL = "https://data.gharchive.org"
DEFAULT_DEST = r"/home/jupyter/git_project/data_extrator/input_data"
CHUNK_SIZE = 1024 * 1024


def download_file(hour_dt: datetime, dest_dir: str) -> str:
    hour = hour_dt.hour
    date_str = hour_dt.strftime("%Y-%m-%d")
    gz_fname = f"{date_str}-{hour}.json.gz"
    json_fname = f"{date_str}-{hour}.json"
    gz_path = os.path.join(dest_dir, gz_fname)
    json_path = os.path.join(dest_dir, json_fname)
    url = f"{BASE_URL}/{gz_fname}"

    if os.path.exists(json_path):
        size_mb = os.path.getsize(json_path) / (1024 * 1024)
        print(f"  [skip]  {json_fname} — already exists ({size_mb:.1f} MB)")
        return "skipped"

    try:
        response = requests.get(url, stream=True, timeout=60)

        if response.status_code == 404:
            print(f"  [skip]  {gz_fname} — not available yet")
            return "skipped"

        response.raise_for_status()
        total_bytes = int(response.headers.get("content-length", 0))

        print(f"  [down]  {gz_fname}")
        with open(gz_path, "wb") as f, tqdm(
            total=total_bytes, unit="B", unit_scale=True,
            unit_divisor=1024, leave=False, desc="          downloading",
        ) as bar:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

    except requests.exceptions.ConnectionError:
        print(f"  [fail]  {gz_fname} — connection error")
        _cleanup(gz_path)
        return "failed"
    except requests.exceptions.Timeout:
        print(f"  [fail]  {gz_fname} — timed out")
        _cleanup(gz_path)
        return "failed"
    except Exception as e:
        print(f"  [fail]  {gz_fname} — {e}")
        _cleanup(gz_path)
        return "failed"

    try:
        print(f"  [unzip] {gz_fname} → {json_fname}")
        with gzip.open(gz_path, "rb") as f_in, open(json_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        os.remove(gz_path)
        size_mb = os.path.getsize(json_path) / (1024 * 1024)
        print(f"  [done]  {json_fname}  ({size_mb:.1f} MB)")
        return "downloaded"

    except gzip.BadGzipFile:
        print(f"  [fail]  {gz_fname} — corrupt file")
        _cleanup(gz_path)
        _cleanup(json_path)
        return "failed"
    except Exception as e:
        print(f"  [fail]  decompression failed — {e}")
        _cleanup(gz_path)
        _cleanup(json_path)
        return "failed"


def _cleanup(path: str):
    if path and os.path.exists(path):
        os.remove(path)


def build_hour_range(start: datetime, end: datetime) -> list:
    start_h = start.replace(minute=0, second=0, microsecond=0)
    end_h = end.replace(minute=0, second=0, microsecond=0)
    hours, c = [], start_h
    while c <= end_h:
        hours.append(c)
        c += timedelta(hours=1)
    return hours


def parse_args():
    parser = argparse.ArgumentParser(
        description="Download GitHub Archive hourly files as plain .json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--date", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument("--hour", type=int, default=None, choices=range(0, 24), metavar="0-23")
    parser.add_argument("--start", type=str, default=None, help='"YYYY-MM-DD HH:MM"')
    parser.add_argument("--end", type=str, default=None, help='"YYYY-MM-DD HH:MM"')
    parser.add_argument("--dest", type=str, default=DEFAULT_DEST)
    return parser.parse_args()


def main():
    args = parse_args()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    if args.start and args.end:
        try:
            start_dt = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(args.end, "%Y-%m-%d %H:%M")
        except ValueError:
            print('ERROR: use "YYYY-MM-DD HH:MM" for --start/--end')
            sys.exit(1)
        mode = f"custom range  {args.start} → {args.end}"

    elif args.date and args.hour is not None:
        try:
            base = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("ERROR: --date must be YYYY-MM-DD")
            sys.exit(1)
        start_dt = base.replace(hour=args.hour)
        end_dt = start_dt
        mode = f"single file   {args.date} hour {args.hour:02d}:00 UTC"

    elif args.date:
        try:
            start_dt = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("ERROR: --date must be YYYY-MM-DD")
            sys.exit(1)
        end_dt = start_dt.replace(hour=23)
        mode = f"full day      {args.date}"

    else:
        end_dt = now_utc.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        start_dt = end_dt - timedelta(hours=23)
        mode = (f"past 24 hours  "
                f"{start_dt.strftime('%Y-%m-%d %H:00')} → "
                f"{end_dt.strftime('%Y-%m-%d %H:00')} UTC")

    hours = build_hour_range(start_dt, end_dt)
    os.makedirs(args.dest, exist_ok=True)

    print()
    print("=" * 60)
    print(f"  Mode        : {mode}")
    print(f"  Files       : {len(hours)}")
    print(f"  Destination : {args.dest}")
    print("=" * 60)
    print()

    counts = {"downloaded": 0, "skipped": 0, "failed": 0}
    for hour_dt in hours:
        counts[download_file(hour_dt, args.dest)] += 1

    print()
    print("=" * 60)
    print(f"  Downloaded : {counts['downloaded']} new file(s)")
    print(f"  Skipped    : {counts['skipped']} already existed")
    print(f"  Failed     : {counts['failed']}")
    print(f"  Location   : {args.dest}")
    if counts["failed"]:
        print("\n  NOTE: failures are usually future hours not yet on gharchive.org")
    print("=" * 60)
    print()

    sys.exit(1 if counts["failed"] > 0 else 0)


if __name__ == "__main__":
    main()





"""
Examples:
  python download_github_archive.py
  python download_github_archive.py --date 2026-02-18
  python download_github_archive.py --date 2026-02-18 --hour 14
  python download_github_archive.py --start "2026-02-18 06:00" --end "2026-02-18 18:00"
  python download_github_archive.py --dest C:/Users/BHARGAV/Desktop/landing

"""