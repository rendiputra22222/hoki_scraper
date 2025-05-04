import os
import json
import time
from collections import defaultdict
from datetime import datetime
from playwright.sync_api import Playwright, sync_playwright
import gspread
from google.oauth2.service_account import Credentials

def upload_to_sheet(sheet_name, data_dict, sorted_dates):
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS_JSON not found in environment variables")

    info = json.loads(creds_json)
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(info, scopes=scope)
    client = gspread.authorize(creds)

    sheet = client.open("DATA HOKI")
    worksheet_title = "HOKI 4D"

    try:
        worksheet = sheet.worksheet(worksheet_title)
    except:
        worksheet = sheet.add_worksheet(title=worksheet_title, rows="100", cols="100")

    header = worksheet.row_values(1)
    if not header:
        header = ["JAM"]

    header_dates = header[1:]
    for tanggal in sorted_dates:
        if tanggal not in header_dates:
            header.append(tanggal)
    worksheet.update(values=[header], range_name="A1")

    jam_rows = worksheet.col_values(1)[1:]
    jam_map = {jam.zfill(2): i + 2 for i, jam in enumerate(jam_rows)}

    for jam, tanggal_data in data_dict.items():
        jam_str = jam.zfill(2)
        row_idx = jam_map.get(jam_str)

        if not row_idx:
            worksheet.append_row([jam_str] + [""] * (len(header) - 1))
            row_idx = worksheet.row_count

        row_values = worksheet.row_values(row_idx)
        if len(row_values) < len(header):
            row_values += [""] * (len(header) - len(row_values))

        for tanggal in sorted_dates:
            col_idx = header.index(tanggal)
            if not row_values[col_idx]:
                value = tanggal_data.get(tanggal, "")
                if value:
                    row_values[col_idx] = value

        worksheet.update(values=[row_values], range_name=f"A{row_idx}")

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.route("**/*", lambda route, request: route.abort() if request.resource_type == "image" else route.continue_())
    page = context.new_page()
    page.goto("https://indratogel31303.com/")

    page.get_by_role("textbox", name="Username").fill("kucingbuta")
    page.get_by_role("textbox", name="Password").fill("Basokikil6")
    page.get_by_role("button", name="LOGIN").click()
    page.get_by_role("button", name="Saya Setuju").click()
    page.get_by_role("link", name=" History ").click()
    page.get_by_role("link", name=" History Nomor").click()
    page.get_by_role("link", name="HOKIDRAW", exact=True).click()

    # Tunggu tabel muncul dengan data tanggal valid
    page.wait_for_selector("table#listhistory tbody tr td:nth-child(1):has-text('-')")
    time.sleep(2)

    rows = page.query_selector_all("table#listhistory tbody tr")
    data = defaultdict(dict)
    tanggal_set = set()

    for row in rows:
        cols = row.query_selector_all("td")
        if len(cols) < 4:
            continue
        datetime_str = cols[0].inner_text().strip()
        nomor_full = cols[3].inner_text().strip()
        nomor = nomor_full[-4:]  # Ambil 4 digit terakhir

        try:
            dt = datetime.strptime(datetime_str, "%d-%m-%Y %H:%M:%S")
            tanggal_iso = dt.strftime("%Y-%m-%d")
            jam_str = dt.strftime("%H")
            data[jam_str][tanggal_iso] = nomor
            tanggal_set.add(tanggal_iso)
        except Exception as e:
            print(f"Error parsing: {datetime_str} -> {e}")

    tanggal_terbaru = sorted(tanggal_set, reverse=True)[:10]
    upload_to_sheet("Hasil Togel", data, tanggal_terbaru)

    print("✅ Data berhasil diupload ke Google Sheet.")
    context.close()
    browser.close()

def safe_run():
    MAX_RETRIES = 3
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with sync_playwright() as playwright:
                run(playwright)
            break  # keluar jika sukses
        except Exception as e:
            print(f"❌ Percobaan {attempt} gagal: {e}")
            if attempt == MAX_RETRIES:
                print("🚫 Gagal setelah 3 kali percobaan.")
            else:
                print("🔁 Mencoba ulang dalam 3 detik...")
                time.sleep(3)

if __name__ == "__main__":
    safe_run()
