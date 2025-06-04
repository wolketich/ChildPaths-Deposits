import csv
import time
from datetime import datetime
from difflib import SequenceMatcher
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import streamlit as st

# === CONFIG ===
CSV_FILE = "transactions.csv"
REPORT_FILE = "transaction_report.csv"
LOG_FILE = "transaction_debug.log"

# === UTILS ===
def fuzzy_match(name, options):
    scores = [(SequenceMatcher(None, name.lower(), o[0].lower()).ratio(), *o) for o in options]
    scores.sort(reverse=True, key=lambda x: x[0])
    return scores[0] if scores else (0, None, None)

def log_debug(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    st.text(msg)

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
    branch_map = {b.text.strip(): b.get_attribute("value") for b in branches if b.get_attribute("value")}
    selected_branch = st.selectbox("Select Branch:", list(branch_map.keys()))
    Select(driver.find_element(By.NAME, "branch")).select_by_value(branch_map[selected_branch])
    log_debug(f"✅ Branch selected: {selected_branch}")
    return branch_map[selected_branch]

def extract_billpayers(driver):
    driver.find_element(By.CSS_SELECTOR, ".select2-selection--multiple").click()
    WebDriverWait(driver, 5).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".select2-results__option")))
    options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
    return [(option.text.strip(), option.get_attribute("id")) for option in options if option.text.strip()]

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

    driver.find_element(By.CSS_SELECTOR, ".select2-selection--multiple").click()
    time.sleep(0.5)
    driver.switch_to.active_element.send_keys(owner_name)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="Create"]').click()
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    errors = driver.find_elements(By.CSS_SELECTOR, ".alert-danger li, .alert-warning li")
    if errors:
        for e in errors:
            log_debug("❌ Form error: " + e.text)
        return False
    log_debug(f"✅ Account created for {owner_name}")
    return True

def get_account_id(driver):
    driver.get("https://app.childpaths.ie/user-finance-account/index")
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr")))
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
        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        log_debug(f"✅ {tx_type.capitalize()} successful for €{amount}")
        return True
    except Exception as e:
        log_debug(f"❌ {tx_type.capitalize()} failed for €{amount}: {str(e)}")
        return False

def run_batch():
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Run Batch") and email and password:
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

                    score, matched_name, _ = fuzzy_match(name, billpayers)
                    if score < 0.6:
                        log_debug(f"❌ Skipped: {name} (no good match)")
                        report.append([name, "N/A", amount, "FAILED", "Billpayer not matched"])
                        continue

                    if matched_name not in accounts:
                        if not create_account(driver, wait, matched_name, branch_value):
                            report.append([matched_name, "Account", amount, "FAILED", "Account creation failed"])
                            continue
                        account_id = get_account_id(driver)
                        accounts[matched_name] = account_id
                    else:
                        account_id = accounts[matched_name]

                    if not make_transaction(driver, wait, account_id, "deposit", tx_amount, note, date):
                        report.append([matched_name, "Deposit", tx_amount, "FAILED", "Error during deposit"])
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
            st.success(f"✅ Done. Report saved to {REPORT_FILE}")
        finally:
            driver.quit()

if __name__ == "__main__":
    st.title("💳 ChildPaths Deposit Dashboard")
    st.markdown("Upload your CSV as 'transactions.csv' and run batch transactions.")
    run_batch()
