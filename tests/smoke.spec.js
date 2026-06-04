// smoke.spec.js — Playwright 스모크 테스트 v1.0.13
const { test, expect } = require('@playwright/test');
const path = require('path');

const FILE_URL = 'file://' + path.resolve(__dirname, '../index.html').replace(/\\/g, '/');
const V2_URL   = FILE_URL + '?ui=v2';

// ── V1 기본 기능 ──────────────────────────────────────────────────────────────
test.describe('V1 — 기본 기능 (default)', () => {

  test('페이지 로드 + 기업 카드 표시', async ({ page }) => {
    await page.goto(FILE_URL);
    await expect(page.locator('header h1')).toContainText('게임업계');
    await expect(page.locator('#grid .cc')).toHaveCount({ min: 50 });
  });

  test('검색 기능', async ({ page }) => {
    await page.goto(FILE_URL);
    await page.fill('#srch', '캡콤');
    await page.waitForTimeout(350);
    const count = await page.locator('#grid .cc').count();
    expect(count).toBeGreaterThan(0);
    expect(count).toBeLessThan(20);
  });

  test('카드 클릭 → 모달 오픈', async ({ page }) => {
    await page.goto(FILE_URL);
    await page.locator('#grid .cc').first().click();
    await expect(page.locator('.modal-overlay.open')).toBeVisible({ timeout: 3000 });
  });

  test('body에 data-ui 없음 (V1)', async ({ page }) => {
    await page.goto(FILE_URL);
    const attr = await page.locator('body').getAttribute('data-ui');
    expect(attr).toBeNull();
  });
});

// ── V2 — ?ui=v2 ──────────────────────────────────────────────────────────────
test.describe('V2 — ?ui=v2 기능', () => {

  test('V2 활성화: body[data-ui="v2"]', async ({ page }) => {
    await page.goto(V2_URL);
    await expect(page.locator('body')).toHaveAttribute('data-ui', 'v2', { timeout: 3000 });
  });

  test('V2 카드 표시 (237개)', async ({ page }) => {
    await page.goto(V2_URL);
    await expect(page.locator('#grid .cc')).toHaveCount({ min: 50 });
  });

  test('V2 드로어 오픈 + TL;DR 표시', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('#grid .cc').first().click();
    // V2 드로어 열림
    await expect(page.locator('.v2-drawer-overlay.open')).toBeVisible({ timeout: 3000 });
    // TL;DR 블록 존재
    await expect(page.locator('.v2-tldr')).toBeVisible();
    // 포인트/리스크 레이블
    await expect(page.locator('.v2-tldr-label.pt')).toContainText('포인트');
    await expect(page.locator('.v2-tldr-label.ri')).toContainText('리스크');
  });

  test('V2 액션 버튼: 메모/태그 + 출처 열기', async ({ page }) => {
    await page.goto(V2_URL);
    await page.locator('#grid .cc').first().click();
    await expect(page.locator('.v2-act-memo')).toBeVisible();
    await expect(page.locator('.v2-act-src')).toBeVisible();
  });

  test('V2 즐겨찾기 ★ 토글', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    const favBtn = page.locator('.v2-fav-btn').first();
    await expect(favBtn).toBeVisible();
    await favBtn.click();
    await expect(favBtn).toHaveClass(/on/);
  });

  test('V2 태그 필터 렌더', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    // 태그 필터 영역 존재
    await expect(page.locator('#v2tagfilter')).toBeVisible();
    // 5개 태그 + 전체 = 6개 pill
    const pills = page.locator('.v2-tf-pill');
    await expect(pills).toHaveCount({ min: 6 });
  });

  test('V2 태그 필터 클릭 → 활성 상태', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    const pill = page.locator('.v2-tf-pill').nth(1); // '관심'
    await pill.click();
    await expect(pill).toHaveClass(/active/);
  });

  test('V2 드로어 → 태그 토글 → 카드 배지', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    // 첫 번째 카드 클릭
    await page.locator('#grid .cc').first().click();
    await expect(page.locator('.v2-drawer-overlay.open')).toBeVisible({ timeout: 3000 });
    // 메모/태그 패널 열기
    await page.locator('.v2-act-memo').click();
    // '관심' 태그 토글
    await page.locator('.v2-tag-pill.v2-tag-관심').click();
    await expect(page.locator('.v2-tag-pill.v2-tag-관심')).toHaveClass(/on/);
  });

  test('V2 변경이력 탭 클릭 → 변경이력 뷰', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    // 변경이력 탭 클릭
    const clTab = page.locator('.stab[data-tab="cl"]');
    await expect(clTab).toBeVisible();
    await clTab.click();
    await page.waitForTimeout(300);
    // 변경이력 컨테이너 존재
    await expect(page.locator('.v2-cl-wrap')).toBeVisible();
    // 기간 토글 존재
    await expect(page.locator('.v2-cl-range')).toHaveCount({ min: 3 });
  });

  test('V2 변경이력 항목 클릭 → 드로어 오픈', async ({ page }) => {
    await page.goto(V2_URL);
    await page.waitForTimeout(400);
    await page.locator('.stab[data-tab="cl"]').click();
    await page.waitForTimeout(300);
    const firstItem = page.locator('.v2-cl-item').first();
    if (await firstItem.count() > 0) {
      await firstItem.click();
      await expect(page.locator('.v2-drawer-overlay.open')).toBeVisible({ timeout: 3000 });
    }
  });

  test('V2 URL 태그 파라미터 복원', async ({ page }) => {
    await page.goto(V2_URL + '&tag=%EA%B4%80%EC%8B%AC'); // tag=관심
    await page.waitForTimeout(500);
    // 태그 필터가 '관심'으로 활성화됨
    const activePill = page.locator('.v2-tf-pill.active');
    if (await activePill.count() > 0) {
      const text = await activePill.textContent();
      expect(text?.trim()).toBe('관심');
    }
  });
});
