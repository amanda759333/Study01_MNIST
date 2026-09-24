# -*- coding: utf-8 -*-
"""바탕 화면 바로가기와 창에 쓸 아이콘 파일(손글씨인식.ico)을 만든다.

윈도우 아이콘은 여러 크기를 한 파일에 담아야 작업 표시줄(32px)부터
큰 아이콘(256px)까지 모두 깔끔하게 보인다.

실행 방법
    python 아이콘_만들기.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

기준경로 = Path(__file__).resolve().parent
아이콘파일 = 기준경로 / "손글씨인식.ico"

바탕색 = (17, 22, 31)      # 앱의 그리기 판과 같은 어두운 색
강조색 = (53, 132, 228)    # 앱에서 쓰는 파란 강조색
글씨색 = (255, 255, 255)
기본크기 = 256             # 이 크기로 그린 뒤 여러 크기로 줄인다.


def 글꼴_찾기(크기):
    """숫자를 굵게 그릴 수 있는 글꼴을 순서대로 찾아 돌려준다."""
    후보들 = ["malgunbd.ttf", "segoeuib.ttf", "arialbd.ttf", "tahomabd.ttf"]
    for 이름 in 후보들:
        try:
            return ImageFont.truetype(이름, 크기)
        except OSError:
            continue
    return ImageFont.load_default()  # 모두 없으면 기본 글꼴로 대체


def 아이콘_그리기():
    """둥근 사각형 바탕에 손글씨 느낌의 숫자를 얹은 그림을 만든다."""
    그림 = Image.new("RGBA", (기본크기, 기본크기), (0, 0, 0, 0))
    붓 = ImageDraw.Draw(그림)

    # 1) 둥근 사각형 바탕
    여백 = 10
    붓.rounded_rectangle(
        [여백, 여백, 기본크기 - 여백, 기본크기 - 여백],
        radius=48, fill=바탕색 + (255,), outline=강조색 + (255,), width=6,
    )

    # 2) 가운데에 숫자 3을 크게 쓴다. 글씨를 살짝 기울여 손글씨 느낌을 준다.
    글자판 = Image.new("RGBA", (기본크기, 기본크기), (0, 0, 0, 0))
    글자붓 = ImageDraw.Draw(글자판)
    글꼴 = 글꼴_찾기(170)
    글자붓.text((기본크기 // 2, 기본크기 // 2 - 12), "3", font=글꼴,
              fill=글씨색 + (255,), anchor="mm")
    글자판 = 글자판.rotate(-8, resample=Image.BICUBIC, center=(기본크기 // 2, 기본크기 // 2))
    그림.alpha_composite(글자판)

    # 3) 아래쪽에 밑줄을 그어 '쓰는 판' 느낌을 살린다.
    붓.rounded_rectangle([70, 196, 186, 208], radius=6, fill=강조색 + (255,))
    return 그림


def main():
    그림 = 아이콘_그리기()
    크기목록 = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    그림.save(아이콘파일, format="ICO", sizes=크기목록)
    print(f"■ 아이콘 저장 완료: {아이콘파일}")
    print(f"■ 담긴 크기: {', '.join(f'{가로}x{세로}' for 가로, 세로 in 크기목록)}")

    # 눈으로 확인하기 쉽도록 미리보기 PNG도 함께 남긴다.
    미리보기 = 기준경로 / "손글씨인식_미리보기.png"
    그림.resize((128, 128), Image.LANCZOS).save(미리보기)
    print(f"■ 미리보기 저장: {미리보기}")


if __name__ == "__main__":
    main()
