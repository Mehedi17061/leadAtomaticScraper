import time
import random
import pandas as pd
from datetime import datetime, timedelta
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


# ---------------- CONFIG ---------------- #

INDEED_SEARCH_URL = "https://au.indeed.com/jobs?q=software+engineer&l=Australia"

DELAY_RANGE = (3, 6)   # Human-like delay


# ---------------- DRIVER SETUP ---------------- #

def setup_driver():
    options = Options()

    # IMPORTANT: Headless দিলে block বেশি হয়
    # options.add_argument("--headless")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


# ---------------- JOB SCRAPER ---------------- #

def scrape_jobs():
    driver = setup_driver()
    wait = WebDriverWait(driver, 20)

    print("Opening Indeed...")
    driver.get(INDEED_SEARCH_URL)
    time.sleep(5)

    # handle cookie popup if present
    try:
        xpath_accept = '//button[contains(., "Accept") or contains(., "I agree") or contains(., "Accept all")]'
        accept_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xpath_accept)))
        accept_btn.click()
        time.sleep(1)
    except:
        pass

    # collect job card links (use multiple selectors as fallback)
    selectors = ["a.tapItem", "a.css-5lfssm", "a.jcs-JobTitle", "div.job_seen_beacon a"]
    job_links = []
    for sel in selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elems:
                href = el.get_attribute('href')
                if href and href not in job_links:
                    job_links.append(href)
            if job_links:
                break
        except Exception:
            continue

    if not job_links:
        print("❌ No job links found – Indeed layout changed or blocked")
        driver.quit()
        return []

    print(f"Found {len(job_links)} job links")

    jobs_data = []
    env_max = int(os.getenv("MAX_JOBS", "50"))
    max_jobs = min(env_max, len(job_links))

    original_window = driver.current_window_handle

    for idx, link in enumerate(job_links[:max_jobs], start=1):
        try:
            # Open job in new tab to avoid stale elements
            driver.execute_script("window.open(arguments[0], '_blank');", link)
            time.sleep(1)
            # switch to new tab
            handles = driver.window_handles
            new_handle = [h for h in handles if h != original_window][-1]
            driver.switch_to.window(new_handle)

            # wait for description or fallback to body text
            try:
                desc_el = wait.until(EC.presence_of_element_located((By.ID, "jobDescriptionText")))
                description = desc_el.text
            except:
                # try alternative selector
                try:
                    desc_el = driver.find_element(By.CSS_SELECTOR, "div#jobDescriptionText, div.jobsearch-JobComponent-description")
                    description = desc_el.text
                except:
                    description = ""

            # title with fallbacks
            title = "N/A"
            for tsel in ["h1.jobsearch-JobInfoHeader-title", "h2.jobsearch-JobInfoHeader-title", "h1", "h2"]:
                try:
                    title = driver.find_element(By.CSS_SELECTOR, tsel).text
                    if title:
                        break
                except:
                    continue

            # company with fallbacks
            company = "N/A"
            for csel in [".jobsearch-CompanyInfoWithoutHeaderImage div", ".jobsearch-InlineCompanyRating div", "div.icl-u-lg-mr--sm.icl-u-xs-mr--xs"]:
                try:
                    company = driver.find_element(By.CSS_SELECTOR, csel).text
                    if company:
                        break
                except:
                    continue

            # location fallback
            location = "Australia"
            try:
                loc = driver.find_elements(By.CSS_SELECTOR, ".jobsearch-JobInfoHeader-subtitle div")
                if len(loc) >= 2:
                    location = loc[1].text
                elif loc:
                    location = loc[0].text
            except:
                pass

            jobs_data.append({
                "title": title,
                "company": company,
                "url": link,
                "location": location,
                "description": description,
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M")
            })

            print(f"✓ Scraped {idx}: {title}")

            # close tab and switch back
            driver.close()
            driver.switch_to.window(original_window)
            time.sleep(random.uniform(*DELAY_RANGE))

        except Exception as e:
            # try to recover: close any extra tabs and switch back
            try:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(original_window)
            except:
                pass
            print(f"⚠ Skipped job {idx} – {str(e)[:120]}")
            continue

    driver.quit()
    return jobs_data


# ---------------- SAVE CSV ---------------- #

def save_csv(data):
    df = pd.DataFrame(data)
    filename = "indeed_jobs_full_description.csv"
    df.to_csv(filename, index=False, encoding="utf-8")
    print(f"\n✓ Saved {len(df)} jobs to {filename}")


# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    jobs = scrape_jobs()
    save_csv(jobs)
