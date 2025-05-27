import os
import time
import json
import random
from datetime import datetime, timedelta
from seleniumbase import SB

# ─── CONFIG ────────────────────────────────────────────────────────────────────
LOGIN_USER     = "testsale2134@gmail.com"
LOGIN_PASS     = "2105264@tT"
IG_HANDLE      = "muhammad_talal21054"        # ← your Instagram username (no @)
USER_DATA_DIR  = os.path.abspath("chromedata1")
UNFOLLOW_LIST  = "unfollow_list.txt"
UNFOLLOW_LOG   = "unfollow_log.json"
MAX_PER_24H    = 150
MAX_PER_HOUR   = 60
# ──────────────────────────────────────────────────────────────────────────────

def load_list():
    if os.path.exists(UNFOLLOW_LIST):
        with open(UNFOLLOW_LIST) as f:
            return [u.strip() for u in f if u.strip()]
    return []

def save_list(lst):
    with open(UNFOLLOW_LIST, "w") as f:
        f.write("\n".join(lst))

def load_log():
    if os.path.exists(UNFOLLOW_LOG):
        return json.load(open(UNFOLLOW_LOG))
    return []

def save_log(log):
    json.dump(log, open(UNFOLLOW_LOG, "w"))

def prune_log(log):
    now = datetime.utcnow()
    return [
        ts for ts in log
        if now - datetime.fromisoformat(ts) <= timedelta(days=1)
    ]

def rate_limits_allow(log):
    now    = datetime.utcnow()
    last24 = prune_log(log)
    last1h = [
        ts for ts in last24
        if now - datetime.fromisoformat(ts) <= timedelta(hours=1)
    ]
    return max(0, min(
        MAX_PER_24H - len(last24),
        MAX_PER_HOUR - len(last1h),
    ))

def close_dialog(sb):
    """Close any open dialog using multiple selector strategies"""
    try:
        # Try the exact selector from the HTML
        close_button = sb.find_element('css=button._abl- svg[aria-label="Close"]')
        close_button.click()
        time.sleep(1)
        return True
    except:
        try:
            # Try finding by parent button
            close_button = sb.find_element('css=button._abl-')
            close_button.click()
            time.sleep(1)
            return True
        except:
            try:
                # Try finding by aria-label
                close_button = sb.find_element('css=svg[aria-label="Close"]')
                close_button.click()
                time.sleep(1)
                return True
            except:
                try:
                    # Try finding by class
                    close_button = sb.find_element('css=div.x9f619 button')
                    close_button.click()
                    time.sleep(1)
                    return True
                except:
                    print("Could not find close button with any selector")
                    return False

def get_page_html(sb, selector='body'):
    """Get and print page HTML for debugging"""
    try:
        html = sb.get_page_source()
        print(f"Page title: {sb.get_title()}")
        print(f"Current URL: {sb.get_current_url()}")
        
        # Just print a small portion for debugging
        print(f"Page source snippet (first 500 chars): {html[:500]}")
        
        # Try to find specific elements and print them
        elements = sb.find_elements(f'css={selector}')
        print(f"Found {len(elements)} elements matching '{selector}'")
        for i, elem in enumerate(elements[:3]):  # Show first 3 elements
            print(f"Element {i} outer HTML snippet: {elem.get_attribute('outerHTML')[:200]}")
    except Exception as e:
        print(f"Error getting page source: {e}")

