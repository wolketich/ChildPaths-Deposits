import csv
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from difflib import SequenceMatcher
from dotenv import load_dotenv

# === CONFIG ===
CSV_FILE = "transactions.csv"
REPORT_FILE = "transaction_report.csv"
LOG_FILE = "transaction_debug.log"

# === UTILS ===
def fuzzy_match(name, options):
    scores = [(SequenceMatcher(None, name.lower(), o[0].lower()).ratio(), *o) for o in options]
    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[:5]

def log_debug(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def load_driver():
    options = Options()
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)

def login(driver, wait, email, password):
    driver.get("https://app.childpaths.ie/auth/login")
    wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "#signin-form button").click()
    wait.until(EC.url_contains("/dashboard"))
    log_debug("✅ Logged in")

def select_branch(driver, wait):
    driver.get("https://app.childpaths.ie/user-finance-account/create")
    wait.until(EC.presence_of_element_located((By.NAME, "branch")))
    branches = driver.find_elements(By.CSS_SELECTOR, "select[name='branch'] option")
    print("\nSelect a branch:")
    for i, b in enumerate(branches):
        print(f"{i}: {b.text.strip()} [{b.get_attribute('value')}]")
    index = int(input("Branch number: "))
    selected = branches[index]
    Select(driver.find_element(By.NAME, "branch")).select_by_value(selected.get_attribute("value"))
    log_debug(f"✅ Branch selected: {selected.text.strip()}")
    time.sleep(1)
    return selected.get_attribute("value")

def extract_billpayers(driver):
    driver.find_element(By.CSS_SELECTOR, ".select2-selection--multiple").click()
    time.sleep(2)
    options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
    billpayers = []
    for option in options:
        name = option.text.strip()
        element_id = option.get_attribute("id")
        if name and element_id:
            billpayers.append((name, element_id))
    log_debug(f"📋 Extracted {len(billpayers)} billpayers.")
    return billpayers

def create_account(driver, wait, owner_name, branch_value):
    driver.get("https://app.childpaths.ie/user-finance-account/create")
    Select(driver.find_element(By.NAME, "branch")).select_by_value(branch_value)
    driver.find_element(By.ID, "display_name").send_keys("Deposit Account")
    Select(driver.find_element(By.NAME, "currency")).select_by_value("EUR")
    try:
        switch_wrapper = driver.find_element(By.CSS_SELECTOR, ".bootstrap-switch-wrapper")
        if "bootstrap-switch-on" in switch_wrapper.get_attribute("class"):
            switch_wrapper.click()
    except: pass
    time.sleep(1)
    driver.find_element(By.CSS_SELECTOR, ".select2-selection--multiple").click()
    time.sleep(1)
    driver.switch_to.active_element.send_keys(owner_name)
    time.sleep(1.5)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    time.sleep(1)
    driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="Create"]').click()
    time.sleep(2)
    errors = driver.find_elements(By.CSS_SELECTOR, ".alert-danger li, .alert-warning li")
    if errors:
        for e in errors:
            log_debug("❌ Form error: " + e.text)
        return False
    log_debug(f"✅ Account created for {owner_name}")
    return True

def get_account_id(driver):
    driver.get("https://app.childpaths.ie/user-finance-account/index")
    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
    for row in rows:
        caption = row.find_elements(By.TAG_NAME, "td")[3].text
        if "Deposit Account" in caption:
            return row.get_attribute("id").replace("ufa_", "")
    return None

def make_transaction(driver, wait, account_id, tx_type, amount, note, date):
    try:
        url = f"https://app.childpaths.ie/user-finance-account/{account_id}/transaction/{tx_type}"
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.NAME, "value")))
        driver.find_element(By.NAME, "value").send_keys(str(amount))
        if note:
            driver.find_element(By.NAME, "description").send_keys(note)
        if date:
            driver.find_element(By.NAME, "received_at").send_keys(date)
        driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="Add"]').click()
        time.sleep(1.5)
        log_debug(f"✅ {tx_type.capitalize()} successful for €{amount}")
        return True
    except Exception as e:
        log_debug(f"❌ {tx_type.capitalize()} failed for €{amount}: {str(e)}")
        return False

def main():
    load_dotenv()
    email = os.getenv("CHILD_EMAIL")
    password = os.getenv("CHILD_PASSWORD")
    driver = load_driver()
    wait = WebDriverWait(driver, 10)
    report = []
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- TRANSACTION DEBUG LOG ---\n")

    try:
        login(driver, wait, email, password)
        branch_value = select_branch(driver, wait)
        billpayers = extract_billpayers(driver)
        accounts = {}

        matches = {}
        with open(CSV_FILE, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            for row in reader:
                row = {k.strip(): v.strip() for k, v in row.items()}
                name = row.get('Bill Payer', '')
                matched = fuzzy_match(name, billpayers)
                if matched and matched[0][0] >= 0.95:
                    matches[name] = matched[0][1]
                else:
                    print(f"❌ No perfect match for: {name}")
                    for i, (score, label, _) in enumerate(matched):
                        print(f"{i}: {label} ({int(score*100)}%)")
                    idx = int(input("Pick best match #: "))
                    matches[name] = matched[idx][1]

        with open(CSV_FILE, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            for row in reader:
                row = {k.strip(): v.strip() for k, v in row.items()}
                name = row.get('Bill Payer', '')
                date = row.get('Date', '')
                note = row.get('Note', '')
                returned = row.get('Is Returned', '').lower() == 'yes'
                amount_str = row.get('Amount', '0')
                amount = float(amount_str) if amount_str else 0.0
                tx_amount = 0.01 if amount == 0 else amount
                matched_name = matches.get(name)

                if matched_name not in accounts:
                    if not create_account(driver, wait, matched_name, branch_value):
                        report.append([matched_name, "Account", amount, "FAILED", "Account creation failed"])
                        continue
                    account_id = get_account_id(driver)
                    accounts[matched_name] = account_id
                else:
                    account_id = accounts[matched_name]

                status = "OK"
                if not make_transaction(driver, wait, account_id, "deposit", tx_amount, note, date):
                    status = "FAILED"
                    report.append([matched_name, "Deposit", tx_amount, status, "Error during deposit"])
                    continue
                report.append([matched_name, "Deposit", tx_amount, "OK", ""])

                if returned or amount == 0:
                    if not make_transaction(driver, wait, account_id, "withdrawal", tx_amount, note, date):
                        report.append([matched_name, "Withdrawal", tx_amount, "FAILED", "Error during withdrawal"])
                    else:
                        report.append([matched_name, "Withdrawal", tx_amount, "OK", ""])

        with open(REPORT_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Bill Payer", "Type", "Amount", "Status", "Notes"])
            writer.writerows(report)
        print(f"✅ Done. Report saved to {REPORT_FILE}")
        print(f"📝 Debug log saved to {LOG_FILE}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
