// 작성일시: 2026-09-24 15:24 (KST)
//
// app.py 의 그림_전처리 를 그대로 옮긴 모듈.
// 사용자가 그린 큰 그림을 MNIST 와 같은 28x28 형식으로 다듬는다.
//
// 브라우저 canvas 의 drawImage 축소는 쓰지 않는다. 보간 방식이 브라우저마다
// 달라 파이썬과 맞출 수도, 검증할 수도 없기 때문이다. 대신 PIL 의 Lanczos 를
// 고정소수점 계산까지 그대로 재현한다.
//
// 이 파일은 브라우저와 Node 양쪽에서 쓰이므로 fetch·document·node:fs 를 쓰지 않는다.

const 정밀도비트 = 22;                     // PIL 의 PRECISION_BITS
const 정밀도배수 = 1 << 정밀도비트;        // 4194304

/**
 * 파이썬 round() 를 흉내낸다.
 * 파이썬은 .5 를 짝수 쪽으로 보내고(은행가 반올림), Math.round 는 위로 올린다.
 * 무게중심 이동량 계산에서 이 차이가 화소 어긋남으로 나타난다.
 */
export function 파이썬_반올림(값) {
  const 내림 = Math.floor(값);
  const 나머지 = 값 - 내림;
  if (나머지 > 0.5) return 내림 + 1;
  if (나머지 < 0.5) return 내림;
  return 내림 % 2 === 0 ? 내림 : 내림 + 1;
}

function 싱크(x) {
  if (x === 0.0) return 1.0;
  const y = x * Math.PI;
  return Math.sin(y) / y;
}

/** PIL 의 lanczos_filter 와 같다. 지지 구간은 [-3, 3) 이다. */
function 란초스(x) {
  if (x >= -3.0 && x < 3.0) return 싱크(x) * 싱크(x / 3.0);
  return 0.0;
}

/** 한 축의 고정소수점 계수표를 만든다. PIL 의 precompute_coeffs 와 같다. */
function 계수표(입력크기, 출력크기) {
  const 배율 = 입력크기 / 출력크기;
  const 필터배율 = Math.max(1.0, 배율);
  const 지지 = 3.0 * 필터배율;
  const 폭 = Math.ceil(지지) * 2 + 1;
  const 계수 = new Int32Array(출력크기 * 폭);
  const 시작들 = new Int32Array(출력크기);
  const 개수들 = new Int32Array(출력크기);
  const 임시 = new Float64Array(폭);
  const 역배율 = 1.0 / 필터배율;

  for (let xx = 0; xx < 출력크기; xx++) {
    const 중심 = (xx + 0.5) * 배율;
    let 시작 = Math.trunc(중심 - 지지 + 0.5);
    if (시작 < 0) 시작 = 0;
    let 끝 = Math.trunc(중심 + 지지 + 0.5);
    if (끝 > 입력크기) 끝 = 입력크기;
    const 개수 = 끝 - 시작;

    let 합 = 0.0;
    for (let x = 0; x < 개수; x++) {
      const w = 란초스((x + 시작 - 중심 + 0.5) * 역배율);
      임시[x] = w;
      합 += w;
    }
    for (let x = 0; x < 개수; x++) {
      const v = 합 !== 0.0 ? 임시[x] / 합 : 임시[x];
      // C 의 (int) 형변환은 0 쪽으로 자른다. Math.trunc 가 같은 일을 한다.
      계수[xx * 폭 + x] = v < 0
        ? Math.trunc(-0.5 + v * 정밀도배수)
        : Math.trunc(0.5 + v * 정밀도배수);
    }
    시작들[xx] = 시작;
    개수들[xx] = 개수;
  }
  return { 계수, 시작들, 개수들, 폭 };
}

/** 22비트 오른쪽 시프트 후 0~255 로 자른다. PIL 의 clip8 과 같다. */
function 자르기8(합) {
  const 값 = Math.floor(합 / 정밀도배수);   // 산술 시프트와 같다(음수는 내림)
  return 값 < 0 ? 0 : (값 > 255 ? 255 : 값);
}

function 가로_크기조정(화소, 너비, 높이, 새너비) {
  const { 계수, 시작들, 개수들, 폭 } = 계수표(너비, 새너비);
  const 결과 = new Uint8Array(새너비 * 높이);
  const 반올림 = 1 << (정밀도비트 - 1);
  for (let y = 0; y < 높이; y++) {
    for (let xx = 0; xx < 새너비; xx++) {
      const 시작 = 시작들[xx];
      const 개수 = 개수들[xx];
      let 합 = 반올림;
      for (let x = 0; x < 개수; x++) {
        합 += 화소[y * 너비 + 시작 + x] * 계수[xx * 폭 + x];
      }
      결과[y * 새너비 + xx] = 자르기8(합);
    }
  }
  return 결과;
}

