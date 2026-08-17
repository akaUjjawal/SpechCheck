# live_data.py
# Everything I scrape gets saved to a file on disk.
# This way I don't waste SerpAPI credits re-fetching things I already have.
# This file also handles: saving/loading the cache, fake listing detection,
# and fetching/caching per-product details.

import json
import os

import config

CACHE_FILE = config.CACHE_FILE


def save_cache(products):
    # make the data folder if it doesn't exist yet
    if not os.path.exists("data"):
        os.mkdir("data")

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        for p in products:
            f.write(json.dumps(p) + "\n")

    print("Saved " + str(len(products)) + " products to " + CACHE_FILE)


def load_live_cache():
    if not os.path.exists(CACHE_FILE):
        raise FileNotFoundError(
            'No scraped data yet. First run:  python main.py scrape "laptop"'
        )
    products = []
    with open(CACHE_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                products.append(json.loads(line))

    mark_suspects(products)
    return products


def price_of(p):
    return p.get("price_inr")


def price_label(p):
    if p.get("price_inr"):
        return "Rs." + format(int(p["price_inr"]), ",")
    return "?"


# ---------------------------------------------------------------------------
# Fake listing detector
#
# While testing I kept seeing listings like "Apple AirPods Rs.399" — clearly
# fake clones. I wanted to flag these automatically so the AI doesn't
# recommend them.
#
# I first tried computing the average price per brand from the scraped data.
# But that approach got confused if there were too many fakes already in the
# results — it would think the low price was normal. So I just hardcoded
# rough minimum prices for big brands. If something costs way less than this,
# it's almost certainly not real.
# ---------------------------------------------------------------------------

BRAND_MIN_PRICES = {
    "apple":       8000,
    "airpods":     3000,
    "iphone":     15000,
    "macbook":    40000,
    "samsung":     2000,
    "galaxy buds": 2000,
    "sony":        2000,
    "bose":        5000,
    "jbl":          800,
    "oneplus":     1500,
    "beats":       3000,
    "sennheiser":  1500,
    "nothing":     2000,
    "dell":       20000,
    "hp":         15000,
    "lenovo":     15000,
    "asus":       15000,
    "acer":       12000,
    "redmi":       5000,
    "realme":      3000,
    "oppo":        5000,
    "vivo":        5000,
    "pixel":      20000,
    "motorola":    5000,
}


def mark_suspects(products):
    for p in products:
        p["suspect"] = False
        name  = (p.get("name") or "").lower()
        price = price_of(p)

        # brand-name product with zero reviews and no rating? suspicious
        if not p.get("review_count") and not p.get("rating_stars"):
            p["suspect"] = True
            continue

        # check if this brand has a known minimum realistic price
        for brand, min_price in BRAND_MIN_PRICES.items():
            if brand in name and price and price < min_price:
                p["suspect"] = True
                break

    return products


# ---------------------------------------------------------------------------
# Per-product details cache — specs + reviews, 1 SerpAPI credit per product
# Once fetched, saved forever so repeat runs cost 0 credits
# ---------------------------------------------------------------------------

def get_details_filepath(product):
    # use product_id as filename if available, otherwise clean up the name
    if product.get("product_id"):
        filename = product["product_id"]
    else:
        # replace any character that isn't a letter or number with underscore
        # I couldn't figure out regex so I just loop through the characters
        clean_name = ""
        for char in product["name"][:60]:
            if char.isalnum() or char == " ":
                clean_name += char
            else:
                clean_name += "_"
        filename = clean_name.strip()

    return os.path.join(config.DETAILS_DIR, filename + ".json")


def get_details(product):
    path = get_details_filepath(product)

    # if we already fetched this product before, load from disk (0 credits)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # no cached copy — need to fetch it (costs 1 credit)
    token = product.get("page_token")
    if not token:
        return None  # Google didn't give a detail page for this listing

    from india_source import fetch_details

    print("  fetching details: " + product["name"][:60] + " (1 credit, cached forever)")
    try:
        details = fetch_details(token)
    except Exception as e:
        # detail page tokens go stale after a while — re-running scrape fixes it
        print("    couldn't fetch: " + str(e))
        print('    tip: re-run  python main.py scrape "..."  to get fresh tokens')
        return None

    if not os.path.exists(config.DETAILS_DIR):
        os.makedirs(config.DETAILS_DIR)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(details, f)

    return details


def describe(product, details=None):
    # Build a plain text block describing one product.
    # This is exactly what gets sent to the AI — so I include everything useful.
    lines = []
    lines.append("NAME: " + product["name"])

    price_text = "PRICE: " + price_label(product)
    if product.get("old_price_inr"):
        price_text = price_text + " (was Rs." + format(int(product["old_price_inr"]), ",") + ")"
    lines.append(price_text)

    stars   = product.get("rating_stars") or "?"
    reviews = product.get("review_count") or 0
    lines.append("RATING: " + str(stars) + " stars (" + str(reviews) + " reviews)")

    if product.get("seller"):
        lines.append("SELLER: " + product["seller"])

    if product.get("description"):
        lines.append("INFO: " + product["description"][:150])

    if product.get("suspect"):
        lines.append("WARNING: LIKELY FAKE/SCAM — brand item at suspiciously low price or zero reviews. Do NOT recommend.")

    if details:
        if details.get("specs"):
            specs_joined = " | ".join(details["specs"][:12])
            lines.append("SPECS: " + specs_joined)

        if details.get("review_snippets"):
            quoted = []
            for s in details["review_snippets"][:6]:
                quoted.append('"' + s + '"')
            lines.append("OWNER REVIEWS: " + " | ".join(quoted))

        if details.get("stores"):
            lines.append("SELLERS: " + " | ".join(details["stores"][:5]))

    return "\n".join(lines)
