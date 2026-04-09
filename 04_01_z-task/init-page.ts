/**
 * Auto-login script for OKO Operations Center
 * Runs on page initialization to authenticate before any browser tools are used
 */

export default async ({ page }: { page: any }) => {
  const okoUrl = process.env.OKO_URL;
  const username = process.env.OKO_USERNAME;
  const password = process.env.OKO_PASSWORD;
  const accessKey = process.env.OKO_ACCESS_KEY;

  if (!okoUrl || !username || !password || !accessKey) {
    console.warn("OKO credentials not fully configured. Skipping auto-login.");
    console.warn(
      "Required env vars: OKO_URL, OKO_USERNAME, OKO_PASSWORD, OKO_ACCESS_KEY",
    );
    return;
  }

  try {
    console.log(`[OKO-LOGIN] Navigating to ${okoUrl}`);
    await page.goto(okoUrl, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2000);

    // Try common selectors for login form fields
    // Adjust these selectors based on the actual OKO login page structure
    const usernameSelectors = [
      'input[name="username"]',
      'input[name="login"]',
      'input[type="text"]:first-of-type',
      'input[placeholder*="username" i]',
      'input[placeholder*="login" i]',
    ];

    const passwordSelectors = [
      'input[name="password"]',
      'input[type="password"]',
      'input[placeholder*="password" i]',
    ];

    const accessKeySelectors = [
      'input[name="accessKey"]',
      'input[name="access_key"]',
      'input[name="key"]',
      'input[placeholder*="access key" i]',
      'input[placeholder*="key" i]',
    ];

    const submitSelectors = [
      'button[type="submit"]',
      'button:has-text("Sign In")',
      'button:has-text("Login")',
      'button:has-text("Zaloguj")',
      'button:has-text("Zatwierdź")',
    ];

    // Find and fill username field
    let usernameFilled = false;
    for (const selector of usernameSelectors) {
      try {
        const elem = await page.$(selector);
        if (elem) {
          await page.fill(selector, username);
          console.log(
            `[OKO-LOGIN] Filled username field using selector: ${selector}`,
          );
          usernameFilled = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (!usernameFilled) {
      console.warn(
        "[OKO-LOGIN] Could not find username field. Please verify OKO login page structure.",
      );
    }

    // Find and fill password field
    let passwordFilled = false;
    for (const selector of passwordSelectors) {
      try {
        const elem = await page.$(selector);
        if (elem) {
          await page.fill(selector, password);
          console.log(
            `[OKO-LOGIN] Filled password field using selector: ${selector}`,
          );
          passwordFilled = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (!passwordFilled) {
      console.warn(
        "[OKO-LOGIN] Could not find password field. Please verify OKO login page structure.",
      );
    }

    // Find and fill access key field
    let accessKeyFilled = false;
    for (const selector of accessKeySelectors) {
      try {
        const elem = await page.$(selector);
        if (elem) {
          await page.fill(selector, accessKey);
          console.log(
            `[OKO-LOGIN] Filled access key field using selector: ${selector}`,
          );
          accessKeyFilled = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (!accessKeyFilled) {
      console.warn(
        "[OKO-LOGIN] Could not find access key field. Please verify OKO login page structure.",
      );
    }

    // Find and click submit button
    let submitClicked = false;
    for (const selector of submitSelectors) {
      try {
        const elem = await page.$(selector);
        if (elem) {
          await page.click(selector);
          console.log(
            `[OKO-LOGIN] Clicked submit button using selector: ${selector}`,
          );
          submitClicked = true;
          break;
        }
      } catch (e) {
        // Try next selector
      }
    }

    if (!submitClicked) {
      console.warn(
        "[OKO-LOGIN] Could not find submit button. Please verify OKO login page structure.",
      );
    }

    // Wait for login to complete (page redirect or navigation)
    console.log("[OKO-LOGIN] Waiting for login to complete...");
    try {
      await page.waitForNavigation({ timeout: 15000 });
      console.log("[OKO-LOGIN] Navigation detected. Login likely successful.");
    } catch (e) {
      console.log(
        "[OKO-LOGIN] No navigation detected within timeout. Page may have updated in place.",
      );
    }

    await page.waitForTimeout(2000);

    const finalUrl = page.url();
    const pageTitle = await page.title();
    console.log(`[OKO-LOGIN] Final URL: ${finalUrl}`);
    console.log(`[OKO-LOGIN] Page title: ${pageTitle}`);

    // Check if we're likely logged in (heuristic)
    if (
      finalUrl.includes("dashboard") ||
      finalUrl.includes("main") ||
      pageTitle.includes("OKO")
    ) {
      console.log("[OKO-LOGIN] ✓ Auto-login completed successfully");
    } else {
      console.warn(
        "[OKO-LOGIN] Login status uncertain. Page may require additional interaction.",
      );
    }
  } catch (error) {
    console.error("[OKO-LOGIN] Error during auto-login:", error);
  }
};
