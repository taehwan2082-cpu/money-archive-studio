import argparse
from datetime import datetime, timedelta, timezone
import glob
import json
import os
import subprocess
import sys
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TOKEN_PATH = os.path.join(STUDIO_DIR, "youtube_token_money_archive.json")
MIN_MIDROLL_LONGFORM_SEC = 485.0  # 8m 05s strict mid-roll floor


def resolve_local_path(raw_path: str, config_dir: str = "") -> str:
    if not raw_path:
        return ""
    if os.path.isabs(raw_path) and os.path.exists(raw_path):
        return raw_path
    cand_studio = os.path.join(STUDIO_DIR, raw_path)
    if os.path.exists(cand_studio):
        return cand_studio
    if config_dir:
        cand_cfg = os.path.join(config_dir, raw_path)
        if os.path.exists(cand_cfg):
            return cand_cfg
    return cand_studio


def probe_video_duration_sec(video_path: str) -> float:
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", video_path],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(res.stdout)["format"]["duration"])


def sanitize_yt_text(text: str) -> str:
    return text.replace("<", "〈").replace(">", "〉")


def find_client_secrets(explicit_path: str = "") -> str:
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path
    env_p = os.environ.get("YOUTUBE_CLIENT_SECRETS", "")
    if env_p and os.path.exists(env_p):
        return env_p
    candidates = (
        glob.glob(os.path.join(STUDIO_DIR, "client_secret*.json"))
        + glob.glob(os.path.join(STUDIO_DIR, "oauth_credentials*.json"))
        + glob.glob(os.path.join(os.path.expanduser("~"), "Desktop", "**", "client_secret*.json"), recursive=True)
    )
    if candidates:
        return candidates[0]
    raise FileNotFoundError(
        f"OAuth 클라이언트 시크릿 JSON 파일을 찾을 수 없습니다: {STUDIO_DIR}\\client_secret*.json"
    )


def get_authenticated_service(
    client_secrets_path: str,
    token_path: str,
    expected_channel_id: str = "",
    port: int = 0,
):
    for attempt in range(3):
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            if not creds or not creds.valid:
                print("\n[인증 안내] 브라우저 창이 열리면 계정 로그인 후", flush=True)
                print("반드시 [머니 아카이브] 브랜드 채널을 선택해 권한을 허용해 주세요!\n", flush=True)
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
                creds = flow.run_local_server(
                    port=port,
                    prompt="consent",
                    authorization_prompt_message="인증 URL: {url}",
                    success_message="머니 아카이브 YouTube API 인증이 완료되었습니다! 이제 자동으로 업로드가 시작됩니다. 이 창을 닫으셔도 됩니다.",
                    open_browser=True,
                )
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        youtube = build("youtube", "v3", credentials=creds)
        resp = youtube.channels().list(part="snippet", mine=True).execute()
        items = resp.get("items", [])
        if not items:
            raise RuntimeError("인증된 계정에서 유튜브 채널을 찾을 수 없습니다.")

        ch = items[0]
        ch_id = ch["id"]
        ch_title = ch["snippet"]["title"]
        print(f"[인증 확인] 연결된 채널: {ch_title} ({ch_id})", flush=True)

        if expected_channel_id and ch_id != expected_channel_id:
            print(
                f"[재선택 요청] '{ch_title}'({ch_id}) 채널이 선택되었습니다. "
                "'머니 아카이브' 채널을 다시 선택해 주세요!",
                flush=True,
            )
            if os.path.exists(token_path):
                os.remove(token_path)
            continue

        return youtube, ch_id, ch_title

    raise RuntimeError("머니 아카이브 채널 인증에 실패했습니다.")


def post_top_comment(youtube, video_id: str, comment_text: str):
    if not comment_text.strip():
        return
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment_text}},
                }
            },
        ).execute()
        print(f"  [상단 댓글 등록 완료] ({video_id})", flush=True)
    except HttpError as e:
        print(f"  [참고] 상단 댓글 자동 등록 건너뜀 ({video_id}): {e}", flush=True)


