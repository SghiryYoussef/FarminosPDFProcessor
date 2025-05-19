import asyncio
import re
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# === Configuration ===
env_data = {
    "base_url": "https://farminos-staging.fly.dev",
    "invoices_url": "https://farminos-staging.fly.dev/Itto%20Group/itto-almonds/invoices",
    "login": "https://farminos-staging.fly.dev/login",
    "email": "irrigation@ittogroup.ma",
    "password": "Irrig1234*"  # Password for staging environment
}


def log(message: str):
    """Prints a timestamped message to the console."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")


async def login(page):
    """Logs into the FarminOS system using credentials."""
    log("Opening login page...")
    await page.goto(env_data["login"])
    await page.fill('input[name="email"]', env_data["email"])
    await page.fill('input[name="password"]', env_data["password"])
    await page.click('button[type="submit"]')
    await page.wait_for_load_state("networkidle")
    log("Successfully logged in.")


async def get_invoice_ids(page):
    """Retrieves all invoice IDs by paging through the invoice list."""
    log("Navigating to the invoice list...")
    await page.goto(env_data["invoices_url"])
    await page.wait_for_selector("table")

    invoice_ids = set()

    while True:
        log("Extracting invoice IDs from the current page...")
        hrefs = await page.eval_on_selector_all(
            'a[href*="/invoices/"]',
            'elements => elements.map(el => el.getAttribute("href"))')
        for href in hrefs:
            match = re.search(r'/invoices/(\d+)$', href)
            if match:
                invoice_ids.add(match.group(1))

        next_button = await page.query_selector("div.join button:last-child")
        if next_button:
            is_disabled = await next_button.is_disabled()
            if not is_disabled:
                log("Moving to the next page of invoices...")
                await next_button.click()
                await asyncio.sleep(2)
                await page.wait_for_selector("table")
            else:
                log("No more pages.")
                break
        else:
            log("Next button not found.")
            break

    log(f"Found {len(invoice_ids)} invoice(s) in total.")
    return list(invoice_ids)


async def clean_units_column(page):
    """Remove only the 'Units' column (2nd column) from header and body."""
    await page.evaluate("""
        const tableRows = document.querySelectorAll("table tr");
        tableRows.forEach(row => {
            const cells = row.querySelectorAll("th, td");
            if (cells.length > 1) {
                cells[1].remove();  // Remove second column (Units)
            }
        });
    """)


async def clean_item_names(page):
    """Remove '(Sac 25 kg)' or similar from product names only (first column)."""
    await page.evaluate("""
        const rows = document.querySelectorAll("table tbody tr");
        rows.forEach(row => {
            const firstCell = row.querySelector("td");
            if (firstCell) {
                firstCell.innerText = firstCell.innerText.replace(/\\(sac\\s*\\d+\\s*kg\\)/gi, "").trim();
            }
        });
    """)


async def remove_payment_method(page):
    """Remove the <div> that contains the 'Payment method' only (with class gap-1)."""
    await page.evaluate("""
        const paymentMethodDiv = document.querySelector("div.gap-1");
        if (paymentMethodDiv) {
            paymentMethodDiv.remove();
        }
    """)


async def modify_and_save_invoice(page, invoice_id, output_dir):
    """Modifies and saves a single invoice as a PDF."""
    invoice_url = f"{env_data['invoices_url']}/{invoice_id}/print"
    log(f"Opening invoice {invoice_id} for editing...")
    await page.goto(invoice_url)
    await page.wait_for_load_state("networkidle")

    await clean_units_column(page)
    await clean_item_names(page)
    await remove_payment_method(page)

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    pdf_path = output_path / f"invoice_{invoice_id}.pdf"

    await page.pdf(path=str(pdf_path), format="A4")
    log(f"Invoice {invoice_id} saved as PDF at: {pdf_path}")


async def main():
    """Main entry point of the script."""
    output_dir = "all_modified_invoices"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale='fr-FR')  # Set browser language to French
        page = await context.new_page()

        await login(page)
        invoice_ids = await get_invoice_ids(page)
        if not invoice_ids:
            log("No invoices found. Exiting.")
            return

        for invoice_id in invoice_ids:
            try:
                log(f"Processing invoice ID: {invoice_id}...")
                await modify_and_save_invoice(page, invoice_id, output_dir)
            except Exception as e:
                log(f"Could not process invoice {invoice_id}: {e}")

        await browser.close()
        log("All invoices processed. Done!")


if __name__ == "__main__":
    asyncio.run(main())
