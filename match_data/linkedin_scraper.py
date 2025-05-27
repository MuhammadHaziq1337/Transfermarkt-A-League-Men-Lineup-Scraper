from seleniumbase import SB
from bs4 import BeautifulSoup
import csv
import os
import re

# Set your Chrome profile path for LinkedIn login session
full_path = os.path.abspath("chromedata1")

def extract_all_jobs(html_content):
    """Extract multiple job details from LinkedIn feed HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    job_posts = []
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

        # ------------------ Extract Author Name & Profile URL ------------------ #
        author_name = None
        profile_url = None

        # Find the actor container like in your original code
        actor_container = post.find_previous('div', class_='update-components-actor__container')
        if actor_container:
            # Extract profile URL using your original approach which was working
            profile_link = actor_container.find('a', href=True)
            if profile_link:
                profile_url = "https://www.linkedin.com" + profile_link['href'] if profile_link['href'].startswith('/') else profile_link['href']
        
        # Find post container for name extraction
        post_container = post.find_parent('div', class_='feed-shared-update-v2') or post.find_parent('div', class_='occludable-update')
        
        if post_container:
            # Try both user and company selectors for author name
            # Method 1: Try the user selector
            author_elem = post_container.select_one('span[dir="ltr"] span[aria-hidden="true"] span')
            
            # Method 2: If not found, try the company selector
            if not author_elem:
                author_elem = post_container.select_one('.update-components-actor__single-line-truncate span[dir="ltr"] span[aria-hidden="true"] span')
            
            # Method 3: Try finding the actor title container directly
            if not author_elem and actor_container:
                name_span = actor_container.select_one('span.update-components-actor__title span[aria-hidden="true"]')
                if name_span:
                    author_elem = name_span
            
            # Extract the text if we found the element
            if author_elem:
                author_name = author_elem.get_text(strip=True)
        
        # If we still don't have an author name but have the actor_container (from your original code)
        if not author_name and actor_container:
            # Fallback to your original method
            profile_link = actor_container.find('a', href=True)
            if profile_link:
                name_span = profile_link.find('span', attrs={'aria-hidden': 'true'})
                if name_span:
                    author_name = name_span.get_text(strip=True)
                else:
                    author_name = profile_link.get_text(strip=True)

        # Extract and clean email addresses
        email = None
        # Use more robust email pattern with common separators
        email_pattern = r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}'
        email_matches = re.findall(email_pattern, full_text)
        if email_matches:
            # Take the first match as the primary email
            email = email_matches[0].lower()
            # Clean the email by removing any trailing punctuation
            email = re.sub(r'[,.;:]+$', '', email)

        # Extract and clean phone numbers
        phone = None
        # Pattern for Indian phone numbers and international formats
        # Handles formats like: +91 9876543210, 9876543210, +91-98765-43210, etc.
        phone_patterns = [
            r'\+\d{1,3}[\s-]?\d{3,5}[\s-]?\d{4,8}',  # International format: +91 98765 43210
            r'(?<!\d)(\d{10})(?!\d)',  # 10 digit numbers: 9876543210
            r'(?<!\d)(\d{3}[\s-]?\d{3}[\s-]?\d{4})(?!\d)',  # Format: 987-654-3210
            r'(?<!\d)(\d{5}[\s-]?\d{5})(?!\d)',  # Format: 98765-43210
        ]
        
        for pattern in phone_patterns:
            phone_matches = re.findall(pattern, full_text)
            if phone_matches:
                # Take the first match as the primary phone number
                phone = phone_matches[0]
                # Remove any spaces or hyphens for consistent format
                phone = re.sub(r'[\s-]', '', phone)
                # Add +91 prefix if it's a 10-digit Indian number without country code
                if len(phone) == 10 and phone.isdigit():
                    phone = "+91" + phone
                break

        job_posts.append({
            'job_description': full_text,
            'post_url': post_url,
            'author_name': author_name,
            'author_profile_url': profile_url,
            'email': email,
            'phone': phone
        })

    return job_posts

def save_to_csv(job_details_list, filename='linkedin_job_posts.csv'):
    """Save multiple job details to CSV with specific column order"""
    file_exists = os.path.isfile(filename)
    # Define the column order explicitly
    fieldnames = ['author_name', 'author_profile_url', 'job_description', 'post_url', 'email', 'phone']

    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()

        for job in job_details_list:
            writer.writerow({
                'author_name': job['author_name'],
                'author_profile_url': job['author_profile_url'],
                'job_description': job['job_description'],
                'post_url': job['post_url'],
                'email': job['email'],
                'phone': job['phone']
            })
    
    print(f"Saved {len(job_details_list)} job posts to {filename}")

def main():
    linkedin_feed_url = "https://www.linkedin.com/search/results/content/?datePosted=%22past-month%22&keywords=System%20Administrator%20Pune%2C%20Maharashtra%2C%20India&origin=FACETED_SEARCH&sid=2T!&sortBy=%22relevance%22"

    with SB(uc=True, headless=False, user_data_dir=full_path) as sb:
        sb.open(linkedin_feed_url)
        input("Press Enter after the page is fully loaded...")

        # Scroll to load more posts
        for _ in range(3):
            sb.scroll_to_bottom()
            sb.sleep(2)

        html_content = sb.get_page_source()
        all_jobs = extract_all_jobs(html_content)

        if all_jobs:
            save_to_csv(all_jobs)
            print("Extracted and saved multiple job posts.")
            for i, job in enumerate(all_jobs[:3], 1):  # Show preview of first 3
                print(f"\nPost {i}:")
                print(f"URL: {job['post_url']}")
                print(f"Author: {job['author_name']} - {job['author_profile_url']}")
                print(f"Email: {job['email']}")
                print(f"Phone: {job['phone']}")
                print(f"Description: {job['job_description'][:100]}...")  # Truncate preview
        else:
            print("No job posts found.")

if __name__ == "__main__":
    main()