from seleniumbase import SB
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import pandas as pd
import os

def extract_player_details_for_half(sb, half_index, timeout=15):
    """Extracts player details for a specific half using website headers."""
    half_stats = []
    try:
        # Click the specified half button
        half_button_xpath = f'button.Opta-Stdperiod[data-period_idx="{half_index}"]'
        sb.click(half_button_xpath)
        time.sleep(2) # Short sleep after clicking

        # Locate the player stats table and wait for it to be visible
        table_xpath = "//div[contains(@class, 'Opta-Team-Both')]//table[contains(@class, 'Opta-Striped')]/tbody"
        sb.wait_for_element_visible(table_xpath, timeout=timeout)
        table = sb.find_element(table_xpath)
        rows = table.find_elements(By.XPATH, "./tr")

        # Locate the table header to get the order of stats
        header_xpath = "//div[contains(@class, 'Opta-Team-Both')]//table[contains(@class, 'Opta-Striped')]/thead[contains(@class, 'Opta-Player-Stats')]/tr/th"
        header_elements = sb.find_elements(header_xpath)
        headers = [h.find_element(By.TAG_NAME, 'abbr').get_attribute('title').strip() if h.find_elements(By.TAG_NAME, 'abbr') else h.text.strip() for h in header_elements]

        print(f"\n--- Player Statistics (Half {half_index}) Headers ---")
        print(headers)
        print(f"\n--- Player Statistics (Half {half_index}) ---")
        for row in rows:
            player_name_element = row.find_element(By.XPATH, "./th[contains(@class, 'Opta-Player')]")
            player_name = player_name_element.text.strip()
            player_stats = {"Player Name": player_name, "Half": half_index}
            cells = row.find_elements(By.XPATH, "./td[contains(@class, 'Opta-Stat')]")

            print(f"\n-- {player_name} --")
            # Start iterating from the second header (index 1) and align with cells from index 0
            for i in range(1, len(headers)):
                header = headers[i]
                cell_index = i - 1
                if cell_index < len(cells):
                    value = cells[cell_index].text.strip()
                    player_stats[header] = value
                    print(f"{header}: {value}")
                elif header:
                    player_stats[header] = ""
                    print(f"{header}: ")

            half_stats.append(player_stats)

    except TimeoutException:
        print(f"⚠️ Error: Player statistics table not found after {timeout} seconds for Half {half_index}.")
    except Exception as e:
        print(f"⚠️ Error extracting data for Half {half_index}:", e)

    return half_stats

def create_match_dataframe(match_data, half_stats):
    """Creates a DataFrame for a specific half of a match."""
    # Create rows with match metadata and player stats
    rows = []
    for player_stat in half_stats:
        row = {
            'Home Team': match_data['Home Team Name'],
            'Away Team': match_data['Away Team Name'],
            'Match Date': match_data['Match Time'],
            'Home_Score': match_data['Home Team'],
            'Away_Score': match_data['Away Team'],
            'Player Name': player_stat['Player Name'],
            'Goals': player_stat.get('Goals', '0'),
            'Assists': player_stat.get('Assists', '0'),
            'Red cards': player_stat.get('Red cards', '0'),
            'Yellow cards': player_stat.get('Yellow cards', '0'),
            'Corners won': player_stat.get('Corners won', '0'),
            'Shots': player_stat.get('Shots', '0'),
            'Shots on target': player_stat.get('Shots on target', '0'),
            'Blocked shots': player_stat.get('Blocked shots', '0'),
            'Passes': player_stat.get('Passes', '0'),
            'Crosses': player_stat.get('Crosses', '0'),
            'Tackles': player_stat.get('Tackles', '0'),
            'Offsides': player_stat.get('Offsides', '0'),
            'Fouls conceded': player_stat.get('Fouls conceded', '0'),
            'Fouls won': player_stat.get('Fouls won', '0'),
            'Saves': player_stat.get('Saves', '0')
        }
        rows.append(row)
    
    return pd.DataFrame(rows)

def save_match_to_excel(match_data, match_index):
    """Saves match data to an Excel file with two sheets for each half."""
    # Create output directory if it doesn't exist
    os.makedirs('match_data', exist_ok=True)
    
    # Create Excel writer object
    filename = f'match_data/match_{match_index + 1}_{match_data["Home Team Name"]}_vs_{match_data["Away Team Name"]}.xlsx'
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    
    # Create and save dataframes for each half
    for half in match_data['Halves']:
        half_number = half['Half']
        half_stats = half['Stats']
        
        df = create_match_dataframe(match_data, half_stats)
        sheet_name = f'Half {half_number}'
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    writer.close()
    print(f"Saved match data to {filename}")

