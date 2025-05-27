from seleniumbase import SB
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import os

def extract_advanced_player_details(sb, timeout=15):
    """Extracts advanced player details from the Match Details section."""
    try:
        table_xpath = "//div[contains(@class, 'Opta-Team-Both')]//table[contains(@class, 'Opta-Striped')]/tbody"
        sb.wait_for_element_visible(table_xpath, timeout=timeout)
        table = sb.find_element(table_xpath)
        rows = table.find_elements(By.XPATH, "./tr")

        header_xpath = "//div[contains(@class, 'Opta-Team-Both')]//table[contains(@class, 'Opta-Striped')]/thead[contains(@class, 'Opta-Player-Stats')]/tr/th"
        header_elements = sb.find_elements(header_xpath)
        headers = [h.find_element(By.TAG_NAME, 'abbr').get_attribute('title').strip() if h.find_elements(By.TAG_NAME, 'abbr') else h.text.strip() for h in header_elements]

        player_stats_list = []
        for row in rows:
            player_name_element = row.find_element(By.XPATH, "./th[contains(@class, 'Opta-Player')]")
            player_name = player_name_element.text.strip()

            if player_name.lower() == "total":
                continue

            player_stats = {"PlayerName": player_name}
            cells = row.find_elements(By.XPATH, "./td")

            try:
                position_element = row.find_element(By.XPATH, "./td[contains(@class, 'Opta-Stat-Position')]")
                player_stats['Position'] = position_element.text.strip()
                stat_cells = cells[1:]
                stat_headers = headers[2:]
            except NoSuchElementException:
                stat_cells = cells[:]
                stat_headers = headers[1:]
                player_stats['Position'] = None

            for i, header in enumerate(stat_headers):
                cell_index = i
                if cell_index < len(stat_cells):
                    value = stat_cells[cell_index].text.strip()
                    player_stats[header] = value
                elif header:
                    player_stats[header] = ""

            player_stats_list.append(player_stats)

        actual_extracted_headers = ['PlayerName', 'Position'] if player_stats_list and 'Position' in player_stats_list[0] and player_stats_list[0]['Position'] is not None else ['PlayerName']
        if player_stats_list:
            sample_player_keys = player_stats_list[0].keys()
            for header in headers[1:]:
                if header in sample_player_keys and header not in actual_extracted_headers:
                    actual_extracted_headers.append(header)

        return player_stats_list, actual_extracted_headers

    except TimeoutException:
        print(f"⚠️ Error: Advanced player statistics table not found after {timeout} seconds.")
        return [], []
    except Exception as e:
        print(f"⚠️ Error extracting advanced data:", e)
        return [], []

