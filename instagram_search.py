import pandas as pd
import time
import os
from datetime import datetime
import random
from tqdm import tqdm   # pip install tqdm

# ==================== INSTAGRAM 200 POSTS VERSION ====================

CHECKPOINT_FILE = "instagram_mahseer_checkpoint.csv"

species_hashtags = {
    "Mahseer (All Species)": ["mahseer", "deccanmahseer"]
}

location_keywords = [
    "Kerala", "Periyar", "Wayanad", "Chaliyar", "Bharathapuzha", "Pamba", "Idukki", "Palakkad",
    "Tamil Nadu", "Tamilnadu", "Cauvery", "Bhavani", "Moyar", "Amaravathi", "Tamiraparani",
    "Western Ghats", "Western Ghat", "Westernghats", "Nilgiris", "Coimbatore", "Kodaikanal"
]

def extract_locations(text):
    if not text: return []
    text_lower = text.lower()
    found = [kw for kw in location_keywords if kw.lower() in text_lower]
    return list(set(found))

# ------------------- FREE MODE: instagrapi (200 posts) -------------------
try:
    from instagrapi import Client
except ImportError:
    print("⚠️ Run: pip install instagrapi tqdm pandas")
    exit()

def fetch_instagrapi(max_posts=200):
    # Credentials
    username = os.getenv("INSTA_USERNAME") or (open("INSTA_USERNAME").read().strip() if os.path.exists("INSTA_USERNAME") else "")
    password = os.getenv("INSTA_PASSWORD") or (open("INSTA_PASSWORD").read().strip() if os.path.exists("INSTA_PASSWORD") else "")
    
    if not username or not password:
        print("❌ Create INSTA_USERNAME and INSTA_PASSWORD files in this folder")
        return []
    
    cl = Client()
    cl.delay_range = [8, 15]
    
    try:
        cl.login(username, password)
        print(f"✅ Logged in — now fetching 200 posts per hashtag")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return []
    
    records = []
    for tag in species_hashtags["Mahseer (All Species)"]:
        print(f"📥 Scraping #{tag} → max 200 posts")
        try:
            medias = cl.hashtag_medias_recent(tag, amount=max_posts)   # ← 200 at a time
            print(f"   ✅ Got {len(medias)} posts for #{tag}")
            
            for media in tqdm(medias, desc=f"Processing #{tag}"):
                caption = media.caption_text or ""
                loc_name = media.location.name if hasattr(media, 'location') and media.location else ""
                full_text = f"{caption} {loc_name}"
                
                records.append({
                    'species': 'Mahseer (All Species)',
                    'source': 'Instagram_instagrapi_Free',
                    'hashtag': tag,
                    'caption': caption[:500].replace('\n', ' ') + ('...' if len(caption) > 500 else ''),
                    'location_tag': loc_name,
                    'extracted_locations': ', '.join(extract_locations(full_text)) or 'None detected',
                    'date': media.taken_at.strftime("%Y-%m-%d") if media.taken_at else None,
                    'link': f"https://www.instagram.com/p/{media.code}/",
                    'likes': media.like_count,
                    'comments': media.comment_count
                })
            
            # Save checkpoint after each hashtag
            pd.DataFrame(records).to_csv(CHECKPOINT_FILE, mode='a', header=not os.path.exists(CHECKPOINT_FILE), index=False)
            
            time.sleep(random.uniform(15, 25))  # safe delay
            
        except Exception as e:
            print(f"⚠️ Stopped on #{tag}: {e} (normal after ~150-200 posts)")
    
    return records

# ------------------- MAIN -------------------
print("🚀 Starting Instagram → 200 posts per hashtag...\n")
data = fetch_instagrapi(max_posts=200)

if data:
    df = pd.DataFrame(data).sort_values('date', ascending=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"mahseer_instagram_200posts_{timestamp}.csv"
    df.to_csv(filename, index=False)
    print(f"\n✅ DONE! Saved {len(df)} posts to {filename}")
    print("\nPreview:")
    print(df[['hashtag', 'extracted_locations', 'location_tag']].head(10))
else:
    print("❌ No posts collected")

print("\n💡 Want more than 200? Switch to Apify paid mode (set APIFY_TOKEN) — it can do 1000+ easily.")