/* Record reproducible browser frames against the real, local solver. */
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright-core');

async function main() {
  const [python, browserPath, output] = process.argv.slice(2);
  if (!output) throw Error('Usage: node scripts/capture_demo.cjs PYTHON BROWSER OUTPUT_DIR');
  const root = path.resolve(__dirname, '..');
  const base = 'http://127.0.0.1:8014';
  const server = spawn(python, ['run.py', '--port', '8014'], {cwd: root, stdio: 'ignore', windowsHide: true});
  let browser;
  try {
    for (let attempt = 0; ; attempt += 1) {
      if (server.exitCode !== null) throw Error('The local server exited before it was ready');
      try {
        if ((await fetch(`${base}/api/health`)).ok) break;
      } catch (_) { /* Startup is still in progress. */ }
      if (attempt >= 100) throw Error('The local server did not start');
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    await fs.mkdir(output, {recursive: true});
    browser = await chromium.launch({executablePath: browserPath, headless: true});
    const page = await browser.newPage({viewport: {width: 1600, height: 900}, deviceScaleFactor: 1});
    await page.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    await page.goto(base);
    await page.locator('#stepContent h2').waitFor();
    await page.locator('#continueButton').click();
    await page.locator('#continueButton').click();
    const shot = name => page.screenshot({path: path.join(output, `${name}.jpg`), type: 'jpeg', quality: 88});
    const generate = async selector => {
      const [response] = await Promise.all([
        page.waitForResponse(response => response.url() === `${base}/api/generate`, {timeout: 50000}),
        page.locator(selector).click(),
      ]);
      assert(response.ok());
      return response.json();
    };

    await shot('01-brief');
    const baseline = await generate('#generateButton');
    assert.equal(baseline.validation_status, 'passed');
    await page.locator('.proof-status').waitFor();
    await shot('02-baseline');
    await page.locator('[data-result-tab="report"]').click();
    await shot('03-validation');

    await page.locator('#quickMeeting').fill('24');
    await page.waitForFunction(() => document.querySelector('#downloadSvg').disabled);
    await shot('04-stale');
    const changed = await generate('.quick-revision [data-action="generate"]');
    assert.equal(changed.validation_status, 'passed');
    const meeting = changed.report.room_schedule.find(room => room.kind === 'meeting');
    assert(meeting.area_m2 >= 24);
    await page.locator('.proof-status').waitFor();
    await shot('05-revised');

    await page.locator('.demo-buttons [data-preset="impossible"]').click();
    await page.locator('#generateButton').waitFor();
    const impossible = await generate('#generateButton');
    assert.equal(impossible.search_status, 'infeasible');
    await page.locator('.conflict h2').waitFor();
    assert.equal(await page.locator('#downloadSvg').isDisabled(), true);
    await shot('06-conflict');

    const evidence = {input: 'built-in synthetic briefs', captured_via: 'real browser and local API',
      baseline: baseline.validation_status, revision: changed.brief_revision, meeting_area_m2: meeting.area_m2,
      infeasible: impossible.search_status, blocked_export: true};
    await fs.writeFile(path.join(output, 'capture.json'), JSON.stringify(evidence, null, 2) + '\n');
    console.log(evidence);
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
}

main().catch(error => { console.error(error); process.exitCode = 1; });
