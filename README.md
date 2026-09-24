# 손글씨 숫자 인식기

마우스나 손가락으로 쓴 숫자를 CNN(합성곱 신경망)이 0~9 중 하나로 알아맞히는 프로그램이다.
모든 코드와 주석, 화면 문구는 한글로 작성했다. 두 가지 버전이 있다.

**웹 데모: <https://amanda759333.github.io/Study01_MNIST/>** — 설치 없이 브라우저에서 바로 써 볼 수 있다.

## 두 버전 비교

| | `desktop_version/` | `web_version/` |
| --- | --- | --- |
| 기술 | PyTorch + Tkinter | 순수 자바스크립트 (외부 라이브러리 없음) |
| 학습 | 할 수 있다 (`train.py`) | 못 한다 — 데스크톱에서 학습한 결과를 가져다 쓴다 |
| 설치 | 필요 (Python, torch, Pillow) | 필요 없다 — 브라우저만 있으면 된다 |
| 실행 | `python app.py` | 링크를 열거나 로컬 서버로 `index.html` |
| 대상 | 윈도우 전용 | 어디서나 (GitHub Pages 로 배포) |

두 버전은 같은 모델(`desktop_version/model.py` 의 `숫자인식CNN`)을 공유한다. 이 계약과
각 버전의 세부 사항은 [`CLAUDE.md`](CLAUDE.md), [`desktop_version/CLAUDE.md`](desktop_version/CLAUDE.md),
[`web_version/CLAUDE.md`](web_version/CLAUDE.md) 에 있다.

## 데스크톱 버전 시작하기

```
cd desktop_version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
python train.py     # 선택 — 학습이 끝난 mnist_cnn.pt 가 이미 저장소에 포함되어 있다
python app.py        # GUI 실행
```

- 설치가 **완전히 끝난 뒤** 실행해야 한다. 설치 중에 실행하면 DLL이 아직 다 쓰이지 않아
  `OSError: [WinError 1114] ... c10.dll` 같은 오류가 날 수 있다.
- 왼쪽 검은 칸에 마우스로 숫자를 하나 쓰면, 마우스 버튼을 떼는 순간 인식해서 오른쪽에
  예측 숫자와 0~9 확률 막대를 보여 준다. `지우기`로 판을 비우고, `다시 인식`으로 같은
  그림을 한 번 더 판정할 수 있다.
- 성능을 점검하려면 `python 점검.py` — MNIST 평가 정확도와 그린 획 인식 결과를 출력한다.
- 바탕 화면 바로가기: `powershell -ExecutionPolicy Bypass -File 바로가기_만들기.ps1`
  (프로젝트 `venv` 의 `pythonw.exe` 로 실행되어 콘솔 창 없이 앱만 뜬다. 작업 표시줄 고정은
  윈도우 제약으로 바로가기를 오른쪽 클릭해 직접 해야 한다.)

윈도우 관련 함정과 구조·불변조건 같은 자세한 내용은 [`desktop_version/CLAUDE.md`](desktop_version/CLAUDE.md) 를 본다.

## 웹 버전 시작하기

가장 쉬운 방법은 위 데모 링크를 여는 것이다. 로컬에서 띄우려면:

```
cd web_version
python -m http.server 8765
# 브라우저에서 http://localhost:8765 열기
```

`index.html` 을 `file://` 로 직접 열면 ES 모듈이 CORS 에 막혀 동작하지 않으므로
반드시 로컬 서버를 거친다. 이식이 파이썬과 맞는지 확인하려면 `node 점검.mjs`.
자세한 내용은 [`web_version/CLAUDE.md`](web_version/CLAUDE.md) 를 본다.

## 폴더 구조

| 경로 | 설명 |
| --- | --- |
| `desktop_version/` | PyTorch 학습·GUI 인식 프로그램 (윈도우 전용) |
| `web_version/` | 브라우저에서 도는 순수 JS 인식기, GitHub Pages 배포 대상 |
| `venv/` | 두 버전이 함께 쓰는 파이썬 가상환경 (저장소 루트에 위치, 생성물이라 커밋 안 함) |
| `.github/workflows/웹_배포.yml` | main push 시 `web_version` 을 검증 후 GitHub Pages 에 배포 |

## venv 가 루트에 있는 이유

`venv/pyvenv.cfg` 와 `Scripts/pip.exe`·`activate` 에는 만들어질 때의 절대 경로가 박혀 있어
폴더를 옮기면 깨진다. 두 버전(`desktop_version/`, `web_version/도구/`)이 같은 환경을
공유하므로 어느 한쪽 안에 두지 않고 저장소 루트에 둔다.

## 배포 설정

웹 데모 링크가 동작하려면 저장소 **Settings → Pages → Source 를 "GitHub Actions" 로
설정**해야 한다(코드만으로는 바꿀 수 없다). 설정 후 main 에 push 하면
`.github/workflows/웹_배포.yml` 이 `web_version` 을 검증하고 자동으로 배포한다.