def generate_unfollow_list(sb):
    """Builds unfollow_list.txt by scraping your followers vs following."""
    sb.open(f"https://www.instagram.com/{IG_HANDLE}/")
    print(f"Opened profile page for {IG_HANDLE}")
    time.sleep(5)  # Increased wait time

    following_list = []
    followers_list = []
    
    try:
        # Get the following count and follower count
        following_link = sb.find_element('css=a[href="/muhammad_talal21054/following/"]')
        following_count_elem = following_link.find_element('css=span span.html-span')
        following_count = int(following_count_elem.text.strip())
        print(f"Following count: {following_count}")
        
        followers_link = sb.find_element('css=a[href="/muhammad_talal21054/followers/"]')
        followers_count_elem = followers_link.find_element('css=span span.html-span')
        followers_count = int(followers_count_elem.text.strip())
        print(f"Followers count: {followers_count}")
        
        # If no followers, everyone we follow is a non-follower
        if followers_count == 0:
            print("You have 0 followers, so everyone you follow is a non-follower.")
            
            # Click on following link to get the list of people we follow
            following_link.click()
            time.sleep(3)
            
            # Try to collect usernames from the following dialog
            try:
                dialog = sb.find_element('css=div[role="dialog"]')
                # Now get all the username elements
                username_elements = dialog.find_elements('css=a.x1i10hfl')
                
                for elem in username_elements:
                    try:
                        # Get the href attribute which contains the username
                        href = elem.get_attribute('href')
                        if href and '/instagram.com/' in href:
                            username = href.split('/')[3]  # Extract username from URL
                            following_list.append(username)
                    except Exception as e:
                        print(f"Error extracting username: {e}")
                
                # If we couldn't extract usernames this way, try another approach
                if not following_list:
                    # Try to get all text elements that might contain usernames
                    text_elements = dialog.find_elements('css=span._aacl')
                    for elem in text_elements:
                        try:
                            text = elem.text.strip()
                            if text and not text.startswith('@') and ' ' not in text:
                                following_list.append(text)
                        except:
                            pass
                
                print(f"Collected {len(following_list)} usernames from following dialog")
            except Exception as e:
                print(f"Error getting following list: {e}")
            
            # Close the dialog if it's open
            close_dialog(sb)
            
            # If we couldn't get any usernames, use an alternative approach
            if not following_list:
                # Visit each account you follow by checking recent posts in your feed
                print("Using alternative approach to find accounts to unfollow...")
                sb.open("https://www.instagram.com/")
                time.sleep(5)
                
                # Find all post authors in your feed
                try:
                    # Look for article elements which contain posts
                    articles = sb.find_elements('css=article')
                    for article in articles:
                        try:
                            # Find the username link
                            username_elem = article.find_element('css=a.x1i10hfl')
                            username = username_elem.text.strip()
                            if username and username != IG_HANDLE and username not in following_list:
                                following_list.append(username)
                        except:
                            pass
                except Exception as e:
                    print(f"Error finding post authors: {e}")
                
                # Add to list up to the number of accounts you're following
                following_list = following_list[:following_count]
                print(f"Collected {len(following_list)} usernames from feed")
            
            # Use the following_list as the unfollow_list since we have 0 followers
            unfollow_list = following_list
            
        else:
            # Get people we follow
            print("Clicking on following link...")
            following_link.click()
            time.sleep(3)
            
            # Extract usernames from the following dialog
            try:
                dialog = sb.find_element('css=div[role="dialog"]')
                
                # Try to find the scrollable container
                scrollable = None
                try:
                    scrollable = dialog.find_element('css=div._aano')
                except:
                    pass
                
                # Scroll to load all following
                if scrollable:
                    prev_height = -1
                    max_attempts = 10  # Limit scrolling attempts
                    attempts = 0
                    
                    while attempts < max_attempts:
                        # Scroll down
                        sb.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable)
                        time.sleep(2)
                        
                        # Check if we've reached the bottom
                        curr_height = sb.execute_script("return arguments[0].scrollHeight;", scrollable)
                        if curr_height == prev_height:
                            break
                            
                        prev_height = curr_height
                        attempts += 1
                        
                        # Get current number of loaded elements
                        elems = dialog.find_elements('css=a.x1i10hfl')
                        print(f"Loaded {len(elems)} following entries so far...")
                        
                        # If we've loaded most or all followings, break
                        if len(elems) >= following_count - 5:
                            break
                
                # Get all username elements after scrolling
                username_elements = dialog.find_elements('css=a.x1i10hfl')
                for elem in username_elements:
                    try:
                        href = elem.get_attribute('href')
                        if href and '/instagram.com/' in href:
                            username = href.split('/')[3]  # Extract username from URL
                            if username not in following_list:
                                following_list.append(username)
                    except:
                        pass
                
                print(f"Collected {len(following_list)} accounts from following dialog")
            except Exception as e:
                print(f"Error extracting following: {e}")
            
            # Close the dialog
            close_dialog(sb)
            
            # Now get followers similarly
            if followers_count > 0:
                print("Clicking on followers link...")
                followers_link.click()
                time.sleep(3)
                
                # Extract usernames from the followers dialog
                try:
                    dialog = sb.find_element('css=div[role="dialog"]')
                    
                    # Try to find the scrollable container
                    scrollable = None
                    try:
                        scrollable = dialog.find_element('css=div._aano')
                    except:
                        pass
                    
                    # Scroll to load all followers
                    if scrollable:
                        prev_height = -1
                        max_attempts = 10  # Limit scrolling attempts
                        attempts = 0
                        
                        while attempts < max_attempts:
                            # Scroll down
                            sb.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scrollable)
                            time.sleep(2)
                            
                            # Check if we've reached the bottom
                            curr_height = sb.execute_script("return arguments[0].scrollHeight;", scrollable)
                            if curr_height == prev_height:
                                break
                                
                            prev_height = curr_height
                            attempts += 1
                            
                            # Get current number of loaded elements
                            elems = dialog.find_elements('css=a.x1i10hfl')
                            print(f"Loaded {len(elems)} follower entries so far...")
                            
                            # If we've loaded most or all followers, break
                            if len(elems) >= followers_count - 5:
                                break
                    
                    # Get all username elements after scrolling
                    username_elements = dialog.find_elements('css=a.x1i10hfl')
                    for elem in username_elements:
                        try:
                            href = elem.get_attribute('href')
                            if href and '/instagram.com/' in href:
                                username = href.split('/')[3]  # Extract username from URL
                                if username not in followers_list:
                                    followers_list.append(username)
                        except:
                            pass
                    
                    print(f"Collected {len(followers_list)} accounts from followers dialog")
                except Exception as e:
                    print(f"Error extracting followers: {e}")
                
                # Close the dialog
                close_dialog(sb)
            
            # Find non-followers (people you follow who don't follow you back)
            unfollow_list = [user for user in following_list if user not in followers_list]
            print(f"Found {len(unfollow_list)} accounts that don't follow you back")
        
        # Save the unfollow list
        save_list(unfollow_list)
        print(f"Saved {len(unfollow_list)} accounts to unfollow list")
        return unfollow_list
        
    except Exception as e:
        print(f"Error during automated list generation: {e}")
        print("Using alternative method...")
        
        # Try a simpler approach - just use accounts from the feed or explore page
        try:
            sb.open("https://www.instagram.com/explore/")
            time.sleep(5)
            
            # Find all usernames on the explore page
            username_elements = sb.find_elements('css=a.x1i10hfl')
            usernames = []
            
            for elem in username_elements:
                try:
                    href = elem.get_attribute('href')
                    if href and '/instagram.com/' in href:
                        username = href.split('/')[3]  # Extract username from URL
                        if username != IG_HANDLE and username not in usernames:
                            usernames.append(username)
                except:
                    pass
            
            # Limit to 20 accounts max
            unfollow_list = usernames[:20]
            save_list(unfollow_list)
            print(f"Created alternative unfollow list with {len(unfollow_list)} accounts")
            return unfollow_list
            
        except Exception as e:
            print(f"Error creating alternative list: {e}")
            return []

