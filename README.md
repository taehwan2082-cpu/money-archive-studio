# 💼 Money Archive Studio (머니 아카이브 — 비즈니스·금융 스릴러 다큐 스튜디오 v2.0)

수백만 조회수 아웃라이어(Outlier) 검증 공식과 YouTube Studio 실측 데이터 피드백을 반영한 **고단가(고RPM) 기업 몰락 & 금융 범죄 스릴러 다큐멘터리 자동 제작·배포 파이프라인** 저장소입니다.

* **공식 유튜브 채널**: [머니 아카이브 (@money-archive-kr)](https://www.youtube.com/@money-archive-kr) (`UC2Q7ithCngR3GyV9HfK3u4w`)
* **핵심 포맷 (v2.0)**:
  * **본편 (16:9 Full HD, 10~15분 미드롤 최적화)**: 6막 논스톱 스릴러 구조 + 실시간 손실/레버리지 카운터 HUD + 오케스트라 3막 BGM & 커스텀 폴리 SFX 믹싱
  * **유입용 쇼츠 (9:16 Full-Bleed 1080x1920, 56~58초)**: 상하 검은 여백 0% 전체화면 + 유튜브 Shorts UI 안전영역(Safe Zone) 자막 + 스튜디오 `[관련 동영상]` 본편 직결 브릿지
  * **고클릭률 썸네일 v2 (1280x720)**: `BlackHanSans` 3D 입체 외곽선·수직 그라데이션 + 우상단 숫자 충격 콜아웃 배지

---

## 📂 에피소드 라인업 및 구조

```text
money-archive-studio/
├── branding/                                    # 채널 프로필(800x800), 배너(2560x1440), 구독 워터마크
├── docs/
│   ├── 01_수백만뷰_아웃라이어_분석리포트.md
│   ├── 02_제1화_15분블록버스터_최종기획서.md
│   └── 03_채널조회수_정밀진단_및_v2개선리포트.md    # 스튜디오 실측 데이터 분석 및 5대 개선 내역
├── ep01_barings_kr/                             # EP01: 베어링스 은행 비밀계좌 88888 & 제롬 케르비엘 9조 증발
├── ep02_archegos_kr/                            # EP02: 빌 황 & 아케고스 캐피털 48시간 28조 증발 사건
├── ep03_jholow_kr/                              # EP03: 조 로우 & 말레이시아 국부펀드 1MDB 6조 강탈 사건
├── generate_ep02_ep03_voice.py                  # 대본(TXT) ➔ 내레이션(MP3) + 타임코드(SRT) 생성기
├── build_finance_sfx.py                         # 금융 스릴러 전용 커스텀 폴리 SFX 6종 합성기
├── build_thumbnails_v2.py                       # 3D 입체 그라데이션 + 숫자 콜아웃 썸네일 v2 생성기
├── build_ep02_ep03_v2.py                        # 16:9 본편 + 9:16 풀스크린 안전영역 쇼츠 v2 렌더러
└── upload_youtube_api.py                        # YouTube Data API v3 자동 업로더
```

---

## 🚀 v2.0 파이프라인 빠른 실행 순서

```bash
# 1. 에피소드 내레이션(MP3) 및 타임코드 자막(SRT) 생성
python generate_ep02_ep03_voice.py

# 2. 고클릭률 v2 썸네일 일괄 생성 (EP01 개선본 · EP02 · EP03)
python build_thumbnails_v2.py

# 3. 본편(16:9) 및 여백 제로 안전영역 쇼츠(9:16) 렌더링
python build_ep02_ep03_v2.py --ep both
```
