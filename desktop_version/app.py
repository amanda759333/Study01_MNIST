# -*- coding: utf-8 -*-
"""마우스로 숫자를 직접 써서 인식하는 GUI 프로그램.

왼쪽 검은 칸에 마우스로 숫자를 쓰면, 버튼을 떼는 순간 학습된 CNN이
0~9 중 어떤 숫자인지 맞히고 오른쪽에 확률 막대로 결과를 보여 준다.

실행 방법
    python app.py      (먼저 train.py로 mnist_cnn.pt를 만들어 두어야 한다)
"""

import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import torch
from PIL import Image, ImageDraw

from model import 숫자인식CNN

# 윈도우 콘솔에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 맞춘다.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

기준경로 = Path(__file__).resolve().parent
가중치파일 = 기준경로 / "mnist_cnn.pt"
아이콘파일 = 기준경로 / "손글씨인식.ico"  # 창과 작업 표시줄에 쓸 아이콘

# 작업 표시줄에서 이 프로그램을 가리키는 고유 이름.
# 바로가기(.lnk)에도 똑같은 값을 넣어 두어야, 고정해 둔 아이콘과
# 실행 중인 창이 하나로 묶인다. 바로가기_만들기.ps1 의 $앱ID 와 반드시 같아야 한다.
앱ID = "MnistHandwriting.Recognizer"

캔버스크기 = 280   # 화면에 보이는 그리기 판의 한 변 길이(픽셀)
붓두께 = 20        # 마우스로 그릴 선의 두께
평균 = 0.1307      # 학습할 때 쓴 정규화 값과 반드시 같아야 한다.
표준편차 = 0.3081


def 모델_불러오기(장치):
    """저장된 가중치(mnist_cnn.pt)를 읽어 평가 모드 모델을 돌려준다."""
    if not 가중치파일.exists():
        raise FileNotFoundError(
            f"가중치 파일을 찾을 수 없습니다: {가중치파일}\n"
            "먼저 'python train.py' 를 실행해 학습을 마쳐 주세요."
        )
    모델 = 숫자인식CNN().to(장치)
    모델.load_state_dict(torch.load(가중치파일, map_location=장치))
    모델.eval()  # 드롭아웃을 끄고 예측만 하는 모드
    return 모델


