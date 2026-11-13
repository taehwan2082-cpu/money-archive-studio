import json
import os
import subprocess
import sys
import time
import urllib.parse
from wsgiref.simple_server import WSGIRequestHandler, make_server

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from upload_youtube_api import SCOPES, find_client_secrets, upload_video

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SECRETS_FALLBACK = os.environ.get(
    "YOUTUBE_CLIENT_SECRETS",
    os.path.join(os.path.expanduser("~"), "Desktop", "건설 AI", "client_secret.json"),
)
TOKEN_PATH = os.path.join(STUDIO_DIR, "youtube_token_money_archive.json")
EXPECTED_CHANNEL_ID = "UC2Q7ithCngR3GyV9HfK3u4w"


class _QuietHandler(WSGIRequestHandler):
    def log_message(self, fmt, *args):
        pass


class _OAuthCallbackApp:
    def __init__(self):
        self.last_request_uri = None

    def __call__(self, environ, start_response):
        start_response("200 OK", [("Content-type", "text/html; charset=utf-8")])
        qs = environ.get("QUERY_STRING", "")
        self.last_request_uri = f"http://{environ['SERVER_NAME']}:{environ['SERVER_PORT']}{environ.get('PATH_INFO','/')}?{qs}"
        html = (
            "<html><head><meta charset='utf-8'><title>머니 아카이브 인증 완료</title></head>"
            "<body style='font-family:sans-serif;background:#0b0f19;color:#fff;text-align:center;padding-top:80px;'>"
            "<h1 style='color:#ffd54f;'>✅ 머니 아카이브 YouTube API 인증 완료!</h1>"
            "<p style='font-size:18px;'>이제 자동으로 EP02·EP03 본편·쇼츠·썸네일 업로드가 진행됩니다.<br>이 창을 닫으셔도 됩니다.</p>"
            "</body></html>"
        )
        return [html.encode("utf-8")]


def pop_browser_foreground(url: str):
    chrome_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for exe in chrome_candidates:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, "--new-window", url])
                return
            except Exception:
                pass
    try:
        os.startfile(url)
    except Exception:
        pass


class _ExclusiveWSGIServer(make_server.__globals__["WSGIServer"]):
    allow_reuse_address = False


def authenticate_visible(client_secrets_path: str, token_path: str, expected_channel_id: str):
    for attempt in range(3):
        creds = None
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
                app = _OAuthCallbackApp()
                # Bind 127.0.0.1 on an OS-guaranteed unused exclusive port (port=0, allow_reuse_address=False)
                server = make_server("127.0.0.1", 0, app, server_class=_ExclusiveWSGIServer, handler_class=_QuietHandler)
                port = server.server_port
                flow.redirect_uri = f"http://localhost:{port}/"
                auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

                print("\n========================================================", flush=True)
                print(f"[AUTH_URL] {auth_url}", flush=True)
                print("========================================================\n", flush=True)
                pop_browser_foreground(auth_url)

                server.handle_request()
                server.server_close()

                if not app.last_request_uri:
                    raise RuntimeError("OAuth 콜백 응답을 받지 못했습니다.")
                os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
                flow.fetch_token(authorization_response=app.last_request_uri)
                creds = flow.credentials

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
                f"[재선택 요청] '{ch_title}'({ch_id}) 채널이 선택되었습니다. 반드시 '머니 아카이브' 브랜드 채널을 선택해 주세요!",
                flush=True,
            )
            if os.path.exists(token_path):
                os.remove(token_path)
            continue

        return youtube, ch_id, ch_title

    raise RuntimeError("머니 아카이브 채널 인증에 실패했습니다.")


def resolve_secrets() -> str:
    try:
        return find_client_secrets()
    except FileNotFoundError:
        if os.path.exists(DEFAULT_SECRETS_FALLBACK):
            return DEFAULT_SECRETS_FALLBACK
        raise


