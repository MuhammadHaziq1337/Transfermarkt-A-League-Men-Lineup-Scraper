from seleniumbase import SB
from selenium.webdriver.common.by import By
import time
import csv
import os
import re
import json

def sanitize_filename(text):
    """Sanitize text for use in filenames by removing invalid characters"""
    # Replace invalid filename characters with underscore
    return re.sub(r'[\\/*?:"<>|]', "_", text)

def extract_lineup_data(lineup_table):
    """Extract player data from a lineup table"""
    lineup = []
    rows = lineup_table.find_elements(By.XPATH, ".//tbody/tr")
    
    for row in rows:
        try:
            # Check if this is a valid player row (has at least 3 cells)
            cells = row.find_elements(By.XPATH, "./td")
            if len(cells) < 3:
                continue
            
            # Position from first td (title)
            position_td = row.find_element(By.XPATH, "./td[contains(@class, 'rueckennummer')]")
            pos_title = position_td.get_attribute("title")
            
            # Name and age
            name_elem = row.find_element(By.XPATH, ".//td[2]//a[contains(@class, 'wichtig')]")
            name = name_elem.text.strip()
            age_block = row.find_element(By.XPATH, ".//td[2]").text
            age = age_block.split('(')[-1].split()[0] if '(' in age_block else ""
            
            # Position + Market Value
            inline_rows = row.find_elements(By.XPATH, ".//td[2]//table//tr")
            if len(inline_rows) >= 2:
                pos_val_text = inline_rows[1].text.strip()
                if ',' in pos_val_text:
                    position, market_value = pos_val_text.split(",", 1)
                    position = position.strip()
                    market_value = market_value.strip()
                else:
                    position = pos_val_text
                    market_value = ""
            else:
                position = pos_title
                market_value = ""
            
            # Nationality
            flag_imgs = row.find_elements(By.XPATH, ".//td[3]//img")
            nationalities = [img.get_attribute("title") for img in flag_imgs]
            
            lineup.append({
                "Name": name,
                "Age": age,
                "Position": position,
                "Market Value": market_value,
                "Nationality": ", ".join(nationalities)
            })
        except Exception:
            continue
    
    return lineup

def get_match_id_from_url(url):
    """Extract the match ID from a URL"""
    # URL format: https://www.transfermarkt.com/path/path/spielbericht/12345 or similar
    match = re.search(r'/spielbericht/(\d+)', url)
    if match:
        return match.group(1)
    return None

