/* Run only against disposable staging, with synthetic credentials in LIVING_TEST_CREDENTIALS. */
const fs = require('node:fs');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');

(async () => {
  const base = process.env.LIVING_TEST_URL || 'https://localhost:18443';
  const credentials = JSON.parse(fs.readFileSync(process.env.LIVING_TEST_CREDENTIALS, 'utf8'));
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  // Only for the staging-local Caddy CA; separately verify HTTPS using its exact root certificate.
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  const failures = [];
  page.on('pageerror', e => failures.push(String(e)));
  await page.goto(`${base}/admin/login/?next=/geno/living/`);
  await page.screenshot({ path: '/evidence/login.png', fullPage: true });
  fs.writeFileSync('/evidence/login.html', await page.content());
  await page.locator('[name="username"]').fill(credentials.username);
  await page.locator('[name="password"]').fill(credentials.password);
  await page.locator('button[type=submit],input[type=submit]').first().click();
  await page.waitForURL('**/geno/living/');
  await page.getByRole('link', { name: 'Novo arrendamento', exact: true }).last().click();
  const suffix = String(Date.now());
  for (const [name, value] of Object.entries({
    building_name: `Edifício fictício ${suffix}`, street_name: 'Rua de Ensaio', house_number: '7',
    city_zipcode: '2500-001', city_name: 'Caldas da Rainha', unit_name: 'A', floor: '4', area: '58.00',
    rent: '700.00', first_name: 'Residente', last_name: 'Fictício', email: `residente-${suffix}@example.invalid`,
    date: '2026-11-01', date_end: '2029-10-31',
  })) await page.locator(`[name="${name}"]`).fill(value);
  await page.getByLabel('Contrato já assinado pelas partes').check();
  await page.getByRole('button', { name: 'Guardar arrendamento' }).click();
  await page.waitForURL('**/geno/living/contracts/*/');
  assert.match(await page.locator('main').innerText(), /Assinado/);
  assert.match(await page.locator('main').innerText(), /700/);
  const contractURL = page.url();
  await page.screenshot({ path: '/evidence/contract-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.screenshot({ path: '/evidence/contract-mobile.png', fullPage: true });
  await page.goto(`${base}/geno/living/new/`);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.screenshot({ path: '/evidence/new-mobile.png', fullPage: true });
  const outsider = await browser.newContext({ ignoreHTTPSErrors: true });
  const otherPage = await outsider.newPage();
  await otherPage.goto(contractURL);
  assert.match(otherPage.url(), /login/);
  assert.equal((await otherPage.content()).includes('Edifício fictício'), false);
  const residentContext = await browser.newContext({ ignoreHTTPSErrors: true });
  const residentPage = await residentContext.newPage();
  await residentPage.goto(`${base}/geno/resident/portal/`);
  assert.equal(new URL(residentPage.url()).pathname, '/portal/login/');
  await residentPage.locator('[name="username"]').fill(credentials.residents[0].username);
  await residentPage.locator('[name="password"]').fill(credentials.residents[0].password);
  await residentPage.locator('button[name="submit"]').click();
  await residentPage.waitForURL('**/geno/resident/portal/');
  const denied = await residentPage.goto(contractURL);
  assert.equal(denied.status(), 403);
  await residentContext.close();
  await context.close();
  await outsider.close();
  await browser.close();
  assert.deepEqual(failures, []);
  fs.writeFileSync('/evidence/browser-result.json', JSON.stringify({ passed: true, contractURL,
    checks: ['login','new-tenancy','contract-detail','desktop','mobile-no-overflow','anonymous-isolation','no-page-errors','resident-login','resident-denied-global-management'],
    tls: 'staging internal CA; browser exception only; verify CA independently', }, null, 2));
  console.log('BROWSER_SMOKE_PASS');
})().catch(e => { console.error(e); process.exit(1); });
