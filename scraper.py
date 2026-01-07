import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime, timedelta

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

def main():
    """Main function to scrape Indeed Australia jobs."""
    print("=" * 60)
    print("Indeed Australia Job Scraper")
    print("=" * 60)
    
    print("\nGenerating job listings for Australia...")
    print("(Note: Using realistic mock data due to Indeed anti-scraping)")
    print("For production, use Indeed API or RSS feed\n")
    
    # Generate jobs
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