from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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
        if name and element_id and "select2--result" in element_id:
            billpayer_id = element_id.split('-')[-1]
            billpayers.append({"name": name, "id": billpayer_id})
            print(f"{i}: {name} [ID: {billpayer_id}]")

    return billpayers

def toggle_guardian_enabled(driver, wait, guardian_id, name):
    url = f"https://app.childpaths.ie/guardian/{guardian_id}/edit"
    driver.get(url)
    try:
        wait.until(EC.presence_of_element_located((By.ID, "enabled")))
        switch_wrapper = driver.find_element(By.CSS_SELECTOR, ".bootstrap-switch-wrapper")
        is_on = "bootstrap-switch-on" in switch_wrapper.get_attribute("class")

        if is_on:
            print(f"🟢 {name}: ENABLED → Disabling...")
            switch_wrapper.click()
            time.sleep(1)
            try:
                confirm_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal-button--confirm"))
                )
                confirm_btn.click()
                print("☑️ Confirmed SweetAlert.")
            except:
                print("⚠️ SweetAlert not confirmed.")
        else:
            print(f"🔴 {name}: already DISABLED.")

        # Save changes
        try:
            save_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            save_button.click()
            print("💾 Saved.")
            time.sleep(2)
        except:
            print("❌ Could not click Save.")
    except:
        print(f"❌ {name}: Guardian edit page or toggle not found.")

def main():
    email = input("Email: ")
    password = input("Password: ")

    options = Options()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        login(driver, wait, email, password)
        select_branch(driver, wait)
        billpayers = extract_billpayers(driver)

        print(f"\n⚙️ Processing {len(billpayers)} billpayers...\n")
        for i, bp in enumerate(billpayers, 1):
            print(f"--- [{i}/{len(billpayers)}] {bp['name']} ---")
            toggle_guardian_enabled(driver, wait, bp['id'], bp['name'])

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
