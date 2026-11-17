import json
import os
import sys
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding="utf-8")

STUDIO_DIR = os.path.dirname(os.path.abspath(__file__))
QUEUE_JSON_PATH = os.path.join(STUDIO_DIR, "auto_pipeline", "episode_queue.json")
TOKEN_CANDIDATES = [
    os.path.join(STUDIO_DIR, "youtube_token_money_archive.json"),
    os.path.join(os.path.dirname(STUDIO_DIR), "youtube_token_money_archive.json"),
]

PLAYLIST_TITLE = "📺 [전편 연속재생] 머니 아카이브 · 금융사기 & 기업몰락 실화 다큐 정주행"
PLAYLIST_DESC = (
    "영상이 끝나면 다음 화로 자동 연결되는 〈머니 아카이브〉 전편 연속재생 공식 플레이리스트입니다.\n"
    "베어링스 은행 비밀계좌 88888부터 아케고스 빌 황, 조 로우 1MDB, 루나·FTX 50조 증발, "
    "테라노스 엘리자베스 홈즈, 엔론 분식회계, 위워크 60조 거품 붕괴까지 역사상 가장 충격적인 금융 스릴러 실화를 연속으로 시청하세요."
)

SHORTS_PLAYLIST_TITLE = "⚡ [쇼츠 연속재생] 머니 아카이브 · 1분 금융 실화 하이라이트"
SHORTS_PLAYLIST_DESC = "〈머니 아카이브〉의 충격 금융·기업 몰락 실화 하이라이트 쇼츠 연속재생 목록입니다."


def get_youtube():
    token_path = next((p for p in TOKEN_CANDIDATES if os.path.exists(p)), None)
    if not token_path:
        raise FileNotFoundError("youtube_token_money_archive.json 파일을 찾을 수 없습니다.")
    creds = Credentials.from_authorized_user_file(token_path)
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def ensure_playlist(youtube, title: str, description: str, existing_id: str = "") -> str:
    # Check existing playlists on the channel first
    res = youtube.playlists().list(part="snippet,status", mine=True, maxResults=50).execute()
    for item in res.get("items", []):
        if item["id"] == existing_id or item["snippet"]["title"] == title:
            pl_id = item["id"]
            print(f"[기존 재생목록 확인] {title} -> ID: {pl_id}", flush=True)
            return pl_id

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": "public",
        },
    }
    created = youtube.playlists().insert(part="snippet,status", body=body).execute()
    pl_id = created["id"]
    print(f"[신규 재생목록 생성 완료!] {title} -> ID: {pl_id}", flush=True)
    return pl_id


def get_playlist_video_ids(youtube, playlist_id: str) -> list[str]:
    video_ids = []
    page_token = None
    while True:
        res = (
            youtube.playlistItems()
            .list(part="snippet", playlistId=playlist_id, maxResults=50, pageToken=page_token)
            .execute()
        )
        for it in res.get("items", []):
            vid = it["snippet"]["resourceId"].get("videoId")
            if vid:
                video_ids.append(vid)
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def add_video_to_playlist(youtube, playlist_id: str, video_id: str, position: int | None = None):
    snippet = {
        "playlistId": playlist_id,
        "resourceId": {
            "kind": "youtube#video",
            "videoId": video_id,
        },
    }
    if position is not None:
        snippet["position"] = position
    youtube.playlistItems().insert(part="snippet", body={"snippet": snippet}).execute()


