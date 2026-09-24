# -*- coding: utf-8 -*-
# 작성일시: 2026-09-24 15:05 (KST)
"""mnist_cnn.pt 를 웹 버전이 쓸 형식으로 내보낸다.

만드는 것
  가중치.bin        float16 이진. state_dict 의 8개 텐서를 선언 순서로 이어 붙인다.
  가중치_구조.json  각 텐서의 이름·모양·오프셋. JS 는 이 파일만 보고 bin 을 자른다.

torch 가 필요하므로 데스크톱 환경에서 실행한다.
    ..\\..\\venv\\Scripts\\python.exe 내보내기.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import torch

기준경로 = Path(__file__).resolve().parent        # web_version/도구
웹폴더 = 기준경로.parent                           # web_version
데스크톱폴더 = 웹폴더.parent / "desktop_version"

# 데스크톱 코드(model.py, app.py, 점검.py)를 빌려 쓰기 위해 경로를 열어 준다.
sys.path.insert(0, str(데스크톱폴더))

from model import 숫자인식CNN  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

가중치파일 = 데스크톱폴더 / "mnist_cnn.pt"

# state_dict 에 이 이름들이 이 순서로 들어 있어야 한다.
# 모델 구조를 바꾸면 여기서 걸려서 조용히 어긋나는 일을 막는다.
층이름들 = [
    "conv1.weight", "conv1.bias",
    "conv2.weight", "conv2.bias",
    "fc1.weight", "fc1.bias",
    "fc2.weight", "fc2.bias",
]


def 사전_불러오기():
    """저장된 state_dict 를 읽고 구조가 예상과 같은지 확인한다."""
    if not 가중치파일.exists():
        raise SystemExit(
            f"가중치 파일이 없습니다: {가중치파일}\n"
            "먼저 desktop_version 에서 'python train.py' 를 실행하세요."
        )
    사전 = torch.load(가중치파일, map_location="cpu")
    if list(사전.keys()) != 층이름들:
        raise SystemExit(
            "모델 구조가 바뀌었습니다. 웹 추론 코드(모델.js)도 함께 고쳐야 합니다.\n"
            f"  기대: {층이름들}\n"
            f"  실제: {list(사전.keys())}"
        )

    # 이름·순서가 같아도 모양(shape)이 바뀌었으면 웹 추론 코드가 못 맞춘다.
    # 새로 만든 모델의 state_dict 를 기준 삼아 층마다 모양을 확인한다.
    기준사전 = 숫자인식CNN().state_dict()
    모양불일치 = [
        (이름, tuple(기준사전[이름].shape), tuple(사전[이름].shape))
        for 이름 in 층이름들
        if tuple(기준사전[이름].shape) != tuple(사전[이름].shape)
    ]
    if 모양불일치:
        불일치_설명 = "\n".join(
            f"  {이름}: 기대 {기대모양} / 실제 {실제모양}"
            for 이름, 기대모양, 실제모양 in 모양불일치
        )
        raise SystemExit(
            "모델 구조가 바뀌었습니다(층 모양 불일치). 웹 추론 코드(모델.js)도 함께 고쳐야 합니다.\n"
            f"{불일치_설명}"
        )
    return 사전


def 양자화_모델(사전, 장치):
    """float16 으로 반올림한 가중치를 되돌려 넣은 모델.

    웹 버전이 실제로 쓰게 될 가중치와 같다. 기준값을 이 모델로 만들어야
    JS 검증에서 '이식 오류'와 '양자화 오차'가 섞이지 않는다.
    """
    양자사전 = {이름: 값.half().float() for 이름, 값 in 사전.items()}
    모델 = 숫자인식CNN().to(장치)
    모델.load_state_dict(양자사전)
    모델.eval()
    return 모델


def 가중치_내보내기(사전):
    """가중치.bin 과 가중치_구조.json 을 만든다."""
    조각들 = []
    층목록 = []
    오프셋 = 0
    for 이름 in 층이름들:
        값 = 사전[이름].detach().cpu().numpy().astype("<f2")  # 리틀엔디언 float16
        바이트 = 값.tobytes()
        층목록.append({
            "이름": 이름,
            "모양": list(사전[이름].shape),
            "오프셋": 오프셋,
            "개수": int(값.size),
        })
        오프셋 += len(바이트)
        조각들.append(바이트)

    (웹폴더 / "가중치.bin").write_bytes(b"".join(조각들))
    구조 = {
        "설명": "mnist_cnn.pt 를 내보낸 것. 도구/내보내기.py 가 만든다. 직접 고치지 말 것.",
        "자료형": "float16",
        "바이트순서": "little",
        "전체바이트": 오프셋,
        "층목록": 층목록,
    }
    (웹폴더 / "가중치_구조.json").write_text(
        json.dumps(구조, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"■ 가중치.bin 저장: {오프셋:,d}바이트 ({오프셋 / 1024 / 1024:.2f}MB)")
    print(f"■ 가중치_구조.json 저장: 층 {len(층목록)}개")
    return 오프셋


def main():
    장치 = torch.device("cpu")
    사전 = 사전_불러오기()
    print(f"■ 가중치 불러오기 완료: {가중치파일}")

    전체바이트 = 가중치_내보내기(사전)

    # 되읽어서 원본과 맞는지 확인한다. 오차는 float16 반올림에서만 나와야 한다.
    원본 = torch.cat([사전[이름].flatten() for 이름 in 층이름들]).numpy()
    되읽음 = np.frombuffer((웹폴더 / "가중치.bin").read_bytes(), dtype="<f2").astype("float32")
    if 되읽음.size * 2 != 전체바이트:
        raise SystemExit(f"되읽은 크기가 다릅니다: {되읽음.size * 2} != {전체바이트}")
    최대오차 = float(np.max(np.abs(원본 - 되읽음)))
    기대오차 = float(np.max(np.abs(원본 - 원본.astype("float16").astype("float32"))))
    print(f"■ 되읽기 최대 오차: {최대오차:.3e} (float16 반올림 한계 {기대오차:.3e})")
    if 최대오차 > 기대오차:
        raise SystemExit("되읽은 값이 float16 반올림으로 설명되지 않습니다. 내보내기가 잘못됐습니다.")

    # 양자화가 정확도를 얼마나 깎는지 측정한다.
    import 점검  # noqa: E402  (torchvision 을 끌고 오므로 필요할 때만 불러온다)

    원본모델 = 숫자인식CNN().to(장치)
    원본모델.load_state_dict(사전)
    원본모델.eval()
    print("□ float32 원본")
    원본정확도 = 점검.평가_정확도(원본모델, 장치)
    print("□ float16 양자화 (웹이 쓰는 것)")
    양자정확도 = 점검.평가_정확도(양자화_모델(사전, 장치), 장치)
    print(f"■ 양자화로 인한 정확도 변화: {양자정확도 - 원본정확도:+.3f}%p")


if __name__ == "__main__":
    main()