def load_scraped_matches():
    """Load the list of already scraped match IDs"""
    progress_file = 'match_csvs/progress.json'
    
    if not os.path.exists('match_csvs'):
        os.makedirs('match_csvs')
        return {}
    
    if not os.path.exists(progress_file):
        return {}
    
    try:
        with open(progress_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Warning: Could not load progress file: {e}")
        return {}

def update_scraped_matches(progress, match_id, match_data=None):
    """Update the list of scraped match IDs"""
    progress_file = 'match_csvs/progress.json'
    
    if not os.path.exists('match_csvs'):
        os.makedirs('match_csvs')
    
    # Add the match ID with timestamp to the progress
    progress[match_id] = {
        'timestamp': time.time(),
        'date': match_data["Match Date"] if match_data else 'N/A',
        'teams': f"{match_data['Home Team']['Name']} vs {match_data['Away Team']['Name']}" if match_data else 'N/A'
    }
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        print(f"⚠️ Warning: Could not update progress file: {e}")

def save_match_to_csv(match_data):
    """Save match data to a CSV file"""
    # Create match_csvs directory if it doesn't exist
    os.makedirs("match_csvs", exist_ok=True)
    
    # Parse and format the date for filename
    date_str = match_data["Match Date"]
    try:
        # Try to convert various date formats to YYYY-MM-DD
        if "," in date_str:
            # Format like "Sat, 10/19/24"
            date_parts = date_str.split(", ")[1].split("/")
            if len(date_parts) == 3:
                month, day, year = date_parts
                if len(year) == 2:
                    year = f"20{year}"
                formatted_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                formatted_date = date_str.replace("/", "-")
        else:
            # Fallback to original string with slashes replaced by hyphens
            formatted_date = date_str.replace("/", "-")
    except Exception:
        # If any issues with date parsing, use a basic sanitized version
        formatted_date = sanitize_filename(date_str)
    
    # Create filename
    home_team = sanitize_filename(match_data["Home Team"]["Name"])
    away_team = sanitize_filename(match_data["Away Team"]["Name"])
    filename = f"{formatted_date}_{home_team}_vs_{away_team}.csv"
    filepath = os.path.join("match_csvs", filename)
    
    # Prepare data for CSV
    csv_rows = []
    
    # Add home team players
    for player in match_data["Home Team"]["Starting XI"]:
        csv_rows.append({
            "Match Date": match_data["Match Date"],
            "Team": match_data["Home Team"]["Name"],
            "Opponent": match_data["Away Team"]["Name"],
            "Lineup Type": "Starting XI",
            "Name": player["Name"],
            "Age": player["Age"],
            "Position": player["Position"],
            "Market Value": player["Market Value"],
            "Nationality": player["Nationality"]
        })
    
    for player in match_data["Home Team"]["Substitutes"]:
        csv_rows.append({
            "Match Date": match_data["Match Date"],
            "Team": match_data["Home Team"]["Name"],
            "Opponent": match_data["Away Team"]["Name"],
            "Lineup Type": "Substitutes",
            "Name": player["Name"],
            "Age": player["Age"],
            "Position": player["Position"],
            "Market Value": player["Market Value"],
            "Nationality": player["Nationality"]
        })
    
    # Add away team players
    for player in match_data["Away Team"]["Starting XI"]:
        csv_rows.append({
            "Match Date": match_data["Match Date"],
            "Team": match_data["Away Team"]["Name"],
            "Opponent": match_data["Home Team"]["Name"],
            "Lineup Type": "Starting XI",
            "Name": player["Name"],
            "Age": player["Age"],
            "Position": player["Position"],
            "Market Value": player["Market Value"],
            "Nationality": player["Nationality"]
        })
    
    for player in match_data["Away Team"]["Substitutes"]:
        csv_rows.append({
            "Match Date": match_data["Match Date"],
            "Team": match_data["Away Team"]["Name"],
            "Opponent": match_data["Home Team"]["Name"],
            "Lineup Type": "Substitutes",
            "Name": player["Name"],
            "Age": player["Age"],
            "Position": player["Position"],
            "Market Value": player["Market Value"],
            "Nationality": player["Nationality"]
        })
    
    # Define column headers
    fieldnames = ["Match Date", "Team", "Opponent", "Lineup Type", "Name", "Age", "Position", "Market Value", "Nationality"]
    
    # Write to CSV
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"✅ CSV saved: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")
        return None