def main():
    secrets_path = resolve_secrets()
    print(f"[OAuth 설정] 클라이언트 시크릿: {secrets_path}", flush=True)

    youtube, ch_id, ch_title = authenticate_visible(
        client_secrets_path=secrets_path,
        token_path=TOKEN_PATH,
        expected_channel_id=EXPECTED_CHANNEL_ID,
    )
    print(f"\n[채널 검증 완료] {ch_title} ({ch_id})", flush=True)

    summary = {"channel_id": ch_id, "channel_title": ch_title, "ep01_thumb_updated": False, "ep02": {}, "ep03": {}}

    # 1. Update EP01 (dF5BvdauZtM) thumbnail to v2 high-CTR version
    ep01_v2_thumb = os.path.join(STUDIO_DIR, "ep01_barings_kr", "EP01_썸네일_v2_머니아카이브_1280x720.jpg")
    if os.path.exists(ep01_v2_thumb):
        try:
            print("\n[EP01 썸네일 v2 교체 중] dF5BvdauZtM...", flush=True)
            youtube.thumbnails().set(
                videoId="dF5BvdauZtM",
                media_body=MediaFileUpload(ep01_v2_thumb, mimetype="image/jpeg"),
            ).execute()
            summary["ep01_thumb_updated"] = True
            print("[EP01 썸네일 v2 교체 완료!]", flush=True)
        except HttpError as e:
            print(f"[경고] EP01 썸네일 교체 실패: {e}", flush=True)

    # 2. Upload EP02 Package (Longform + Thumbnail + Shorts)
    ep02_cfg_path = os.path.join(STUDIO_DIR, "ep02_archegos_kr", "ep02_upload_config.json")
    with open(ep02_cfg_path, "r", encoding="utf-8") as f:
        ep02_cfg = json.load(f)

    print("\n================ [1/2] EP02 빌 황 · 아케고스 업로드 ================", flush=True)
    ep02_long_id = upload_video(youtube, ep02_cfg["longform"])
    summary["ep02"]["longform_id"] = ep02_long_id
    summary["ep02"]["longform_url"] = f"https://youtu.be/{ep02_long_id}"
    time.sleep(3)

    ep02_shorts_meta = dict(ep02_cfg["shorts"])
    ep02_shorts_meta["description"] = (
        ep02_shorts_meta["description"].rstrip()
        + f"\n\n👉 2화 본편 풀버전: https://youtu.be/{ep02_long_id}"
    )
    ep02_shorts_id = upload_video(youtube, ep02_shorts_meta)
    summary["ep02"]["shorts_id"] = ep02_shorts_id
    summary["ep02"]["shorts_url"] = f"https://youtube.com/shorts/{ep02_shorts_id}"
    time.sleep(4)

    # 3. Upload EP03 Package (Longform + Thumbnail + Shorts)
    ep03_cfg_path = os.path.join(STUDIO_DIR, "ep03_jholow_kr", "ep03_upload_config.json")
    with open(ep03_cfg_path, "r", encoding="utf-8") as f:
        ep03_cfg = json.load(f)

    print("\n================ [2/2] EP03 조 로우 · 1MDB 업로드 ================", flush=True)
    ep03_long_id = upload_video(youtube, ep03_cfg["longform"])
    summary["ep03"]["longform_id"] = ep03_long_id
    summary["ep03"]["longform_url"] = f"https://youtu.be/{ep03_long_id}"
    time.sleep(3)

    ep03_shorts_meta = dict(ep03_cfg["shorts"])
    ep03_shorts_meta["description"] = (
        ep03_shorts_meta["description"].rstrip()
        + f"\n\n👉 3화 본편 풀버전: https://youtu.be/{ep03_long_id}"
    )
    ep03_shorts_id = upload_video(youtube, ep03_shorts_meta)
    summary["ep03"]["shorts_id"] = ep03_shorts_id
    summary["ep03"]["shorts_url"] = f"https://youtube.com/shorts/{ep03_shorts_id}"

    out_json = os.path.join(STUDIO_DIR, "upload_results_20261113.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n=== 🎉 금일 2개 컨텐츠 패키지(EP02·EP03) 전체 업로드 완료! ===", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
