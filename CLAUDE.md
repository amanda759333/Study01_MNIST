# CLAUDE.md

마우스나 손가락으로 쓴 숫자를 인식하는 CNN 프로그램. 두 버전이 있다.

| 폴더 | 무엇인가 |
| --- | --- |
| `desktop_version/` | PyTorch + Tkinter. 학습과 인식을 모두 한다. 윈도우 전용. |
| `web_version/` | 외부 라이브러리 없는 순수 자바스크립트. 인식만 한다. GitHub Pages 에 올라간다. |

각 폴더의 `CLAUDE.md` 에 그 버전의 명령·구조·함정이 있다. **먼저 그쪽을 읽을 것.**
이 파일에는 두 버전에 공통으로 걸리는 것만 둔다.

## 가장 중요한 규칙: 모든 것을 한글로

이 프로젝트는 **변수·함수·클래스 이름까지 한글**로 쓴다. 주석, docstring, GUI 문구,
콘솔 출력도 전부 한글이다. 예: `숫자인식CNN`, `그림_전처리`, `확률_계산`, `붓_이동`, `기준경로`.
**자바스크립트도 예외가 아니다.** 파일명도 한글로 쓴다(`index.html` 만 GitHub Pages
요구로 영문이다). 새 코드를 추가하거나 기존 코드를 고칠 때 이 규칙을 깨지 말 것.

## 새 파일에는 작성일시 주석

새로 만드는 파일은 맨 위에 작성 날짜와 시각을 주석으로 적는다. 형식은
`작성일시: YYYY-MM-DD HH:MM (KST)` 이고, 파일 형식에 맞는 주석 문법을 쓴다.
파이썬은 인코딩 선언 아래, 마크다운은 HTML 주석, JS 는 `//`, CSS 는 `/* */`, YAML 은 `#`.

시각은 **항상 대한민국 표준시(KST)**로 적는다. 짐작하지 말고 만드는 시점에 확인한다.

```powershell
[System.TimeZoneInfo]::ConvertTimeBySystemTimeZoneId([DateTime]::UtcNow, 'Korea Standard Time').ToString('yyyy-MM-dd HH:mm')
```

**Git Bash 의 `TZ=Asia/Seoul date` 는 이 환경에서 9시간 어긋난다.** 위 PowerShell 명령만 쓸 것.

이미 있는 파일을 고칠 때는 이 줄을 건드리지 않는다(최초 작성 시각으로 고정).

## 두 버전에 걸친 계약 (깨면 정확도가 조용히 무너진다)

두 버전은 같은 모델을 공유한다. 한쪽만 고치면 다른 쪽이 조용히 어긋난다.

1. **모델 구조를 바꾸면 양쪽을 다 손봐야 한다.**
   `desktop_version/model.py` 의 `숫자인식CNN` 을 바꾸면
   ① `train.py` 로 재학습해 `mnist_cnn.pt` 를 다시 만들고
   ② `web_version/도구/내보내기.py` 로 웹 가중치를 다시 내보내고
   ③ `web_version/모델.js` 의 순전파도 같이 고쳐야 한다.
   (`내보내기.py` 는 텐서 이름·순서가 다르면 멈추므로 ②를 잊으면 드러난다)

2. **정규화 상수가 세 곳에 있다.** `평균 = 0.1307`, `표준편차 = 0.3081` 이
   `desktop_version/train.py`, `desktop_version/app.py`, `web_version/모델.js` 에
   각각 있다. 셋이 같아야 한다.

3. **전처리가 두 곳에 쌍으로 있다.** `desktop_version/app.py` 의 `그림_전처리` 와
   `web_version/전처리.js` 의 `그림_전처리` 는 같은 일을 한다.
   한쪽만 고치면 안 된다. 고친 뒤에는 `web_version` 에서 `node 점검.mjs` 를 돌린다.

## venv 는 저장소 루트에 있다

`venv/pyvenv.cfg` 와 `Scripts/pip.exe`·`activate` 에 절대 경로가 박혀 있어
**폴더를 옮기면 깨진다.** 그래서 `desktop_version/` 안이 아니라 루트에 둔다.
파이썬 실행은 `./venv/Scripts/python.exe` 로 한다.

## 검증

각 버전에 검증 스크립트가 하나씩 있다. 테스트 프레임워크는 없다.

```
cd desktop_version && ../venv/Scripts/python.exe 점검.py   # MNIST 정확도 + 그린 획 10개
cd web_version && node 점검.mjs                            # JS 이식이 파이썬과 맞는가
```

기준선은 각 폴더의 `CLAUDE.md` 에 있다.
