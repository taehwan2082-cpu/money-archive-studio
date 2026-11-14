import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import sys
import time

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from upload_youtube_api import (
    DEFAULT_TOKEN_PATH,
    STUDIO_DIR,
    find_client_secrets,
    get_authenticated_service,
    post_top_comment,
    resolve_local_path,
    upload_video,
)

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
EXPECTED_CHANNEL_ID = "UC2Q7ithCngR3GyV9HfK3u4w"
QUEUE_JSON_PATH = os.path.join(STUDIO_DIR, "auto_pipeline", "episode_queue.json")


def update_ep01_non_portrait_thumbnail(youtube):
    ep01_thumb = os.path.join(STUDIO_DIR, "ep01_barings_kr", "EP01_썸네일_v2_머니아카이브_1280x720.jpg")
    if not os.path.exists(ep01_thumb):
        return False
    try:
        youtube.thumbnails().set(
            videoId="dF5BvdauZtM",
            media_body=MediaFileUpload(ep01_thumb, mimetype="image/jpeg"),
        ).execute()
        print("[EP01 썸네일 교체 완료] dF5BvdauZtM -> 88888 비밀계좌 다큐 오브제 썸네일!", flush=True)
        return True
    except HttpError as e:
        print(f"[경고] EP01 썸네일 교체 실패: {e}", flush=True)
        return False


def main():
    parser = argparse.ArgumentParser(description="머니 아카이브 일일 단일 에피소드 v3.0 업로더 (하루 1회차 + 시차 예약)")
    parser.add_argument("--ep-id", default="", help="업로드할 에피소드 폴더명 (비우면 episode_queue.json의 첫 pending 1개 선택)")
    parser.add_argument("--stagger-shorts-minutes", type=int, default=150)
    parser.add_argument("--update-ep01-thumb", action="store_true", help="EP01 가짜 인물 썸네일을 88888 CRT 썸네일로 교체")
    args = parser.parse_args()

    secrets_path = find_client_secrets()
    youtube, ch_id, ch_title = get_authenticated_service(
        client_secrets_path=secrets_path,
        token_path=DEFAULT_TOKEN_PATH,
        expected_channel_id=EXPECTED_CHANNEL_ID,
    )
    print(f"[채널 검증 완료] {ch_title} ({ch_id})", flush=True)

    if args.update_ep01_thumb:
        update_ep01_non_portrait_thumbnail(youtube)
        if not args.ep_id:
            return

    queue = json.load(open(QUEUE_JSON_PATH, "r", encoding="utf-8"))
    target_item = None
    for item in queue["episodes"]:
        if args.ep_id and item["ep_id"] == args.ep_id:
            target_item = item
            break
        if not args.ep_id and item.get("status") == "pending":
            target_item = item
            break

    if not target_item:
        print("[완료] 업로드 대기 중인 pending 에피소드가 없습니다.", flush=True)
        return

    ep_id = target_item["ep_id"]
    prefix = ep_id.split("_")[0]
    cfg_path = os.path.join(STUDIO_DIR, ep_id, f"{prefix}_upload_config.json")
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"업로드 설정 파일이 없습니다: {cfg_path}")

    cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
    cfg_dir = os.path.dirname(cfg_path)

    print(f"\n================ [{ep_id}] v3.0 단일 회차 업로드 시작 ================", flush=True)
    long_id = upload_video(youtube, cfg["longform"], config_dir=cfg_dir, is_longform=True)
    time.sleep(3)

    shorts_meta = dict(cfg["shorts"])
    if long_id not in shorts_meta.get("description", ""):
        shorts_meta["description"] = (
            shorts_meta.get("description", "").rstrip()
            + f"\n\n👉 풀버전 본편 바로가기: https://youtu.be/{long_id}"
        )

    shorts_publish_at = None
    if args.stagger_shorts_minutes > 0:
        target_dt = (datetime.now(timezone.utc) + timedelta(minutes=args.stagger_shorts_minutes)).replace(microsecond=0)
        shorts_publish_at = target_dt.isoformat().replace("+00:00", "Z")

    short_id = upload_video(
        youtube,
        shorts_meta,
        config_dir=cfg_dir,
        is_longform=False,
        publish_at_iso=shorts_publish_at,
    )

    target_item["status"] = "published"
    target_item["longform_video_id"] = long_id
    target_item["shorts_video_id"] = short_id
    if shorts_publish_at:
        target_item["shorts_scheduled_publish_at"] = shorts_publish_at

    with open(QUEUE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(f"\n[완료] {ep_id} 본편({long_id}) 즉시 공개 & 쇼츠({short_id}) 시차 예약 등록 완료!", flush=True)


if __name__ == "__main__":
    main()