with SB(uc=True) as sb:
    sb.open("https://optaplayerstats.statsperform.com/en_GB/soccer/a-league-men-2024-2025/4yylure37f3rnsje6vmsps2s4/opta-player-stats")
    time.sleep(4)

    try:
        cookie_accept_button = sb.find_element("#onetrust-accept-btn-handler", timeout=5)
        if cookie_accept_button:
            cookie_accept_button.click()
            time.sleep(2)
    except:
        pass

    try:
        match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")
        if not match_links:
            print("❌ No match links found on the main page.")
            exit()
    except Exception as e:
        print(f"❌ Error finding match links on the main page: {e}")
        exit()

    for index, match_link in enumerate(match_links):
        print(f"\n=== Processing Match {index + 1} ===")

        try:
            parent_row = match_link.find_element(By.XPATH, "./ancestor::tr")
            temp_home_team_element = parent_row.find_element(By.XPATH, ".//td[contains(@class, 'Opta-Team') and contains(@class, 'Opta-Home')]")
            temp_away_team_element = parent_row.find_element(By.XPATH, ".//td[contains(@class, 'Opta-Team') and contains(@class, 'Opta-Away')]")

            temp_home_team = temp_home_team_element.text.strip()
            temp_away_team = temp_away_team_element.text.strip()

            potential_filename = f'match_data/match_{index + 1}_{temp_home_team.replace(" ", "_")}_vs_{temp_away_team.replace(" ", "_")}_AdvancedStats.xlsx'

            if os.path.exists(potential_filename):
                print(f"✅ Advanced match data already exists for {temp_home_team} vs {temp_away_team}. Skipping this match.")
                continue

        except Exception as e:
            pass

        max_retries = 3
        clicked = False
        for retry in range(max_retries):
            try:
                current_match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")
                if index < len(current_match_links):
                    current_match_link_element = current_match_links[index]
                    sb.execute_script("arguments[0].scrollIntoView(true);", current_match_link_element)
                    time.sleep(0.5)
                    current_match_link_element.click()
                    time.sleep(5)
                    clicked = True
                    break
                else:
                    break
            except Exception as e:
                if retry < max_retries - 1:
                    time.sleep(2)
                else:
                    break

        if not clicked:
            continue

        match_data = {"Match": index + 1}

        try:
            home_team = sb.get_text("td.Opta-Team.Opta-Home.Opta-TeamName").strip()
            away_team = sb.get_text("td.Opta-Team.Opta-Away.Opta-TeamName").strip()
            home_score = sb.get_text("td.Opta-Score.Opta-Home .Opta-Team-Score").strip()
            away_score = sb.get_text("td.Opta-Score.Opta-Away .Opta-Team-Score").strip()
            match_date = sb.get_text("span.Opta-Date").strip()

            print(f"🏠 Home Team: {home_team} ({home_score})")
            print(f"🚗 Away Team: {away_team} ({away_score})")
            print(f"🗓️ Match Date: {match_date}")

            try:
                attendance = sb.get_text("//dt[text()='Attendance']/following-sibling::dd[1]").strip()
                print(f"👥 Attendance: {attendance}")
            except:
                attendance = None

            match_data["Attendance"] = attendance

        except Exception as e:
            print("⚠️ Error extracting basic match data:", e)

        match_details_link_locator = "a[href$='/match-details']"
        advanced_stats = []
        advanced_headers = []

        try:
            sb.wait_for_element_visible(match_details_link_locator, timeout=6)
            match_details_link_element = sb.find_element(match_details_link_locator)
            sb.execute_script("arguments[0].scrollIntoView(true);", match_details_link_element)
            time.sleep(0.5)
            match_details_link_element.click()
            time.sleep(3)

            advanced_stats, advanced_headers = extract_advanced_player_details(sb)

        except Exception as e:
            print(f"⚠️ Error clicking 'Match Details' link or extracting advanced stats: {e}")

        advanced_df = pd.DataFrame(advanced_stats)
        if not advanced_df.empty:
            advanced_df['Home Team'] = home_team
            advanced_df['Away Team'] = away_team
            advanced_df['Match Date'] = match_date
            advanced_df['Home_Score'] = home_score
            advanced_df['Away_Score'] = away_score
            advanced_df['Attendance'] = match_data.get("Attendance", None)

            all_cols = ['Home Team', 'Away Team', 'Match Date', 'Home_Score', 'Away_Score', 'Attendance'] + advanced_headers
            all_cols = [col for col in all_cols if col in advanced_df.columns]
            advanced_df = advanced_df[all_cols]

            os.makedirs('match_data', exist_ok=True)
            filename = f'match_data/match_{index + 1}_{home_team.replace(" ", "_")}_vs_{away_team.replace(" ", "_")}_AdvancedStats.xlsx'
            try:
                with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                    advanced_df.to_excel(writer, sheet_name='Advanced Stats', index=False)
                print(f"💾 Advanced data saved to {filename}")
            except Exception as e:
                print(f"⚠️ Error saving advanced data to {filename}: {e}")
        else:
            print("⚠️ No advanced stats extracted to save.")

        try:
            sb.go_back()
            time.sleep(3)
            sb.go_back()
            time.sleep(3)
            
            try:
                match_links = sb.find_elements("//td[contains(@class, 'Opta-Score') and contains(@class, 'Opta-Home') and @title='View match']/span[contains(@class, 'Opta-Team-Score')]")
                if not match_links:
                    sb.open("https://optaplayerstats.statsperform.com/en_GB/soccer/a-league-men-2024-2025/4yylure37f3rnsje6vmsps2s4/opta-player-stats")
                    time.sleep(5)
            except:
                sb.open("https://optaplayerstats.statsperform.com/en_GB/soccer/a-league-men-2024-2025/4yylure37f3rnsje6vmsps2s4/opta-player-stats")
                time.sleep(5)
                
        except Exception as e:
            print(f"⚠️ Error navigating back to main page for Match {index + 1}: {e}")
            try:
                sb.open("https://optaplayerstats.statsperform.com/en_GB/soccer/a-league-men-2024-2025/4yylure37f3rnsje6vmsps2s4/opta-player-stats")
                time.sleep(5)
            except:
                break

    print("\n--- Scraping Completed (Advanced Stats Saved) ---")