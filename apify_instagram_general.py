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
# COMBINE BOTH HASHTAGS
# ======================
hashtags = ["mahseer", "tamilnadu"]

# Build direct URLs (this actor works better on free tier)
direct_urls = [f"https://www.instagram.com/explore/tags/{h}/" for h in hashtags]

# ======================
# LOCATION KEYWORDS
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
# ACTOR INPUT — Use instagram-scraper (better on free tier)
# ======================
run_input = {
    "directUrls": direct_urls,
    "resultsType": "posts",
    "resultsLimit": 300,                  # ← try 300 (free tier often gives more here)
    "maxRequestRetries": 4,
    "proxyConfiguration": {"useApifyProxy": True, "groups": ["RESIDENTIAL"]}
}

print("🚀 Starting with instagram-scraper (better free-tier limit)...")
run = client.actor("apify/instagram-scraper").call(run_input=run_input)
dataset_id = run["defaultDatasetId"]
print(f"✅ Run complete → Dataset: {dataset_id}")

# ======================
# PROCESS → EXACT 10 COLUMNS
# ======================
records = []

for item in client.dataset(dataset_id).iterate_items():
    caption = item.get("caption") or ""
    location_tag = item.get("locationName") or ""
    shortcode = item.get("shortCode") or ""
    source_hashtag = item.get("sourceHashtag") or ", ".join(hashtags)

    full_text = f"{caption} {location_tag} {' '.join(item.get('hashtags', []))}"

    records.append({
        "species": "Mahseer (All Species)",
        "source": "Instagram_Apify_Scraper",
        "hashtag": source_hashtag,
        "caption": caption[:500] + ("..." if len(caption) > 500 else ""),
        "location_tag": location_tag,
        "extracted_locations": ", ".join(extract_locations(full_text)) or "None detected",
        "date": item.get("timestamp")[:10] if item.get("timestamp") else "",
        "link": f"https://www.instagram.com/p/{shortcode}/" if shortcode else "",
        "likes": item.get("likesCount") or 0,
        "comments": item.get("commentsCount") or 0
    })

# ======================
# SAVE
# ======================
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
filename = f"mahseer_tamilnadu_combined_{timestamp}.csv"

df = pd.DataFrame(records)
df.to_csv(filename, index=False)

print(f"\n✅ DONE! Saved {len(df)} posts to → {filename}")
print("Posts from #mahseer:", len(df[df['hashtag'].str.contains('mahseer', case=False)]))
print("Posts from #tamilnadu:", len(df[df['hashtag'].str.contains('tamilnadu', case=False)]))
print("Posts with Kerala/Tamil Nadu mention:", len(df[df['extracted_locations'] != 'None detected']))