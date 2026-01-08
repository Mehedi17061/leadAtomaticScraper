import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import sys
import os
from typing import List, Optional

# Try importing Selenium and webdriver-manager. If unavailable, we'll fall back
# to the lightweight requests-based approach and mock data generation.
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

# Lightweight headers to attempt fetching job detail pages
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-AU,en;q=0.9',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

def fetch_full_description(url, session=None, timeout=15):
    """Fetch full job description from a job URL using requests.

    Returns the description text or an informative message if blocked/unavailable.
    """
    if not url or not url.startswith('http'):
        return 'No valid URL to fetch description'

    sess = session or requests.Session()
    sess.headers.update(HEADERS)

    try:
        resp = sess.get(url, timeout=timeout)
        # Detect obvious blocking
        if resp.status_code == 403:
            return 'Blocked (403) when fetching description'
        resp.raise_for_status()

        html = resp.content
        soup = BeautifulSoup(html, 'html.parser')

        # Common Indeed selectors for job description
        selectors = [
            ('div', {'id': 'jobDescriptionText'}),
            ('div', {'class': lambda x: x and 'jobsearch-jobDescriptionText' in x}),
            ('div', {'class': lambda x: x and 'jobDescription' in x}),
            ('section', {'id': 'jobDescriptionText'})
        ]

        for tag, attrs in selectors:
            elem = soup.find(tag, attrs)
            if elem and elem.get_text(strip=True):
                return ' '.join(elem.get_text(separator=' ').split())

        # Fallback: try to extract main article text
        body_text = soup.get_text(separator=' ', strip=True)
        if len(body_text) > 200:
            return body_text[:10000]  # limit size

        return 'Description not found or page blocked'

    except requests.exceptions.RequestException as e:
        return f'Error fetching description: {str(e)}'


def fetch_full_description_selenium(url, driver, timeout=15):
    """Fetch full job description using a Selenium `driver`.

    Returns the description text or an informative message if blocked/unavailable.
    """
    if not url or not url.startswith('http'):
        return 'No valid URL to fetch description'

    try:
        driver.get(url)

        wait = WebDriverWait(driver, timeout)

        # Try common Indeed selectors for the job description pane
        selectors = [
            (By.ID, 'jobDescriptionText'),
            (By.ID, 'vjs-content'),
            (By.CSS_SELECTOR, 'div.jobsearch-jobDescriptionText'),
            (By.CSS_SELECTOR, 'div.jobDescription')
        ]

        for by, sel in selectors:
            try:
                elem = wait.until(EC.presence_of_element_located((by, sel)))
                text = elem.text.strip()
                if len(text) > 20:
                    return ' '.join(text.split())
            except Exception:
                continue

        # Fallback: page text
        body = driver.find_element(By.TAG_NAME, 'body')
        body_text = body.text.strip()
        if len(body_text) > 200:
            return ' '.join(body_text.split())[:10000]

        return 'Description not found or page blocked (selenium)'

    except Exception as e:
        return f'Error fetching description with selenium: {str(e)}'


def load_proxies(path='proxies.txt') -> List[str]:
    """Load proxies from a local `proxies.txt` file (one proxy per line).

    Proxy format: http://host:port or host:port
    Returns an empty list if file not found.
    """
    if not os.path.exists(path):
        return []
    out = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                p = line.strip()
                if not p:
                    continue
                if not p.startswith('http'):
                    p = 'http://' + p
                out.append(p)
    except Exception:
        return []
    return out


def create_selenium_driver(proxy: Optional[str] = None, headless: bool = True):
    """Create a Chrome Selenium driver. If `proxy` provided, use it.

    Returns a webdriver instance (caller must quit it).
    """
    options = Options()
    if headless:
        options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def is_blocked_text(text: str) -> bool:
    """Simple heuristics to detect captcha/blocked pages."""
    if not text:
        return True
    lower = text.lower()
    blocks = ['captcha', 'verify', 'unusual traffic', 'access denied', 'robot check', 'are you a robot']
    return any(b in lower for b in blocks)

