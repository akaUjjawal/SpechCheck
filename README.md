# SpecCheck

A simple CLI tool I built to stop wasting hours on shopping sites. It pulls
**live products sold in India** (Flipkart, Amazon.in, Croma, Reliance Digital
and more, with rupee prices) through SerpAPI's Google Shopping engine, then
asks a free Groq LLM to **compare the options in my price range and tell me
the best one to buy** — grounded in real specs and owner reviews. Along the
way I also added a simple check that flags fake/scam listings (big-brand
name at an impossible price with zero reviews... you know the ones).

## What you need

- Python 3.10+
- A free Groq API key — https://console.groq.com/keys
- A free SerpAPI key — https://serpapi.com 

## Setup (one time)

Open a terminal inside the `speccheck` folder:

```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

Then create a `.env` file with both keys:

```
GROQ_API_KEY=your_groq_key
SERPAPI_KEY=your_serpapi_key
```

## How I use it

### 1. Scrape live products (costs 1-2 SerpAPI credits)

```bash
python main.py scrape "wireless earbuds"
python main.py scrape "gaming laptop" --site amazon     # only Amazon listings
python main.py scrape "phone under 20000" --site flipkart
```

`--site` keeps listings from a single store — I added it because mixing
Flipkart and random resellers made price comparisons inconsistent. Google
Shopping doesn't have a per-store search, so this filters by seller after
fetching (works for amazon / flipkart / croma / reliance...).

### 2. See what got scraped

```bash
python main.py list
```

Every product gets a `#` number. Suspected fakes show `[SUSPECT?]`.

### 3a. Compare one product against its price-range rivals

```bash
python main.py compare 3
python main.py compare 3 --range 50    # wider band, +/-50%
```

Finds the strongest rivals within ±25% of that product's price, pulls their
real specs and owner-review snippets (≤5 credits, **cached forever** — the
same comparison a second time costs 0), and prints a verdict table plus one
**BEST PICK** with reasons.

### 3b. Or just ask for advice

```bash
python main.py advise "earbuds for gym, good bass" 1500
python main.py advise "light laptop for college" 55k --deep
```

The budget is optional and pretty flexible — `1500`, `1,500`, `55k`, `1.5k`
all work. `--deep` also fetches real specs/reviews for the top 5 candidates
(≤5 credits, cached) so the advice is much better grounded.

## Credit usage 

| Action                       | Credits |
|------------------------------|---------|
| `scrape` (up to 60 products) | 1-2     |
| `compare` (first time)       | up to 5 |
| `compare` (repeat)           | 0       |
| `advise` (without `--deep`)  | 0       |
| `advise --deep` (first time) | up to 5 |

Product details land in `data/details/` and are never re-fetched.

## When something breaks

- **"GROQ_API_KEY is not set"** → create `.env` with your Groq key.
- **"SerpAPI key missing"** → add `SERPAPI_KEY=...` to `.env`.
- **"No scraped data yet"** → run `scrape` before `list`/`compare`/`advise`.
- **Details won't fetch / "couldn't fetch"** → Google's detail-page tokens
  expire after a while. Re-run `scrape` to get fresh ones, then retry —
  already-cached details keep working forever.
- **SerpAPI quota error** → free tier is 100 searches/month; usage is at
  https://serpapi.com/dashboard.
- **Weird recommendation?** → prices go stale; re-run `scrape`.

## Things I learned building this

- Google's immersive-product response keeps moving fields around — specs
  currently live in `about_the_product.features`, which cost me a whole
  evening of "why are my laptops coming back with no specs".
- Just sorting by star rating doesn't work — a product with 5 stars from
  2 reviews beats everything. I multiply rating by review count instead,
  so products that many people actually bought come first.
- Caching every detail-page response is the only way to survive on 100
  free searches a month.
