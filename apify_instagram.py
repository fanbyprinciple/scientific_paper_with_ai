import time
import pandas as pd
from apify_client import ApifyClient
from datetime import datetime

# ======================
# TOKEN
# ======================
with open("apify_api.txt", "r") as f:
    token = f.read().strip()

client = ApifyClient(token)

# ======================
# COMBINE TWO HASHTAGS HERE
# ======================
hashtags = ["mahseer", "tamilnadu"]   # ← Change to ["mahseer", "tamilnadu", "kerala"] if you want 3

# ======================
# LOCATION KEYWORDS (your old filter)
# ======================
location_keywords = [
    "Kerala", "Periyar", "Wayanad", "Chaliyar", "Bharathapuzha", "Pamba", "Idukki", "Palakkad",
    "Tamil Nadu", "Tamilnadu", "Cauvery", "Bhavani", "Moyar", "Amaravathi", "Tamiraparani",
    "Western Ghats", "Western Ghat", "Westernghats", "Nilgiris", "Coimbatore", "Kodaikanal",
    "Coorg", "Karnataka"
]

def extract_locations(text):
    if not text: return []
    text_lower = text.lower()
    found = [kw for kw in location_keywords if kw.lower() in text_lower]
    return list(set(found))

# ======================
# ACTOR INPUT (one run, two hashtags)
# ======================
run_input = {
    "hashtags": hashtags,
    "resultsType": "posts",
    "resultsLimit": 400,                  # ← 400 per hashtag = ~800 total (cheap!)
    "maxRequestRetries": 4,
    "proxyConfiguration": {
        "useApifyProxy": True,
        "groups": ["RESIDENTIAL"]
    }
}

print(f"🚀 Starting ONE run for hashtags: {hashtags}")
run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
dataset_id = run["defaultDatasetId"]
print(f"✅ Run complete → Dataset: {dataset_id}")

# ======================
# PROCESS → EXACT 10 COLUMNS YOU WANTED
# ======================
records = []

for item in client.dataset(dataset_id).iterate_items():
    caption = item.get("caption") or ""
    location_tag = item.get("locationName") or ""
    shortcode = item.get("shortCode") or ""
    hashtags_list = " ".join(item.get("hashtags") or [])

    full_text = f"{caption} {location_tag} {hashtags_list}"

    records.append({
        "species": "Mahseer (All Species)",
        "source": "Instagram_Apify_HashtagScraper",
        "hashtag": item.get("sourceHashtag") or ", ".join(hashtags),   # shows which hashtag it came from
        "caption": caption[:500] + ("..." if len(caption) > 500 else ""),
        "location_tag": location_tag,
        "extracted_locations": ", ".join(extract_locations(full_text)) or "None detected",
        "date": item.get("timestamp")[:10] if item.get("timestamp") else "",
        "link": f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
        "likes": item.get("likesCount") or 0,
        "comments": item.get("commentsCount") or 0
    })

# ======================
# SAVE CSV (exact columns you showed)
# ======================
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
filename = f"mahseer_tamilnadu_combined_{timestamp}.csv"

df = pd.DataFrame(records)
df.to_csv(filename, index=False)

print(f"\n✅ DONE! Saved {len(df)} posts to → {filename}")
print("Columns: species | source | hashtag | caption | location_tag | extracted_locations | date | link | likes | comments")
print(f"\nPosts from #mahseer: {len(df[df['hashtag'].str.contains('mahseer', case=False)])}")
print(f"Posts from #tamilnadu: {len(df[df['hashtag'].str.contains('tamilnadu', case=False)])}")
print(f"Posts with Kerala/Tamil Nadu mention: {len(df[df['extracted_locations'] != 'None detected'])}")

print("\nOpen the CSV in Excel — it will look exactly like your screenshot!")