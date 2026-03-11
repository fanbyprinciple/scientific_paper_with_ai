import pandas as pd
import requests
import time
import os
from datetime import datetime
import json
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  tqdm not installed → install with: pip install tqdm (for progress bars)")

# ==================== FULLY WORKING GOOGLE SCHOLAR CODE FOR MAHSEER LOCATIONS ====================
# FREE DEFAULT: scholarly library (no API key needed)
# PAID OPTION: SerpAPI (more reliable, faster, 250 free searches/month)
# Extracts titles, snippets/abstracts + LOCATION keywords (rivers, states, Western Ghats etc.)
# Saves clean CSV ready for your PowerPoint

# ------------------- 1. INSTALL (run once) -------------------
# FREE (default):
#   pip install scholarly pandas
#
# PAID (SerpAPI):
#   No extra pip if you use requests (built-in)
#   Get free API key: https://serpapi.com/ (250 searches/month free)

# ------------------- SPECIES LIST (from your slide) -------------------
species_list = [
    "Tor kudree",       # auto-corrected
    "Tor remadevii",
    "Tor malabaricus",
    "Neolissochilus wynaadensis"
]

# Additional common name / synonym queries to catch papers that don't use scientific names
additional_queries = [
    "Deccan Mahseer",
    "Humpback Mahseer",
    "blue-finned mahseer",
    "Mahseer Western Ghats",
    "Deccan mahseer distribution",
    "Tor khudree habitat",
    # Kerala & Tamil Nadu focused queries
    "Mahseer Kerala",
    "Mahseer Tamil Nadu",
    "Tor malabaricus Kerala",
    "Tor malabaricus Periyar",
    "Tor remadevii Cauvery",
    "Neolissochilus wynaadensis Kerala",
    "Mahseer Periyar river",
    "Mahseer Chalakudy river",
    "Mahseer Moyar river",
    "freshwater fish Kerala endangered",
    "freshwater fish Tamil Nadu mahseer",
]

name_map = {
    "Tor kudree": "Tor khudree",
    "Tor remadevii": "Tor remadevii",
    "Tor malabaricus": "Tor malabaricus",
    "Neolissochilus wynaadensis": "Neolissochilus wynaadensis"
}

# ------------------- LOCATION KEYWORDS (Indian rivers & places) -------------------
location_keywords = [
    # Major rivers
    "Cauvery", "Krishna", "Godavari", "Periyar", "Netravati", "Bhadra", "Tunga", "Bhima",
    "Tungabhadra", "Sharavathi", "Mullaperiyar", "Kabini", "Hemavati", "Koyna",
    "Mula", "Mutha", "Nira", "Panchganga", "Moyar", "Chalakudy", "Valapattanam",
    "Bhavani", "Amaravathi", "Kali", "Malaprabha", "Ghataprabha", "Mandovi", "Zuari",
    # Kerala rivers & water bodies
    "Chaliyar", "Bharathapuzha", "Pamba", "Achankovil", "Manimala", "Meenachil",
    "Kallada", "Kuttiadi", "Iruvazhinji", "Kabani", "Kadalundi", "Chandragiri",
    "Neyyar", "Chittar", "Thejaswini", "Uppala",
    # Tamil Nadu rivers & water bodies
    "Tamiraparani", "Vaigai", "Noyyal", "Siruvani", "Aliyar", "Parambikulam",
    "Sholayar", "Anamalai", "Kallar", "Kodaikanal", "Palani Hills",
    # Kerala districts & regions
    "Idukki", "Palakkad", "Thrissur", "Ernakulam", "Kottayam", "Pathanamthitta",
    "Thiruvananthapuram", "Kollam", "Malappuram", "Kozhikode", "Kannur", "Kasaragod",
    # Tamil Nadu districts & regions
    "Nilgiris", "Coimbatore", "Theni", "Dindigul", "Tirunelveli", "Erode",
    "Dharmapuri", "Hogenakkal", "Mettur",
    # States & other regions
    "Karnataka", "Kerala", "Maharashtra", "Tamil Nadu", "Goa", "Andhra Pradesh",
    "Wayanad", "Kodagu", "Coorg", "Satara", "Kolhapur", "Pune",
    # Sanctuaries & parks (Kerala/TN focus)
    "Parambikulam Tiger Reserve", "Silent Valley", "Eravikulam", "Periyar Tiger Reserve",
    "Chinnar", "Anamalai Tiger Reserve", "Mudumalai", "Kalakkad Mundanthurai",
    "Sathyamangalam", "Megamalai", "Topslip",
    # General habitat terms
    "Western Ghats", "Western Ghat", "Cauvery basin", "Godavari basin",
    "Krishna basin", "Mahseer habitat", "distribution", "Pambar",
    "Deccan Plateau", "Sahyadri", "riverine", "freshwater",
]

