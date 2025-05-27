import requests
import json
import os
import csv
import re
import hashlib
from datetime import datetime
from seleniumbase import SB
from bs4 import BeautifulSoup
from urllib.parse import quote
import time
from lxml import html
import phonenumbers
from phonenumbers import carrier, geocoder, timezone
from phone_iso3166.country import phone_country
from email_validator import validate_email, EmailNotValidError
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pickle
import os.path

# Email validation constants and helper
RAW_EMAIL_RE = re.compile(
    r'(?<![\w@.+-])'                            # left boundary
    r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,10})',  # local@domain
    re.I
)

_LEADING = re.compile(r'^(?:to|via|at|on)\s*', re.I)
COMMON_TLDS = {
    'com','net','org','info','edu','gov','mil','io','ai',
    'co','uk','in','sa','ae','ca','me'
}
MULTI_LEVEL = ('co.uk', 'co.in', 'com.au')      # extend if you need more

def tidy_email(raw: str) -> Optional[str]:
    """Strip leading keywords + junk stuck after the TLD."""
    raw = _LEADING.sub('', raw).lower().strip(",.;:)>] ")

    if '@' not in raw:
        return None

    local, domain = raw.split('@', 1)

    # --- exact match for 2‑level endings (co.uk, etc.) -------------
    for m in MULTI_LEVEL:
        if domain.endswith(m):
            return f"{local}@{domain}"

    # --- shrink the tail until the suffix is a known 1‑level TLD ----
    head, dot, tail = domain.rpartition('.')
    for end_len in range(len(tail), 1, -1):          # longest → shortest
        tld = tail[:end_len]
        if tld in COMMON_TLDS:
            return f"{local}@{head}.{tld}"

    return None        # give up if nothing sensible found

