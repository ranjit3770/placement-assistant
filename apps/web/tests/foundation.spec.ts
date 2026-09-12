import { expect, test } from "@playwright/test";

test("foundation renders, connects and fits the viewport", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "Your next opportunity",
  );
  await expect(page.getByRole("status")).toHaveText("Platform connected");
  await expect(
    page.getByText("No student records loaded", { exact: false }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("connection failure offers a working retry", async ({ page }) => {
  await page.route("**/ready", (route) =>
    route.fulfill({ status: 503, json: { status: "not_ready" } }),
  );
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("unavailable");
  await page.unroute("**/ready");
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByRole("status")).toHaveText("Platform connected");
});