def extract_locations(text):
    if not text:
        return []
    text = text.lower()
    found = [kw for kw in location_keywords if kw.lower() in text]
    return list(set(found))  # remove duplicates

# ------------------- FREE OPTION: scholarly -------------------
try:
    from scholarly import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    print("⚠️  scholarly not installed → install with: pip install scholarly")

def fetch_scholarly(sci_name, max_results=20):
    if not SCHOLARLY_AVAILABLE:
        return []
    query = f'"{sci_name}" (distribution OR location OR habitat OR "Western Ghats" OR river OR Cauvery OR Krishna)'
    print(f"   🔍 Searching scholarly: {query}")
    
    records = []
    try:
        # Optional: use free proxies to avoid blocks (uncomment if blocked)
        # from scholarly import ProxyGenerator
        # pg = ProxyGenerator()
        # pg.FreeProxies()
        # scholarly.use_proxy(pg)
        
        search = scholarly.search_pubs(query)
        
        if TQDM_AVAILABLE:
            pbar = tqdm(total=max_results, desc="      Fetching", leave=False)
            
        i = 0
        for pub in search:
            if i >= max_results:
                break
                
            # Fill to get abstract (slow but accurate)
            try:
                filled = scholarly.fill(pub)
                abstract = filled['bib'].get('abstract', filled['bib'].get('title', ''))
                year = filled['bib'].get('pub_year')
                authors = filled['bib'].get('author', 'Unknown')
                link = filled.get('pub_url') or filled.get('eprint_url')
                pdf_link = filled.get('eprint_url')
            except Exception:
                abstract = pub.get('bib', {}).get('abstract', '')
                year = pub.get('bib', {}).get('pub_year')
                authors = pub.get('bib', {}).get('author', 'Unknown')
                link = pub.get('pub_url')
                pdf_link = None
            
            
            snippet = abstract or pub.get('bib', {}).get('title', '')
            locations = extract_locations(snippet)
            
            records.append({
                'species': sci_name,
                'source': 'Google_Scholar_Free',
                'title': pub.get('bib', {}).get('title', 'No title'),
                'year': year,
                'authors': authors,
                'snippet_abstract': snippet[:500] + '...' if len(snippet) > 500 else snippet,
                'extracted_locations': ', '.join(locations) if locations else 'None detected',
                'link': link,
                'pdf_link': pdf_link
            })
            if TQDM_AVAILABLE:
                pbar.update(1)
                
            i += 1
            time.sleep(3)  # avoid rate limit
            
        if TQDM_AVAILABLE:
            pbar.close()
            
    except Exception as e:
        print(f"   ❌ scholarly error (common): {e} → Try proxy or switch to SerpAPI")
        if TQDM_AVAILABLE and 'pbar' in locals():
            pbar.close()
            
    return records