def upload_video(
    youtube,
    meta: dict,
    config_dir: str = "",
    is_longform: bool = False,
    publish_at_iso: str | None = None,
) -> str:
    video_file = resolve_local_path(meta["video_file"], config_dir=config_dir)
    if not os.path.exists(video_file):
        raise FileNotFoundError(f"동영상 파일을 찾을 수 없습니다: {video_file}")

    dur_sec = probe_video_duration_sec(video_file)
    if is_longform and dur_sec < MIN_MIDROLL_LONGFORM_SEC:
        raise RuntimeError(
            f"[업로드 차단] 본편 영상 길이({dur_sec:.1f}초)가 유튜브 중간광고 안전 기준({MIN_MIDROLL_LONGFORM_SEC:.0f}초 / 8분 05초) 미만입니다! "
            f"대본 및 음성을 보강한 뒤 다시 업로드하세요."
        )

    file_mb = os.path.getsize(video_file) / (1024 * 1024)
    clean_title = sanitize_yt_text(meta["title"])[:100]
    clean_desc = sanitize_yt_text(meta["description"])
    print(f"\n[업로드 시작] 파일: {os.path.basename(video_file)} ({file_mb:.2f} MB, {dur_sec:.1f}s)", flush=True)
    print(f"[제목] {clean_title}", flush=True)

    status_body = {
        "privacyStatus": "private" if publish_at_iso else meta.get("privacy_status", "public"),
        "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
        "containsSyntheticMedia": bool(meta.get("contains_synthetic_media", True)),
    }
    if publish_at_iso:
        status_body["publishAt"] = publish_at_iso
        print(f"[예약 공개 설정] publishAt = {publish_at_iso}", flush=True)

    body = {
        "snippet": {
            "title": clean_title,
            "description": clean_desc,
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "27"),
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": status_body,
    }

    media = MediaFileUpload(
        video_file,
        mimetype="video/mp4",
        chunksize=10 * 1024 * 1024,  # 10 MB resumable chunks
        resumable=True,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    last_pct = -1
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            if pct >= last_pct + 10:
                print(f"  -> 업로드 진행률: {pct}%", flush=True)
                last_pct = pct

    video_id = response["id"]
    print(f"\n[동영상 업로드 성공!] Video ID: {video_id}", flush=True)
    print(f"  - 시청 링크: https://youtu.be/{video_id}", flush=True)
    print(f"  - 스튜디오 링크: https://studio.youtube.com/video/{video_id}/edit", flush=True)

    thumb_file = resolve_local_path(meta.get("thumbnail_file", ""), config_dir=config_dir)
    if thumb_file and os.path.exists(thumb_file):
        print(f"[썸네일 적용 시도] {os.path.basename(thumb_file)}", flush=True)
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_file, mimetype="image/jpeg"),
            ).execute()
            print("[썸네일 적용 완료!]", flush=True)
        except HttpError as e:
            print(f"[참고] 맞춤 썸네일 API 적용 건너뜀: {e}", flush=True)

    # Auto-post top comment ONLY when immediately public (scheduled private videos reject public comments until live)
    pinned_comment = meta.get("pinned_comment", "")
    if pinned_comment and not publish_at_iso and status_body["privacyStatus"] == "public":
        post_top_comment(youtube, video_id, pinned_comment)

    return video_id


def main():
    parser = argparse.ArgumentParser(description="머니 아카이브 공식 YouTube Data API v3 자동 업로더 (v3.0 시차 발행 지원)")
    parser.add_argument("--config", default=os.path.join(STUDIO_DIR, "ep03_jholow_kr", "ep03_upload_config.json"))
    parser.add_argument("--target", choices=["longform", "shorts", "both"], default="both")
    parser.add_argument(
        "--stagger-shorts-minutes",
        type=int,
        default=150,
        help="본편 공개 후 쇼츠 예약 공개까지 대기 시간(분). 기본 150분(18:00 본편 -> 20:30 쇼츠). 0이면 즉시 동시 공개.",
    )
    parser.add_argument("--client-secrets", default="")
    parser.add_argument("--token", default=DEFAULT_TOKEN_PATH)
    parser.add_argument("--auth-only", action="store_true")
    args = parser.parse_args()

    cfg_abs = resolve_local_path(args.config)
    cfg_dir = os.path.dirname(cfg_abs)
    with open(cfg_abs, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    secrets_path = find_client_secrets(args.client_secrets)
    youtube, ch_id, ch_title = get_authenticated_service(
        client_secrets_path=secrets_path,
        token_path=args.token,
        expected_channel_id=cfg.get("expected_channel_id", ""),
    )

    if args.auth_only:
        print("[인증 테스트 완료] 이제 언제든 클릭 0번으로 업로드할 수 있습니다!", flush=True)
        return

    results = {}
    long_id = ""
    if args.target in ("longform", "both"):
        long_id = upload_video(youtube, cfg["longform"], config_dir=cfg_dir, is_longform=True)
        results["longform"] = long_id
        if args.target == "both":
            time.sleep(3)

    if args.target in ("shorts", "both"):
        shorts_meta = dict(cfg["shorts"])
        if long_id and long_id not in shorts_meta.get("description", ""):
            shorts_meta["description"] = (
                shorts_meta.get("description", "").rstrip()
                + f"\n\n👉 풀버전 본편 바로가기: https://youtu.be/{long_id}"
            )

        shorts_publish_at = None
        if args.target == "both" and args.stagger_shorts_minutes > 0:
            kst = timezone(timedelta(hours=9))
            target_dt = (datetime.now(timezone.utc) + timedelta(minutes=args.stagger_shorts_minutes)).replace(microsecond=0)
            shorts_publish_at = target_dt.isoformat().replace("+00:00", "Z")
            print(
                f"[시차 예약] 쇼츠가 {args.stagger_shorts_minutes}분 뒤 "
                f"({target_dt.astimezone(kst).strftime('%Y-%m-%d %H:%M KST')}) 자동 공개됩니다.",
                flush=True,
            )

        results["shorts"] = upload_video(
            youtube,
            shorts_meta,
            config_dir=cfg_dir,
            is_longform=False,
            publish_at_iso=shorts_publish_at,
        )
        if shorts_publish_at:
            results["shorts_publish_at"] = shorts_publish_at

    print("\n=== 최종 업로드 결과 요약 ===", flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
