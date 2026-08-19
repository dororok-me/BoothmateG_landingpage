/**
 * boothmate_engine_vs_source.html → PNG 렌더 스크립트
 *
 *   node boothmate_engine_vs_render.js
 *
 * 산출물
 *   boothmate_engine_vs.png           1600×900 @2x (섹션/OG용 와이드)
 *   boothmate_engine_vs_portrait.png  1080×1500 @2x (모바일·SNS 세로)
 *
 * 필요: playwright(chromium), Pretendard 폰트 설치
 */
const path = require('path');
const { chromium } = require('playwright');

const SRC = 'file://' + path.resolve(__dirname, 'boothmate_engine_vs_source.html');

// 세로 변형은 소스 HTML을 건드리지 않고 렌더 시점에만 오버라이드한다.
const PORTRAIT_CSS = `
  body{width:1080px;height:1500px}
  .stage{width:1080px;height:1500px;padding:40px 40px 36px}
  .glow.a{width:620px;height:480px;left:-140px;top:160px}
  .glow.b{width:660px;height:520px;right:-160px;bottom:60px;top:auto}
  .head{margin-bottom:20px}
  .head h1{font-size:32px;line-height:1.34}
  .eyebrow{font-size:17px;margin-bottom:9px}
  .vs{grid-template-columns:1fr;grid-template-rows:1fr 76px 1fr}
  .card{padding:26px 28px 22px}
  .card h2{font-size:26px}
  .card p.sub{font-size:15px;min-height:0}
  .rule{margin:14px 0 13px}
  .stream{font-size:17px}
  .out{font-size:18px;padding:13px 15px}
  .alt{font-size:15px}
  .st{font-size:13px}
  .vsbadge{width:56px;height:56px;font-size:18px}
  .foot{margin-top:14px;font-size:14px}
`;

const SHOTS = [
  { file: 'boothmate_engine_vs.png',          width: 1600, height: 900,  css: null },
  { file: 'boothmate_engine_vs_portrait.png', width: 1080, height: 1500, css: PORTRAIT_CSS },
];

(async () => {
  const browser = await chromium.launch();
  for (const shot of SHOTS) {
    const page = await browser.newPage({
      viewport: { width: shot.width, height: shot.height },
      deviceScaleFactor: 2,
    });
    await page.goto(SRC);
    if (shot.css) await page.addStyleTag({ content: shot.css });
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.resolve(__dirname, shot.file) });
    await page.close();
    console.log('rendered', shot.file);
  }
  await browser.close();
})();