# ------------------- PAID OPTION: SerpAPI (recommended for reliability) -------------------
def fetch_serpapi(sci_name, api_key, max_results=60):
    if not api_key:
        return []
    query = f'"{ sci_name}" (distribution OR location OR habitat OR "Western Ghats" OR river OR Cauvery OR Krishna)'
    print(f"   🔍 Searching SerpAPI: {query}")
    
    records = []
    url = "https://serpapi.com/search"
    
    if TQDM_AVAILABLE:
        # Paginates by 20, so total pages = max_results / 20
        total_pages = (max_results + 19) // 20
        pbar = tqdm(total=total_pages, desc="      Pages Fetched", leave=False)
        
    # Paginate through results (SerpAPI caps at 20 per page)
    for start in range(0, max_results, 20):
        page_size = min(20, max_results - start)
        params = {
            "engine": "google_scholar",
            "q": query,
            "hl": "en",
            "api_key": api_key,
            "num": page_size,
            "start": start
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            data = r.json()
            
            # SerpAPI returns an "error" key if the API key is invalid or credits are out
            if "error" in data:
                print(f"\n   ❌ SerpAPI Error: {data['error']}")
                break
                
            results = data.get("organic_results", [])
            
            if not results:
                break  # No more results available
            
            for result in results:
                snippet = result.get('snippet', result.get('title', ''))
                locations = extract_locations(snippet)
                
                pdf_link = None
                if 'resources' in result:
                    for res in result['resources']:
                        if res.get('file_format') == 'PDF':
                            pdf_link = res.get('link')
                            break
                
                records.append({
                    'species': sci_name,
                    'source': 'Google_Scholar_SerpAPI',
                    'title': result.get('title', 'No title'),
                    'year': result.get('year'),
                    'authors': result.get('publication_info', {}).get('authors', 'Unknown'),
                    'snippet_abstract': snippet[:500] + '...' if len(snippet) > 500 else snippet,
                    'extracted_locations': ', '.join(locations) if locations else 'None detected',
                    'link': result.get('link'),
                    'pdf_link': pdf_link
                })
            
            if TQDM_AVAILABLE:
                pbar.update(1)
                
            time.sleep(1)  # brief pause between pages
            
        except Exception as e:
            print(f"   ❌ SerpAPI error on page starting at {start}: {e}")
            break
            
    if TQDM_AVAILABLE:
        pbar.close()
        
    return records

# ------------------- MAIN EXECUTION -------------------
all_records = []
SERPAPI_KEY = ""

if os.path.exists("SERPAPI_KEY"):
    with open("SERPAPI_KEY", "r") as f:
        SERPAPI_KEY = f.read().strip()
else:
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")

seen_titles = set()  # deduplicate papers found via multiple queries

print("🚀 Starting Google Scholar location search for Mahseer...\n")
print("Mode: FREE (scholarly) by default | PAID (SerpAPI) if 'SERPAPI_KEY' file or env var is set\n")

# Build the full query list: scientific names + common/synonym names
all_queries = []
for user_name in species_list:
    sci_name = name_map.get(user_name, user_name)
    all_queries.append((user_name, sci_name))

for common_name in additional_queries:
    all_queries.append((common_name, common_name))

for user_name, query_name in all_queries:
    print(f"📍 Processing: {user_name} → {query_name}")
    
    if SERPAPI_KEY:
        data = fetch_serpapi(query_name, SERPAPI_KEY, max_results=60)
        print(f"   📊 SerpAPI records: {len(data)}")
    else:
        data = fetch_scholarly(query_name, max_results=50)
        print(f"   📊 Free scholarly records: {len(data)}")
    
    # Deduplicate by title (case-insensitive)
    for record in data:
        title_key = record['title'].strip().lower()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            all_records.append(record)
        else:
            print(f"   ⏭️  Skipping duplicate: {record['title'][:60]}...")
    
    print("-" * 50)

# ------------------- SAVE TO CSV -------------------
if all_records:
    df = pd.DataFrame(all_records)
    
    # Sort & clean
    df = df.sort_values(['species', 'year'], ascending=[True, False])
    
    print(f"\n✅ TOTAL PAPERS FOUND: {len(df)}")
    print("\nBreakdown by species:")
    print(df.groupby('species').size())
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"mahseer_scholar_locations_{timestamp}.csv"
    df.to_csv(filename, index=False)
    
    print(f"\n💾 Saved to: {filename}")
    print("\nColumns: species | source | title | year | extracted_locations | link | pdf_link")
    
    # Preview
    print("\n📋 SAMPLE (first 5 rows):")
    print(df[['species', 'source', 'title', 'extracted_locations', 'year']].head())
    
else:
    print("❌ No results. Try:")
    print("   1. pip install scholarly")
    print("   2. Set SERPAPI_KEY for paid mode")
    print("   3. Run with proxy in scholarly (see comments)")

print("\n🎉 Done!")
print("Next: Open CSV → filter 'extracted_locations' column → add GPS from GBIF/iNat code!")
print("Tip: For full PDFs, click pdf_link or use PyMuPDF to auto-extract more locations.")