def 그림_전처리(그림):
    """사용자가 그린 큰 그림을 MNIST와 같은 28x28 형식으로 다듬는다.

    MNIST 숫자는 20x20 안에 들어가도록 크기를 맞춘 뒤,
    글씨의 무게중심을 28x28 이미지의 가운데에 놓은 형태다.
    같은 방식으로 맞춰 주면 인식률이 크게 올라간다.
    """
    글씨영역 = 그림.getbbox()  # 흰 획이 있는 최소 사각형 영역
    if 글씨영역 is None:
        return None  # 아무것도 그리지 않은 경우

    잘린그림 = 그림.crop(글씨영역)
    너비, 높이 = 잘린그림.size

    # 가로세로 비율을 지키면서 긴 변을 20픽셀로 맞춘다.
    if 너비 > 높이:
        새너비 = 20
        새높이 = max(1, round(높이 * 20 / 너비))
    else:
        새높이 = 20
        새너비 = max(1, round(너비 * 20 / 높이))
    축소그림 = 잘린그림.resize((새너비, 새높이), Image.LANCZOS)

    # 28x28 검은 바탕의 가운데에 붙인다.
    결과 = Image.new("L", (28, 28), color=0)
    결과.paste(축소그림, ((28 - 새너비) // 2, (28 - 새높이) // 2))

    # 밝기의 무게중심을 정확히 가운데(13.5, 13.5)로 평행 이동한다.
    화소 = list(결과.tobytes())  # 'L' 모드이므로 화소값(0~255)이 순서대로 들어 있다.
    총합 = sum(화소)
    if 총합 > 0:
        x합 = sum((i % 28) * 값 for i, 값 in enumerate(화소))
        y합 = sum((i // 28) * 값 for i, 값 in enumerate(화소))
        이동x = round(13.5 - x합 / 총합)
        이동y = round(13.5 - y합 / 총합)
        결과 = 결과.transform(
            (28, 28), Image.AFFINE, (1, 0, -이동x, 0, 1, -이동y), fillcolor=0
        )
    return 결과


def 확률_계산(모델, 장치, 그림28):
    """28x28 그림을 모델에 넣어 숫자 0~9의 확률 목록을 돌려준다."""
    # 0~255 값을 0~1로 바꾸고 학습 때와 같은 정규화를 적용한다.
    화소 = torch.tensor(list(그림28.tobytes()), dtype=torch.float32) / 255.0
    입력 = ((화소 - 평균) / 표준편차).reshape(1, 1, 28, 28).to(장치)
    with torch.no_grad():  # 예측만 하므로 기울기 계산은 끈다.
        로그확률 = 모델(입력)
    return 로그확률.exp().squeeze(0).tolist()  # 로그 확률 → 실제 확률


class 손글씨인식창:
    """그리기 판과 결과 표시를 담당하는 메인 화면."""

    def __init__(self, 루트, 모델, 장치):
        self.루트 = 루트
        self.모델 = 모델
        self.장치 = 장치
        self.이전좌표 = None  # 선을 이어 그리기 위한 직전 마우스 위치

        루트.title("손글씨 숫자 인식기 (PyTorch CNN)")
        루트.resizable(False, False)
        # 창 왼쪽 위와 작업 표시줄에 전용 아이콘을 표시한다.
        # (아이콘 파일이 없어도 프로그램은 그대로 동작해야 하므로 예외는 넘긴다)
        try:
            루트.iconbitmap(default=str(아이콘파일))
        except Exception:
            pass
        루트.configure(bg="#f4f4f4")

        # 화면에 보이지 않는 그림 사본. 실제 인식은 이 사본으로 한다.
        self.그림 = Image.new("L", (캔버스크기, 캔버스크기), color=0)
        self.그리기 = ImageDraw.Draw(self.그림)

        # ---- 왼쪽: 그리기 영역 ----------------------------------
        왼쪽 = tk.Frame(루트, bg="#f4f4f4")
        왼쪽.grid(row=0, column=0, padx=16, pady=16)

        tk.Label(왼쪽, text="아래 칸에 숫자를 하나 쓰세요",
                 font=("맑은 고딕", 11), bg="#f4f4f4").pack(pady=(0, 8))

        self.캔버스 = tk.Canvas(왼쪽, width=캔버스크기, height=캔버스크기,
                              bg="black", highlightthickness=2,
                              highlightbackground="#888888", cursor="pencil")
        self.캔버스.pack()

        # 마우스 이벤트 연결: 누르기 / 끌기 / 떼기
        self.캔버스.bind("<Button-1>", self.붓_누름)
        self.캔버스.bind("<B1-Motion>", self.붓_이동)
        self.캔버스.bind("<ButtonRelease-1>", self.붓_뗌)

        단추칸 = tk.Frame(왼쪽, bg="#f4f4f4")
        단추칸.pack(pady=10, fill="x")
        tk.Button(단추칸, text="지우기", font=("맑은 고딕", 10),
                  width=12, command=self.지우기).pack(side="left", expand=True)
        tk.Button(단추칸, text="다시 인식", font=("맑은 고딕", 10),
                  width=12, command=self.인식하기).pack(side="right", expand=True)

        # ---- 오른쪽: 결과 영역 ----------------------------------
        오른쪽 = tk.Frame(루트, bg="#f4f4f4")
        오른쪽.grid(row=0, column=1, padx=(0, 20), pady=16, sticky="n")

        tk.Label(오른쪽, text="인식 결과", font=("맑은 고딕", 11),
                 bg="#f4f4f4").pack()
        self.결과글씨 = tk.Label(오른쪽, text="?", font=("맑은 고딕", 64, "bold"),
                              fg="#1a5fb4", bg="#f4f4f4", width=3)
        self.결과글씨.pack()
        self.신뢰도글씨 = tk.Label(오른쪽, text="숫자를 써 보세요",
                               font=("맑은 고딕", 10), fg="#555555", bg="#f4f4f4")
        self.신뢰도글씨.pack(pady=(0, 10))

        # 숫자 0~9별 확률을 보여 주는 막대 10개를 미리 만들어 둔다.
        self.막대들 = []
        self.막대값글씨 = []
        표 = tk.Frame(오른쪽, bg="#f4f4f4")
        표.pack()
        for 숫자 in range(10):
            tk.Label(표, text=str(숫자), font=("맑은 고딕", 10, "bold"),
                     width=2, bg="#f4f4f4").grid(row=숫자, column=0)
            바탕 = tk.Frame(표, width=120, height=14, bg="#dddddd")
            바탕.grid(row=숫자, column=1, pady=2)
            바탕.grid_propagate(False)  # 내부 막대 크기에 따라 줄어들지 않게 고정
            막대 = tk.Frame(바탕, width=1, height=14, bg="#9ec3ec")
            막대.place(x=0, y=0)
            값 = tk.Label(표, text="0.0%", font=("맑은 고딕", 8),
                         width=6, anchor="w", fg="#555555", bg="#f4f4f4")
            값.grid(row=숫자, column=2, padx=(6, 0))
            self.막대들.append(막대)
            self.막대값글씨.append(값)

    # ---- 마우스로 그리는 부분 --------------------------------
    def 붓_누름(self, 사건):
        """마우스를 누른 지점에 점을 하나 찍는다."""
        self.이전좌표 = (사건.x, 사건.y)
        반지름 = 붓두께 // 2
        self.캔버스.create_oval(사건.x - 반지름, 사건.y - 반지름,
                              사건.x + 반지름, 사건.y + 반지름,
                              fill="white", outline="white")
        self.그리기.ellipse([사건.x - 반지름, 사건.y - 반지름,
                          사건.x + 반지름, 사건.y + 반지름], fill=255)

    def 붓_이동(self, 사건):
        """마우스를 끌고 가는 동안 직전 위치와 현재 위치를 선으로 잇는다."""
        if self.이전좌표 is None:
            self.이전좌표 = (사건.x, 사건.y)
            return
        x0, y0 = self.이전좌표
        self.캔버스.create_line(x0, y0, 사건.x, 사건.y, fill="white",
                              width=붓두께, capstyle=tk.ROUND, smooth=True)
        self.그리기.line([x0, y0, 사건.x, 사건.y], fill=255, width=붓두께)
        # 꺾이는 부분이 각지지 않도록 이음새에 원을 하나 더 찍는다.
        반지름 = 붓두께 // 2
        self.그리기.ellipse([사건.x - 반지름, 사건.y - 반지름,
                          사건.x + 반지름, 사건.y + 반지름], fill=255)
        self.이전좌표 = (사건.x, 사건.y)

    def 붓_뗌(self, 사건):
        """마우스 버튼을 떼면 곧바로 인식을 실행한다."""
        self.이전좌표 = None
        self.인식하기()

    # ---- 인식과 화면 갱신 ------------------------------------
    def 인식하기(self):
        """지금 그려진 그림을 전처리해서 모델에 넣고 결과를 표시한다."""
        그림28 = 그림_전처리(self.그림)
        if 그림28 is None:
            self.결과표시(None, [0.0] * 10)
            return
        확률목록 = 확률_계산(self.모델, self.장치, 그림28)
        예측숫자 = max(range(10), key=lambda 숫자: 확률목록[숫자])
        self.결과표시(예측숫자, 확률목록)
        print(f"인식 결과: {예측숫자} (확률 {확률목록[예측숫자] * 100:.1f}%)")

    def 결과표시(self, 예측숫자, 확률목록):
        """큰 숫자, 신뢰도 문구, 확률 막대 10개를 한꺼번에 갱신한다."""
        if 예측숫자 is None:
            self.결과글씨.config(text="?")
            self.신뢰도글씨.config(text="숫자를 써 보세요")
        else:
            self.결과글씨.config(text=str(예측숫자))
            self.신뢰도글씨.config(text=f"신뢰도 {확률목록[예측숫자] * 100:.1f}%")

        for 숫자 in range(10):
            비율 = 확률목록[숫자]
            # 가장 확률이 높은 숫자만 진한 색으로 강조한다.
            self.막대들[숫자].config(width=max(1, int(120 * 비율)),
                                  bg="#1a5fb4" if 숫자 == 예측숫자 else "#9ec3ec")
            self.막대값글씨[숫자].config(text=f"{비율 * 100:.1f}%")

    def 지우기(self):
        """그림과 결과를 모두 초기 상태로 되돌린다."""
        self.캔버스.delete("all")
        self.그리기.rectangle([0, 0, 캔버스크기, 캔버스크기], fill=0)
        self.결과표시(None, [0.0] * 10)


def 작업표시줄_이름_등록():
    """작업 표시줄이 이 프로세스를 전용 프로그램으로 인식하게 만든다.

    venv 로 실행하면 창을 실제로 띄우는 것은 기반 파이썬(pythonw.exe)이라,
    이름을 지정해 두지 않으면 고정해 둔 바로가기와 실행 중인 창이 따로 표시된다.
    창을 만들기 전에 불러야 효과가 있다.
    """
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(앱ID)
    except Exception:
        pass  # 윈도우가 아니거나 실패해도 프로그램 자체는 그대로 동작한다.


def main():
    작업표시줄_이름_등록()
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"■ 사용 장치: {장치}")
    try:
        모델 = 모델_불러오기(장치)
    except FileNotFoundError as 오류:
        # 학습 전이라면 GUI를 띄우지 않고 안내 창만 보여 준 뒤 종료한다.
        임시창 = tk.Tk()
        임시창.withdraw()
        messagebox.showerror("가중치 없음", str(오류))
        임시창.destroy()
        return
    print(f"■ 가중치 불러오기 완료: {가중치파일}")

    루트 = tk.Tk()
    손글씨인식창(루트, 모델, 장치)
    루트.mainloop()


if __name__ == "__main__":
    main()
