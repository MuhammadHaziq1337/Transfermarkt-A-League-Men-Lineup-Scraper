from seleniumbase import SB
from selenium.webdriver.common.by import By
import time
import csv
import os
import re

# Create a directory for CSV files if it doesn't exist
output_dir = "team_data"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

visited_teams = set()

with SB(uc=True, headless=False) as sb:
    url = "https://www.transfermarkt.com/a-league-men/gesamtspielplan/wettbewerb/AUS1/saison_id/2024"
    sb.open(url)
    time.sleep(5)
    
    print("Scraping A-League teams data...")

    matchday_blocks = sb.driver.find_elements(
        By.XPATH,
        "//div[contains(@class, 'box') and .//div[contains(@class, 'content-box-headline')]]"
    )

    team_links = set()

    for block in matchday_blocks:
        team_anchors = block.find_elements(By.XPATH, ".//td[contains(@class, 'hauptlink')]/a")
        for anchor in team_anchors:
            team_name = anchor.get_attribute("title")
            href = anchor.get_attribute("href")
            if not team_name or not href or "/spielbericht/" in href:
                continue
            team_name = team_name.strip()
            full_url = f"https://www.transfermarkt.com{href}" if href.startswith("/") else href
            if team_name not in visited_teams:
                team_links.add((team_name, full_url))
                visited_teams.add(team_name)

    print(f"Found {len(team_links)} unique teams")
    
    for i, (team_name, original_url) in enumerate(team_links, 1):
        try:
            # Create a valid filename
            filename = re.sub(r'[\\/*?:"<>|]', "", team_name).replace(" ", "_") + ".csv"
            file_path = os.path.join(output_dir, filename)
            
            squad_url = original_url.replace("/spielplan/", "/kader/") + "/plus/1"
            print(f"[{i}/{len(team_links)}] Scraping squad data for: {team_name}")
            sb.open(squad_url)
            time.sleep(5)

            player_rows = sb.find_elements("xpath", "//table[contains(@class,'items')]/tbody/tr")
            
            # Prepare CSV file
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Player', 'Position', 'DOB/Age', 'Nationality', 
                    'Height', 'Foot', 'Joined', 'Signed from', 
                    'Contract', 'Market value'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                player_count = 0
                for row in player_rows:
                    if "bg_blau" in row.get_attribute("class"):
                        continue

                    try:
                        player_cell = row.find_element("xpath", "./td[2]")
                        player_name_elem = player_cell.find_element("xpath", ".//td[@class='hauptlink']/a")
                        player_name = player_name_elem.text.strip()
                        position_elem = player_cell.find_element("xpath", ".//tr[2]/td")
                        position = position_elem.text.strip()

                        dob_age = row.find_element("xpath", "./td[3]").text.strip()
                        nationality_imgs = row.find_elements("xpath", "./td[4]//img")
                        nationality = ", ".join(img.get_attribute("title") for img in nationality_imgs)

                        height = row.find_element("xpath", "./td[5]").text.strip()
                        foot = row.find_element("xpath", "./td[6]").text.strip()
                        joined = row.find_element("xpath", "./td[7]").text.strip()

                        signed_from = "-"
                        sf_links = row.find_elements("xpath", "./td[8]//a")
                        if sf_links:
                            sf_title = sf_links[0].get_attribute("title")
                            if sf_title and ":" in sf_title:
                                signed_from = sf_title.split(":")[0].strip()

                        contract = row.find_element("xpath", "./td[9]").text.strip()
                        
                        market_value = "-"
                        mv_links = row.find_elements("xpath", "./td[10]//a")
                        if mv_links:
                            market_value = mv_links[0].text.strip()
                        else:
                            mv_text = row.find_element("xpath", "./td[10]").text.strip()
                            if mv_text:
                                market_value = mv_text

                        # Write to CSV
                        writer.writerow({
                            'Player': player_name,
                            'Position': position,
                            'DOB/Age': dob_age,
                            'Nationality': nationality,
                            'Height': height,
                            'Foot': foot,
                            'Joined': joined,
                            'Signed from': signed_from,
                            'Contract': contract,
                            'Market value': market_value
                        })
                        
                        player_count += 1

                    except Exception as e:
                        print(f"  [Warning] Error parsing player: {e}")
                        continue
            
            print(f"  ✓ Saved {player_count} players to {filename}")

        except Exception as e:
            print(f"  [Error] Failed to process {team_name}: {e}")
            continue

    print("\nScraping completed! Files saved to the 'team_data' directory.")
