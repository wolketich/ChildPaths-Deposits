from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
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

def toggle_guardian_enabled(driver, wait, guardian_id):
    url = f"https://app.childpaths.ie/guardian/{guardian_id}/edit"
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.ID, "enabled")))

    switch_wrapper = driver.find_element(By.CSS_SELECTOR, ".bootstrap-switch-wrapper")
    is_on = "bootstrap-switch-on" in switch_wrapper.get_attribute("class")

    if is_on:
        print("🟢 Account is ENABLED. Disabling now...")
        switch_wrapper.click()
        time.sleep(1)

        # Wait for SweetAlert modal and confirm
        try:
            confirm_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".swal-button--confirm"))
            )
            confirm_btn.click()
            print("☑️ Confirmed disable via SweetAlert.")
        except:
            print("⚠️ Failed to confirm disable modal.")
    else:
        print("🔴 Account is already DISABLED.")

    # Press Save
    try:
        save_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        save_button.click()
        print("💾 Save button clicked.")
        time.sleep(2)
    except:
        print("❌ Could not find Save button.")

def main():
    email = input("Email: ")
    password = input("Password: ")
    guardian_id = input("Enter Guardian ID to edit: ")

    options = Options()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        login(driver, wait, email, password)
        toggle_guardian_enabled(driver, wait, guardian_id)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
