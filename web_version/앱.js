// 작성일시: 2026-09-24 15:34 (KST)
//
// 화면을 담당하는 부분. 캔버스에 그리고, 전처리와 추론을 불러 결과를 보여 준다.
//
// 화면에 보이는 canvas 와 별개로 안티앨리어싱 없는 280x280 사본에 획을 직접 찍는다.
// app.py 가 Tk 캔버스와 PIL 사본을 따로 두는 것과 같은 구조다.
// 이렇게 해야 전처리에 들어가는 그림이 브라우저 렌더링 방식에 흔들리지 않는다.

import { 가중치_펼치기, 확률_계산 } from "./모델.js";
import { 그림_전처리 } from "./전처리.js";

const 캔버스크기 = 280;   // app.py 의 같은 이름 상수와 맞춘다
const 붓두께 = 20;
const 붓반지름 = 붓두께 / 2;

const 그리기판 = document.getElementById("그리기판");
const 결과숫자 = document.getElementById("결과숫자");
const 신뢰도 = document.getElementById("신뢰도");
const 확률표 = document.getElementById("확률표");
const 지우기단추 = document.getElementById("지우기단추");
const 다시인식단추 = document.getElementById("다시인식단추");

const 붓 = 그리기판.getContext("2d");
const 그림 = new Uint8Array(캔버스크기 * 캔버스크기);  // 인식에 쓰는 사본

let 가중치들 = null;
let 그리는중 = false;
let 이전좌표 = null;
let 그리는붓 = null;   // 현재 획을 그리고 있는 pointerId. 다른 포인터(손바닥 등)는 무시한다.

const 막대들 = [];
const 값글씨들 = [];
const 줄들 = [];

function 확률표_만들기() {
  for (let 숫자 = 0; 숫자 < 10; 숫자++) {
    const 줄 = document.createElement("li");
    const 이름 = document.createElement("span");
    이름.className = "숫자";
    이름.textContent = String(숫자);
    const 바탕 = document.createElement("span");
    바탕.className = "막대바탕";
    const 막대 = document.createElement("span");
    막대.className = "막대";
    바탕.appendChild(막대);
    const 값 = document.createElement("span");
    값.className = "값";
    값.textContent = "0.0%";
    줄.append(이름, 바탕, 값);
    확률표.appendChild(줄);
    막대들.push(막대);
    값글씨들.push(값);
    줄들.push(줄);
  }
}

// ---- 그리기 ------------------------------------------------

/** 사본에 반지름 붓반지름 의 채운 원을 찍는다. 안티앨리어싱은 하지 않는다. */
function 원_찍기(중심x, 중심y) {
  const 반지름제곱 = 붓반지름 * 붓반지름;
  const 왼 = Math.max(0, Math.floor(중심x - 붓반지름));
  const 오 = Math.min(캔버스크기 - 1, Math.ceil(중심x + 붓반지름));
  const 위 = Math.max(0, Math.floor(중심y - 붓반지름));
  const 아래 = Math.min(캔버스크기 - 1, Math.ceil(중심y + 붓반지름));
  for (let y = 위; y <= 아래; y++) {
    const dy = y - 중심y;
    for (let x = 왼; x <= 오; x++) {
      const dx = x - 중심x;
      if (dx * dx + dy * dy <= 반지름제곱) 그림[y * 캔버스크기 + x] = 255;
    }
  }
}

/** 두 점을 잇는 굵은 선을 사본에 찍는다. 원을 촘촘히 겹쳐 둥근 끝과 이음새를 만든다. */
function 선_찍기(x0, y0, x1, y1) {
  const 길이 = Math.hypot(x1 - x0, y1 - y0);
  const 걸음수 = Math.max(1, Math.ceil(길이 * 2));   // 0.5 픽셀 간격
  for (let i = 0; i <= 걸음수; i++) {
    const 비율 = i / 걸음수;
    원_찍기(x0 + (x1 - x0) * 비율, y0 + (y1 - y0) * 비율);
  }
}

function 좌표_구하기(사건) {
  const 상자 = 그리기판.getBoundingClientRect();
  // getBoundingClientRect 는 테두리까지 포함한 크기를 준다. 그리는 면은 그 안쪽이므로
  // 테두리 두께를 빼야 한다. clientWidth 는 테두리를 뺀 값이라 이걸로 환산한다.
  // (빼지 않으면 좌표가 테두리 두께만큼 어긋나 획이 조금씩 밀린다)
  const 안쪽너비 = 그리기판.clientWidth;
  const 안쪽높이 = 그리기판.clientHeight;
  const 가로테두리 = (상자.width - 안쪽너비) / 2;
  const 세로테두리 = (상자.height - 안쪽높이) / 2;
  return {
    x: (사건.clientX - 상자.left - 가로테두리) * (캔버스크기 / 안쪽너비),
    y: (사건.clientY - 상자.top - 세로테두리) * (캔버스크기 / 안쪽높이),
  };
}

