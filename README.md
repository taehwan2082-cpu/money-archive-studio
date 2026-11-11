# 💼 Money Archive Studio (머니 아카이브 — 비즈니스·금융 스릴러 다큐 스튜디오)

수백만 조회수 아웃라이어(Outlier) 검증 공식을 적용한 **고단가(고RPM) 기업 몰락 & 금융 사건 스릴러 다큐멘터리 자동 제작 파이프라인** 저장소입니다.

* **공식 유튜브 채널**: [머니 아카이브 (@money-archive-kr)](https://www.youtube.com/@money-archive-kr)
* **핵심 포맷**: 14~15분 2단 에스컬레이션 본편(16:9 Full HD, 미드롤 중간광고 3회 최적화) + 55초 하이라이트 유입용 쇼츠(9:16) 동시 렌더링

---

## 📂 프로젝트 구조

```text
money-archive-studio/
├── branding/                                    # 채널 프로필(800x800), 배너(2560x1440), 구독 워터마크
├── raw_images/                                  # 시네마틱 다큐 장면 원화 & 썸네일 배경 에셋
├── ep01_barings_kr/
│   ├── script_longform_kr.txt                   # 제1화 15분 블록버스터 본편 풀 대본 (베어링스 88888 + 제롬 케르비엘)
│   ├── script_shorts_kr.txt                     # 제1화 60초 쇼츠 내레이션 대본
│   ├── ep01_longform_kr.mp3 / .srt              # 본편 AI 내레이션 오디오 및 타임코드 자막
│   ├── ep01_shorts_kr.mp3 / .srt                # 쇼츠 AI 내레이션 오디오 및 타임코드 자막
│   └── EP01_썸네일_머니아카이브_1280x720.jpg     # 아웃라이어 공식 적용 고클릭률 완성본 썸네일
├── generate_voice_and_srt.py                    # 대본(TXT) ➔ 음성(MP3) + 자막(SRT) 자동 변환기
├── build_finance_sfx.py                         # 금융 스릴러 전용 커스텀 폴리 SFX 6종 합성기
├── build_money_branding.py                      # 채널 프로필·배너·워터마크 자동 렌더링 스크립트
├── build_money_thumbnail.py                     # 1280x720 고대비 다큐 썸네일 생성기
└── build_ep01_cinematic.py                      # 4K Ken Burns + 실시간 부채 카운터 HUD + 오케스트라 믹싱 MP4 빌더
```

---

## 🚀 빠른 실행 순서

```bash
# 1. 내레이션 오디오(MP3) 및 자막(SRT) 생성
python generate_voice_and_srt.py

# 2. 금융 스릴러 전용 효과음(SFX) 6종 생성
python build_finance_sfx.py

# 3. 채널 프로필·배너 및 제1화 썸네일 생성
python build_money_branding.py
python build_money_thumbnail.py

# 4. 제1화 본편(16:9) & 쇼츠(9:16) 시네마틱 MP4 렌더링
python build_ep01_cinematic.py
```