def build_series_block(published_eps: list[dict], playlist_id: str, current_vid: str) -> str:
    # Find next episode in binge order (if watching EP07, link to EP06 with &list=..., etc.)
    ordered = sorted(published_eps, key=lambda x: x.get("ep_num", 0), reverse=True)
    next_vid = ordered[0]["longform_video_id"]
    for i, ep in enumerate(ordered):
        if ep.get("longform_video_id") == current_vid:
            next_vid = ordered[(i + 1) % len(ordered)]["longform_video_id"]
            break

    lines = [
        "📺 〈머니 아카이브〉 전편 자동재생 & 정주행 시리즈",
        f"▶️ [전편 연속 자동재생 틀어놓기]: https://www.youtube.com/watch?v={next_vid}&list={playlist_id}",
        f"📂 [전체 재생목록 보기]: https://www.youtube.com/playlist?list={playlist_id}",
    ]
    short_labels = {
        1: "1화 (단돈 1,700원에 파산한 233년 은행 · 비밀계좌 88888)",
        2: "2화 (단 이틀 만에 28조 날린 한국인 · 빌 황 아케고스)",
        3: "3화 (나랏돈 6조 털어 디카프리오 영화 찍은 사기꾼 · 조 로우 1MDB)",
        4: "4화 (11만 원 ➔ 0.01원 사흘 만에 50조 증발 · 루나 권도형 & FTX)",
        5: "5화 (피 한 방울 10조 사기극 · 테라노스 엘리자베스 홈즈)",
        6: "6화 (유령회사 3,000개 미국 7위 제국 위조 · 엔론 파산 실화)",
        7: "7화 (손정의 돈 20조 태워 먹은 월세 사무실 · 위워크 아담 뉴먼)",
        8: "8화 (40년간 주식 0주 사고 85조 꿀꺽 · 버니 매도프 폰지 사기)",
        9: "9화 (필리핀 은행 2.6조 유령 계좌 · 와이어카드 증발 실화)",
    }
    for ep in ordered:
        ep_num = ep.get("ep_num")
        vid = ep.get("longform_video_id")
        label = short_labels.get(ep_num, f"{ep_num}화 ({ep.get('topic', '')[:28]})")
        lines.append(f"👉 {label}: https://www.youtube.com/watch?v={vid}&list={playlist_id}")
    return "\n".join(lines)


def update_video_descriptions_with_playlist(youtube, published_eps: list[dict], playlist_id: str):
    for ep in published_eps:
        vid = ep.get("longform_video_id")
        if not vid:
            continue
        res = youtube.videos().list(part="snippet", id=vid).execute()
        items = res.get("items", [])
        if not items:
            continue
        snippet = items[0]["snippet"]
        old_desc = snippet.get("description", "")
        series_block = build_series_block(published_eps, playlist_id, vid)

        if "📺 〈머니 아카이브〉" in old_desc:
            before, after_part = old_desc.split("📺 〈머니 아카이브〉", 1)
            # Find hashtag line at bottom if present
            after_lines = after_part.splitlines()
            hashtag_lines = [ln for ln in after_lines if ln.strip().startswith("#")]
            new_desc = before.rstrip() + "\n\n" + series_block
            if hashtag_lines:
                new_desc += "\n\n" + "\n".join(hashtag_lines)
        else:
            new_desc = old_desc.rstrip() + "\n\n" + series_block

        snippet["description"] = new_desc
        youtube.videos().update(part="snippet", body={"id": vid, "snippet": snippet}).execute()
        print(f"[설명란 자동재생 링크 업데이트 완료] EP{ep['ep_num']:02d} ({vid})", flush=True)
        time.sleep(0.5)


def update_shorts_descriptions_with_longform(youtube, published_eps: list[dict], long_pl_id: str):
    """Ensure every Shorts description links directly to its full Longform episode & autoplay playlist."""
    marker = "📺 본편 전체보기"
    for ep in published_eps:
        svid = ep.get("shorts_video_id")
        lvid = ep.get("longform_video_id")
        if not svid or not lvid:
            continue
        res = youtube.videos().list(part="snippet", id=svid).execute()
        items = res.get("items", [])
        if not items:
            continue
        snippet = items[0]["snippet"]
        old_desc = snippet.get("description", "")
        link_block = (
            f"{marker} ({ep.get('ep_num')}화 풀버전 다큐): "
            f"https://www.youtube.com/watch?v={lvid}&list={long_pl_id}\n"
            f"📂 전편 연속재생: https://www.youtube.com/playlist?list={long_pl_id}"
        )
        if marker in old_desc:
            before = old_desc.split(marker, 1)[0].rstrip()
            new_desc = (before + "\n\n" + link_block).strip()
        else:
            new_desc = (old_desc.rstrip() + "\n\n" + link_block).strip()
        if new_desc != old_desc:
            snippet["description"] = new_desc
            youtube.videos().update(part="snippet", body={"id": svid, "snippet": snippet}).execute()
            print(f"[쇼츠->본편 유입 링크 업데이트 완료] EP{ep['ep_num']:02d} Shorts ({svid}) -> {lvid}", flush=True)
            time.sleep(0.4)


