// 작성일시: 2026-09-24 15:18 (KST)
//
// 웹 버전이 파이썬과 같은 결과를 내는지 브라우저 없이 확인한다.
//   1단계 추론 엔진: 기준 28x28 -> 확률이 파이썬과 같은가
//   2단계 전처리:    기준 280x280 -> 28x28 이 파이썬과 같은가
// 두 단계를 따로 돌려 어느 쪽이 깨졌는지 바로 드러나게 한다.
//
// 실행 방법
//     node 점검.mjs

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { 가중치_펼치기, 확률_계산 } from "./모델.js";

const 기준경로 = dirname(fileURLToPath(import.meta.url));

// 합격선. 1단계는 누적 순서 차이만 남아야 하고, 2단계는 화소가 정확히 같아야 한다.
const 확률_허용오차 = 1e-4;
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

function main() {
  const 기준값 = 기준값_읽기();
  const 가중치들 = 가중치_읽기();
  const 결과 = [일단계_추론엔진(가중치들, 기준값)];
  const 모두통과 = 결과.every(Boolean);
  console.log(모두통과 ? "\n■ 전부 통과" : "\n■ 실패한 단계가 있습니다");
  if (!모두통과) process.exitCode = 1;
}

main();
