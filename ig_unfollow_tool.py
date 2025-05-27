import os, re, time, json, random
from datetime import datetime, timedelta
from typing import Optional, List, Set

from selenium.webdriver.common.keys import Keys
from seleniumbase import SB

# ── CONFIG ───────────────────────────────────────────────────────
LOGIN_USER  = "testsale2134@gmail.com"
LOGIN_PASS  = "2105264@tT"
IG_HANDLE   = "muhammad_talal21054"       # your IG username (no @)

USER_DATA   = os.path.abspath("chromedata1")
UNFOLLOW_TXT = "unfollow_list.txt"
LOG_JSON     = "unfollow_log.json"

MAX24 = 150
MAX1H = 60
# ─────────────────────────────────────────────────────────────────


def load_list() -> List[str]:
    return [u.strip() for u in open(UNFOLLOW_TXT, encoding="utf-8")] \
           if os.path.exists(UNFOLLOW_TXT) else []

def save_list(lst: List[str]) -> None:
    with open(UNFOLLOW_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lst))

def load_log() -> List[str]:
    return json.load(open(LOG_JSON)) if os.path.exists(LOG_JSON) else []

def save_log(log: List[str]) -> None:
    json.dump(log, open(LOG_JSON, "w"))

def prune_log(log: List[str]) -> List[str]:
    now = datetime.utcnow()
    return [ts for ts in log if now - datetime.fromisoformat(ts) <= timedelta(days=1)]

def rate_limits_allow(log: List[str]) -> int:
    now    = datetime.utcnow()
    last24 = prune_log(log)
    last1  = [ts for ts in last24 if now - datetime.fromisoformat(ts) <= timedelta(hours=1)]
    return max(0, min(MAX24 - len(last24), MAX1H - len(last1)))


# ── "1 follower", "42 following" → int ──────────────────────────────
digit_re = re.compile(r'(\d[\d,]*)')
def read_counter(sb, xpath: str) -> int:
    text = (sb.get_text(xpath) or "0").strip()
    m = digit_re.search(text)
    return int(m.group(1).replace(",", "")) if m else 0


# ── Improved usernames extraction - filters out suggestions better ───────────
# ── Username extraction (robust) ──────────────────────────────
def extract_usernames_from_dialog(sb) -> Set[str]:
    js = f"""
      const dlg = document.querySelector('div[role="dialog"]');
      if (!dlg) return [];

      const users = new Set();
      dlg.querySelectorAll('a[href^="/"]').forEach(a => {{
          /* /user/ or /user/?next=… → keep first segment */
          const m = a.getAttribute('href').match(/^\\/([^\\/\\?]+)[\\/\\?]/);
          if (!m) return;
          const uname = m[1].toLowerCase();

          /* skip your own handle */
          if (uname === "{IG_HANDLE.lower()}") return;

          const row = a.closest('div');
          if (!row) return;

          /* 1️⃣  suggestion header */
          if (row.innerText.toLowerCase().includes('suggested for you')) return;

          /* 2️⃣  suggestion button */
          const btn = row.querySelector('button');
          if (btn) {{
              const t = btn.innerText.toLowerCase();
              if (t === 'follow' || t === 'follow back') return;
          }}

          users.add(uname);
      }});
      return Array.from(users);
    """
    return set(sb.execute_script(js))


# ── Smart scroll (deepest pane) ───────────────────────────────
def smart_scroll_dialog(sb, hard_timeout: int = 120) -> Set[str]:
    t0         = time.time()
    users      = extract_usernames_from_dialog(sb)
    stagnation = 0

    while True:
        # find the DEEPEST scrollable pane
        at_bottom = sb.execute_script("""
            const dlg = document.querySelector('div[role="dialog"]');
            if (!dlg) return true;

            let panes = [...dlg.querySelectorAll('div')]
                          .filter(el => el.scrollHeight > el.clientHeight);
            if (!panes.length) return true;

            /* deepest = not ancestor of any other pane */
            panes = panes.filter(p => !panes.some(o => o !== p && o.contains(p)));

            const pane = panes[0];
            const nearBottom = Math.abs(
                  pane.scrollHeight - pane.scrollTop - pane.clientHeight) < 2;
            pane.scrollTop += pane.clientHeight;   // one viewport
            return nearBottom;
        """)

        time.sleep(1.4)
        new_users = extract_usernames_from_dialog(sb)

        stagnation = stagnation + 1 if len(new_users) == len(users) else 0
        users      = new_users

        if stagnation >= 4:           break
        if at_bottom and stagnation>=2: break
        if time.time() - t0 > hard_timeout: break

    return users

# ── Build unfollow list ─────────────────────────────────────────────
def generate_unfollow_list(sb) -> List[str]:
    sb.open(f"https://www.instagram.com/{IG_HANDLE}/"); time.sleep(3)

    # -------- Followers ----------
    foll = f"//a[@href='/{IG_HANDLE}/followers/']"
    sb.wait_for_element(foll, timeout=15)
    exp_foll = read_counter(sb, foll)
    print(f"Expected followers count: {exp_foll}")
    sb.click(foll); time.sleep(2)
    followers = smart_scroll_dialog(sb)
    print(f"Extracted {len(followers)} followers (expected {exp_foll})")
    sb.send_keys("body", Keys.ESCAPE); time.sleep(1)

    # -------- Following ----------
    folg = f"//a[@href='/{IG_HANDLE}/following/']"
    sb.wait_for_element(folg, timeout=15)
    exp_folg = read_counter(sb, folg)
    print(f"Expected following count: {exp_folg}")
    sb.click(folg); time.sleep(2)
    following = smart_scroll_dialog(sb)
    print(f"Extracted {len(following)} following (expected {exp_folg})")
    sb.send_keys("body", Keys.ESCAPE); time.sleep(1)

    nonfollowers = sorted(following - followers)
    save_list(nonfollowers)
    print(f"→ Found {len(nonfollowers)} non-followers.")
    return nonfollowers


# ── Unfollow loop ───────────────────────────────────────────────────
def unfollow_users(sb, queue: List[str], log: List[str]) -> None:
    for user in queue:
        try:
            sb.open(f"https://www.instagram.com/{user}/")
            sb.wait_for_element('//button[contains(.,"Following")]', timeout=15)
            sb.click('//button[contains(.,"Following")]')
            sb.wait_for_element('//button[text()="Unfollow"]', timeout=8)
            sb.click('//button[text()="Unfollow"]')
            sb.wait_for_element('//button[text()="Follow"]',   timeout=15)
            print(f"{user} successfully unfollowed")

            log.append(datetime.utcnow().isoformat()); save_log(log)
            remaining = load_list()
            if user in remaining: remaining.remove(user); save_list(remaining)

            time.sleep(random.uniform(20, 30))
        except Exception as e:
            print(f"⚠ Error unfollowing {user}: {e}")


def main() -> None:
    log     = prune_log(load_log())
    allowed = rate_limits_allow(log)
    if allowed == 0:
        print("⚠ Rate-limit reached. Try again later."); return

    with SB(uc=True, user_data_dir=USER_DATA, headless=False) as sb:
        sb.maximize_window()
        sb.open("https://www.instagram.com/accounts/login/")
        input("➤ Log in, then press Enter…")

        todo = load_list() or generate_unfollow_list(sb)
        if not todo:
            print("🎉 No non-followers found. Exiting."); return

        queue = todo[:allowed]
        print(f"→ Will unfollow up to {len(queue)} accounts now.")
        unfollow_users(sb, queue, log)


if __name__ == "__main__":
    main()