# india_source.py
# All my SerpAPI calls are in this file.
# I use two of their endpoints:
#   1) google_shopping          — gives live Indian product listings with rupee prices
#   2) google_immersive_product — gives one product's detail page (specs + reviews)
#
# The detail page costs 1 credit per product, so live_data.py saves whatever
# it returns to a file and never asks for it again.

import os

import requests

import config

SEARCH_URL = "https://serpapi.com/search.json"
PAGE_SIZE = 100


def get_api_key():
    key = os.getenv("SERPAPI_KEY", "")
    key = key.strip()
    if not key:
        print("Error: SerpAPI key missing.")
        print("1. Make a free account at https://serpapi.com (100 searches/month free)")
        print("2. Add SERPAPI_KEY=your_key to your .env file")
        raise Exception("SERPAPI_KEY not set")
    return key


def make_request(params):
    # send the API request and return the JSON response
    response = requests.get(SEARCH_URL, params=params, timeout=40)
    response.raise_for_status()   # this throws an error if the HTTP status is bad
    data = response.json()
    if data.get("error"):
        raise Exception("SerpAPI returned an error: " + str(data["error"]))
    return data


def map_item(item, query):
    # Take one result from Google Shopping and pull out only the fields I need.
    # I build a short description from whatever extra info Google gives.
    description_parts = []
    if item.get("source"):
        description_parts.append("Sold by: " + item["source"])
    if item.get("delivery"):
        description_parts.append(item["delivery"])
    if item.get("snippet"):
        description_parts.append(item["snippet"])

    description = " | ".join(description_parts)

    return {
        "category":    query,
        "name":        item.get("title") or "?",
        "price_inr":   item.get("extracted_price"),
        "old_price_inr": item.get("extracted_old_price"),
        "seller":      item.get("source"),
        "description": description,
        "rating_stars": item.get("rating"),
        "review_count": item.get("reviews"),
        "url":         item.get("product_link") or item.get("link"),
        "product_id":  item.get("product_id"),
        "page_token":  item.get("immersive_product_page_token"),
        "thumbnail":   item.get("thumbnail"),
    }


def fetch_india(query, max_products=60, site=None):
    # Fetch live product listings from Google Shopping for the Indian market.
    # gl=in and google.co.in are what make prices come back in rupees.
    # I added --site filtering because mixing Amazon and random resellers
    # made price comparisons inconsistent. Google Shopping doesn't let you
    # filter by store directly, so I filter the results after fetching.
    key = get_api_key()
    items = []
    page  = 0

    while len(items) < max_products and page < config.MAX_PAGES:
        data = make_request({
            "engine":        "google_shopping",
            "q":             query,
            "gl":            "in",
            "hl":            "en",
            "google_domain": "google.co.in",
            "start":         page * PAGE_SIZE,
            "api_key":       key,
        })

        batch = data.get("shopping_results") or []
        if not batch:
            break

        for item in batch:
            p = map_item(item, query)
            # if user asked for a specific store, skip everything else
            if site:
                seller = p.get("seller") or ""
                if site.lower() not in seller.lower():
                    continue
            items.append(p)

        print("  got " + str(len(items)) + " listings so far ...")
        page += 1

        if len(batch) < PAGE_SIZE:
            break  # Google ran out of results

    items = items[:max_products]

    if site:
        print("Google Shopping (India): " + str(len(items)) + " live listings from " + site + " for '" + query + "'")
    else:
        print("Google Shopping (India): " + str(len(items)) + " live listings for '" + query + "'")

    return items


# ---------------------------------------------------------------------------
# Product details — specs + review snippets, costs 1 credit per product
# ---------------------------------------------------------------------------

def parse_details(product_data):
    # Pull out specs, reviews, and store listings from Google's detail response.
    #
    # Google keeps changing where it puts the specs in the JSON.
    # I spent an evening trying to figure out why my laptop searches came back
    # with zero specs — the AI was basically just guessing from the name.
    # Eventually I found that in 2025/2026 specs are almost always in:
    #   product_data["about_the_product"]["features"]
    # So I check that first, and then one backup location.

    specs    = []
    reviews  = []
    stores   = []

    # --- specs ---
    about = product_data.get("about_the_product") or {}

    if about.get("description"):
        specs.append(about["description"][:300])

    features = about.get("features") or []
    for feature in features:
        if isinstance(feature, dict):
            title = feature.get("title") or ""
            value = feature.get("value") or ""
            if title and value:
                specs.append(title + ": " + value)
            elif title:
                specs.append(title)
        elif isinstance(feature, str):
            specs.append(feature)

    # backup: some older responses put specs here instead
    if not specs:
        highlights = product_data.get("highlights") or []
        for h in highlights:
            if isinstance(h, str):
                specs.append(h)

    # --- reviews ---
    # I just check the two most common spots Google uses for review text.
    # I removed the recursive search because it was hard to explain and
    # also sometimes picked up random strings that weren't actual reviews.
    reviews_section = product_data.get("user_reviews") or product_data.get("reviews_results") or []
    if isinstance(reviews_section, list):
        for review in reviews_section[:12]:
            if isinstance(review, str) and len(review) > 15:
                reviews.append(review)
            elif isinstance(review, dict):
                text = review.get("text") or review.get("snippet") or review.get("body") or ""
                if text and len(text) > 15:
                    reviews.append(text[:300])

    # --- stores ---
    sellers_section = product_data.get("stores") or product_data.get("online_sellers") or []
    for seller in sellers_section[:8]:
        if isinstance(seller, dict):
            name  = seller.get("name") or seller.get("source") or "?"
            price = seller.get("price") or seller.get("total_price") or ""
            stores.append(name + " " + str(price))

    return {
        "specs":            specs[:25],
        "review_snippets":  reviews[:12],
        "stores":           stores[:8],
    }


def fetch_details(page_token):
    # costs 1 SerpAPI credit — live_data.get_details() saves the result so this
    # is only ever called once per product
    data = make_request({
        "engine":     "google_immersive_product",
        "page_token": page_token,
        "api_key":    get_api_key(),
    })
    product_data = data.get("product_results") or data
    return parse_details(product_data)