class JobScraper:
    def __init__(self):
        self.pyjamahr_base_url = "https://api.pyjamahr.com/api/career/jobs/"
        self.linkedin_base_url = "https://www.linkedin.com/search/results/content/?datePosted=%22past-month%22&keywords=(title:%22{}%22)(vacancy%20OR%20job%20OR%20%22jobs%22%20OR%20%22requirement%22%20OR%20hiring%20OR%20opening)%20-title:Internship&origin=GLOBAL_SEARCH_HEADER&sortBy=%22relevance%22"
        self.linkedin_jobs_url = "https://www.linkedin.com/jobs/search/?currentJobId=4211256877&f_C=82305020&f_TPR=r2592000&geoId=92000000&origin=JOB_SEARCH_PAGE_JOB_FILTER"
        self.chrome_data_dir = os.path.abspath("chromedata1")
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.creds = None
        self.service = None

    def get_current_timestamp(self):
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()

    def generate_linkedin_job_id(self, title, location):
        """Generate a unique ID based on title and location"""
        unique_string = f"{title}_{location}".encode('utf-8')
        return hashlib.md5(unique_string).hexdigest()

    def extract_linkedin_job_listings(self, page_source):
        """Extract job listings from LinkedIn job search page"""
        tree = html.fromstring(page_source)
        jobs = []
        current_time = self.get_current_timestamp()

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
            job_id = self.generate_linkedin_job_id(title, location)
            
            # Create job dictionary
            job = {
                'id': job_id,
                'title': title,
                'location': location,
                'source': 'linkedin',
                'scraped_at': current_time
            }
            jobs.append(job)
            print(f"Extracted LinkedIn job: {title} - {location}")

        return jobs

    def fetch_linkedin_jobs(self):
        """Fetch jobs from LinkedIn job search page"""
        jobs = []
        with SB(uc=True, headless=False, user_data_dir=self.chrome_data_dir) as sb:
            sb.open(self.linkedin_jobs_url)
            time.sleep(5)  # Let it load
            sb.scroll_to_bottom()
            time.sleep(4)  # Load more jobs if needed

            html_content = sb.get_page_source()
            jobs = self.extract_linkedin_job_listings(html_content)
        
        return jobs

    def fetch_pyjamahr_jobs(self, company_uuid):
        """Fetch jobs from PyjamaHR API"""
        params = {
            "company_uuid": company_uuid,
            "page": 1,
            "is_careers_page": "true"
        }
        jobs = []
        current_time = self.get_current_timestamp()

        while True:
            response = requests.get(self.pyjamahr_base_url, params=params)
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
                    "source": "pyjamahr",
                    "scraped_at": current_time
                })

            if not data.get('next'):
                break

            params["page"] += 1

        return jobs

    def load_existing_data(self, filepath):
        """Load existing job data from JSON file"""
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                return json.load(f)
        return []

    def save_jobs_to_json(self, filepath, new_data):
        """Save jobs incrementally to JSON"""
        existing_data = self.load_existing_data(filepath)
        existing_ids = {job["id"] for job in existing_data}

        unique_new_jobs = [job for job in new_data if job["id"] not in existing_ids]
        if unique_new_jobs:
            print(f"Saving {len(unique_new_jobs)} new job(s).")
        else:
            print("No new jobs to save.")

        all_data = existing_data + unique_new_jobs

        with open(filepath, "w") as f:
            json.dump(all_data, f, indent=2)
        
        return unique_new_jobs

    def extract_linkedin_data(self, html_content, original_job):
        """Extract job details from LinkedIn HTML with enhanced author information, email and phone extraction"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_posts = []
        current_time = self.get_current_timestamp()
        
        post_blocks = soup.find_all('div', class_='update-components-text')
        
        for post in post_blocks:
            full_text = post.get_text(strip=True)
            
            # Extract unique post ID
            post_id = None
            parent = post.find_parent('div', attrs={'data-view-tracking-scope': True})
            if parent:
                tracking_data = parent.get('data-view-tracking-scope')
                if tracking_data and 'updateUrn' in tracking_data:
                    try:
                        update_urn = tracking_data.split('updateUrn":"')[1].split('"')[0]
                        post_id = update_urn
                    except IndexError:
                        pass

            post_url = f"https://www.linkedin.com/feed/update/{post_id}" if post_id else None
            
            # Extract author information with multiple fallback methods
            author_name = None
            profile_url = None
            
            # Method 1: Try to find the actor container
            actor_container = post.find_previous('div', class_='update-components-actor__container')
            if actor_container:
                # Try to find profile link and name
                profile_link = actor_container.find('a', href=True)
                if profile_link:
                    profile_url = "https://www.linkedin.com" + profile_link['href'] if profile_link['href'].startswith('/') else profile_link['href']
                    # Try to find name in aria-hidden span
                    name_span = profile_link.find('span', attrs={'aria-hidden': 'true'})
                    if name_span:
                        author_name = name_span.get_text(strip=True)
                    else:
                        author_name = profile_link.get_text(strip=True)
            
            # Method 2: Try to find post container and extract name
            if not author_name:
                post_container = post.find_parent('div', class_='feed-shared-update-v2') or post.find_parent('div', class_='occludable-update')
                if post_container:
                    # Try multiple selectors for author name
                    selectors = [
                        'span[dir="ltr"] span[aria-hidden="true"] span',
                        '.update-components-actor__single-line-truncate span[dir="ltr"] span[aria-hidden="true"] span',
                        'span.update-components-actor__title span[aria-hidden="true"]',
                        '.update-components-actor__title span[aria-hidden="true"]'
                    ]
                    
                    for selector in selectors:
                        author_elem = post_container.select_one(selector)
                        if author_elem:
                            author_name = author_elem.get_text(strip=True)
                            break
            
            # Method 3: Try to find name in actor title container
            if not author_name and actor_container:
                name_span = actor_container.select_one('span.update-components-actor__title span[aria-hidden="true"]')
                if name_span:
                    author_name = name_span.get_text(strip=True)

            # Extract and clean email addresses using the new two-stage approach
            email = None
            match = RAW_EMAIL_RE.search(full_text)
            if match:
                clean_email = tidy_email(match.group(1))
                if clean_email:
                    try:
                        # Final validation using email_validator
                        email = validate_email(clean_email, check_deliverability=False).email
                    except EmailNotValidError:
                        email = None

            # Extract and clean phone numbers with enhanced patterns
            phone = self.clean_phone_number(full_text)

            job_posts.append({
                'job_title': original_job['title'],
                'location': original_job['location'],
                'author_name': author_name,
                'author_profile_url': profile_url,
                'post_url': post_url,
                'email': email,
                'phone': phone,
                'post_text': full_text,
                'scraped_at': current_time
            })
        
        return job_posts

    def setup_google_sheets(self):
        """Set up Google Sheets API credentials"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('sheets', 'v4', credentials=self.creds)

    def create_google_sheet(self, title):
        """Create a new Google Sheet with the given title"""
        if not self.service:
            self.setup_google_sheets()

        spreadsheet = {
            'properties': {
                'title': title
            },
            'sheets': [
                {
                    'properties': {
                        'title': 'Job Details',
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 26
                        }
                    }
                }
            ]
        }
        
        spreadsheet = self.service.spreadsheets().create(body=spreadsheet).execute()
        return spreadsheet.get('spreadsheetId')

    def save_linkedin_data_to_google_sheet(self, data, filename, spreadsheet_id=None):
        """Save LinkedIn data to both CSV and Google Sheet"""
        # First save to CSV as before
        self.save_linkedin_data(data, filename)

        # Create Google Sheet if it doesn't exist
        if not spreadsheet_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sheet_title = f"LinkedIn Job Details {timestamp}"
            spreadsheet_id = self.create_google_sheet(sheet_title)
            
            # Add headers if this is a new sheet
            headers = [
                'Job Title', 'Location', 'Author Name', 'Author Profile URL',
                'Post URL', 'Email', 'Phone', 'Post Text', 'Scraped At'
            ]
            
            # Write headers
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Job Details!A1',
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()

            # Get the sheet ID
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheet_id = sheet_metadata['sheets'][0]['properties']['sheetId']

            # Format headers
            header_format = {
                'requests': [
                    {
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 0,
                                'endRowIndex': 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'backgroundColor': {
                                        'red': 0.8,
                                        'green': 0.8,
                                        'blue': 0.8
                                    },
                                    'textFormat': {
                                        'bold': True
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                        }
                    },
                    {
                        'autoResizeDimensions': {
                            'dimensions': {
                                'sheetId': sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': len(headers)
                            }
                        }
                    }
                ]
            }

            self.service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=header_format
            ).execute()

        # Get the next empty row
        result = self.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Job Details!A:A'
        ).execute()
        next_row = len(result.get('values', [])) + 1

        # Prepare the data for the sheet
        for job in data:
            row = [
                job['job_title'],
                job['location'],
                job.get('author_name', ''),
                job.get('author_profile_url', ''),
                job.get('post_url', ''),
                job.get('email', ''),
                job.get('phone', ''),
                job['post_text'],
                job['scraped_at']
            ]
            
            # Write data to the next empty row
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f'Job Details!A{next_row}',
                valueInputOption='RAW',
                body={'values': [row]}
            ).execute()
            
            next_row += 1

        print(f"Saved data to Google Sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        return spreadsheet_id

    def scrape_linkedin_details(self, jobs, output_csv):
        """Scrape LinkedIn for detailed information about each job"""
        existing_jobs = self.load_existing_linkedin_data(output_csv)
        new_jobs_to_scrape = []
        
        # Filter out jobs that have already been processed
        for job in jobs:
            job_key = f"{job['title']}_{job['location']}"
            if job_key not in existing_jobs:
                new_jobs_to_scrape.append(job)
            else:
                print(f"Skipping already processed job: {job['title']} in {job['location']}")
        
        if not new_jobs_to_scrape:
            print("No new jobs to scrape details for.")
            return
        
        print(f"Found {len(new_jobs_to_scrape)} new jobs to scrape details for.")
        
        # Create a new Google Sheet for this batch of jobs
        spreadsheet_id = None
        
        with SB(uc=True, headless=False, user_data_dir=self.chrome_data_dir) as sb:
            for job in new_jobs_to_scrape:
                search_query = f"{job['title']} {job['location']}"
                encoded_query = quote(search_query)
                linkedin_url = self.linkedin_base_url.format(encoded_query)
                
                print(f"Scraping LinkedIn details for: {search_query}")
                
                try:
                    sb.open(linkedin_url)
                    time.sleep(2)
                    
                    for _ in range(3):
                        sb.scroll_to_bottom()
                        time.sleep(2)
                    
                    html_content = sb.get_page_source()
                    job_data = self.extract_linkedin_data(html_content, job)
                    
                    if job_data:
                        # Save to both CSV and Google Sheet, passing the spreadsheet_id to append to existing sheet
                        spreadsheet_id = self.save_linkedin_data_to_google_sheet(job_data, output_csv, spreadsheet_id)
                        print(f"Saved details for job: {search_query}")
                    else:
                        print(f"No details found for job: {search_query}")
                    
                except Exception as e:
                    print(f"Error scraping LinkedIn for {search_query}: {str(e)}")
                    continue

    def load_existing_linkedin_data(self, filepath):
        """Load existing LinkedIn data from CSV file"""
        existing_jobs = set()
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    job_key = f"{row['job_title']}_{row['location']}"
                    existing_jobs.add(job_key)
        return existing_jobs

    def save_linkedin_data(self, data, filename):
        """Save LinkedIn data to CSV"""
        fieldnames = [
            'job_title', 
            'location', 
            'author_name',
            'author_profile_url', 
            'post_url',
            'email', 
            'phone',
            'post_text',
            'scraped_at'
        ]
        file_exists = os.path.isfile(filename)

        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerows(data)
        
        print(f"Saved {len(data)} LinkedIn job posts to {filename}")

    def clean_phone_number(self, text):
        """Clean and standardize phone numbers from text using enhanced phone number libraries"""
        def extract_phone_numbers(text):
            """Extract all potential phone numbers from text"""
            # First, try to find numbers with explicit country codes
            for match in phonenumbers.PhoneNumberMatcher(text, None):
                try:
                    if phonenumbers.is_valid_number(match.number):
                        return phonenumbers.format_number(
                            match.number, 
                            phonenumbers.PhoneNumberFormat.E164
                        )
                except:
                    continue

            # If no explicit country code found, try with common country codes
            common_countries = ['IN', 'US', 'GB', 'CA', 'AU']  # Add more as needed
            for country in common_countries:
                for match in phonenumbers.PhoneNumberMatcher(text, country):
                    try:
                        if phonenumbers.is_valid_number(match.number):
                            return phonenumbers.format_number(
                                match.number, 
                                phonenumbers.PhoneNumberFormat.E164
                            )
                    except:
                        continue

            return None

        def enrich_phone_info(phone_number):
            """Enrich phone number with additional information"""
            try:
                parsed_number = phonenumbers.parse(phone_number)
                if not phonenumbers.is_valid_number(parsed_number):
                    return None

                # Get country information
                country_code = phone_country(phone_number)
                
                # Get carrier information
                carrier_name = carrier.name_for_number(parsed_number, "en")
                
                # Get geographic information
                region = geocoder.description_for_number(parsed_number, "en")
                
                # Get timezone information
                time_zones = timezone.time_zones_for_number(parsed_number)
                
                return {
                    'number': phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164),
                    'country': country_code,
                    'carrier': carrier_name,
                    'region': region,
                    'timezone': time_zones[0] if time_zones else None
                }
            except:
                return None

        # First try to extract a valid phone number
        phone_number = extract_phone_numbers(text)
        if not phone_number:
            return None

        # Then enrich it with additional information
        enriched_info = enrich_phone_info(phone_number)
        if enriched_info:
            return enriched_info['number']  # Return just the standardized number
        
        return None

