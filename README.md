# Camera OCR Reader

웹캠으로 책·문서를 촬영해 한국어/영어 텍스트를 추출하고, 별도의 뷰어 창에서 읽기 좋게 보여주는 도구입니다. 메카트로닉스 프로젝트용 "카메라 기반 독서 보조 / 책 스캐너" 입니다.

촬영(capture)과 보기(monitor)는 서로 다른 프로세스로 분리되어 있으며, `stream/` 디렉토리의 JSON 파일을 통해 통신합니다.

---

## 주요 기능

- **멀티프레임 스태킹(super-resolution)** — `c` 키를 누른 순간 직전 N개 프레임을 ECC 정합 후 평균내어 노이즈를 줄이고 해상도를 2~4배로 업스케일합니다.
- **이미지 보정** — CLAHE + 언샤프 마스킹(또는 샤프닝 커널)으로 글자 윤곽을 선명하게 만듭니다.
- **배경 비침(bleed-through) 제거** — 배경 추정 + 적응형 이진화로 종이 뒷면 글자가 비치는 현상을 줄입니다.
- **펼침면 자동 분할** — OCR 텍스트 박스의 가로 분포 히스토그램을 분석해 좌/우 두 페이지를 가르는 세로선을 동적으로 찾습니다.
- **본문 영역 크롭 / 머리말·꼬리말 제거** — 박스를 header/footer/body로 분류해 본문만 잘라냅니다.
- **노이즈 필터링** — 신뢰도(min_confidence) 미만이거나 여백에 떠 있는 단일 글자(비침·잡음)를 결과에서 제거합니다.
- **문단 재구성** — 박스를 줄·문단 단위로 묶고, 좌측 페이지 끝과 우측 페이지 시작 문단을 자연스럽게 이어 붙입니다.
- **한국어 띄어쓰기 교정** — `kiwipiepy`로 OCR 결과의 띄어쓰기를 다시 계산합니다.
- **실시간 뷰어** — Tkinter 창이 `stream/`을 감시하다가 새 페이지가 들어오면 즉시 표시. 창 크기/폰트에 맞춰 동적으로 페이지를 나눕니다.
- **오프라인 재처리 모드** — 카메라 없이 이전에 저장한 `raw.png`로 파이프라인을 다시 돌릴 수 있습니다.

---

## 동작 파이프라인

```
웹캠 스트림
   │  (사용자가 'c' 입력 → 직전 프레임 버퍼를 비동기 워커 큐에 적재)
   ▼
프레임 스태킹 + 업스케일 (ECC 정합)
   ▼
보정 (CLAHE + 언샤프 마스킹 + 배경 비침 제거)
   ▼
레이아웃 분석 (PaddleOCR) → 분할선 계산
   ▼
좌/우 페이지 본문 영역 크롭
   ▼
텍스트 OCR (PaddleOCR) + 신뢰도·여백 노이즈 필터링
   ▼
문단 재구성 + 한국어 띄어쓰기 교정
   ▼
stream/page_XXXX.json 저장  +  stream/metadata.json 갱신
   ▼
monitor.py 뷰어가 변경을 감지해 화면에 표시
```

무거운 처리는 모두 백그라운드 워커 **스레드**에서 돌기 때문에, 촬영 화면은 끊김 없이 계속 동작합니다.

---

## 디렉토리 구조

```
camera/
├─ cfg/
│  ├─ capture_cfg.yaml     # 카메라·OCR·보정·경로 등 메인 설정
│  └─ monitor_config.yml   # 뷰어 폰트 설정
├─ functions/
│  ├─ capture.py           # WebcamCapturer: 촬영·스태킹·분할·OCR 오케스트레이션
│  ├─ enhance.py           # 영상 파일 기반 스태킹 유틸(별도 실험용)
│  └─ ocr/
│     ├─ base.py               # OCREngine 추상 인터페이스
│     ├─ paddle_ocr_engine.py  # PaddleOCR 구현 (단일 엔진)
│     └─ pipeline.py           # 전처리·분할·분류·필터링·문단 재구성 핵심 로직
├─ scripts/
│  ├─ capture.py           # ▶ 촬영 실행 진입점
│  ├─ monitor.py           # ▶ 뷰어 실행 진입점
│  └─ list_cameras.py      # 카메라 인덱스 확인용 유틸리티
├─ scratch/                # 실험용 테스트 스크립트
├─ requirements.txt
└─ (실행 시 자동 생성) data/, stream/, models/, outputs/
```

> `data/`, `stream/`, `models/`, `outputs/` 는 `.gitignore`에 포함되어 있어 저장소에는 올라가지 않습니다.

---

## 설치

Python 3.9+ 권장. 가상환경 사용을 권장합니다.

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

- PaddleOCR 모델은 **최초 실행 시 자동으로 다운로드**됩니다(`~/.paddlex` 및 `models/` 캐시).
- GPU를 쓰려면 환경에 맞는 CUDA 버전의 `torch` / `paddlepaddle-gpu`가 필요합니다. GPU가 없으면 `cfg/capture_cfg.yaml`의 `ocr.gpu`를 `false`로 바꾸세요.

---

## 사용법

### 1. 촬영 (capture)

```bash
python scripts/capture.py
```

