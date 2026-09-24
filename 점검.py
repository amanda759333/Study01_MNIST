# -*- coding: utf-8 -*-
"""저장된 가중치(mnist_cnn.pt)가 제대로 동작하는지 GUI 없이 확인하는 스크립트.

두 가지를 확인한다.
  1) MNIST 평가 데이터 1만 장에 대한 정확도
  2) 마우스로 그린 것처럼 굵은 획으로 만든 숫자 그림의 인식 결과
     (app.py 의 전처리·예측 함수를 그대로 불러 쓴다)

실행 방법
    python 점검.py
"""

import sys

import torch
from PIL import Image, ImageDraw
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

import app  # GUI를 띄우지 않고 전처리/예측 함수만 빌려 쓴다.
from model import 숫자인식CNN

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def 평가_정확도(모델, 장치):
    """MNIST 평가 데이터 전체에 대한 정확도를 계산해 출력한다."""
    변환 = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((app.평균,), (app.표준편차,)),
    ])
    평가셋 = datasets.MNIST(root=str(app.기준경로 / "data"), train=False,
                          download=True, transform=변환)
    로더 = DataLoader(평가셋, batch_size=1000, shuffle=False)

    맞힌개수 = 0
    with torch.no_grad():
        for 이미지, 정답 in 로더:
            이미지, 정답 = 이미지.to(장치), 정답.to(장치)
            맞힌개수 += (모델(이미지).argmax(dim=1) == 정답).sum().item()

    전체 = len(평가셋)
    print(f"■ MNIST 평가 정확도: {맞힌개수}/{전체} ({100.0 * 맞힌개수 / 전체:.2f}%)")
    return 100.0 * 맞힌개수 / 전체


def 손글씨_그리기(숫자):
    """마우스로 쓴 것과 비슷하게 280x280 판에 굵은 획으로 숫자를 그린다.

    실제 GUI에서 사람이 그리는 상황을 대신 흉내내는 용도다.
    """
    그림 = Image.new("L", (app.캔버스크기, app.캔버스크기), 0)
    붓 = ImageDraw.Draw(그림)
    두께 = app.붓두께

    # 숫자별로 획을 좌표로 직접 지정한다. (선분 목록 또는 호 정보)
    획모음 = {
        0: [("타원", (80, 50, 200, 230))],
        1: [("선", [(140, 50), (140, 230)]), ("선", [(110, 80), (140, 50)])],
        2: [("선", [(90, 90), (120, 55), (170, 60), (180, 105), (95, 225)]),
            ("선", [(95, 225), (195, 225)])],
        3: [("선", [(95, 65), (170, 55), (175, 125), (120, 135)]),
            ("선", [(120, 135), (180, 150), (170, 220), (95, 225)])],
        4: [("선", [(160, 50), (85, 165), (200, 165)]), ("선", [(160, 110), (160, 235)])],
        5: [("선", [(190, 60), (100, 60), (95, 130), (165, 140), (175, 200), (95, 220)])],
        6: [("선", [(180, 60), (105, 130), (100, 200), (150, 225), (180, 185),
                    (140, 150), (100, 175)])],
        7: [("선", [(85, 60), (195, 60), (120, 230)])],
        8: [("타원", (95, 50, 190, 135)), ("타원", (90, 135, 195, 230))],
        9: [("타원", (95, 50, 185, 140)), ("선", [(185, 95), (170, 230)])],
    }

    for 종류, 값 in 획모음[숫자]:
        if 종류 == "선":
            붓.line([좌표 for 점 in 값 for 좌표 in 점], fill=255, width=두께,
                   joint="curve")
        else:
            붓.ellipse(값, outline=255, width=두께)
    return 그림


def 그린숫자_인식(모델, 장치):
    """0~9를 차례로 그려서 모델이 몇 개를 맞히는지 확인한다."""
    print("■ 직접 그린 획 인식 결과")
    맞힌개수 = 0
    for 숫자 in range(10):
        그림28 = app.그림_전처리(손글씨_그리기(숫자))
        확률목록 = app.확률_계산(모델, 장치, 그림28)
        예측 = max(range(10), key=lambda i: 확률목록[i])
        표시 = "정답" if 예측 == 숫자 else "오답"
        맞힌개수 += 예측 == 숫자
        print(f"  그린 숫자 {숫자} → 예측 {예측} ({확률목록[예측] * 100:5.1f}%) {표시}")
    print(f"  합계: 10개 중 {맞힌개수}개 정답")
    return 맞힌개수


def main():
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"■ 사용 장치: {장치}")
    모델 = 숫자인식CNN().to(장치)
    모델.load_state_dict(torch.load(app.가중치파일, map_location=장치))
    모델.eval()
    print(f"■ 가중치 불러오기 완료: {app.가중치파일}")

    평가_정확도(모델, 장치)
    그린숫자_인식(모델, 장치)


if __name__ == "__main__":
    main()
