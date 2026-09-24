# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

마우스로 쓴 숫자를 인식하는 PyTorch CNN + Tkinter 프로그램. 윈도우 전용이며 git 저장소가 아니다.

## 가장 중요한 규칙: 모든 것을 한글로

이 프로젝트는 **변수·함수·클래스 이름까지 한글**로 쓴다. 주석, docstring, GUI 문구,
콘솔 출력도 전부 한글이다. 예: `숫자인식CNN`, `그림_전처리`, `확률_계산`, `붓_이동`, `기준경로`.
새 코드를 추가하거나 기존 코드를 고칠 때 이 규칙을 깨지 말 것. 영어 식별자를 섞으면
주변 코드와 이질적이 된다.

## 명령

```
python train.py              # 학습 후 mnist_cnn.pt 저장 (CPU 3에폭 약 3.5분)
python train.py --에폭 10    # 옵션도 한글. --배치크기, --평가배치크기, --학습률
python app.py                # GUI 실행 (mnist_cnn.pt 필요)
python 점검.py               # 검증: MNIST 평가 정확도 + 그린 획 0~9 인식
python 아이콘_만들기.py      # 손글씨인식.ico 재생성
powershell -ExecutionPolicy Bypass -File 바로가기_만들기.ps1   # 바탕 화면 바로가기
```

테스트 프레임워크는 없다. `점검.py`가 유일한 검증 경로이며 두 가지를 독립적으로 확인한다.
하나만 돌리려면 `main()` 대신 `평가_정확도(모델, 장치)` 또는 `그린숫자_인식(모델, 장치)`를
직접 호출하면 된다. 기준선: MNIST 99.1%, 그린 획 10/10.

## 구조와 핵심 불변조건

`model.py`의 `숫자인식CNN` 하나를 `train.py`·`app.py`·`점검.py`가 공유한다. 저장하는 것은
`state_dict`뿐이므로 **모델 구조를 바꾸면 기존 `mnist_cnn.pt`는 못 읽는다** — 구조 변경 시
반드시 재학습해야 한다.

세 파일에 흩어진 두 가지 계약을 깨면 정확도가 조용히 무너진다:

1. **정규화 상수**: `train.py`의 `평균`/`표준편차`(0.1307/0.3081)와 `app.py`의 동명 상수가
   같아야 한다. `점검.py`는 `app.py` 쪽 값을 가져다 쓴다.
2. **전처리 형식**: `app.py`의 `그림_전처리`가 캔버스 그림을 MNIST와 같은 형식
   (획을 잘라내 긴 변 20픽셀로 축소 → 28x28 중앙에 무게중심 정렬)으로 바꾼다.
   이 단계를 생략하거나 단순 리사이즈로 바꾸면 화면 결과가 크게 나빠진다.
   `train.py`가 넣은 회전·이동 증강도 마우스 글씨의 삐뚤어짐을 흡수하려는 같은 목적이다.

`app.py`는 GUI이면서 동시에 **import 가능한 모듈**이다. `점검.py`가 `import app` 후
`그림_전처리`/`확률_계산`/상수들을 빌려 쓰므로, import 시점에 창을 만들거나 가중치를
읽는 코드를 최상위에 두면 안 된다(모든 부수효과는 `main()` 안에 있어야 한다).

## 윈도우 관련 함정 (이미 겪은 것들)

- **`pip install torch` 가 끝나기 전에 실행하면** `OSError: [WinError 1114] ... c10.dll`이 난다.
  DLL이 덜 쓰인 상태일 뿐이고 VC++ 런타임 문제가 아니다. 설치 완료를 기다렸다가 실행할 것.
- **`.ps1` 파일은 UTF-8 BOM으로 저장**해야 한다. Windows PowerShell 5.1은 BOM이 없으면
  한글을 ANSI로 읽어 파싱 에러가 난다.
- 파이썬 스크립트 앞부분의 `sys.stdout.reconfigure(encoding="utf-8")`는 콘솔 한글 깨짐 방지용이다.
- 바로가기는 콘솔 창을 없애기 위해 `python.exe`가 아니라 **`pythonw.exe`**를 대상으로 한다.
  작업 표시줄 고정은 윈도우가 API를 막아 두어 프로그램이 대신 할 수 없고 사용자가 직접 해야 한다.
- **venv의 `pythonw.exe`는 껍데기(launcher)** 라서 창을 실제로 띄우는 것은 자식 프로세스인
  기반 파이썬(`C:\Python313\pythonw.exe`)이다. 그래서 작업 표시줄이 고정된 아이콘과
  실행 중인 창을 같은 것으로 보게 하려면 **앱 ID(AppUserModelID)를 양쪽에 명시**해야 한다:
  `app.py`의 `앱ID` 상수와 `바로가기_만들기.ps1`의 `$앱ID`가 같은 값이어야 하며,
  `app.py`는 창을 만들기 전에 `작업표시줄_이름_등록()`을 부른다.
- `InitPropVariantFromString`은 헤더의 인라인 함수라 `propsys.dll`에서 못 불러온다.
  문자열 PROPVARIANT는 `VT_LPWSTR`로 직접 만들어야 한다(`바로가기_만들기.ps1` 참고).
- 파워셸은 GUI 프로그램인 `pythonw.exe`의 종료를 기다리지 않는다. 종료 코드가 필요한 확인은
  같은 환경의 콘솔용 `python.exe`로 할 것.

## 실행 환경이 둘이다

- 프로젝트 `venv\` (torch 2.14.0+cpu, system-site-packages 사용 안 함) — **기준 환경**.
  바탕 화면 바로가기도 이쪽을 가리킨다.
- 전역 `C:\Python313` (torch 2.14.0+cpu) — venv가 없을 때의 대비책.

패키지를 추가할 때는 venv 쪽에 넣을 것. `바로가기_만들기.ps1`은 venv를 먼저 찾고
없을 때만 PATH의 파이썬으로 넘어가며, 만들기 전에 torch/Pillow/tkinter 존재를 확인한다.

## 생성물 (커밋/공유 대상 아님)

`mnist_cnn.pt`(4.8MB), `data/`(MNIST 원본), `__pycache__/`, `venv/`,
`손글씨인식_미리보기.png`는 모두 명령으로 다시 만들 수 있는 산출물이다.
