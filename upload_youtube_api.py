import argparse
import glob
import json
import os
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
]

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TOKEN_PATH = os.path.join(STUDIO_DIR, "youtube_token_money_archive.json")


def find_client_secrets(explicit_path: str = "") -> str:
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path
    candidates = (
        glob.glob(os.path.join(STUDIO_DIR, "client_secret*.json"))
        + glob.glob(os.path.join(STUDIO_DIR, "oauth_credentials.json"))
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
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                print("\n[인증 안내] 브라우저 창이 열리면 taehwan2082@gmail.com 로그인 후", flush=True)
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


def upload_video(youtube, meta: dict) -> str:
    video_file = meta["video_file"]
    if not os.path.exists(video_file):
        raise FileNotFoundError(f"동영상 파일을 찾을 수 없습니다: {video_file}")

    file_mb = os.path.getsize(video_file) / (1024 * 1024)
    print(f"\n[업로드 시작] 파일: {os.path.basename(video_file)} ({file_mb:.2f} MB)", flush=True)
    print(f"[제목] {meta['title']}", flush=True)

    body = {
        "snippet": {
            "title": meta["title"],
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": meta.get("category_id", "27"),
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": meta.get("privacy_status", "public"),
            "selfDeclaredMadeForKids": bool(meta.get("made_for_kids", False)),
            "containsSyntheticMedia": bool(meta.get("contains_synthetic_media", True)),
        },
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
            if pct >= last_pct + 5:
                print(f"  -> 업로드 진행률: {pct}%", flush=True)
                last_pct = pct

    video_id = response["id"]
    print(f"\n[동영상 업로드 성공!] Video ID: {video_id}", flush=True)
    print(f"  - 시청 링크: https://youtu.be/{video_id}", flush=True)
    print(f"  - 스튜디오 링크: https://studio.youtube.com/video/{video_id}/edit", flush=True)

    thumb_file = meta.get("thumbnail_file", "")
    if thumb_file and os.path.exists(thumb_file):
        print(f"[썸네일 적용 시도] {os.path.basename(thumb_file)}", flush=True)
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_file, mimetype="image/jpeg"),
            ).execute()
            print("[썸네일 적용 완료!]", flush=True)
        except HttpError as e:
            print(
                f"[참고] 맞춤 썸네일 API 적용 건너뜀 (채널 전화번호 중간 기능 인증 필요 가능성): {e}",
                flush=True,
            )

    return video_id


def main():
    parser = argparse.ArgumentParser(description="머니 아카이브 공식 YouTube Data API v3 자동 업로더")
    parser.add_argument("--config", default=os.path.join(STUDIO_DIR, "ep01_barings_kr", "ep01_upload_config.json"))
    parser.add_argument("--target", choices=["longform", "shorts", "both"], default="longform")
    parser.add_argument("--client-secrets", default="")
    parser.add_argument("--token", default=DEFAULT_TOKEN_PATH)
    parser.add_argument("--auth-only", action="store_true")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
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
    if args.target in ("longform", "both"):
        results["longform"] = upload_video(youtube, cfg["longform"])
        if args.target == "both":
            time.sleep(3)
    if args.target in ("shorts", "both"):
        results["shorts"] = upload_video(youtube, cfg["shorts"])

    print("\n=== 최종 업로드 결과 요약 ===", flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
