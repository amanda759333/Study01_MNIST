# -*- coding: utf-8 -*-
"""MNIST 손글씨 숫자 데이터로 CNN을 학습하고 가중치를 mnist_cnn.pt로 저장한다.

실행 방법
    python train.py                # 기본 설정(3에폭)으로 학습
    python train.py --에폭 5       # 에폭 수를 바꿔서 학습
"""

import argparse
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

from model import 숫자인식CNN

# 윈도우 콘솔에서도 한글이 깨지지 않도록 출력 인코딩을 UTF-8로 맞춘다.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 이 파일이 있는 폴더를 기준 경로로 삼는다.
기준경로 = Path(__file__).resolve().parent
데이터폴더 = 기준경로 / "data"          # MNIST 원본이 내려받아질 위치
가중치파일 = 기준경로 / "mnist_cnn.pt"  # 학습 결과를 저장할 파일

# MNIST 전체 평균/표준편차 (정규화에 사용하는 관례적인 값)
평균 = 0.1307
표준편차 = 0.3081


def 데이터로더_준비(배치크기, 평가배치크기):
    """MNIST 학습/평가 데이터셋을 내려받아 DataLoader로 감싸서 돌려준다."""
    # 학습용 변환: 살짝 회전/이동시켜 데이터를 늘리면
    # 마우스로 그린 글씨처럼 삐뚤삐뚤한 입력에도 더 잘 견딘다.
    학습변환 = transforms.Compose([
        transforms.RandomAffine(degrees=10, translate=(0.1, 0.1), scale=(0.9, 1.1)),
        transforms.ToTensor(),
        transforms.Normalize((평균,), (표준편차,)),
    ])
    # 평가용 변환: 원본을 그대로 쓰고 정규화만 적용한다.
    평가변환 = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((평균,), (표준편차,)),
    ])

    학습셋 = datasets.MNIST(root=str(데이터폴더), train=True, download=True, transform=학습변환)
    평가셋 = datasets.MNIST(root=str(데이터폴더), train=False, download=True, transform=평가변환)

    학습로더 = DataLoader(학습셋, batch_size=배치크기, shuffle=True)
    평가로더 = DataLoader(평가셋, batch_size=평가배치크기, shuffle=False)
    return 학습로더, 평가로더


def 한_에폭_학습(모델, 장치, 학습로더, 최적화기, 에폭):
    """학습 데이터를 한 번 전부 돌면서 가중치를 갱신한다."""
    모델.train()  # 드롭아웃을 켜는 학습 모드
    전체배치수 = len(학습로더)
    누적손실 = 0.0

    for 배치번호, (이미지, 정답) in enumerate(학습로더, start=1):
        이미지, 정답 = 이미지.to(장치), 정답.to(장치)

        최적화기.zero_grad()              # 이전 기울기 초기화
        예측 = 모델(이미지)                # 순전파
        손실 = F.nll_loss(예측, 정답)      # 로그 소프트맥스와 짝을 이루는 손실
        손실.backward()                   # 역전파로 기울기 계산
        최적화기.step()                   # 가중치 갱신

        누적손실 += 손실.item()
        # 진행 상황을 100배치마다 한 줄로 보여 준다.
        if 배치번호 % 100 == 0 or 배치번호 == 전체배치수:
            print(f"  [에폭 {에폭}] {배치번호:>4}/{전체배치수} 배치 · 평균 손실 {누적손실 / 배치번호:.4f}")

    return 누적손실 / 전체배치수


def 평가(모델, 장치, 평가로더):
    """평가 데이터로 평균 손실과 정확도를 계산한다."""
    모델.eval()  # 드롭아웃을 끄는 평가 모드
    누적손실 = 0.0
    맞힌개수 = 0

    with torch.no_grad():  # 평가할 때는 기울기를 계산하지 않는다.
        for 이미지, 정답 in 평가로더:
            이미지, 정답 = 이미지.to(장치), 정답.to(장치)
            예측 = 모델(이미지)
            누적손실 += F.nll_loss(예측, 정답, reduction="sum").item()
            예측숫자 = 예측.argmax(dim=1)
            맞힌개수 += (예측숫자 == 정답).sum().item()

    전체개수 = len(평가로더.dataset)
    평균손실 = 누적손실 / 전체개수
    정확도 = 100.0 * 맞힌개수 / 전체개수
    print(f"  ▶ 평가 결과: 평균 손실 {평균손실:.4f} · 정확도 {맞힌개수}/{전체개수} ({정확도:.2f}%)")
    return 평균손실, 정확도


def main():
    파서 = argparse.ArgumentParser(description="MNIST 손글씨 숫자 인식 CNN 학습 스크립트")
    파서.add_argument("--에폭", type=int, default=3, help="학습을 반복할 횟수 (기본값 3)")
    파서.add_argument("--배치크기", type=int, default=128, help="학습 배치 크기 (기본값 128)")
    파서.add_argument("--평가배치크기", type=int, default=1000, help="평가 배치 크기 (기본값 1000)")
    파서.add_argument("--학습률", type=float, default=1.0, help="Adadelta 학습률 (기본값 1.0)")
    설정 = 파서.parse_args()

    # GPU가 있으면 GPU를, 없으면 CPU를 쓴다.
    장치 = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"■ 사용 장치: {장치}")
    print(f"■ 설정: 에폭 {설정.에폭} · 배치크기 {설정.배치크기} · 학습률 {설정.학습률}")

    torch.manual_seed(1)  # 실행할 때마다 결과가 비슷하게 나오도록 난수 고정

    print("■ MNIST 데이터 준비 중...")
    학습로더, 평가로더 = 데이터로더_준비(설정.배치크기, 설정.평가배치크기)
    print(f"  학습 데이터 {len(학습로더.dataset)}장 · 평가 데이터 {len(평가로더.dataset)}장")

    모델 = 숫자인식CNN().to(장치)
    최적화기 = optim.Adadelta(모델.parameters(), lr=설정.학습률)
    # 에폭마다 학습률을 0.7배로 줄여 마지막에 더 정밀하게 수렴하도록 한다.
    스케줄러 = optim.lr_scheduler.StepLR(최적화기, step_size=1, gamma=0.7)

    시작시각 = time.time()
    최고정확도 = 0.0

    for 에폭 in range(1, 설정.에폭 + 1):
        print(f"■ 에폭 {에폭}/{설정.에폭} 학습 시작")
        한_에폭_학습(모델, 장치, 학습로더, 최적화기, 에폭)
        _, 정확도 = 평가(모델, 장치, 평가로더)
        스케줄러.step()
        최고정확도 = max(최고정확도, 정확도)

    걸린시간 = time.time() - 시작시각
    print(f"■ 학습 완료 · 총 {걸린시간 / 60:.1f}분 소요 · 최고 정확도 {최고정확도:.2f}%")

    # 가중치만 저장한다(모델 구조는 model.py가 갖고 있다).
    torch.save(모델.state_dict(), 가중치파일)
    print(f"■ 가중치 저장 완료: {가중치파일}")


if __name__ == "__main__":
    main()
