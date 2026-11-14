# 💼 Money Archive Studio v3.0 (머니 아카이브 — 금융·기업 몰락 스릴러 다큐 스튜디오)

수백만 조회수 아웃라이어(Outlier) 검증 공식과 YouTube Studio 실측 데이터를 바탕으로 개편된 **〈머니 아카이브 (`@money-archive-kr`)〉 단일 사건 금융·비즈니스 스릴러 자동 제작·배포 파이프라인 v3.0** 저장소입니다.

* **공식 유튜브 채널**: [머니 아카이브 (@money-archive-kr)](https://www.youtube.com/@money-archive-kr) (`UC2Q7ithCngR3GyV9HfK3u4w`)

---

## 🔥 v3.0 파이프라인 6대 핵심 규격 (오후 6시 자동화 표준)

1. **대중성 100% 단일 기업 몰락·사기 실화 집중 (`auto_pipeline/episode_queue.json`)**:
   * 난해한 파생상품 용어를 제목에서 배제하고, 누구나 1초 만에 이해하는 희대의 단일 실화(`EP04` 테라노스 피 한 방울 10조 사기극, `EP05` FTX 40조 붕괴, `EP06` 엔론, `EP07` 위워크, `EP08` 버니 매도프, `EP09` 와이어카드, `EP10` 루이싱커피, `EP11` 니콜라 수소트럭, `EP12` 테라·루나)를 하루 1편씩 깊게 다룹니다.
2. **8분 미드롤 안전선 코드 강제 (`>= 485초`)**:
   * `generate_ep02_ep03_voice.py`, `build_ep02_ep03_v2.py`, `upload_youtube_api.py` 3단계에서 오디오 `500초+` / 최종 MP4 `485초(8분 05초)+` 미만 시 자동 속도 보정 및 업로드 차단을 수행합니다.
3. **쇼츠 36~45초 클리프행어 절단 (결말·형량 스포일러 금지)**:
   * 쇼츠에서 징역 형량이나 파산 결말까지 다 요약해 주던 구성을 폐기하고, 사기극이 들통나기 직전 절정(36~45초)에서 끊어 시청자가 `[▶ 관련 동영상]`으로 본편을 클릭하게 만듭니다.
4. **하루 1회차 + 본편·쇼츠 2시간 30분 시차 예약 발행 (`publishAt`)**:
   * 한 번에 영상 4개를 동시 투하하던 `upload_today_batch_api.py`를 전면 개편하여, 하루 **단 1회차(18:00 본편 즉시 공개 ➔ 20:30 쇼츠 `+150분` 예약 공개)**만 시차 발행합니다.
5. **가짜 AI 웃는 인물 썸네일 폐기 ➔ 다큐 오브제·현장 썸네일 적용**:
   * EP01의 가짜 AI 트레이더 얼굴(`thumb_smiling_trader.jpg`) 대신 비밀 계좌 `88888` 야간 딜링룸 모니터(`ch3_account_88888_crt.jpg`) 기반 3D `BlackHanSans` 다큐 썸네일로 교체했습니다.
6. **멀티 PC 100% 호환 상대경로 & 상단 유도 댓글(`commentThreads.insert`) 자동 등록**:
   * 번들링된 `branding/fonts/BlackHanSans-Regular.ttf` 및 상대경로 적용으로 `C:\Users\USER` 등 어느 PC에서나 `git pull` 즉시 실행되며, 업로드 직후 `pinned_comment`가 유튜브 댓글창에 자동 등록됩니다.

---

## 🚀 다른 PC(`C:\Users\USER`) 오후 6시 자동화 동기화 & 실행 방법

```powershell
# 1. 최신 v3.0 파이프라인 및 대기열 동기화
git pull origin main

# 2. 내레이션(MP3) + 타임코드(SRT) 생성 (500초+ 미드롤 & 45초 쇼츠 자동 검증)
python generate_ep02_ep03_voice.py ep04_theranos_kr

# 3. 다큐 오브제 기반 3D 바이럴 썸네일 생성
python build_thumbnails_v2.py

# 4. 본편 즉시 공개(18:00) + 쇼츠 +150분 예약 공개(20:30) + 상단 댓글 자동 등록
python upload_today_batch_api.py --stagger-shorts-minutes 150

# 5. EP01 기존 가짜 인물 썸네일을 88888 CRT 다큐 썸네일로 즉시 교체할 때 (1회 실행)
python upload_today_batch_api.py --update-ep01-thumb

# 6. 진행 상태 커밋 & 푸시 (토큰/시크릿 JSON은 .gitignore로 자동 보호)
git add auto_pipeline/episode_queue.json
git commit -m "Publish daily Money Archive v3 episode"
git push origin main
```
