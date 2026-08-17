# advisor.py
# The "just tell me what to buy" command.
# I send the scraped products to the Groq AI and ask it to pick the best ones.

import os

from groq import Groq

import config
from live_data import describe, get_details, load_live_cache, price_of


def ask_llm(system_message, user_message):
    # I tried LangChain first but it had too many layers to understand —
    # prompts, chains, output parsers. The Groq Python library does the same
    # thing much more simply: create a client, send messages, get text back.
    api_key = os.getenv("GROQ_API_KEY")
    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        temperature=0.2,   # low = more focused answers, less random
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user",   "content": user_message}
        ]
    )
    return response.choices[0].message.content


def get_popularity_score(p):
    # I want products that are both well-rated AND have many reviews.
    # At first I just sorted by star rating. A product with 5 stars but only
    # 2 reviews kept coming out on top — that felt wrong. 2 people can't
    # really tell me if a product is good.
    # So I multiply stars by review count. 4.2 stars from 800 reviews = 3360.
    # 5 stars from 2 reviews = 10. Now products that many people actually
    # bought and reviewed come first.
    stars = 0
    reviews = 0
    if p.get("rating_stars"):
        stars = p["rating_stars"]
    if p.get("review_count"):
        reviews = p["review_count"]
    return stars * reviews


def sort_by_popularity(products):
    # make a copy so we don't change the original list
    sorted_list = list(products)
    sorted_list.sort(key=get_popularity_score, reverse=True)
    return sorted_list


# The instructions I give to the AI — kept simple and direct
ADVISE_PROMPT = """You are a helpful shopping assistant for the Indian market.
I will give you a list of products scraped from Indian shopping sites with prices in rupees.
Recommend the 3 best products for my need.
For each one, tell me why it's good and what the trade-offs are.
If a product says WARNING: LIKELY FAKE, warn me about it but do not recommend it.
If nothing fits my budget well, just say so honestly."""


def advise(need, budget=None, deep=False):
    products = load_live_cache()

    # filter by budget if the user gave one
    if budget:
        in_budget = []
        for p in products:
            price = price_of(p)
            if price and price <= budget:
                in_budget.append(p)
        products = in_budget

    if not products:
        return "No products found in that budget. Try a higher amount or run scrape again."

    products = sort_by_popularity(products)

    # --deep: fetch real specs and reviews for the top products
    # costs up to 5 SerpAPI credits but the AI advice is much better with real specs
    details = {}
    if deep:
        count = 0
        for p in products:
            if p.get("suspect"):
                continue
            if count >= config.MAX_DETAIL_FETCHES:
                break
            d = get_details(p)
            if d:
                details[p["name"]] = d
            count += 1

    # build one big text block with all products to send to the AI
    all_descriptions = []
    for p in products[:60]:
        product_details = None
        if p["name"] in details:
            product_details = details[p["name"]]
        all_descriptions.append(describe(p, product_details))

    listing_text = "\n\n".join(all_descriptions)

    if budget:
        budget_text = "Rs." + format(int(budget), ",")
    else:
        budget_text = "not specified"

    user_message = "My need: " + need + "\nBudget: " + budget_text + "\n\nProducts:\n" + listing_text

    return ask_llm(ADVISE_PROMPT, user_message)