def generate_mock_jobs():
    """
    Generate realistic mock job data for Indeed Australia.
    Used because Indeed actively blocks web scraping.
    In production, use Indeed API or RSS feed.
    
    Returns:
        list: List of dictionaries containing job details
    """
    
    companies = [
        'Google Australia', 'Microsoft', 'Amazon', 'Apple', 'Meta',
        'Accenture', 'Deloitte', 'PwC', 'EY', 'KPMG',
        'Commonwealth Bank', 'Westpac', 'NAB', 'ANZ',
        'Telstra', 'Optus', 'Vodafone', 'Nbv',
        'Woolworths', 'Coles', 'IGA', 'Bunnings',
        'Atlassian', 'Seek', 'REA Group', 'News Corp'
    ]
    
    locations = [
        'Sydney, NSW', 'Melbourne, VIC', 'Brisbane, QLD', 'Perth, WA',
        'Adelaide, SA', 'Hobart, TAS', 'Darwin, NT', 'Canberra, ACT',
        'Central Coast, NSW', 'Gold Coast, QLD', 'Geelong, VIC'
    ]
    
    job_types = ['Permanent', 'Temporary', 'Contract', 'Full-time', 'Part-time']
    
    software_jobs = [
        {'title': 'Senior Software Engineer', 'salary': '$120,000 - $160,000'},
        {'title': 'Python Developer', 'salary': '$90,000 - $130,000'},
        {'title': 'Full Stack Developer', 'salary': '$100,000 - $150,000'},
        {'title': 'DevOps Engineer', 'salary': '$110,000 - $150,000'},
        {'title': 'Data Engineer', 'salary': '$100,000 - $140,000'},
        {'title': 'Solutions Architect', 'salary': '$130,000 - $180,000'},
        {'title': 'Cloud Engineer', 'salary': '$105,000 - $145,000'},
    ]
    
    data_jobs = [
        {'title': 'Data Analyst', 'salary': '$80,000 - $110,000'},
        {'title': 'Data Scientist', 'salary': '$100,000 - $150,000'},
        {'title': 'Business Intelligence Developer', 'salary': '$90,000 - $130,000'},
        {'title': 'Analytics Engineer', 'salary': '$95,000 - $140,000'},
    ]
    
    project_jobs = [
        {'title': 'Project Manager', 'salary': '$90,000 - $130,000'},
        {'title': 'Agile Coach', 'salary': '$100,000 - $140,000'},
        {'title': 'Program Manager', 'salary': '$105,000 - $150,000'},
    ]
    
    nurse_jobs = [
        {'title': 'Registered Nurse', 'salary': '$65,000 - $95,000'},
        {'title': 'RN - Emergency Department', 'salary': '$70,000 - $100,000'},
        {'title': 'Clinical Nurse Specialist', 'salary': '$80,000 - $110,000'},
    ]
    
    electrician_jobs = [
        {'title': 'Electrician', 'salary': '$70,000 - $100,000'},
        {'title': 'Licensed Electrician', 'salary': '$75,000 - $105,000'},
        {'title': 'Electrical Technician', 'salary': '$60,000 - $85,000'},
    ]
    
    job_categories = [
        ('Software Engineer', software_jobs),
        ('Data Analyst', data_jobs),
        ('Project Manager', project_jobs),
        ('Nurse', nurse_jobs),
        ('Electrician', electrician_jobs),
    ]
    
    all_jobs = []
    base_date = datetime.now()
    
    for category, jobs in job_categories:
        for job_template in jobs:
            # Generate 8-12 listings per job type
            for i in range(random.randint(8, 12)):
                job_data = {
                    'title': job_template['title'],
                    'company': random.choice(companies),
                    'location': random.choice(locations),
                    'salary': job_template['salary'],
                    'job_type': random.choice(job_types),
                    'summary': f"Exciting opportunity in {category}. We are looking for a talented professional to join our team.",
                    'posted': (base_date - timedelta(days=random.randint(1, 30))).strftime('%d %b %Y'),
                    'url': f'https://au.indeed.com/jobs?q={job_template["title"].replace(" ", "+")}&l=Australia'
                }
                all_jobs.append(job_data)
    
    # Shuffle the list
    random.shuffle(all_jobs)
    
    return all_jobs

def save_to_csv(jobs, filename='indeed_australia_jobs.csv'):
    """
    Save scraped jobs to CSV file.
    
    Args:
        jobs (list): List of job dictionaries
        filename (str): Output CSV filename
    """
    if jobs:
        df = pd.DataFrame(jobs)
        try:
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"\n✓ Saved {len(jobs)} jobs to {filename}")
        except PermissionError:
            # Fallback: save with timestamped filename if file is locked
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            alt_name = filename.replace('.csv', f'_{ts}.csv')
            df.to_csv(alt_name, index=False, encoding='utf-8')
            print(f"\n! Permission denied for {filename}. Saved to {alt_name} instead.")
    else:
        print("No jobs to save.")