def sync_playlists():
    youtube = get_youtube()
    with open(QUEUE_JSON_PATH, "r", encoding="utf-8") as f:
        queue = json.load(f)

    long_pl_id = ensure_playlist(
        youtube,
        PLAYLIST_TITLE,
        PLAYLIST_DESC,
        queue.get("longform_playlist_id", ""),
    )
    shorts_pl_id = ensure_playlist(
        youtube,
        SHORTS_PLAYLIST_TITLE,
        SHORTS_PLAYLIST_DESC,
        queue.get("shorts_playlist_id", ""),
    )

    queue["longform_playlist_id"] = long_pl_id
    queue["longform_playlist_url"] = f"https://www.youtube.com/playlist?list={long_pl_id}"
    queue["shorts_playlist_id"] = shorts_pl_id
    queue["shorts_playlist_url"] = f"https://www.youtube.com/playlist?list={shorts_pl_id}"

    published_eps = [
        ep for ep in queue.get("episodes", [])
        if ep.get("status") == "published" and ep.get("longform_video_id")
    ]
    # Sort newest first (EP07 -> EP06 -> ... -> EP01) so clicking the playlist starts with the latest episode and autoplays through all episodes!
    published_eps_newest_first = sorted(published_eps, key=lambda x: x.get("ep_num", 0), reverse=True)

    existing_long_vids = get_playlist_video_ids(youtube, long_pl_id)
    for ep in published_eps_newest_first:
        vid = ep["longform_video_id"]
        if vid not in existing_long_vids:
            pos = 0 if existing_long_vids else None
            add_video_to_playlist(youtube, long_pl_id, vid, position=pos)
            print(f"[본편 재생목록 추가 완료] EP{ep['ep_num']:02d} -> {vid}", flush=True)
            time.sleep(0.5)

    existing_short_vids = get_playlist_video_ids(youtube, shorts_pl_id)
    for ep in published_eps_newest_first:
        svid = ep.get("shorts_video_id")
        if not svid:
            continue
        # Preserve intentionally scheduled Shorts (publishAt set); only publish unscheduled private videos
        v_res = youtube.videos().list(part="status", id=svid).execute()
        v_items = v_res.get("items", [])
        st = v_items[0]["status"] if v_items else {}
        if v_items and st.get("privacyStatus") != "public":
            if st.get("publishAt") or ep.get("shorts_scheduled_publish_at"):
                sched = st.get("publishAt") or ep.get("shorts_scheduled_publish_at")
                print(f"[쇼츠 예약 공개 유지] EP{ep['ep_num']:02d} Shorts ({svid}) -> {sched}", flush=True)
            else:
                youtube.videos().update(
                    part="status",
                    body={
                        "id": svid,
                        "status": {
                            "privacyStatus": "public",
                            "selfDeclaredMadeForKids": False,
                        },
                    },
                ).execute()
                print(f"[쇼츠 즉시 공개 전환 완료!] EP{ep['ep_num']:02d} Shorts ({svid}) -> PUBLIC", flush=True)
                ep.pop("shorts_scheduled_publish_at", None)
        if svid not in existing_short_vids:
            pos = 0 if existing_short_vids else None
            add_video_to_playlist(youtube, shorts_pl_id, svid, position=pos)
            print(f"[쇼츠 재생목록 추가 완료] EP{ep['ep_num']:02d} Shorts -> {svid}", flush=True)
            time.sleep(0.5)

    update_video_descriptions_with_playlist(youtube, published_eps, long_pl_id)
    update_shorts_descriptions_with_longform(youtube, published_eps, long_pl_id)

    with open(QUEUE_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(f"\n[전체 완료] 본편 자동재생 목록: https://www.youtube.com/playlist?list={long_pl_id}", flush=True)
    print(f"[전체 완료] 쇼츠 자동재생 목록: https://www.youtube.com/playlist?list={shorts_pl_id}", flush=True)


if __name__ == "__main__":
    sync_playlists()