def process_match_lineup(sb, match_url, progress):
    """Process a single match's lineup page"""
    # Get match ID for tracking
    match_id = get_match_id_from_url(match_url)
    
    # Check if already scraped
    if match_id in progress:
        print(f"⏩ Skipping already scraped match (ID: {match_id}): {progress[match_id]['teams']}")
        return None
    
    # Replace 'index' with 'aufstellung' to go to line-up page
    lineup_url = match_url.replace("/index/", "/aufstellung/")
    print(f"🔍 Processing: {lineup_url}")
    
    # Open line-up page directly
    sb.open(lineup_url)
    time.sleep(5)  # Wait for page to load
    
    try:
        # Extract team names
        team_boxes = sb.driver.find_elements(By.XPATH, "//div[contains(@class, 'large-6 columns')]//h2[contains(@class, 'content-box-headline')]")
        teams = []
        
        for box in team_boxes:
            # Each team appears twice (once for starting XI, once for subs)
            team_name = box.find_element(By.XPATH, "./a").get_attribute("title")
            if team_name not in teams:
                teams.append(team_name)
        
        if len(teams) < 2:
            print("⚠️ Warning: Expected 2 teams, found", len(teams))
            return None
        
        # Home team is first, away team is second
        home_team, away_team = teams[0], teams[1]
        
        # Extract match date
        try:
            date_elem = sb.driver.find_element(By.XPATH, "//p[@class='sb-datum hide-for-small']/a[2]")
            match_date = date_elem.text.strip()
        except Exception:
            match_date = "N/A"
        
        # Try to get match score if available
        try:
            score_elem = sb.driver.find_element(By.XPATH, "//div[contains(@class, 'sb-endstand')]")
            match_score = score_elem.text.strip()
        except Exception:
            match_score = "N/A"
        
        # Print minimal match info
        print(f"📅 {match_date} | {home_team} vs {away_team}")
        
        # Initialize data structure
        match_data = {
            "Match Date": match_date,
            "Score": match_score,
            "Home Team": {
                "Name": home_team,
                "Starting XI": [],
                "Substitutes": []
            },
            "Away Team": {
                "Name": away_team,
                "Starting XI": [],
                "Substitutes": []
            }
        }
        
        # Get all team blocks
        team_blocks = sb.driver.find_elements(By.XPATH, "//div[contains(@class, 'large-6 columns')]/div[contains(@class, 'box')]")
        
        for block in team_blocks:
            try:
                # Determine which team and if starting or subs
                header = block.find_element(By.XPATH, ".//h2").text
                team_name = block.find_element(By.XPATH, ".//h2/a").get_attribute("title")
                
                # Skip manager blocks
                if "manager" in header.lower():
                    continue
                    
                # Convert header to lowercase for case-insensitive comparison
                header_lower = header.lower()
                is_subs = "substitutes" in header_lower
                lineup_type = "Substitutes" if is_subs else "Starting XI"
                
                # Find the lineup table inside this section
                lineup_table = block.find_element(By.XPATH, ".//table[contains(@class, 'items')]")
                players = extract_lineup_data(lineup_table)
                
                # Determine if home or away team
                team_key = "Home Team" if team_name == home_team else "Away Team"
                match_data[team_key][lineup_type] = players
                
                # Print simple progress for each team section
                print(f"  ✓ Extracted {len(players)} players: {team_name} {lineup_type}")
                
            except Exception as e:
                print(f"⚠️ Error processing team block: {e}")
        
        # Save data to CSV
        csv_path = save_match_to_csv(match_data)
        
        # Update progress
        if match_id:
            update_scraped_matches(progress, match_id, match_data)
        
        return match_data
        
    except Exception as e:
        print(f"❌ Error processing match: {e}")
        return None

# Main execution
with SB(uc=True, headless=False) as sb:
    # Load progress information
    scraped_matches = load_scraped_matches()
    print(f"ℹ️ Found {len(scraped_matches)} previously scraped matches")
    
    # Open the season schedule page
    sb.open("https://www.transfermarkt.com/a-league-men/gesamtspielplan/wettbewerb/AUS1/saison_id/2024")
    time.sleep(5)  # Wait for page to load

    # Get all match detail links
    match_links = sb.driver.find_elements(By.XPATH, "//a[contains(@class, 'ergebnis-link') and contains(@href, '/spielbericht/')]")
    
    if not match_links:
        print("❌ No match links found")
    else:
        total_matches = len(match_links)
        print(f"✅ Found {total_matches} matches")
        
        # Limit the number of matches for testing
        #match_links = match_links[:3]  # Process only first 3 matches
        if len(match_links) < total_matches:
            print(f"ℹ️ Processing only {len(match_links)} of {total_matches} matches")
        
        # Extract URLs and filter already scraped matches
        match_urls = []
        already_scraped = 0
        
        for link in match_links:
            href = link.get_attribute("href")
            full_url = f"https://www.transfermarkt.com{href}" if href.startswith("/") else href
            match_id = get_match_id_from_url(full_url)
            
            # Track the URL whether scraped or not
            match_urls.append(full_url)
            
            # Count already scraped matches
            if match_id in scraped_matches:
                already_scraped += 1
        
        if already_scraped > 0:
            print(f"ℹ️ {already_scraped} matches already scraped (will be skipped)")
        
        # Process each match
        successful_matches = 0
        for i, match_url in enumerate(match_urls):
            print(f"\n📊 Match {i+1}/{len(match_urls)}")
            match_data = process_match_lineup(sb, match_url, scraped_matches)
            if match_data:
                successful_matches += 1
            time.sleep(2)  # Brief pause between matches to avoid overloading the server
        
        print(f"\n✅ Completed: {successful_matches} new matches processed successfully")
        print(f"📁 CSV files saved in match_csvs/ folder")
        print(f"📊 Total scraped matches: {len(scraped_matches)}")


