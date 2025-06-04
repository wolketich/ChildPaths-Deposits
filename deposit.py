from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time

def login(driver, wait, email, password):
    driver.get("https://app.childpaths.ie/auth/login")
    wait.until(EC.presence_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "#signin-form button").click()
    wait.until(EC.url_contains("/dashboard"))
    print("✅ Logged in")

def create_finance_account(driver, wait, branch_value, owner_name):
    driver.get("https://app.childpaths.ie/user-finance-account/create")
    wait.until(EC.presence_of_element_located((By.NAME, "branch")))

    # Select the branch
    Select(driver.find_element(By.NAME, "branch")).select_by_value(branch_value)

    # Fill "Deposit Account"
    driver.find_element(By.ID, "display_name").send_keys("Deposit Account")

    # Select currency
    Select(driver.find_element(By.NAME, "currency")).select_by_value("EUR")

    # Uncheck "Set as default" if it's on
    try:
        toggle = driver.find_element(By.ID, "set_as_default")
        if toggle.is_selected():
            toggle.click()
    except:
        pass

    # Focus on Select2 input for Owner
    script = """
    document.querySelector('.select2-search__field').focus();
    """
    driver.execute_script(script)
    time.sleep(1)

    # Type owner name
    driver.switch_to.active_element.send_keys(owner_name)
    time.sleep(2)  # wait for dropdown
    driver.switch_to.active_element.send_keys(Keys.ENTER)

    # Submit
    driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][value="Create"]').click()
    print("✅ Finance account created")

def main():
    email = input("Email: ")
    password = input("Password: ")
    owner_name = input("Type exact Owner name (for Select2): ")
    
    # List branches and ask
    options = Options()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    try:
        login(driver, wait, email, password)

        # Go to creation page and ask for branch
        driver.get("https://app.childpaths.ie/user-finance-account/create")
        wait.until(EC.presence_of_element_located((By.NAME, "branch")))
        branches = driver.find_elements(By.CSS_SELECTOR, "select[name='branch'] option")
        print("\nSelect a branch:")
        for i, b in enumerate(branches):
            print(f"{i}: {b.text} [{b.get_attribute('value')}]")
        index = int(input("Branch number: "))
        branch_value = branches[index].get_attribute("value")

        # Create account
        create_finance_account(driver, wait, branch_value, owner_name)
        time.sleep(3)

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
