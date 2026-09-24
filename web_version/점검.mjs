// 작성일시: 2026-09-24 15:18 (KST)
//
// 웹 버전이 파이썬과 같은 결과를 내는지 브라우저 없이 확인한다.
//   0단계 지문 대조: desktop_version/mnist_cnn.pt 가 마지막 내보내기 이후 바뀌지 않았는가
//   1단계 추론 엔진: 기준 28x28 -> 확률이 파이썬과 같은가
//   2단계 전처리:    기준 280x280 -> 28x28 이 파이썬과 같은가
// 단계를 따로 돌려 어느 쪽이 깨졌는지 바로 드러나게 한다.
//
// 실행 방법
//     node 점검.mjs

import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { 가중치_펼치기, 확률_계산 } from "./모델.js";
import { 그림_전처리 } from "./전처리.js";

const 기준경로 = dirname(fileURLToPath(import.meta.url));

// 합격선. 1단계는 누적 순서 차이만 남아야 하고, 2단계는 화소가 정확히 같아야 한다.
// design.md 의 목표(절대 오차 1e-5 이내)와 맞춘다.
const 확률_허용오차 = 1e-5;
const 화소_허용오차 = 0;

function 읽기(이름) {
  return readFileSync(join(기준경로, 이름));
}

function base64_풀기(글자) {
  return new Uint8Array(Buffer.from(글자, "base64"));
}

function 기준값_읽기() {
  return JSON.parse(읽기("기준값.json").toString("utf-8"));
}

function 가중치_읽기() {
  const 구조 = JSON.parse(읽기("가중치_구조.json").toString("utf-8"));
  const 바이트 = 읽기("가중치.bin");
  // Buffer 는 큰 풀을 공유하므로 정확한 구간만 잘라 ArrayBuffer 로 넘긴다.
  const 버퍼 = 바이트.buffer.slice(바이트.byteOffset, 바이트.byteOffset + 바이트.byteLength);
  if (버퍼.byteLength !== 구조.전체바이트) {
    throw new Error(`가중치.bin 크기가 구조와 다릅니다: ${버퍼.byteLength} != ${구조.전체바이트}`);
  }
  return 가중치_펼치기(버퍼, 구조);
}

/**
 * mnist_cnn.pt 가 마지막 'node 도구/내보내기.py' 실행 이후 바뀌었는지 확인한다.
 *
 * 이름·모양 검사(내보내기.py 안)는 내보내기를 실제로 돌렸을 때만 작동한다.
 * 흔한 재학습(같은 구조, 에폭만 늘림)은 이름·모양이 그대로라 그 검사에 안 걸리고,
 * 재내보내기를 잊으면 기준값.json 과 가중치.bin 은 예전 그대로 서로 맞아
 * 점검.mjs 가 영원히 통과해 버린다. 그래서 원본 파일의 SHA-256 을 따로 대조한다.
 */
function 영단계_지문대조() {
  console.log("■ 0단계 지문 대조 (mnist_cnn.pt 가 마지막 내보내기 이후 바뀌었는가)");
  const 구조 = JSON.parse(읽기("가중치_구조.json").toString("utf-8"));
  const 원본경로 = join(기준경로, "..", "desktop_version", "mnist_cnn.pt");

  if (!existsSync(원본경로)) {
    console.log("  desktop_version/mnist_cnn.pt 가 없어 건너뜀 (이 검사는 아무것도 확인하지 못했다)");
    return true;
  }
  if (!구조.원본_sha256) {
    console.log("  가중치_구조.json 에 원본_sha256 이 없다 — 이 검사가 생기기 전에 만든 결과물이다.");
    console.log("  ../venv/Scripts/python.exe 도구/내보내기.py 로 다시 내보내야 한다.");
    return false;
  }

  const 실제지문 = createHash("sha256").update(readFileSync(원본경로)).digest("hex");
  const 통과 = 실제지문 === 구조.원본_sha256;
  if (통과) {
    console.log(`  지문 일치 (${실제지문.slice(0, 12)}...) 통과`);
  } else {
    console.log(`  지문 불일치: 가중치_구조.json ${구조.원본_sha256.slice(0, 12)}... / 실제 파일 ${실제지문.slice(0, 12)}... 실패`);
    console.log("  mnist_cnn.pt 가 마지막 내보내기 이후 바뀌었다(재학습 후 재내보내기를 잊은 것으로 보인다).");
    console.log("  ../venv/Scripts/python.exe 도구/내보내기.py 를 다시 실행해 웹 가중치를 갱신할 것.");
  }
  return 통과;
}

