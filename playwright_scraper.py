import time
import random
import os
import pandas as pd
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

# ================= CONFIG =================
HASHTAG = "mahseer"
OUTPUT_FILE = "mahseer_master_dataset.csv"
MEMORY_FILE = "scanned_posts.txt"
SESSION_DIR = "./insta_session"
POSTS_PER_BATCH = 50
TOTAL_TARGET = 1000

KERALA_KEYWORDS = ["kerala", "periyar", "wayanad", "idukki", "pamba", "bharathapuzha", "chaliyar", "palakkad"]
TN_KEYWORDS = ["tamil nadu", "tamilnadu", "cauvery", "kaveri", "bhavani", "moyar", "coimbatore", "nilgiri", "hogenakkal"]

# ================= MAHSEER SPECIES DETECTION =================
MAHSEER_PATTERNS = [
    (r"tor\s*remadevii|remadevii|humpback|hump-backed|orange[- ]*fin|orange fin|orange-finned", "Humpback Mahseer (Tor remadevii)"),
    (r"tor\s*khudree|khudree|deccan|blue[- ]*fin|blue fin|blue-finned|black[- ]*fin|black fin|black-finned", "Deccan Mahseer (Tor khudree)"),
    (r"tor\s*malabaricus|malabaricus|malabar|wayanad|neolissochilus\s*wynaadensis|wynaadensis", "Malabar / Wayanad Mahseer (Tor malabaricus / Neolissochilus wynaadensis)"),
    (r"tor\s*remadeviae", "Orange-finned Mahseer (Tor remadeviae)"),
    (r"tor\s*mosal|mosal|copper", "Copper Mahseer (Tor mosal)"),
    (r"golden|putitora", "Golden Mahseer (Tor putitora)"),
    (r"tor\s*tor|red[- ]*fin|red fin", "Red-finned Mahseer (Tor tor)"),
    (r"tor\s*mussullah|mussullah", "Tor mussullah (legacy / misapplied name)"),
    (r"cauvery|kaveri|mahseer\s+and\s+cauvery|mahaseer\s+and\s+cauvery|mohshir\s+and\s+cauvery|mahseer\s+and\s+kaveri|mohshir\s+and\s+kaveri|cauvery\s+mahseer", "Cauvery Mahseer"),
    (r"true\s*mahseer", "True Mahseer"),
    (r"mahseer", "Mahseer (unspecified)"),
]

def detect_mahseer_type(text: str) -> str:
    if not text:
        return "Unspecified"
    t = text.lower()
    for pattern, label in MAHSEER_PATTERNS:
        if re.search(pattern, t):
            return label
    return "Mahseer (unspecified)"

def extract_hashtags(caption: str) -> str:
    if not caption:
        return ""
    return ", ".join(re.findall(r'#(\w+)', caption))

# ================= HUMAN BEHAVIOR =================
def human_delay(min_s=4.0, max_s=10.0):
    time.sleep(random.uniform(min_s, max_s))

def human_move_and_click(page, selector):
    try:
        element = page.locator(selector).first
        box = element.bounding_box()
        if box:
            page.mouse.move(
                box['x'] + box['width'] / 2 + random.randint(-8, 8),
                box['y'] + box['height'] / 2 + random.randint(-8, 8),
                steps=random.randint(12, 25)
            )
            human_delay(0.6, 1.8)
            element.click()
            return True
    except:
        return False