function 화면_그리기_시작() {
  붓.strokeStyle = "#ffffff";
  붓.fillStyle = "#ffffff";
  붓.lineWidth = 붓두께;
  붓.lineCap = "round";
  붓.lineJoin = "round";
}

function 붓_누름(사건) {
  if (!가중치들) return;
  // 이미 다른 손가락(펜)으로 그리는 중이면 새 접촉은 무시한다.
  // 그러지 않으면 손바닥이 스치는 것만으로 이전좌표가 엉뚱한 점으로 바뀐다.
  if (그리는중) return;
  그리기판.setPointerCapture(사건.pointerId);
  그리는중 = true;
  그리는붓 = 사건.pointerId;
  const { x, y } = 좌표_구하기(사건);
  이전좌표 = { x, y };
  붓.beginPath();
  붓.arc(x, y, 붓반지름, 0, Math.PI * 2);
  붓.fill();
  원_찍기(x, y);
}

function 붓_이동(사건) {
  if (!그리는중 || 사건.pointerId !== 그리는붓) return;
  const { x, y } = 좌표_구하기(사건);
  붓.beginPath();
  붓.moveTo(이전좌표.x, 이전좌표.y);
  붓.lineTo(x, y);
  붓.stroke();
  선_찍기(이전좌표.x, 이전좌표.y, x, y);
  이전좌표 = { x, y };
}

function 붓_뗌(사건) {
  if (!그리는중 || 사건.pointerId !== 그리는붓) return;
  그리는중 = false;
  이전좌표 = null;
  그리는붓 = null;
  인식하기();
}

// ---- 인식과 화면 갱신 ---------------------------------------

function 인식하기() {
  if (!가중치들) return;
  const 그림28 = 그림_전처리(그림, 캔버스크기);
  if (그림28 === null) {
    결과표시(null, new Array(10).fill(0), "숫자를 써 보세요");
    return;
  }
  const 확률 = 확률_계산(가중치들, 그림28);
  let 예측 = 0;
  for (let i = 1; i < 10; i++) if (확률[i] > 확률[예측]) 예측 = i;
  결과표시(예측, 확률, `신뢰도 ${(확률[예측] * 100).toFixed(1)}%`);
}

function 결과표시(예측, 확률, 문구) {
  결과숫자.textContent = 예측 === null ? "?" : String(예측);
  신뢰도.textContent = 문구;
  for (let 숫자 = 0; 숫자 < 10; 숫자++) {
    const 비율 = 확률[숫자];
    막대들[숫자].style.width = `${Math.max(0, 비율 * 100)}%`;
    값글씨들[숫자].textContent = `${(비율 * 100).toFixed(1)}%`;
    줄들[숫자].classList.toggle("으뜸", 숫자 === 예측);
  }
}

function 지우기() {
  붓.fillStyle = "#000000";
  붓.fillRect(0, 0, 캔버스크기, 캔버스크기);
  화면_그리기_시작();
  그림.fill(0);
  결과표시(null, new Array(10).fill(0), "숫자를 써 보세요");
}

// ---- 시작 ---------------------------------------------------

async function 가중치_불러오기() {
  const [구조응답, 이진응답] = await Promise.all([
    fetch("가중치_구조.json"),
    fetch("가중치.bin"),
  ]);
  if (!구조응답.ok || !이진응답.ok) {
    throw new Error(`가중치를 받지 못했습니다 (${구조응답.status}, ${이진응답.status})`);
  }
  const 구조 = await 구조응답.json();
  const 버퍼 = await 이진응답.arrayBuffer();
  if (버퍼.byteLength !== 구조.전체바이트) {
    throw new Error(`가중치 크기가 다릅니다: ${버퍼.byteLength} != ${구조.전체바이트}`);
  }
  return 가중치_펼치기(버퍼, 구조);
}

async function 시작() {
  확률표_만들기();
  지우기();
  신뢰도.textContent = "모델을 불러오는 중…";
  지우기단추.disabled = true;
  다시인식단추.disabled = true;

  그리기판.addEventListener("pointerdown", 붓_누름);
  그리기판.addEventListener("pointermove", 붓_이동);
  그리기판.addEventListener("pointerup", 붓_뗌);
  그리기판.addEventListener("pointercancel", 붓_뗌);
  지우기단추.addEventListener("click", 지우기);
  다시인식단추.addEventListener("click", 인식하기);

  try {
    가중치들 = await 가중치_불러오기();
  } catch (오류) {
    신뢰도.textContent = `모델을 불러오지 못했습니다: ${오류.message}`;
    return;
  }
  지우기단추.disabled = false;
  다시인식단추.disabled = false;
  신뢰도.textContent = "숫자를 써 보세요";
}

시작();
