# 💼 Money Archive Studio v3.0 (머니 아카이브 — 금융·기업 몰락 스릴러 다큐 스튜디오)

수백만 조회수 아웃라이어(Outlier) 검증 공식과 YouTube Studio 실측 데이터를 바탕으로 구축된 **〈머니 아카이브 (`@money-archive-kr`)〉 금융·비즈니스 스릴러 자동 제작·배포 파이프라인 v3.0** 저장소입니다.

* **공식 유튜브 채널**: [머니 아카이브 (@money-archive-kr)](https://www.youtube.com/@money-archive-kr) (`UC2Q7ithCngR3GyV9HfK3u4w`)

---

## 📺 공개 완료 에피소드 (EP01 ~ EP04)

| 회차 | 폴더 | 본편 (Longform) | 쇼츠 (Shorts) | 핵심 주제 |
| :---: | :--- | :---: | :---: | :--- |
| **EP01** | `ep01_barings_kr` | [`dF5BvdauZtM`](https://youtu.be/dF5BvdauZtM) | [`HRgi7EBKGes`](https://youtube.com/shorts/HRgi7EBKGes) | 233년 베어링스 은행 비밀계좌 `88888` & 케르비엘 9조 증발 실화 |
| **EP02** | `ep02_archegos_kr` | [`gzCdxJrVPPg`](https://youtu.be/gzCdxJrVPPg) | [`Lq-d7zWxrg0`](https://youtube.com/shorts/Lq-d7zWxrg0) | 빌 황 & 아케고스 캐피털 48시간 28조 증발 실화 |
| **EP03** | `ep03_jholow_kr` | [`NwNM_Ow2WLs`](https://youtu.be/NwNM_Ow2WLs) | [`y4LHN2pOjdg`](https://youtube.com/shorts/y4LHN2pOjdg) | 조 로우 & 말레이시아 국부펀드 1MDB 6조 횡령 실화 |
| **EP04** | `ep04_luna_kr` | [`3ivxegZ6BBI`](https://youtu.be/3ivxegZ6BBI) | [`0H-cYDPP7eU`](https://youtube.com/shorts/0H-cYDPP7eU) | 11만 원 ➔ 0.01원 사흘 만에 50조 증발한 루나·권도형 & FTX 몰락 실화 |

---

## 🔥 v3.0 파이프라인 6대 핵심 규격 (오후 6시 무인 자동화)

1. **원클릭 자가 빌드 & 업로드 (`upload_today_batch_api.py`)**:
   * `*_본편.mp4` 대용량 영상이 `.gitignore`로 제외되어 다른 PC(`C:\Users\USER`)에 없더라도, `python upload_today_batch_api.py` 실행 시 자동으로 ① 음성·자막(`generate_ep02_ep03_voice.py`), ② 썸네일(`build_thumbnails_v2.py`), ③ 본편·쇼츠 MP4(`build_daily_episode_v3.py`)를 생성한 뒤 즉시 업로드합니다.
2. **8분 미드롤 안전선 코드 강제 (`>= 485초`)**:
   * 오디오 `500초+` / 최종 MP4 `485초(8분 05초)+` 미만 시 자동 속도 보정 및 업로드 차단을 수행합니다.
3. **쇼츠 9:16 여백 제로(Full-Bleed) + 클리프행어 절단**:
   * 상하 검은 여백 0% 전체화면(`1080x1920`) 및 안전영역 자막을 적용하고, 절정 구간에서 `[▶ 관련 동영상]` 본편 클릭을 유도합니다.
4. **하루 1회차 + 본편·쇼츠 2시간 30분 시차 예약 발행 (`publishAt`)**:
   * 하루 **단 1회차(18:00 본편 즉시 공개 ➔ 20:30 쇼츠 `+150분` 예약 공개)**만 시차 발행합니다.
5. **다큐 오브제·현장 썸네일 (`build_thumbnails_v2.py`)**:
   * 어색한 AI 인물 정면 얼굴을 배제하고, 결정적 물증·폭락 차트·현장 오브제 중심 고대비 썸네일을 생성합니다 (`Pillow` 미설치 PC에서도 `FFmpeg + ASS` 엔진으로 100% 동일하게 동작).
6. **멀티 PC 100% 호환 상대경로 & 토큰 스코프 호환**:
   * 어느 PC에서나 `git pull` 즉시 실행됩니다.

---

## 🚀 다른 PC(`C:\Users\USER`) 오후 6시 자동화 실행 방법

```powershell
# 1. 최신 v3.0 파이프라인 및 대기열 동기화
git pull origin main

# 2. 다음 대기 회차(현재 EP05: ep05_theranos_kr) 자동 빌드(음성·썸네일·MP4) + 시차 업로드 원클릭 실행
python upload_today_batch_api.py --stagger-shorts-minutes 150

# 3. 진행 상태 커밋 & 푸시 (토큰/시크릿 JSON은 .gitignore로 자동 보호)
git add auto_pipeline/episode_queue.json
git commit -m "Publish daily Money Archive v3 episode"
git push origin main
```
