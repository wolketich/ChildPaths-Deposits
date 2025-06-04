from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from difflib import SequenceMatcher
import time

def login(driver, wait, email, password):
    driver.get("https://app.childpaths.ie/auth/login")
    wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "#signin-form button").click()
    wait.until(EC.url_contains("/dashboard"))
    print("✅ Logged in")

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
    print(f"\n✅ Branch selected: {selected.text.strip()}")
    time.sleep(1)

def extract_billpayers(driver):
    driver.find_element(By.CSS_SELECTOR, ".select2-selection--multiple").click()
    time.sleep(2)
    options = driver.find_elements(By.CSS_SELECTOR, ".select2-results__option")
    billpayers = []
    print("\n📋 Billpayers loaded:")
    for i, option in enumerate(options):
        name = option.text.strip()
        element_id = option.get_attribute("id")
        if name and element_id:
            billpayer_id = element_id.split('-')[-1]
            billpayers.append((name, billpayer_id))
            print(f"{i}: {name} [ID: {billpayer_id}]")
    return billpayers

def match_billpayer(billpayers, user_input):
    matches = []
    for name, billpayer_id in billpayers:
        score = SequenceMatcher(None, user_input.lower(), name.lower()).ratio()
        matches.append((score, name, billpayer_id))
    matches.sort(reverse=True, key=lambda x: x[0])
    best = matches[0]
    if best[0] >= 0.95:
        print(f"✅ Auto-selected match: {best[1]} [ID: {best[2]}] (Score: {round(best[0]*100)}%)")
        return best[1]
    else:
        print("\n⚠️ No perfect match. Top 5:")
        for i, (score, name, billpayer_id) in enumerate(matches[:5]):
            print(f"{i}: {name} [ID: {billpayer_id}] (Score: {round(score*100)}%)")
        choice = int(input("Choose correct number: "))
        return matches[choice][1]

def select_owner(driver, matched_name):
    # Reopen Select2 field
    driver.find_element(By.CSS_SELECTOR, ".select2-selection--multiple").click()
    time.sleep(1)
    driver.switch_to.active_element.send_keys(matched_name)
    time.sleep(1)
    driver.switch_to.active_element.send_keys(Keys.ENTER)
    print(f"✅ Typed and selected: {matched_name}")

def create_finance_account(driver, wait):
    driver.find_element(By.ID, "display_name").send_keys("Deposit Account")
    Select(driver.find_element(By.NAME, "currency")).select_by_value("EUR")
    try:
        switch_wrapper = driver.find_element(By.CSS_SELECTOR, ".bootstrap-switch-wrapper")
        if "bootstrap-switch-on" in switch_wrapper.get_attribute("class"):
            switch_wrapper.click()
            print("🔁 Switched 'Set as default' to OFF")
    except Exception as e:
        print(f"⚠️ Switch error: {e}")
    time.sleep(1)
    driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="Create"]').click()
    print("✅ Finance account created")

def extract_latest_deposit_account(driver, wait):
    driver.get("https://app.childpaths.ie/user-finance-account/index")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr")))
    rows = driver.find_elements(By.CSS_SELECTOR, "table.table tbody tr")
    for row in rows:
        caption_cell = row.find_elements(By.TAG_NAME, "td")[3]
        if "Deposit Account" in caption_cell.text:
            cells = row.find_elements(By.TAG_NAME, "td")
            account_id = row.get_attribute("id").replace("ufa_", "")
            details = {
                "Account ID": account_id,
                "Balance": cells[6].text.strip(),
                "Available Funds": cells[7].text.strip()
            }
            print("\n🧾 Latest Deposit Account:")
            for k, v in details.items():
                print(f"{k}: {v}")
            return account_id
    print("❌ Deposit Account not found")
    return None

def make_transaction(driver, wait, account_id, tx_type):
    url = f"https://app.childpaths.ie/user-finance-account/{account_id}/transaction/{tx_type}"
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.NAME, "value")))
    amount = input(f"{'💰' if tx_type == 'deposit' else '💸'} Amount: ")
    description = input("📝 Description (optional): ")
    received_at = input("📅 Received at (dd/mm/yyyy, optional): ")

    driver.find_element(By.NAME, "value").send_keys(amount)
    if description:
        driver.find_element(By.NAME, "description").send_keys(description)
    if received_at:
        driver.find_element(By.NAME, "received_at").send_keys(received_at)

    driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="Add"]').click()
    print(f"✅ {tx_type.capitalize()} submitted")
    time.sleep(2)

def main():
    email = input("Email: ")
    password = input("Password: ")
    input_name = input("Billpayer name to match: ")

    options = Options()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        login(driver, wait, email, password)
        select_branch(driver, wait)
        billpayers = extract_billpayers(driver)
        matched_name = match_billpayer(billpayers, input_name)
        select_owner(driver, matched_name)
        create_finance_account(driver, wait)

        account_id = extract_latest_deposit_account(driver, wait)
        if account_id:
            while True:
                print("\nActions:")
                print("1. Deposit")
                print("2. Withdrawal")
                print("3. Show balance")
                print("4. Exit")
                action = input("Select: ").strip()
                if action == "1":
                    make_transaction(driver, wait, account_id, "deposit")
                elif action == "2":
                    make_transaction(driver, wait, account_id, "withdrawal")
                elif action == "3":
                    extract_latest_deposit_account(driver, wait)
                elif action == "4":
                    break
                else:
                    print("❌ Invalid input")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
