// korean_only.spec.js — V2 UI 한국어 전용 강제 검증
// 이 테스트가 실패하면 PR 병합 불가 (CI gate)

const { test, expect } = require('@playwright/test');
const path = require('path');

const FILE_URL = 'file://' + path.resolve(__dirname, '../index.html').replace(/\\/g, '/');
const V2_URL   = FILE_URL + '?ui=v2';

// 일본어 감지 regex (히라가나 + 가타카나 + CJK 한자)
const JP_REGEX = /[぀-ヿ㐀-䶿一-鿿]/;

/**
 * 텍스트에서 일본어 허용 구역을 제거 후 검사
 * 허용 구역: '원문' 레이블이 붙은 필드
 */
function stripAllowedZones(text) {
  // '원문 (Original)' 뒤 내용 제거 (drawer 원문 필드)
  return text.replace(/원문\s*\(Original\)[^]*?(?=\n\n|\Z)/g, '');
}

function hasJapanese(text) {
  return JP_REGEX.test(stripAllowedZones(text || ''));
}

// ── 스태틱 UI 라벨 검사 ───────────────────────────────────────────────────
test.describe('Korean-only: 정적 UI 라벨', () => {

  test('헤더에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    const text = await page.locator('header').textContent();
    expect(hasJapanese(text), `헤더 일본어 감지됨: ${text}`).toBe(false);
  });

  test('탭 버튼에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    const ctb = await page.locator('#ctb').textContent();
    expect(hasJapanese(ctb), `탭 일본어 감지됨: ${ctb}`).toBe(false);
  });

  test('필터 칩 영역에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    const chips = await page.locator('#v2chips').textContent();
    expect(hasJapanese(chips), `칩 일본어 감지됨: ${chips}`).toBe(false);
  });

  test('태그 필터 바에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    const tagbar = await page.locator('#v2tagfilter').textContent().catch(() => '');
    expect(hasJapanese(tagbar), `태그바 일본어 감지됨: ${tagbar}`).toBe(false);
  });
});

// ── Drawer 열었을 때 라벨 검사 ────────────────────────────────────────────
test.describe('Korean-only: Drawer 라벨', () => {

  test('Drawer TL;DR 레이블에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('#grid .cc').first().click();
    await page.waitForSelector('.v2-drawer-overlay.open', { timeout: 3000 });

    // TL;DR 레이블 (포인트/리스크)
    const tldrText = await page.locator('.v2-tldr').textContent();
    // 레이블만 확인 (포인트/리스크 텍스트), 파생된 내용의 일본어는 sanitize됨
    const labels = await page.locator('.v2-tldr-label').allTextContents();
    for (const label of labels) {
      expect(hasJapanese(label), `TL;DR 레이블 일본어: ${label}`).toBe(false);
    }
  });

  test('Drawer 섹션 레이블(.v2-dsl)에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('#grid .cc').first().click();
    await page.waitForSelector('.v2-drawer-overlay.open', { timeout: 3000 });
    await page.waitForTimeout(300);

    const labels = await page.locator('.v2-dsl').allTextContents();
    for (const label of labels) {
      // '원문' 레이블 자체는 허용
      if (label.includes('원문')) continue;
      expect(hasJapanese(label), `섹션 레이블 일본어: "${label}"`).toBe(false);
    }
  });

  test('Drawer 액션 버튼에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('#grid .cc').first().click();
    await page.waitForSelector('.v2-drawer-overlay.open', { timeout: 3000 });

    const actText = await page.locator('.v2-actions').textContent().catch(() => '');
    expect(hasJapanese(actText), `액션 버튼 일본어: ${actText}`).toBe(false);
  });

  test('TL;DR 파생 텍스트에 일본어 없음 (sanitize 적용)', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    // 여러 카드를 열어서 TL;DR 내용 확인
    const cards = page.locator('#grid .cc');
    const count = Math.min(await cards.count(), 5);
    for (let i = 0; i < count; i++) {
      await page.locator('#grid .cc').nth(i).click();
      await page.waitForSelector('.v2-drawer-overlay.open', { timeout: 3000 });
      await page.waitForTimeout(200);

      const tldrTexts = await page.locator('.v2-tldr-text').allTextContents();
      for (const t of tldrTexts) {
        expect(hasJapanese(t), `TL;DR[${i}] 일본어 미sanitize: "${t.slice(0,50)}"`).toBe(false);
      }
      await page.locator('.v2-dclose').click();
      await page.waitForTimeout(200);
    }
  });

  test('원문 필드는 일본어 허용 (allow-list)', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    // 일본어 회사명이 있는 기업 카드 열기 (대부분 있음)
    await page.locator('#grid .cc').first().click();
    await page.waitForSelector('.v2-drawer-overlay.open', { timeout: 3000 });

    const origBlock = page.locator('.v2-orig-block');
    if (await origBlock.count() > 0) {
      // 원문 필드 레이블은 한국어 ('원문 (Original)')
      const label = await page.locator('.v2-orig-block .v2-gentext').textContent();
      expect(label).toContain('원문');
      // 원문 필드 내용은 일본어 포함 허용
      const origText = await page.locator('.v2-orig-field').textContent();
      // 내용이 있으면 OK (일본어여도 됨)
      expect(origText.length).toBeGreaterThan(0);
    }
    // pass: 원문 필드 없어도 OK (Korean name only company)
  });
});

