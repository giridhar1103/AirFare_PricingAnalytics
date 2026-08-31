import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const workspaces = [
  ["overview", "./"],
  ["markets", "markets"],
  ["models", "models"],
  ["scenario", "scenario"],
  ["methodology", "methodology"]
] as const;

for (const [name, path] of workspaces) {
  test(`${name} workspace has no automated WCAG A or AA violations`, async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-chromium", "One semantic audit per workspace is sufficient");
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const violations = results.violations.map((violation) => ({
      id: violation.id,
      impact: violation.impact,
      nodes: violation.nodes.map((node) => ({
        target: node.target,
        html: node.html,
        summary: node.failureSummary
      }))
    }));
    expect(violations).toEqual([]);
  });
}