with SB(uc=True) as sb:
    sb.open("https://optaplayerstats.statsperform.com/en_GB/soccer/a-league-men-2024-2025/4yylure37f3rnsje6vmsps2s4/opta-player-stats")
    time.sleep(4)

    # Handle cookie consent banner if it appears
    try:
        cookie_accept_button = sb.find_element("#onetrust-accept-btn-handler", timeout=5)
        if cookie_accept_button:
            cookie_accept_button.click()
            time.sleep(2)
    except:
        print("No cookie banner found or already accepted")

    # Get all match elements
    match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")

    all_matches_data = []

    for index, match_link in enumerate(match_links):
        print(f"\n=== Processing Match {index + 1} ===")
        
        # Check if match data already exists
        try:
            home_team = sb.get_text("td.Opta-Team.Opta-Home.Opta-TeamName").strip()
            away_team = sb.get_text("td.Opta-Team.Opta-Away.Opta-TeamName").strip()
            potential_filename = f'match_data/match_{index + 1}_{home_team}_vs_{away_team}.xlsx'
            
            if os.path.exists(potential_filename):
                print(f"✅ Match data already exists for {home_team} vs {away_team}. Skipping...")
                continue
        except Exception as e:
            print("⚠️ Error checking for existing file:", e)
        
        try:
            # Try to click the match link with retry mechanism
            max_retries = 3
            for retry in range(max_retries):
                try:
                    match_link.click()
                    time.sleep(5)
                    break
                except Exception as e:
                    if retry < max_retries - 1:
                        print(f"⚠️ Click failed, retrying ({retry + 1}/{max_retries})...")
                        time.sleep(2)
                        # Refresh the match link element
                        match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")
                        match_link = match_links[index]
                    else:
                        raise e
        except Exception as e:
            print(f"⚠️ Error clicking match link: {e}")
            continue

        match_data = {"Match": index + 1}

        try:
            # Extract basic match information
            home_team = sb.get_text("td.Opta-Team.Opta-Home.Opta-TeamName").strip()
            away_team = sb.get_text("td.Opta-Team.Opta-Away.Opta-TeamName").strip()
            match_data["Home Team"] = sb.get_text("td.Opta-Score.Opta-Home .Opta-Team-Score").strip()
            match_data["Away Team"] = sb.get_text("td.Opta-Score.Opta-Away .Opta-Team-Score").strip()
            match_data["Match Time"] = sb.get_text("span.Opta-Date").strip()

            print(f"🏠 Home Team: {home_team} ({match_data['Home Team']})")
            print(f"🚗 Away Team: {away_team} ({match_data['Away Team']})")
            print(f"🕒 Match Time: {match_data['Match Time']}")

            match_data["Home Team Name"] = home_team
            match_data["Away Team Name"] = away_team

        except Exception as e:
            print("⚠️ Error extracting basic match data:", e)
            match_data["Basic Match Data Error"] = str(e)
            sb.go_back()
            time.sleep(5)
            match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")
            continue # Skip to the next match if basic info fails

        try:
            # Extract attendance
            attendance = sb.get_text("//dt[text()='Attendance']/following-sibling::dd[1]").strip()
            match_data["Attendance"] = attendance
            print(f"👥 Attendance: {attendance}")
        except NoSuchElementException:
            print("⚠️ Attendance information not found for this match.")
            match_data["Attendance"] = None
        except Exception as e:
            print(f"⚠️ Error extracting attendance:", e)
            match_data["Attendance Error"] = str(e)


        match_data["Halves"] = []

        # Extract First Half details
        print("\n--- First Half ---")
        first_half_stats = extract_player_details_for_half(sb, 1)
        match_data["Halves"].append({"Half": 1, "Stats": first_half_stats})

        # Extract Second Half details
        print("\n--- Second Half ---")
        second_half_stats = extract_player_details_for_half(sb, 2)
        match_data["Halves"].append({"Half": 2, "Stats": second_half_stats})

        all_matches_data.append(match_data)
        
        # Save match data to Excel file
        save_match_to_excel(match_data, index)

        sb.go_back()  # Go back to the main page
        time.sleep(5)

        # Refresh element list to avoid stale references
        match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")

    print("\n--- All Matches Data ---")
    print(json.dumps(all_matches_data, indent=4))