def enrich_jobs_with_descriptions(jobs, max_workers=1):
    """Attempt to fetch full descriptions for each job in-place.

    This uses requests and is deliberately sequential (max_workers ignored) to
    avoid rapid requests. It sets a `description` key on each job dict.
    """
    if not jobs:
        return jobs

    # If Selenium is available, use it to fetch descriptions faster and more
    # reliably (handles JS-rendered content). Otherwise fall back to requests.
    if SELENIUM_AVAILABLE:
        # Try without proxy first, then rotate proxies on detection of blocking
        proxies = load_proxies()
        used_proxy = None
        driver = None
        try:
            driver = create_selenium_driver(proxy=None, headless=True)
            for idx, job in enumerate(jobs, 1):
                url = job.get('url')
                print(f"(selenium) Fetching description {idx}/{len(jobs)}...")
                desc = fetch_full_description_selenium(url, driver)
                # If heuristics indicate blocking, try rotating proxies
                if is_blocked_text(desc) and proxies:
                    for p in proxies:
                        try:
                            print(f"Blocked detected — retrying description via proxy {p}")
                            try:
                                driver.quit()
                            except Exception:
                                pass
                            driver = create_selenium_driver(proxy=p, headless=True)
                            desc = fetch_full_description_selenium(url, driver)
                            if not is_blocked_text(desc):
                                used_proxy = p
                                break
                        except Exception:
                            continue

                job['description'] = desc
                # small polite delay
                time.sleep(random.uniform(0.5, 1.5))
        finally:
            try:
                if driver:
                    driver.quit()
            except Exception:
                pass

        return jobs

    # Fallback: requests based sequential fetch
    session = requests.Session()
    session.headers.update(HEADERS)

    for idx, job in enumerate(jobs, 1):
        url = job.get('url')
        print(f"Fetching description {idx}/{len(jobs)}...")
        desc = fetch_full_description(url, session=session)
        job['description'] = desc
        # polite delay
        time.sleep(random.uniform(1.5, 3.5))

    return jobs


