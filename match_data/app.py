import requests
import json
import os
import hashlib
from seleniumbase import SB
from lxml import html
import time

def generate_linkedin_job_id(title, location):
    # Generate a unique ID based on title and location
    unique_string = f"{title}_{location}".encode('utf-8')
    return hashlib.md5(unique_string).hexdigest()

def extract_linkedin_jobs(page_source):
    tree = html.fromstring(page_source)
    jobs = []

    # Find all job cards that have a valid job-id
    job_cards = tree.xpath("//li[contains(@class, 'scaffold-layout__list-item') and @data-occludable-job-id]")
    print(f"Found {len(job_cards)} LinkedIn job cards")
    
    for card in job_cards:
        # Extract job title
        title_element = card.xpath(".//a[contains(@class, 'job-card-list__title--link')]//strong/text()")
        if not title_element:
            continue
            
        title = title_element[0].strip()
        
        # Extract location
        location_element = card.xpath("string(.//ul[contains(@class, 'job-card-container__metadata-wrapper')]//span)")
        if not location_element.strip():
            continue
            
        location = ' '.join(location_element.split())
        
        # Generate unique ID for LinkedIn job
        job_id = generate_linkedin_job_id(title, location)
        
        # Create job dictionary
        job = {
            'id': job_id,
            'title': title,
            'location': location,
            'source': 'linkedin'
        }
        jobs.append(job)
        print(f"Extracted LinkedIn job: {title} - {location}")

    return jobs

def fetch_linkedin_jobs():
    full_path = os.path.abspath("chromedata1")
    job_search_url = "https://www.linkedin.com/jobs/search/?currentJobId=4211256877&f_C=82305020&f_TPR=r2592000&geoId=92000000&origin=JOB_SEARCH_PAGE_JOB_FILTER"
    
    jobs = []
    with SB(uc=True, headless=False, user_data_dir=full_path) as sb:
        sb.open(job_search_url)
        time.sleep(5)  # Let it load
        sb.scroll_to_bottom()
        time.sleep(4)  # Load more jobs if needed

        html_content = sb.get_page_source()
        jobs = extract_linkedin_jobs(html_content)
    
    return jobs

def fetch_pyjamahr_jobs(company_uuid):
    base_url = "https://api.pyjamahr.com/api/career/jobs/"
    params = {
        "company_uuid": company_uuid,
        "page": 1,
        "is_careers_page": "true"
    }
    jobs = []

    while True:
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            print(f"Error: Failed to fetch page {params['page']}, Status code: {response.status_code}")
            break

        data = response.json()
        page_jobs = data.get('results', [])
        
        for job in page_jobs:
            jobs.append({
                "id": job["id"],
                "title": job["title"],
                "location": job["location"],
                "source": "pyjamahr"
            })

        if not data.get('next'):
            break

        params["page"] += 1

    return jobs

def load_existing_data(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            return json.load(f)
    return []

def save_data_incrementally(filepath, new_data):
    existing_data = load_existing_data(filepath)
    existing_ids = {job["id"] for job in existing_data}

    unique_new_jobs = [job for job in new_data if job["id"] not in existing_ids]
    if unique_new_jobs:
        print(f"Saving {len(unique_new_jobs)} new job(s).")
    else:
        print("No new jobs to save.")

    all_data = existing_data + unique_new_jobs

    with open(filepath, "w") as f:
        json.dump(all_data, f, indent=2)

if __name__ == "__main__":
    company_uuid = "DD8D585B0A"
    file_path = "jobs_data.json"

    # Fetch jobs from both sources
    print("Fetching jobs from Pyjamahr...")
    pyjamahr_jobs = fetch_pyjamahr_jobs(company_uuid)
    print(f"Found {len(pyjamahr_jobs)} jobs from Pyjamahr")

    print("\nFetching jobs from LinkedIn...")
    linkedin_jobs = fetch_linkedin_jobs()
    print(f"Found {len(linkedin_jobs)} jobs from LinkedIn")

    # Combine all jobs
    all_jobs = pyjamahr_jobs + linkedin_jobs
    print(f"\nTotal jobs found: {len(all_jobs)}")

    # Save to JSON
    save_data_incrementally(file_path, all_jobs)