function 세로_크기조정(화소, 너비, 높이, 새높이) {
  const { 계수, 시작들, 개수들, 폭 } = 계수표(높이, 새높이);
  const 결과 = new Uint8Array(너비 * 새높이);
  const 반올림 = 1 << (정밀도비트 - 1);
  for (let yy = 0; yy < 새높이; yy++) {
    const 시작 = 시작들[yy];
    const 개수 = 개수들[yy];
    for (let x = 0; x < 너비; x++) {
      let 합 = 반올림;
      for (let y = 0; y < 개수; y++) {
        합 += 화소[(시작 + y) * 너비 + x] * 계수[yy * 폭 + y];
      }
      결과[yy * 너비 + x] = 자르기8(합);
    }
  }
  return 결과;
}

/** PIL 의 resize(LANCZOS) 와 같다. 가로 먼저, 세로 나중. 크기가 같은 축은 건너뛴다. */
export function 란초스_크기조정(화소, 너비, 높이, 새너비, 새높이) {
  let 현재 = 화소;
  let 현너비 = 너비;
  let 현높이 = 높이;
  if (새너비 !== 현너비) {
    현재 = 가로_크기조정(현재, 현너비, 현높이, 새너비);
    현너비 = 새너비;
  }
  if (새높이 !== 현높이) {
    현재 = 세로_크기조정(현재, 현너비, 현높이, 새높이);
    현높이 = 새높이;
  }
  return 현재;
}

/** 값이 0 이 아닌 화소를 모두 담는 최소 사각형. PIL 의 getbbox 와 같다(우·하는 배타적). */
export function 글씨영역(화소, 너비, 높이) {
  let 좌 = 너비, 상 = 높이, 우 = 0, 하 = 0;
  for (let y = 0; y < 높이; y++) {
    for (let x = 0; x < 너비; x++) {
      if (화소[y * 너비 + x] !== 0) {
        if (x < 좌) 좌 = x;
        if (x >= 우) 우 = x + 1;
        if (y < 상) 상 = y;
        if (y >= 하) 하 = y + 1;
      }
    }
  }
  return 우 === 0 ? null : { 좌, 상, 우, 하 };
}

function 잘라내기(화소, 너비, 영역) {
  const 새너비 = 영역.우 - 영역.좌;
  const 새높이 = 영역.하 - 영역.상;
  const 결과 = new Uint8Array(새너비 * 새높이);
  for (let y = 0; y < 새높이; y++) {
    for (let x = 0; x < 새너비; x++) {
      결과[y * 새너비 + x] = 화소[(영역.상 + y) * 너비 + 영역.좌 + x];
    }
  }
  return { 화소: 결과, 너비: 새너비, 높이: 새높이 };
}

/**
 * 사용자가 그린 큰 그림을 MNIST 와 같은 28x28 형식으로 다듬는다.
 *
 * MNIST 숫자는 20x20 안에 들어가도록 크기를 맞춘 뒤, 글씨의 무게중심을
 * 28x28 이미지의 가운데에 놓은 형태다. 같은 방식으로 맞춰야 인식률이 나온다.
 *
 * 아무것도 그리지 않았으면 null 을 돌려준다.
 */
export function 그림_전처리(화소, 크기) {
  const 영역 = 글씨영역(화소, 크기, 크기);
  if (영역 === null) return null;

  const 잘린 = 잘라내기(화소, 크기, 영역);

  // 가로세로 비율을 지키면서 긴 변을 20픽셀로 맞춘다.
  let 새너비, 새높이;
  if (잘린.너비 > 잘린.높이) {
    새너비 = 20;
    새높이 = Math.max(1, 파이썬_반올림(잘린.높이 * 20 / 잘린.너비));
  } else {
    새높이 = 20;
    새너비 = Math.max(1, 파이썬_반올림(잘린.너비 * 20 / 잘린.높이));
  }
  const 축소 = 란초스_크기조정(잘린.화소, 잘린.너비, 잘린.높이, 새너비, 새높이);

  // 28x28 검은 바탕의 가운데에 붙인다.
  const 결과 = new Uint8Array(784);
  const 왼쪽 = (28 - 새너비) >> 1;   // 파이썬의 // 2 와 같다(둘 다 양수)
  const 위 = (28 - 새높이) >> 1;
  for (let y = 0; y < 새높이; y++) {
    for (let x = 0; x < 새너비; x++) {
      결과[(위 + y) * 28 + 왼쪽 + x] = 축소[y * 새너비 + x];
    }
  }

  // 밝기의 무게중심을 정확히 가운데(13.5, 13.5)로 평행 이동한다.
  let 총합 = 0, x합 = 0, y합 = 0;
  for (let i = 0; i < 784; i++) {
    const 값 = 결과[i];
    총합 += 값;
    x합 += (i % 28) * 값;
    y합 += ((i / 28) | 0) * 값;
  }
  if (총합 <= 0) return 결과;

  const 이동x = 파이썬_반올림(13.5 - x합 / 총합);
  const 이동y = 파이썬_반올림(13.5 - y합 / 총합);
  if (이동x === 0 && 이동y === 0) return 결과;

  const 옮긴 = new Uint8Array(784);
  for (let y = 0; y < 28; y++) {
    const 원y = y - 이동y;
    if (원y < 0 || 원y >= 28) continue;
    for (let x = 0; x < 28; x++) {
      const 원x = x - 이동x;
      if (원x < 0 || 원x >= 28) continue;
      옮긴[y * 28 + x] = 결과[원y * 28 + 원x];
    }
  }
  return 옮긴;
}
