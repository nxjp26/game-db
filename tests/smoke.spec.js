// smoke.spec.js — Playwright スモークテスト
// index.html の基本機能が壊れていないことを確認する

const { test, expect } = require('@playwright/test');
const path = require('path');

const FILE_URL = 'file://' + path.resolve(__dirname, '../index.html').replace(/\\/g, '/');

test.describe('Dashboard Smoke Tests (v1 — default)', () => {

  test('ページロード + 企業カード表示', async ({ page }) => {
    await page.goto(FILE_URL);
    // ヘッダーが表示される
    await expect(page.locator('header h1')).toContainText('게임업계');
    // グリッドに企業カードが存在する
    const cards = page.locator('#grid .cc');
    await expect(cards).toHaveCount({ min: 50 });  // 최소 50개
  });

  test('검색 기능', async ({ page }) => {
    await page.goto(FILE_URL);
    // 검색창에 입력
    await page.fill('#srch', '캡콤');
    await page.waitForTimeout(400); // debounce 대기
    const cards = page.locator('#grid .cc');
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThan(20);  // 필터링 동작 확인
  });

  test('필터 클릭 — 국가 필터', async ({ page }) => {
    await page.goto(FILE_URL);
    // 필터 버튼 찾기 (한국)
    const filterArea = page.locator('#filters');
    await expect(filterArea).toBeVisible();
    const krFilter = filterArea.locator('text=한국').first();
    if (await krFilter.count() > 0) {
      await krFilter.click();
      await page.waitForTimeout(300);
      const cards = page.locator('#grid .cc');
      const count = await cards.count();
      expect(count).toBeGreaterThan(0);
    }
  });

  test('카드 클릭 → 모달/드로어 오픈', async ({ page }) => {
    await page.goto(FILE_URL);
    const firstCard = page.locator('#grid .cc').first();
    await firstCard.click();
    // 모달 또는 V2 드로어 중 하나가 열림
    const modal = page.locator('.modal-overlay.open, .v2-drawer-overlay.open');
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('V2 mode — ?ui=v2 으로 플래그 ON', async ({ page }) => {
    await page.goto(FILE_URL + '?ui=v2');
    // body에 data-ui="v2" 속성이 설정됨
    const body = page.locator('body');
    await expect(body).toHaveAttribute('data-ui', 'v2', { timeout: 3000 });
    // 카드 존재 확인
    const cards = page.locator('#grid .cc');
    await expect(cards).toHaveCount({ min: 50 });
  });

  test('V2 mode — 드로어 오픈', async ({ page }) => {
    await page.goto(FILE_URL + '?ui=v2');
    await page.waitForTimeout(500);
    const firstCard = page.locator('#grid .cc').first();
    await firstCard.click();
    // V2 드로어가 열림
    const drawer = page.locator('.v2-drawer-overlay.open');
    await expect(drawer).toBeVisible({ timeout: 3000 });
    // 회사명 표시 확인
    const drawerName = page.locator('#v2dname');
    await expect(drawerName).not.toBeEmpty();
  });

  test('V2 mode — 즐겨찾기 토글', async ({ page }) => {
    await page.goto(FILE_URL + '?ui=v2');
    await page.waitForTimeout(500);
    // ★ 버튼 클릭
    const favBtn = page.locator('.v2-fav-btn').first();
    await expect(favBtn).toBeVisible();
    await favBtn.click();
    // 즐겨찾기 칩이 나타남
    // (localStorage 처리가 동기적이므로 즉시 확인)
    await expect(favBtn).toHaveClass(/on/);
  });

});
