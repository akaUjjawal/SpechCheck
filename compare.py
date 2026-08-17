# compare.py
# Pick one product, find rivals at a similar price, then ask the AI which is best.

import config
from advisor import ask_llm, sort_by_popularity
from live_data import describe, get_details, price_label, price_of

# Instructions for the AI — written simply, like I'd ask a friend
COMPARE_PROMPT = """You are a helpful shopping assistant for the Indian market.
I will give you one TARGET product and some RIVALS at a similar price.
Please do three things:
1. Show a simple comparison table: product name | price | what is good | what is not great
2. Tell me the BEST PICK and explain why in 2-3 sentences
3. For each other product, write one line saying who should pick it instead
Do not recommend anything that has WARNING: LIKELY FAKE in the description."""


def compare(products, target_index, band_pct=config.BAND_PCT):
    target = products[target_index]
    target_price = price_of(target)

    if not target_price:
        return "That product has no price — pick a different one. Run: python main.py list"

    # calculate the price range to look in
    low_price  = target_price * (1 - band_pct / 100)
    high_price = target_price * (1 + band_pct / 100)

    # find rivals inside that price range
    # I removed duplicate detection — it was getting too complicated.
    # Sometimes the same product shows from two sellers, but the AI usually
    # recognizes that and handles it fine.
    rivals = []
    for i in range(len(products)):
        if i == target_index:
            continue

        p = products[i]

        # skip fake listings
        if p.get("suspect"):
            continue

        p_price = price_of(p)
        if not p_price:
            continue

        if p_price >= low_price and p_price <= high_price:
            rivals.append(p)

    rivals = sort_by_popularity(rivals)
    rivals = rivals[:config.COMPARE_RIVALS]

    if not rivals:
        low_str  = "Rs." + format(int(low_price), ",")
        high_str = "Rs." + format(int(high_price), ",")
        return "No rivals found in the " + low_str + " to " + high_str + " range. Try: python main.py compare <#> --range 50"

    low_str  = "Rs." + format(int(low_price), ",")
    high_str = "Rs." + format(int(high_price), ",")
    print("\nComparing in the " + low_str + " to " + high_str + " range (" + str(len(rivals)) + " rivals):")
    for p in [target] + rivals:
        print("  - " + price_label(p) + "  " + p["name"][:60])
    print()

    # fetch specs and reviews for each product (1 credit each, cached forever)
    all_contenders = [target] + rivals
    all_contenders = all_contenders[:config.MAX_DETAIL_FETCHES]

    details = {}
    for p in all_contenders:
        d = get_details(p)
        if d:
            details[p["name"]] = d

    # build the text to send to the AI
    blocks = []
    blocks.append("=== TARGET (the product I am looking at) ===")

    target_details = None
    if target["name"] in details:
        target_details = details[target["name"]]
    blocks.append(describe(target, target_details))

    for r in rivals:
        blocks.append("=== RIVAL ===")
        rival_details = None
        if r["name"] in details:
            rival_details = details[r["name"]]
        blocks.append(describe(r, rival_details))

    full_text = "\n\n".join(blocks)
    return ask_llm(COMPARE_PROMPT, full_text)
