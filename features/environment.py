from os import getenv
from shutil import which

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait


def before_scenario(context, _scenario):
    context.base_url = getenv("BASE_URL", "http://127.0.0.1:8080").rstrip("/")

    driver_path = which("chromedriver")
    browser_path = which("chromium") or which("google-chrome")

    if not driver_path or not browser_path:
        raise RuntimeError("Browser or ChromeDriver was not found.")

    options = webdriver.ChromeOptions()
    options.binary_location = browser_path
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    context.browser = webdriver.Chrome(
        service=Service(driver_path),
        options=options,
    )
    context.add_cleanup(context.browser.quit)

    context.wait = WebDriverWait(
        context.browser,
        int(getenv("WAIT_SECONDS", "30")),
    )
