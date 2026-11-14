import json
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE_DIR, "youtube_token_money_archive.json")
CHANNEL_ID = "UC2Q7ithCngR3GyV9HfK3u4w"
EP01_LONG_ID = "dF5BvdauZtM"
EP01_SHORTS_ID = "HRgi7EBKGes"
EP01_V2_THUMB = os.path.join(BASE_DIR, "ep01_barings_kr", "EP01_썸네일_v2_머니아카이브_1280x720.jpg")


def get_yt():
    creds = Credentials.from_authorized_user_file(TOKEN_PATH)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def main():
    yt = get_yt()

    # 1. Update Channel Branding (Country = KR + Rich Finance Documentary Keywords)
    ch_resp = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()
    ch_item = ch_resp["items"][0]
    branding = ch_item.get("brandingSettings", {})
    ch_cfg = branding.setdefault("channel", {})
    ch_cfg["country"] = "KR"
    ch_cfg["defaultLanguage"] = "ko"
    ch_cfg["keywords"] = (
        '"경제다큐" "기업몰락" "금융실화" "금융사기" "주식" "코인" '
        '"루나" "월스트리트" "실화다큐" "머니아카이브" "투자" "경제역사"'
    )
    # Remove read-only or deprecated sub-keys in image if present (channels.update accepts channel + watch)
    clean_branding = {"channel": ch_cfg}
    yt.channels().update(
        part="brandingSettings",
        body={"id": CHANNEL_ID, "brandingSettings": clean_branding},
    ).execute()
    print("[1/4] 채널 국가(KR) 및 경제·금융 핵심 키워드 세팅 완료!")

    # 2. Update EP01 Longform Title, Category (25), and Searchable Tags
    v_resp = yt.videos().list(part="snippet", id=EP01_LONG_ID).execute()
    snip = v_resp["items"][0]["snippet"]
    new_title = "고작 3천만 원 숨기려다 233년 은행 파산! '닉 리슨 & 케르비엘' 9조 증발 실화"
    new_tags = [
        "닉리슨", "베어링스은행", "제롬케르비엘", "소시에테제네랄", "88888",
        "금융사고", "금융사기", "기업몰락", "경제다큐", "실화다큐", "머니아카이브", "주식", "선물옵션"
    ]
    update_snip = {
        "title": new_title,
        "description": snip["description"],
        "categoryId": "25",
        "tags": new_tags,
        "defaultLanguage": "ko",
        "defaultAudioLanguage": "ko",
    }
    yt.videos().update(
        part="snippet",
        body={"id": EP01_LONG_ID, "snippet": update_snip},
    ).execute()
    print(f"[2/4] EP01 본편({EP01_LONG_ID}) 제목·카테고리(25)·검색태그 업데이트 완료!")

    # 3. Upload Non-AI-Face High-CTR v2 Thumbnail to EP01 Longform
    yt.thumbnails().set(
        videoId=EP01_LONG_ID,
        media_body=MediaFileUpload(EP01_V2_THUMB, mimetype="image/jpeg"),
    ).execute()
    print(f"[3/4] EP01 본편({EP01_LONG_ID}) 고클릭률 v2 맞춤 썸네일 교체 완료!")

    # 4. Align EP01 Shorts Category & Tags into the same Finance Cluster
    s_resp = yt.videos().list(part="snippet", id=EP01_SHORTS_ID).execute()
    if s_resp.get("items"):
        s_snip = s_resp["items"][0]["snippet"]
        yt.videos().update(
            part="snippet",
            body={
                "id": EP01_SHORTS_ID,
                "snippet": {
                    "title": s_snip["title"],
                    "description": s_snip["description"],
                    "categoryId": "25",
                    "tags": ["닉리슨", "베어링스은행", "88888", "금융실화", "경제다큐", "머니아카이브", "쇼츠", "shorts"],
                    "defaultLanguage": "ko",
                    "defaultAudioLanguage": "ko",
                },
            },
        ).execute()
        print(f"[4/4] EP01 쇼츠({EP01_SHORTS_ID}) 금융 카테고리(25)·태그 정렬 완료!")

    # Verify live state
    verify_ch = yt.channels().list(part="brandingSettings", id=CHANNEL_ID).execute()["items"][0]["brandingSettings"]["channel"]
    verify_v = yt.videos().list(part="snippet", id=EP01_LONG_ID).execute()["items"][0]["snippet"]
    print(json.dumps({
        "channel_country": verify_ch.get("country"),
        "channel_keywords": verify_ch.get("keywords"),
        "ep01_title": verify_v.get("title"),
        "ep01_category": verify_v.get("categoryId"),
        "ep01_thumb_url": verify_v.get("thumbnails", {}).get("maxres", verify_v.get("thumbnails", {}).get("high", {})).get("url"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