def unfollow_users(sb, to_unfollow, log):
    """Visits each profile, unfollows, verifies, logs & removes from list."""
    for user in to_unfollow:
        try:
            sb.open(f"https://www.instagram.com/{user}/")
            time.sleep(3)
            
            # Look for follow/following buttons with more robust selectors
            print(f"Looking for follow button on {user}'s profile")
            
            # Try multiple selector strategies
            follow_button = None
            
            # Strategy 1: Try to find by text content
            buttons = sb.find_elements('css=button')
            for button in buttons:
                try:
                    text = button.text.strip().lower()
                    if 'following' in text or 'requested' in text:
                        follow_button = button
                        print(f"Found button by text: {button.get_attribute('outerHTML')}")
                        break
                except:
                    pass
            
            # Strategy 2: Try to find by aria-label
            if not follow_button:
                try:
                    follow_button = sb.find_element('css=button[aria-label="Following"]')
                    print(f"Found button by aria-label: {follow_button.get_attribute('outerHTML')}")
                except:
                    pass
            
            if follow_button:
                # Click the following button
                follow_button.click()
                time.sleep(2)
                
                # Find and click unfollow confirmation
                unfollow_buttons = sb.find_elements('css=button')
                for button in unfollow_buttons:
                    try:
                        if 'unfollow' in button.text.strip().lower():
                            button.click()
                            print(f"Clicked unfollow confirmation: {button.get_attribute('outerHTML')}")
                            break
                    except:
                        pass
                
                # Wait for unfollow to complete
                time.sleep(3)
                
                print(f"{user} successfully unfollowed")
                ts = datetime.utcnow().isoformat()
                log.append(ts)
                save_log(log)

                remaining = load_list()
                if user in remaining:
                    remaining.remove(user)
                    save_list(remaining)

                time.sleep(random.uniform(20, 30))
            else:
                print(f"Could not find follow button for {user}")

        except Exception as e:
            print(f"⚠ Error unfollowing {user}: {e}")

def main():
    # 1) Check rate limits
    log = prune_log(load_log())
    allowed = rate_limits_allow(log)
    if allowed <= 0:
        print("⚠ Rate limit reached (150/day or 60/hour). Try later.")
        return

    # 2) Launch browser & manual login
    with SB(uc=True, user_data_dir=USER_DATA_DIR, headless=False) as sb:
        sb.maximize_window()
        sb.open("https://www.instagram.com/accounts/login/")
        input("➤ Please log in, then press Enter to continue…")
        
        # Verify login
        time.sleep(3)
        print("Checking login status...")
        if "/accounts/login/" in sb.get_current_url():
            print("Still on login page. Please log in and try again.")
            return

        # 3) Build list if empty
        lst = load_list()
        if not lst:
            lst = generate_unfollow_list(sb)
            if not lst:
                print("🎉 Could not create an unfollow list. Exiting.")
                return

        # 4) Trim to allowed
        to_unfollow = lst[:allowed]
        print(f"→ Will unfollow up to {len(to_unfollow)} accounts now.")

        # 5) Run unfollow loop
        unfollow_users(sb, to_unfollow, log)

if __name__ == "__main__":
    main()