def apply_manual_stealth(page):
    stealth_js = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
    """
    page.add_init_script(stealth_js)

# ================= DATA UTILS =================
def extract_shortcode(href: str) -> str | None:
    match = re.search(r'/p/([A-Za-z0-9_-]+)', href)
    return match.group(1) if match else None

def detect_geo(text: str):
    t = text.lower()
    k = any(x in t for x in KERALA_KEYWORDS)
    tn = any(x in t for x in TN_KEYWORDS)
    if k and tn: return "Yes", "Both", "Medium"
    elif k: return "Yes", "Kerala", "High"
    elif tn: return "Yes", "Tamil Nadu", "High"
    return "No", "Unknown", "Low"

def load_memory() -> set:
    if not os.path.exists(MEMORY_FILE):
        return set()
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

# ================= CORE SCRAPE FUNCTION =================
def run_scrape_session(page, target_count: int, scanned: set):
    scraped_this_session = 0

    print(f"🎣 At explore/tags/{HASHTAG}/ — resuming scroll...")

    while scraped_this_session < target_count:
        post_links = page.locator("a[href*='/p/']").all()
        random.shuffle(post_links)

        skipped = 0
        for post in post_links:
            try:
                href = post.get_attribute("href")
                shortcode = extract_shortcode(href)

                if not shortcode or shortcode in scanned:
                    skipped += 1
                    continue

                post.scroll_into_view_if_needed()
                human_delay(1.2, 3.5)
                human_move_and_click(page, f"a[href='{href}']")
                human_delay(5, 10)

                caption = ""
                for sel in [
                    "article h1",
                    "div._a9zs span",
                    "h1._ap3a",
                    "span._aacl._aaco._aacu._aacx._aad6._aade"
                ]:
                    try:
                        caption = page.locator(sel).first.inner_text(timeout=5000)
                        if caption.strip():
                            break
                    except:
                        continue

                loc_tag = ""
                try:
                    loc_tag = page.locator("a[href*='/explore/locations/']").first.inner_text(timeout=4000)
                except:
                    pass

                username = ""
                try:
                    username = page.locator("header a[href^='/'][role='link']").first.inner_text(timeout=4000).strip()
                except:
                    pass

                post_date = ""
                try:
                    dt_str = page.locator("time").first.get_attribute("datetime", timeout=4000)
                    if dt_str:
                        post_date = datetime.fromisoformat(dt_str.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
                except:
                    pass

                likes = ""
                try:
                    likes_el = page.get_by_text(re.compile(r"\d+[\s,]*like", re.I)).first
                    if likes_el:
                        likes = likes_el.inner_text().strip()
                except:
                    pass

                comments = ""
                try:
                    comm_el = page.get_by_text(re.compile(r"\d+[\s,]*comment", re.I)).first
                    if comm_el:
                        comments = comm_el.inner_text().strip()
                except:
                    pass

                is_video = page.locator("video").count() > 0

                hashtags_str = extract_hashtags(caption)
                mahseer_type = detect_mahseer_type(f"{caption} {loc_tag}")
                geo_detected, state, conf = detect_geo(f"{caption} {loc_tag}")

                row = {
                    "species": "Mahseer",
                    "mahseer_type": mahseer_type,
                    "username": username,
                    "post_date": post_date,
                    "caption": caption[:700].replace('\n', ' ') if caption else "",
                    "location_tag": loc_tag,
                    "geo_state": state,
                    "geo_confidence": conf,
                    "hashtags": hashtags_str,
                    "is_video": is_video,
                    "likes": likes,
                    "comments": comments,
                    "link": f"https://www.instagram.com/p/{shortcode}/",
                    "scrape_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                pd.DataFrame([row]).to_csv(
                    OUTPUT_FILE,
                    mode="a",
                    index=False,
                    header=not os.path.exists(OUTPUT_FILE),
                    encoding="utf-8"
                )

                with open(MEMORY_FILE, "a", encoding="utf-8") as f:
                    f.write(shortcode + "\n")
                scanned.add(shortcode)

                scraped_this_session += 1
                print(f"    Saved: {mahseer_type} | @{username} | {state} | total: {len(scanned)}")

                page.keyboard.press("Escape")
                human_delay(3.5, 8)

            except Exception as e:
                if shortcode:
                    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
                        f.write(shortcode + "\n")
                    scanned.add(shortcode)
                try:
                    page.keyboard.press("Escape")
                except:
                    pass
                human_delay(1, 3)
                continue

            if scraped_this_session >= target_count:
                break

        for _ in range(random.randint(4, 9)):
            page.mouse.wheel(0, random.randint(600, 1100))
            time.sleep(random.uniform(0.7, 2.0))

        human_delay(6, 14)
        print(f"  Skipped already seen posts this view: {skipped}")

# ================= MAIN =================
def main():
    scanned = load_memory()
    total_collected = len(scanned)

    print(f"\n{'='*60}")
    print(f"  Mahseer scraper resume — already have {total_collected} unique posts")
    print(f"  Target: {TOTAL_TARGET}    Batch size: {POSTS_PER_BATCH}")
    print(f"{'='*60}\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            SESSION_DIR,
            headless=False,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800},
            ignore_https_errors=True,
            bypass_csp=True
        )
        page = context.pages[0] if context.pages else context.new_page()
        apply_manual_stealth(page)

        # ── Improved navigation with retries ──
        print("Navigating to explore page...")
        max_retries = 3
        loaded = False

        for attempt in range(1, max_retries + 1):
            try:
                print(f"  Attempt {attempt}/{max_retries}...")
                page.goto(
                    f"https://www.instagram.com/explore/tags/{HASHTAG}/",
                    wait_until="domcontentloaded",
                    timeout=90000
                )
                human_delay(4, 9)

                print("  Waiting for post grid to appear...")
                page.wait_for_selector(
                    "a[href*='/p/']",
                    state="visible",
                    timeout=45000
                )
                print("  Explore grid loaded successfully!")
                loaded = True
                break

            except Exception as e:
                print(f"  Attempt {attempt} failed: {str(e)[:120]}...")
                if attempt < max_retries:
                    human_delay(15, 40)
                else:
                    print("\n⚠️ All retries failed.")
                    print("   Browser remains open. Suggestions:")
                    print("   • Manually log in to Instagram if prompted")
                    print("   • Scroll a little or interact with the page")
                    print("   • Then restart the script (it will reuse the session)")
                    raise

        if not loaded:
            raise Exception("Failed to load explore page after retries")

        try:
            while total_collected < TOTAL_TARGET:
                print(f"\n--- Starting new batch — {total_collected} collected so far ---")
                run_scrape_session(page, POSTS_PER_BATCH, scanned)
                total_collected += POSTS_PER_BATCH

                if total_collected < TOTAL_TARGET:
                    break_seconds = random.randint(600, 1500)  # 10–25 minutes
                    break_minutes = break_seconds // 60
                    print(f"\n{'─'*60}")
                    print(f"  💤 LONG BREAK: ≈ {break_minutes} minutes")
                    print(f"  → Feel free to use the browser now")
                    print(f"  → Script will continue automatically after break")
                    print(f"  → Or press Ctrl+C to stop early")
                    print(f"{'─'*60}\n")
                    time.sleep(break_seconds)

        except KeyboardInterrupt:
            print("\n\n🛑 Ctrl+C detected — graceful shutdown")
            print(f"   → Saved {len(scanned)} posts so far")
            print("   → Restart anytime to continue")
        except Exception as e:
            print(f"\n⚠️ Unexpected error: {e}")
            print("→ Session preserved. Restart to resume.")
        finally:
            print(f"\nSession finished. Total unique posts collected: {len(scanned)}")
            # context.close()  # Keep commented to allow resume

if __name__ == "__main__":
    main()