def main():
    scraper = JobScraper()
    
    # Configuration
    company_uuid = "DD8D585B0A"
    jobs_json_file = "jobs_data.json"
    linkedin_details_file = "linkedin_job_details.csv"
    
    # Step 1: Fetch jobs from Pyjamahr
    print("Fetching jobs from Pyjamahr...")
    pyjamahr_jobs = scraper.fetch_pyjamahr_jobs(company_uuid)
    print(f"Found {len(pyjamahr_jobs)} jobs from Pyjamahr")
    
    # Step 2: Fetch jobs from LinkedIn
    print("\nFetching jobs from LinkedIn...")
    linkedin_jobs = scraper.fetch_linkedin_jobs()
    print(f"Found {len(linkedin_jobs)} jobs from LinkedIn")
    
    # Step 3: Combine and save all jobs to JSON
    all_jobs = pyjamahr_jobs + linkedin_jobs
    print(f"\nTotal jobs found: {len(all_jobs)}")
    new_jobs = scraper.save_jobs_to_json(jobs_json_file, all_jobs)
    
    # Step 4: Only scrape LinkedIn details if we found new jobs
    if new_jobs:
        print("\nScraping LinkedIn for detailed information...")
        scraper.scrape_linkedin_details(new_jobs, linkedin_details_file)
    else:
        print("\nNo new jobs found. Skipping LinkedIn details scraping.")
    
    print("\nJob scraping completed!")

if __name__ == "__main__":
    main()