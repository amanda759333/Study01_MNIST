# -*- coding: utf-8 -*-
"""손글씨 숫자(MNIST) 인식을 위한 CNN 모델 정의 모듈.

학습(train.py)과 예측(app.py)에서 똑같은 구조를 공유하기 위해
모델 클래스를 이 파일 하나에 모아 둔다.
"""

import torch.nn as nn
import torch.nn.functional as F


class 숫자인식CNN(nn.Module):
    """28x28 흑백 손글씨 숫자 이미지를 0~9 중 하나로 분류하는 합성곱 신경망.

    구조 요약
        입력 1x28x28
        → 합성곱(32채널) → 합성곱(64채널) → 최대풀링 → 드롭아웃
        → 완전연결(128) → 드롭아웃 → 완전연결(10)
    """

    def __init__(self):
        super().__init__()
        # 첫 번째 합성곱: 채널 1 → 32, 3x3 커널 (28x28 → 26x26)
        self.conv1 = nn.Conv2d(in_channels=1, out_channels=32, kernel_size=3)
        # 두 번째 합성곱: 채널 32 → 64, 3x3 커널 (26x26 → 24x24)
        self.conv2 = nn.Conv2d(in_channels=32, out_channels=64, kernel_size=3)
        # 과적합을 줄이기 위한 드롭아웃 두 개
        self.dropout1 = nn.Dropout(0.25)  # 풀링 직후에 적용
        self.dropout2 = nn.Dropout(0.5)   # 완전연결 층 사이에 적용
        # 풀링까지 거치면 64채널 x 12 x 12 = 9216개의 특징이 남는다.
        self.fc1 = nn.Linear(64 * 12 * 12, 128)
        # 최종 출력은 숫자 0~9에 대한 점수 10개
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        """순전파를 수행하고 각 숫자에 대한 로그 확률을 돌려준다."""
        x = F.relu(self.conv1(x))      # 특징 추출 + 비선형 활성화
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2)         # 24x24 → 12x12 로 절반 축소
        x = self.dropout1(x)
        x = x.flatten(1)               # 배치 차원만 남기고 1차원으로 펼치기
        x = F.relu(self.fc1(x))
        x = self.dropout2(x)
        x = self.fc2(x)
        # 손실 함수로 NLLLoss를 쓰기 위해 로그 소프트맥스를 적용한다.
        return F.log_softmax(x, dim=1)