def scrape_jobs_selenium(query='software engineer', location='Australia', max_results=50, headless=True):
    """Scrape job listings from Indeed Australia using Selenium.

    Returns a list of job dicts with `description` populated when possible.
    """
    if not SELENIUM_AVAILABLE:
        raise RuntimeError('Selenium not available in this environment')

    # Allow proxy rotation: try direct, then proxies from file
    proxies = load_proxies()
    driver = None
    wait = None

    base_url = f"https://au.indeed.com/jobs?q={query}&l={location}&sort=date"

    jobs = []

    try:
        # Try without proxy first
        driver = create_selenium_driver(proxy=None, headless=headless)
        wait = WebDriverWait(driver, 15)
        driver.get(base_url)

        # Detect blocking using body text heuristics
        try:
            body = driver.find_element(By.TAG_NAME, 'body').text
            if is_blocked_text(body):
                raise Exception('Detected blocking on initial page')
        except Exception:
            # Try rotating proxies
            if proxies:
                for p in proxies:
                    try:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = create_selenium_driver(proxy=p, headless=headless)
                        wait = WebDriverWait(driver, 15)
                        driver.get(base_url)
                        body = driver.find_element(By.TAG_NAME, 'body').text
                        if not is_blocked_text(body):
                            print(f'Loaded search page via proxy {p}')
                            break
                    except Exception:
                        continue
            else:
                print('No proxies available and initial request looks blocked')

        # Wait until job cards are present
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'a.tapItem, div.job_seen_beacon')))
        except Exception:
            pass

        cards = driver.find_elements(By.CSS_SELECTOR, 'a.tapItem, div.job_seen_beacon')

        for idx, card in enumerate(cards[:max_results], 1):
            try:
                # Extract common fields with fallbacks
                title = ''
                company = ''
                loc = ''
                summary = ''
                salary = ''
                posted = ''
                url = ''

                try:
                    title_elem = card.find_element(By.CSS_SELECTOR, 'h2.jobTitle')
                    title = title_elem.text.strip()
                except Exception:
                    try:
                        title = card.get_attribute('aria-label') or ''
                    except Exception:
                        title = ''

                try:
                    company = card.find_element(By.CSS_SELECTOR, 'span.companyName').text.strip()
                except Exception:
                    company = ''

                try:
                    loc = card.find_element(By.CSS_SELECTOR, 'div.companyLocation').text.strip()
                except Exception:
                    loc = ''

                try:
                    salary = card.find_element(By.CSS_SELECTOR, 'div.salary-snippet').text.strip()
                except Exception:
                    salary = ''

                try:
                    summary = card.find_element(By.CSS_SELECTOR, 'div.job-snippet').text.strip()
                except Exception:
                    summary = ''

                try:
                    href = card.get_attribute('href')
                    if href and href.startswith('/rc'):
                        href = 'https://au.indeed.com' + href
                    url = href or ''
                except Exception:
                    url = ''

                job = {
                    'title': title,
                    'company': company,
                    'location': loc,
                    'salary': salary,
                    'job_type': '',
                    'summary': summary,
                    'posted': posted,
                    'url': url
                }

                # Try to click to load description pane if possible
                try:
                    driver.execute_script('arguments[0].scrollIntoView(true);', card)
                    card.click()
                    # Wait a moment for the description pane to populate
                    time.sleep(0.6)
                    desc = ''
                    try:
                        desc_elem = driver.find_element(By.ID, 'jobDescriptionText')
                        desc = desc_elem.text.strip()
                    except Exception:
                        try:
                            desc_elem = driver.find_element(By.ID, 'vjs-content')
                            desc = desc_elem.text.strip()
                        except Exception:
                            desc = ''

                    job['description'] = ' '.join(desc.split()) if desc else ''
                except Exception:
                    # If clicking fails, open URL in same driver and fetch
                    if url:
                        job['description'] = fetch_full_description_selenium(url, driver)
                    else:
                        job['description'] = ''

                jobs.append(job)
                # small delay between cards
                time.sleep(random.uniform(0.3, 0.8))
            except Exception:
                continue

        return jobs

    finally:
        try:
            driver.quit()
        except Exception:
            pass

def main():
    """Main function to scrape Indeed Australia jobs."""
    print("=" * 60)
    print("Indeed Australia Job Scraper")
    print("=" * 60)
    print("\nPreparing job listings for Australia...")

    # Allow optional command-line arguments: query, location, max_results
    # Default to empty query to search across Australia
    query = ''
    location = 'Australia'
    max_results = 50
    if len(sys.argv) > 1:
        query = sys.argv[1]
    if len(sys.argv) > 2:
        location = sys.argv[2]
    if len(sys.argv) > 3:
        try:
            max_results = int(sys.argv[3])
        except Exception:
            pass

    jobs = []

    proxies = load_proxies()
    if proxies:
        print(f"Loaded {len(proxies)} proxies from proxies.txt")

    if SELENIUM_AVAILABLE:
        print('\nSelenium is available — attempting live scrape with Selenium (full descriptions).')
        print(f'Query: "{query or "<any>"}" | Location: {location} | Max results: {max_results}')
        try:
            jobs = scrape_jobs_selenium(query=query, location=location, max_results=max_results, headless=True)
        except Exception as e:
            print(f"Selenium scraping failed: {e}\nFalling back to mock data.")

    if not jobs:
        print("\n(Using realistic mock data due to site anti-scraping or Selenium unavailable)")
        jobs = generate_mock_jobs()

        # Attempt to enrich jobs with full descriptions (best-effort)
        print("\nEnriching jobs with full descriptions (may be blocked by site)...")
        jobs = enrich_jobs_with_descriptions(jobs)
    
    # Save to CSV
    save_to_csv(jobs)
    
    # Display summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total jobs generated: {len(jobs)}")
    
    if jobs:
        df = pd.read_csv('indeed_australia_jobs.csv')
        print(f"\nTop companies:")
        print(df['company'].value_counts().head(10))
        
        print(f"\n\nTop 10 jobs found:")
        print(df[['title', 'company', 'location', 'salary']].head(10).to_string(index=False))
        
        print(f"\n\nJob type distribution:")
        print(df['job_type'].value_counts())

if __name__ == "__main__":
    main()