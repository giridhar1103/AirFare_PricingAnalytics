import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  const browserErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  page.on("pageerror", (error) => browserErrors.push(error.message));
  await page.goto("./");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  expect(browserErrors).toEqual([]);
});

test("loads observed data and navigates every primary workspace", async ({ page }) => {
  await expect(page.getByText("Observed DOT route pricing workspace")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Turn market evidence into review-ready actions." })).toBeVisible();

  for (const [link, heading] of [
    ["Market explorer", "Read the route before changing the fare."],
    ["Model lab", "Forecast what is predictable. Flag what is not identified."],
    ["Scenario lab", "Stress test a fare plan before you recommend it."],
    ["Methodology", "Every recommendation should survive a review."]
  ]) {
    const menuButton = page.getByRole("button", { name: "Open navigation" });
    if (await menuButton.isVisible()) await menuButton.click();
    await page.getByRole("link", { name: link }).click();
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
  }
});

test("supports a direct model-lab refresh under the nested base path", async ({ page }) => {
  await page.goto("models");
  await expect(page).toHaveURL(/\/farelab\/models$/);
  await expect(page.getByRole("heading", { name: "Forecast what is predictable. Flag what is not identified." })).toBeVisible();
  await expect(page.getByText("No DOT-derived elasticity is approved for scenario use")).toBeVisible();
});

test("updates scenario math from feasible inputs", async ({ page }) => {
  await page.goto("scenario");
  const initialFare = await page.locator("#fare-change").inputValue();
  expect(initialFare).toBe("3");
  await page.locator("#fare-change").fill("5");
  await page.locator("#capacity-change").fill("4");
  await page.locator("#elasticity-assumption").fill("-1.2");
  await expect(page.locator('output[for="fare-change"]')).toHaveText("+5%");
  await expect(page.getByRole("definition").filter({ hasText: "Analyst supplied" })).toBeVisible();
  await expect(page.getByText("Revenue proxy change")).toBeVisible();
});

test("generates a grounded decision brief without changing scenario math", async ({ page }) => {
  await page.route("https://api.giriworks.com/farelab-ai/brief", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        routeId: "11433:13342:DL",
        provider: "Anthropic",
        model: "claude-haiku-4-5-20251001",
        generatedAtUtc: "2026-09-02T00:00:00Z",
        generationMode: "ai",
        calculationSource: "FareLab server calculation using governed scenario equations",
        support: "Within observed range",
        scenario: {},
        brief: {
          recommendation: "Run controlled test",
          headline: "Supported fare adjustment is suitable for a controlled test",
          summary: "The scenario remains within observed support and warrants a measured market test.",
          evidence: [
            "Proposed fare remains within the observed range.",
            "Revenue proxy moves higher under the supplied assumptions."
          ],
          risks: [
            "Elasticity is analyst supplied.",
            "Revenue proxy excludes route accounting cost."
          ],
          nextStep: "Define a test cell and rollback criteria before implementation."
        }
      })
    });
  });
  await page.goto("scenario");
  const revenueBefore = await page.locator(".decision-change").textContent();
  await page.getByRole("button", { name: "Generate decision brief" }).click();
  await expect(page.getByText("Run controlled test", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Supported fare adjustment is suitable for a controlled test" })).toBeVisible();
  await expect(page.getByText(/AI-generated narrative from Anthropic/)).toBeVisible();
  const revenueAfter = await page.locator(".decision-change").textContent();
  expect(revenueAfter).toBe(revenueBefore);
});

test("does not overflow the viewport", async ({ page }) => {
  const viewport = page.viewportSize();
  const layout = await page.evaluate(() => {
    window.scrollTo(1000, 0);
    const kpis = document.querySelector<HTMLElement>(".kpi-grid");
    return {
      bodyScrollWidth: document.body.scrollWidth,
      windowScrollX: window.scrollX,
      kpiOverflowIsContained: Boolean(kpis && kpis.scrollWidth > kpis.clientWidth && getComputedStyle(kpis).overflowX === "auto")
    };
  });
  expect(layout.bodyScrollWidth).toBeLessThanOrEqual(viewport?.width ?? layout.bodyScrollWidth);
  expect(layout.windowScrollX).toBe(0);
  if ((viewport?.width ?? 1000) <= 650) expect(layout.kpiOverflowIsContained).toBe(true);
});
