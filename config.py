# config.py
# I put all settings in one file so I don't have to search through
# every file when I want to change a number.

# Which Groq model to use — this one is free and fast enough
GROQ_MODEL = "llama-3.3-70b-versatile"

# SerpAPI free tier only gives 100 searches a month.
# I burned through half of them in the first day of testing,
# so I added limits to stop that from happening again.
MAX_DETAIL_FETCHES = 5   # max product detail pages to fetch per run
COMPARE_RIVALS = 4       # how many rival products to compare against
BAND_PCT = 25            # price range for compare: +/- 25% by default
MAX_PAGES = 3            # max pages to scrape (each page = 1 credit)

# Where I save scraped data so I don't have to re-fetch it
CACHE_FILE = "data/live_products.jsonl"
DETAILS_DIR = "data/details"
