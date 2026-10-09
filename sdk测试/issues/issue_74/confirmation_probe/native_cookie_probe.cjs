// Independent native Chrome API comparator: no UIAutoma package is loaded.
// Existing published target URLs are passed as strings; no target page code runs.
const { chromium } = require('C:/Users/moby/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');

const main = 'https://baobaomi900901.github.io/xpath/#/cookie-test';
const guard = 'https://baobaomi900901.github.io/xpath/stop-load-test/slow.svg';
const prefix = 'sdk_cookie_native_confirm_' + crypto.randomUUID().replaceAll('-', '') + '_';
const out = process.argv[2];
if (!out) throw new Error('report filename required');
const report = { target_url: main, guard_url: guard, headless: true, isolated_profile: true,
  target_documents_loaded: false, product_engine_loaded: false, cases: [], cleanup: {} };
let context;
(async () => {
  try {
    context = await chromium.launchPersistentContext(path.join(__dirname, 'profile_' + crypto.randomUUID()), {
      executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe',
      headless: true, timeout: 20000,
      ignoreDefaultArgs: ['--disable-extensions'],
      args: ['--enable-unsafe-extension-debugging'],
    });
    report.browser_version = context.browser().version();
    const cdp = await context.browser().newBrowserCDPSession();
    const loaded = await cdp.send('Extensions.loadUnpacked', { path: path.join(__dirname, 'extension') });
    let worker = context.serviceWorkers().find(w => w.url().includes(loaded.id));
    if (!worker) worker = await context.waitForEvent('serviceworker', { timeout: 10000 });
    report.extension_permissions = await worker.evaluate(() => chrome.runtime.getManifest().permissions);
    report.extension_host_permissions = await worker.evaluate(() => chrome.runtime.getManifest().host_permissions);
    for (let round = 1; round <= 3; round++) {
      for (const scene of [
        { id: 'matching_path', url: main, path: '/xpath/', returns: 'cookie' },
        { id: 'other_path', url: main, path: '/xpath/stop-load-test/', returns: 'undefined' },
        { id: 'matching_url_for_other_path', url: guard, path: '/xpath/stop-load-test/', returns: 'cookie' },
      ]) {
        for (const mode of ['callback', 'promise']) {
          const name = `${prefix}${round}_${scene.id}_${mode}`;
          const details = { url: scene.url, name, value: 'native-written', path: scene.path, secure: false, httpOnly: false };
          const actual = await worker.evaluate(async ({ details, mode, main, guard }) => {
            let returned;
            if (mode === 'callback') {
              returned = await new Promise(resolve => chrome.cookies.set(details, value => {
                resolve({ kind: value === undefined ? 'undefined' : value === null ? 'null' : 'cookie',
                  value: value ?? null, last_error: chrome.runtime.lastError?.message ?? null, rejected: false });
              }));
            } else {
              try {
                const value = await chrome.cookies.set(details);
                returned = { kind: value === undefined ? 'undefined' : value === null ? 'null' : 'cookie',
                  value: value ?? null, last_error: null, rejected: false };
              } catch (e) {
                returned = { kind: 'exception', message: String(e), rejected: true };
              }
            }
            const stored = await chrome.cookies.getAll({ name: details.name });
            const fromMain = await chrome.cookies.get({ url: main, name: details.name });
            const fromGuard = await chrome.cookies.get({ url: guard, name: details.name });
            return { returned, stored, main_get: fromMain ?? null, guard_get: fromGuard ?? null };
          }, { details, mode, main, guard });
          const native = (await context.cookies([guard])).filter(c => c.name === name);
          const row = { round, scene: scene.id, mode, details, ...actual, cdp_cookies: native };
          report.cases.push(row);
          assert.equal(actual.returned.kind, scene.returns, JSON.stringify(row));
          assert.equal(actual.returned.last_error, null);
          assert.equal(actual.returned.rejected, false);
          assert.equal(native.length, 1);
          assert.equal(native[0].value, details.value);
          assert.equal(native[0].path, scene.path);
          assert.equal(actual.stored.length, 1);
          assert.equal(actual.guard_get.value, details.value);
          if (scene.id === 'other_path') assert.equal(actual.main_get, null);
          row.status = 'PASS';
          console.log(`${round} ${scene.id} ${mode}: ${actual.returned.kind}, lastError=null, independent_CDP_cookie=${native.length}`);
        }
      }
    }
    report.lifecycle = 'NATIVE_RETURN_CONFIRMED';
  } catch (e) {
    report.error = String(e.stack || e);
    process.exitCode = 1;
    console.error(report.error);
  } finally {
    if (context) {
      try {
        const before = (await context.cookies()).filter(c => c.name.startsWith(prefix));
        await context.clearCookies({ name: new RegExp('^' + prefix) });
        const after = (await context.cookies()).filter(c => c.name.startsWith(prefix));
        report.cleanup = { before_count: before.length, after_count: after.length, owned_cookies_removed: after.length === 0 };
        assert.equal(after.length, 0);
      } catch (e) { report.cleanup.error = String(e); process.exitCode = 1; }
      await context.close();
      report.cleanup.isolated_browser_closed = true;
    }
    fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n', 'utf8');
    console.log('cleanup ' + JSON.stringify(report.cleanup));
  }
})();