function 일단계_추론엔진(가중치들, 기준값) {
  console.log("■ 1단계 추론 엔진 (기준 28x28 -> 확률)");
  let 최대차이 = 0;
  let 맞힌개수 = 0;
  let 실패 = 0;
  for (const 항목 of 기준값.항목들) {
    const 화소28 = base64_풀기(항목.기대_28x28_base64);
    const 확률 = 확률_계산(가중치들, 화소28);
    let 차이 = 0;
    for (let i = 0; i < 10; i++) 차이 = Math.max(차이, Math.abs(확률[i] - 항목.기대_확률[i]));
    최대차이 = Math.max(최대차이, 차이);

    let 예측 = 0;
    for (let i = 1; i < 10; i++) if (확률[i] > 확률[예측]) 예측 = i;
    if (예측 === 항목.숫자) 맞힌개수++;

    const 통과 = 차이 <= 확률_허용오차 && 예측 === 항목.숫자;
    if (!통과) 실패++;
    console.log(
      `  숫자 ${항목.숫자} -> 예측 ${예측} (${(확률[예측] * 100).toFixed(1)}%)` +
      ` 최대 확률차 ${차이.toExponential(2)} ${통과 ? "통과" : "실패"}`
    );
  }
  console.log(`  합계: 10개 중 ${맞힌개수}개 정답, 최대 확률차 ${최대차이.toExponential(2)}` +
              ` (허용 ${확률_허용오차.toExponential(0)})`);
  return 실패 === 0 && 맞힌개수 === 10;
}

/** 1비트로 묶인 280x280 입력을 0/255 배열로 되돌린다. */
function 비트풀기(묶음, 개수) {
  const 화소 = new Uint8Array(개수);
  for (let i = 0; i < 개수; i++) {
    화소[i] = (묶음[i >> 3] >> (i & 7)) & 1 ? 255 : 0;
  }
  return 화소;
}

function 이단계_전처리(기준값) {
  console.log("\n■ 2단계 전처리 (기준 280x280 -> 28x28)");
  let 최대차이 = 0;
  let 실패 = 0;
  for (const 항목 of 기준값.항목들) {
    const 화소280 = 비트풀기(base64_풀기(항목.입력_1비트_base64), 280 * 280);
    const 얻은것 = 그림_전처리(화소280, 280);
    const 기대 = base64_풀기(항목.기대_28x28_base64);
    if (얻은것 === null) {
      console.log(`  숫자 ${항목.숫자} -> 전처리 결과가 비었다 실패`);
      실패++;
      continue;
    }
    let 차이 = 0;
    let 다른화소 = 0;
    for (let i = 0; i < 784; i++) {
      const d = Math.abs(얻은것[i] - 기대[i]);
      if (d > 0) 다른화소++;
      차이 = Math.max(차이, d);
    }
    최대차이 = Math.max(최대차이, 차이);
    const 통과 = 차이 <= 화소_허용오차;
    if (!통과) 실패++;
    console.log(
      `  숫자 ${항목.숫자} -> 최대 화소차 ${차이}, 다른 화소 ${다른화소}/784 ` +
      `${통과 ? "통과" : "실패"}`
    );
  }
  console.log(`  합계: 최대 화소차 ${최대차이} (허용 ${화소_허용오차})`);
  return 실패 === 0;
}

function main() {
  const 지문통과 = 영단계_지문대조();
  console.log();
  const 기준값 = 기준값_읽기();
  const 가중치들 = 가중치_읽기();
  const 결과 = [지문통과, 일단계_추론엔진(가중치들, 기준값), 이단계_전처리(기준값)];
  const 모두통과 = 결과.every(Boolean);
  console.log(모두통과 ? "\n■ 전부 통과" : "\n■ 실패한 단계가 있습니다");
  if (!모두통과) process.exitCode = 1;
}

main();
