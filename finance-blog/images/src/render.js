// Renders each .card in covers.html to PNG (with text and illustration-only "clean" versions).
// Usage: node src/render.js   (requires Playwright)
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1200 } });
  const file = 'file://' + path.join(__dirname, 'covers.html');
  for (const [hash, dir] of [['', 'posts'], ['#clean', 'clean']]) {
    await page.goto(file + hash);
    await page.reload();
    await page.evaluate(() => document.fonts.ready);
    for (const card of await page.$$('.card')) {
      const id = await card.getAttribute('id');
      await card.screenshot({ path: path.join(__dirname, '..', dir, id + '.png') });
      console.log(dir + '/' + id + '.png');
    }
  }
  await browser.close();
})();