웹캠 창이 뜨면:

| 키 | 동작 |
|----|------|
| `c` (또는 `s`) | 현재 프레임 버퍼를 캡처해 스태킹·OCR 처리 큐에 추가 |
| `q` | 종료 |

화면 상단에 `Queue Size`(대기 중 작업 수)와 `Worker` 상태가 표시됩니다. 캡처 결과는 `data/<촬영시각>/<번호>/` 와 `stream/`에 저장됩니다.

### 2. 뷰어 (monitor)

별도의 터미널에서:

```bash
python scripts/monitor.py
```

촬영본이 추가될 때마다 텍스트가 자동으로 누적·표시됩니다.

| 키 | 동작 |
|----|------|
| `←` / `→` | 이전 / 다음 화면 페이지 |
| `+` / `=` / `-` | 글자 크기 조절 (페이지 재계산) |

> 일반적인 흐름: **터미널 두 개를 띄워** 한쪽에서 `monitor.py`로 뷰어를 켜 두고, 다른 쪽에서 `capture.py`로 책장을 넘기며 `c`를 눌러 스캔합니다.

---

## 설정 (`cfg/capture_cfg.yaml`)

주요 항목만 발췌:

```yaml
camera:
  index: 0          # 웹캠 장치 번호
  resolution: { width: 1920, height: 1080 }
  flip: 180         # 0 / 90 / 180 / 270 / "horizontal" / "vertical"

ocr:
  engine: "paddleocr"             # OCR 엔진 (현재 PaddleOCR 단일 엔진)
  languages: ['ko', 'en']
  gpu: false                      # GPU 있으면 true
  min_confidence: 0.6             # 이 신뢰도 미만 텍스트는 노이즈로 제거
  filter_margin_single_char: true # 여백에 떠 있는 단일 글자(비침·잡음) 제거
  margin_ratio: 0.15              # 여백 정의 비율 (바깥 15%)

enhancement:
  strength: "unsharp"             # standard / strong / unsharp
  bleed_through_removal: true     # 종이 뒷면 글자 비침 제거
  stacking:
    enabled: true
    max_frames: 15                # 스태킹할 프레임 수
    scale_factor: 2               # 업스케일 배수 (2=4K, 4=8K)

layout:
  dynamic_split: true             # 펼침면 자동 분할 on/off (단일 페이지면 false)

post_process:
  kiwi_spacing: true              # 한국어 띄어쓰기 교정
  reset_whitespace: true

development:
  reprocess_latest: false         # true면 카메라 대신 마지막 raw.png를 재처리 (오프라인 모드)
```

뷰어 폰트는 `cfg/monitor_config.yml`에서 `font_family` / `font_size`로 조절합니다.

---

## 출력물

캡처 1건당 `data/<세션시각>/<번호>/` 폴더에 생성됩니다:

| 파일 | 내용 |
|------|------|
| `raw.png` | 스태킹 기준이 된 원본 프레임 |
| `enhanced.png` | 스태킹·보정을 거친 고해상도 이미지 |
| `left.png` / `right.png` | 분할된 좌/우 페이지 본문 크롭 |
| `left_context.png` / `right_context.png` | 박스·분류 결과를 그린 디버그 이미지 |
| `ocr.txt` | 최종 추출 텍스트 |
| `bbox.txt` | 검출된 박스별 텍스트 목록 |

뷰어 통신용 파일은 `stream/`에 생성됩니다:

- `page_XXXX.json` — 페이지별 텍스트 페이로드
- `metadata.json` — 최신 페이지 번호(뷰어가 이 파일의 변경을 폴링)

---

## 오프라인 재처리 모드

카메라 없이, 가장 최근 세션 폴더에 저장된 `raw.png`들에 대해 OCR·분할 파이프라인을 다시 돌릴 수 있습니다. 파라미터를 바꿔가며 결과를 비교할 때 유용합니다.

```yaml
development:
  reprocess_latest: true
```

로 바꾼 뒤 `python scripts/capture.py`를 실행하면, `data/`의 최신 세션 폴더에 있는 모든 캡처(`raw.png` 제외 중간 산출물은 지우고)를 다시 처리합니다.

> 기본값은 `false`(실시간 카메라 촬영)입니다. `true`로 두면 카메라를 열지 않고 곧바로 재처리 모드로 들어가니, 다시 촬영하려면 `false`로 되돌리세요.

---

## 문제 해결

- **웹캠이 안 열림** — `camera.index`를 0, 1, 2… 로 바꿔보세요.
- **글자가 뒤집혀 나옴** — `camera.flip` 값을 조정하세요(스캔 받침대 방향에 따라 180이 흔함).
- **GPU 관련 오류 / 너무 느림** — `ocr.gpu`를 `false`로 설정하면 CPU로 동작합니다.
- **단일 페이지 문서인데 좌/우로 잘림** — `layout.dynamic_split: false`로 두면 분할 없이 한 페이지로 처리합니다.
- **띄어쓰기가 어색함** — `kiwipiepy`가 설치되어 있어야 교정이 동작합니다(`requirements.txt`에 포함).
- 모델 첫 다운로드는 시간이 걸릴 수 있습니다(`models/`에 캐시되어 이후엔 빠릅니다).
