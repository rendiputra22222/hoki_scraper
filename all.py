import re
import os
import json
import time
from collections import defaultdict
from playwright.sync_api import sync_playwright
import gspread
from google.oauth2.service_account import Credentials

markets = {
    "TTM6": "TTM PAGI", "HUA01": "HUAHIN 0100", "BKK01": "BANGKOK 0130", "KTM": "KENTUCKY MID",
    "FLM": "FLORIDA MID", "NYM": "NEWYORK MID", "BRU02": "BRUNEI 02", "NCD": "CAROLINA DAY",
    "ORG03": "OREGON 03", "ORG6": "OREGON 06", "CLF": "CALIFORNIA", "FLE": "FLORIDA EVE",
    "ORG09": "OREGON 09", "BKK02": "BANGKOK 0930", "NYE": "NEWYORK EVE", "KTE": "KENTUCKY EVE",
    "NCD2": "CAROLINA EVE", "TTC": "TOTO CAMBODIA", "CHS11": "CHELSEA 11", "ORG12": "OREGON 12",
    "PPT12": "POIPET 12", "TTM1": "TTM SIANG", "BLE": "BULLSEYE", "SYDLT": "SYDNEY",
    "BRU14": "BRUNEI 14", "CHS15": "CHELSEA 15", "MALI15": "TOTOMALI 1530", "PPT15": "POIPET 15",
    "TTM2": "TTM SORE", "HUA02": "HUAHIN 1630", "KK1": "KINGKONG 4D SORE", "SGD": "SINGAPORE",
    "MAG": "MAGNUM4D", "TTM3": "TTM MALAM 1", "CHS19": "CHELSEA 19", "PPT19": "POIPET 19",
    "PCO": "PCSO", "MALI20": "TOTOMALI 2030", "CHS21": "CHELSEA 21", "HUA03": "HUAHIN 2100",
    "NVD": "NEVADA", "BRU21": "BRUNEI 21", "TTM4": "TTM MALAM 2", "PPT22": "POIPET 22",
    "HKGLT": "HONGKONG", "TTM5": "TTM MALAM 3", "KK2": "KINGKONG 4D MALAM", "MALI23": "TOTOMALI 2330"
}

def extract_date(raw_date):
    match = re.match(r"(\d{4}-\d{2}-\d{2})", raw_date)
    return match.group(1) if match else None

def extract_result(raw_result):
    match = re.match(r"(\d{4})", raw_result)
    return match.group(1) if match else None

def extract_first_page(page, pasaran_name, data, all_dates):
    print(f"[{pasaran_name}] Ambil halaman pertama saja")
    rows = page.locator("table tbody tr")
    count = rows.count()
    for i in range(count):
        row = rows.nth(i)
        tanggal = extract_date(row.locator("td").nth(2).text_content())
        result = extract_result(row.locator("td").nth(3).text_content())
        if tanggal and result:
            data[pasaran_name][tanggal] = result
            all_dates.add(tanggal)

def write_to_spreadsheet(data, sorted_dates):
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not creds_json:
        print("❌ GOOGLE_CREDENTIALS_JSON tidak ditemukan.")
        return

    creds_dict = json.loads(creds_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(creds_dict, scopes=scopes)

    gc = gspread.authorize(credentials)
    sh = gc.open("PASAR MALAM")
    worksheet = sh.worksheet("All")

    existing_data = worksheet.get_all_values()
    header = existing_data[0] if existing_data else ["pasaran"]
    header_map = {col: i for i, col in enumerate(header)}
    new_dates = [d for d in sorted_dates if d not in header_map]

    if new_dates:
        header += new_dates
        worksheet.update("A1", [header])
        header_map = {col: i for i, col in enumerate(header)}

    pasaran_rows = {row[0]: i + 2 for i, row in enumerate(existing_data[1:])}

    for pasaran, values in data.items():
        if pasaran in pasaran_rows:
            row_idx = pasaran_rows[pasaran]
            for tanggal, result in values.items():
                col_idx = header_map.get(tanggal)
                if col_idx is not None:
                    current = worksheet.cell(row_idx, col_idx + 1).value
                    if not current:
                        worksheet.update_cell(row_idx, col_idx + 1, result)
        else:
            row_data = [""] * len(header)
            row_data[0] = pasaran
            for tanggal, result in values.items():
                col_idx = header_map.get(tanggal)
                if col_idx is not None:
                    row_data[col_idx] = result
            worksheet.append_row(row_data)

    print("✅ Data berhasil ditambahkan ke Google Sheet tanpa menghapus data lama.")

def scrape_all():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(java_script_enabled=True, bypass_csp=True)
        context.route("**/*", lambda route, request: route.abort() if request.resource_type == "image" else route.continue_())
        page = context.new_page()
        page.goto("https://depobos80993.com/#/index?category=lottery")

        page.get_by_role("img", name="close").click()

        with page.expect_popup() as popup_info:
            page.get_by_role("img", name="MAGNUM4D").click()
        page1 = popup_info.value

        page1.get_by_role("textbox", name="-14 digit atau kombinasi huruf").fill("babikecilku")
        page1.get_by_role("textbox", name="-16 angka atau kombinasi huruf").fill("Basokikil6")
        page1.get_by_text("Masuk").click()
        page1.get_by_role("link", name="Saya Setuju").click()
        time.sleep(3)
        page1.get_by_role("link", name="NOMOR HISTORY NOMOR").click()
        page1.wait_for_timeout(1500)

        data = defaultdict(dict)
        all_dates = set()

        for code, name in markets.items():
            print(f"⏳ Memproses: {name}")
            page1.locator("#marketSelect").select_option(code)
            page1.wait_for_timeout(1500)
            extract_first_page(page1, name, data, all_dates)

        sorted_dates = sorted(all_dates, reverse=True)
        write_to_spreadsheet(data, sorted_dates)

        context.close()
        browser.close()

if __name__ == "__main__":
    scrape_all()