// ── 변경이력 탭 검사 ────────────────────────────────────────────────────────
test.describe('Korean-only: 변경이력 탭', () => {

  test('변경이력 탭 레이블에 일본어 없음', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('.stab[data-tab="cl"]').click();
    await page.waitForTimeout(300);

    // 기간 토글 버튼
    const ranges = await page.locator('.v2-cl-range').allTextContents();
    for (const r of ranges) {
      expect(hasJapanese(r), `기간 토글 일본어: ${r}`).toBe(false);
    }
    // 타입 배지
    const badges = await page.locator('.v2-cl-type-badge').allTextContents();
    for (const b of badges) {
      expect(hasJapanese(b), `타입 배지 일본어: ${b}`).toBe(false);
    }
    // 회사명은 nk(한국어) 사용
    const names = await page.locator('.v2-cl-co').allTextContents();
    for (const n of names) {
      expect(hasJapanese(n), `변경이력 회사명 일본어: ${n}`).toBe(false);
    }
  });

  test('변경이력 노트가 sanitize됨 (일본어 없음)', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('.stab[data-tab="cl"]').click();
    await page.waitForTimeout(300);

    const notes = await page.locator('.v2-cl-note').allTextContents();
    for (const note of notes) {
      expect(hasJapanese(note), `변경이력 노트 일본어 미sanitize: "${note.slice(0,60)}"`).toBe(false);
    }
  });
});

// ── 전체 V2 UI 종합 스캔 (CI gate) ────────────────────────────────────────
test('CI-gate: V2 UI 전체 일본어 누출 없음', async ({ page }) => {
  await page.goto(V2_URL);
  await page.waitForTimeout(500);

  // 검사 대상 셀렉터 목록
  const selectors = [
    'header',
    '#ctb',
    '#v2chips',
    '#v2tagfilter',
    '.ctrl',
  ];

  for (const sel of selectors) {
    const el = page.locator(sel);
    if (await el.count() === 0) continue;
    const text = await el.textContent() || '';
    expect(
      hasJapanese(text),
      `[CI-gate] '${sel}' 에 일본어 감지됨:\n  "${text.slice(0, 120)}"`
    ).toBe(false);
  }

  // 카드 1개 열어서 드로어 검사 (원문 필드 제외)
  await page.locator('#grid .cc').first().click();
  await page.waitForSelector('.v2-drawer-overlay.open', { timeout: 3000 });
  await page.waitForTimeout(300);

  // 원문 블록 제외한 드로어 텍스트 검사
  const drawerText = await page.evaluate(() => {
    const dbody = document.getElementById('v2dbody');
    if (!dbody) return '';
    const origBlock = dbody.querySelector('.v2-orig-block');
    if (origBlock) origBlock.style.display = 'none';
    const text = dbody.textContent || '';
    if (origBlock) origBlock.style.display = '';
    return text;
  });

  const JP = /[぀-ヿ㐀-䶿一-鿿]/;
  expect(
    JP.test(drawerText),
    `[CI-gate] 드로어 본문에 일본어 감지됨 (원문 필드 제외):\n  "${drawerText.slice(0,200)}"`
  ).toBe(false);
});
