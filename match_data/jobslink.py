from seleniumbase import SB
from lxml import html
import csv
import os
import time

full_path = os.path.abspath("chromedata1")

def extract_job_listings(page_source):
    tree = html.fromstring(page_source)

    # Find all job cards that have a valid job-id
    job_cards = tree.xpath("//li[contains(@class, 'scaffold-layout__list-item') and @data-occludable-job-id]")
    print(f"Found {len(job_cards)} job cards")
    
    jobs = []
    for card in job_cards:
        # Extract job title
        title_element = card.xpath(".//a[contains(@class, 'job-card-list__title--link')]//strong/text()")
        if not title_element:
            continue  # Skip this card if no title found
            
        title = title_element[0].strip()
        
        # Extract location - using string() to get all text including commented nodes
        location_element = card.xpath("string(.//ul[contains(@class, 'job-card-container__metadata-wrapper')]//span)")
        if not location_element.strip():
            continue  # Skip this card if no location found
            
        location = ' '.join(location_element.split())
        
        # Create job dictionary
        job = {
            'title': title,
            'location': location
        }
        jobs.append(job)
        print(f"Extracted job {len(jobs)}: {title} - {location}")

    print(f"\nSuccessfully extracted {len(jobs)} valid jobs")
    return jobs

def save_jobs_to_csv(job_list, filename='linkedin_jobs_dynamic.csv'):
    if not job_list:
        print("No jobs found to save")
        return

    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'location'])
        writer.writeheader()
        for job in job_list:
            writer.writerow(job)
            print(f"Writing to CSV: {job['title']} - {job['location']}")

    print(f"Saved {len(job_list)} jobs to {filename}")

def main():
    job_search_url = "https://www.linkedin.com/jobs/search/?currentJobId=4211256877&f_C=82305020&f_TPR=r2592000&geoId=92000000&origin=JOB_SEARCH_PAGE_JOB_FILTER"

    with SB(uc=True, headless=False, user_data_dir=full_path) as sb:
        sb.open(job_search_url)
        time.sleep(6)  # Let it load
        sb.scroll_to_bottom()
        time.sleep(4)  # Load more jobs if needed

        html_content = sb.get_page_source()
        jobs = extract_job_listings(html_content)
        save_jobs_to_csv(jobs)

if __name__ == "__main__":
    main()
