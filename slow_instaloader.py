import instaloader
import pandas as pd
import time
import random
import os
from datetime import datetime

USERNAME = "aegonphd"

HASHTAGS = [
    "mahseer",
    "mahseerfishing",
    "cauveryfishing",
    "riverfishingindia",
    "tamilnadu",
    "wildfishingindia"
]

LOCATION_KEYWORDS = [
    "kerala","periyar","wayanad","cauvery","bhavani","moyar",
    "nilgiri","coimbatore","western ghats","karnataka","coorg"
]

MASTER_FILE = "MASTER_INSTAGRAM_DATASET.csv"
RAW_FILE = "RAW_INSTAGRAM_DATASET.csv"
FILTERED_FILE = "FILTERED_INSTAGRAM_DATASET.csv"

# ======================
# LOAD INSTALOADER SESSION
# ======================
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=False,
    download_comments=False,
    save_metadata=False
)

L.load_session_from_file(USERNAME)

# ======================
# LOAD OLD DATA (resume capability)
# ======================
seen = set()

if os.path.exists(MASTER_FILE):
    df_old = pd.read_csv(MASTER_FILE)
    seen = set(df_old["url"].tolist())

print(f"🔁 Loaded {len(seen)} previously collected posts")

# ======================
# AUTONOMOUS LOOP
# ======================
while True:

    random.shuffle(HASHTAGS)

    for tag in HASHTAGS:

        print(f"\n🌿 Browsing hashtag → #{tag}")

        try:
            posts = instaloader.Hashtag.from_name(L.context, tag).get_posts()

            for post in posts:

                url = f"https://instagram.com/p/{post.shortcode}/"

                if url in seen:
                    continue

                caption = post.caption or ""
                location = post.location.name if post.location else ""

                row = {
                    "hashtag": tag,
                    "caption": caption[:400],
                    "location": location,
                    "likes": post.likes,
                    "comments": post.comments,
                    "date": post.date_utc,
                    "url": url
                }

                # SAVE RAW
                pd.DataFrame([row]).to_csv(
                    RAW_FILE,
                    mode="a",
                    header=not os.path.exists(RAW_FILE),
                    index=False
                )

                text = (caption + " " + location).lower()

                if any(k in text for k in LOCATION_KEYWORDS):
                    pd.DataFrame([row]).to_csv(
                        FILTERED_FILE,
                        mode="a",
                        header=not os.path.exists(FILTERED_FILE),
                        index=False
                    )

                # SAVE MASTER
                pd.DataFrame([row]).to_csv(
                    MASTER_FILE,
                    mode="a",
                    header=not os.path.exists(MASTER_FILE),
                    index=False
                )

                seen.add(url)

                print("✅ Collected:", url)

                # ⭐ HUMAN DELAY
                delay = random.randint(8, 15)
                print(f"Sleeping {delay} sec")
                time.sleep(delay)

                break   # collect only 1 post per hashtag visit

        except Exception as e:
            print("⚠️ Block detected:", e)
            cooldown = random.randint(300, 600)
            print(f"Cooling down {cooldown/60:.1f} minutes")
            time.sleep(cooldown)

    # LONG HUMAN REST CYCLE
    long_rest = random.randint(900, 1800)
    print(f"\n😴 Cycle complete → resting {long_rest/60:.1f} minutes\n")
    time.sleep(long_rest)