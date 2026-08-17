# main.py
# SpecCheck — my live shopping advisor for the Indian market.
#
# Commands:
#   python main.py scrape "gaming laptop"
#   python main.py scrape "wireless earbuds" --site flipkart
#   python main.py list
#   python main.py compare 3
#   python main.py compare 3 --range 50
#   python main.py advise "earbuds for gym, good bass" 1500
#   python main.py advise "light laptop for college" 55k --deep

import os
import sys

from dotenv import load_dotenv


def parse_budget(text):
    # I want to type the budget however feels natural: 1500 / 1,500 / 55k / Rs.2000
    # So I clean up the text and convert to a plain number.
    if text is None:
        return None

    text = text.lower()
    text = text.replace(",", "")
    text = text.replace("rs.", "")
    text = text.replace("rs", "")
    text = text.strip()

    try:
        if text.endswith("k"):
            return float(text[:-1]) * 1000
        return float(text)
    except ValueError:
        print('Could not understand the budget "' + text + '". Try something like 1500 or 55k')
        sys.exit(1)


def check_groq_key():
    if not os.getenv("GROQ_API_KEY"):
        print("Error: GROQ_API_KEY is not set.")
        print("1. Get a free key at https://console.groq.com/keys")
        print("2. Add this line to your .env file:  GROQ_API_KEY=your_key_here")
        sys.exit(1)


def print_table(products, limit=60):
    print("\n#    Price          Stars    Reviews    Name")
    print("-" * 80)
    for i in range(min(limit, len(products))):
        p = products[i]
        num     = str(i + 1)
        price   = get_price_label(p)
        stars   = str(p.get("rating_stars") or "?")
        reviews = str(p.get("review_count") or 0)
        name    = p["name"][:45]
        flag    = " [SUSPECT?]" if p.get("suspect") else ""
        print(num + ".  " + price + "    " + stars + " stars    " + reviews + " reviews    " + name + flag)


def get_price_label(p):
    # small helper so I don't have to import inside the loop
    from live_data import price_label
    return price_label(p)


def cmd_scrape(query, site):
    from india_source import fetch_india
    from live_data import load_live_cache, save_cache

    try:
        results = fetch_india(query, max_products=60, site=site)
    except Exception as e:
        print(str(e))
        sys.exit(1)

    if not results:
        if site:
            print('Nothing found from "' + site + '" — try without --site, or check the spelling.')
        else:
            print("Nothing fetched — check your connection and try again.")
        return

    save_cache(results)
    products = load_live_cache()   # reload so suspect flags are set
    print_table(products, limit=25)

    if len(products) > 25:
        print("... and " + str(len(products) - 25) + " more (run: python main.py list)")

    print("\nNext:  python main.py compare <#>")
    print("  or:  python main.py advise \"" + query + "\" <budget>")


def cmd_list():
    from live_data import load_live_cache

    try:
        products = load_live_cache()
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    print_table(products, limit=60)
    print("\n[SUSPECT?] = brand name at an impossible price or zero reviews — probably fake.")
    print("Use the # with:  python main.py compare <#>")


def cmd_compare(product_num, band):
    check_groq_key()
    from compare import compare
    from live_data import load_live_cache

    try:
        products = load_live_cache()
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)

    if product_num < 1 or product_num > len(products):
        print("Pick a product number between 1 and " + str(len(products)) + ". Run: python main.py list")
        sys.exit(1)

    print(compare(products, product_num - 1, band))


def cmd_advise(need, budget, deep):
    check_groq_key()
    from advisor import advise

    try:
        print(advise(need, budget, deep=deep))
    except FileNotFoundError as e:
        print(str(e))
        sys.exit(1)


def main():
    # Windows sometimes shows weird characters for rupee signs etc — this fixes it
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    load_dotenv()

    # I used to use argparse but it had too much setup for a simple script.
    # Now I just check sys.argv directly — easier to understand and explain.
    if len(sys.argv) < 2:
        print("Usage:")
        print('  python main.py scrape "gaming laptop"')
        print('  python main.py scrape "earbuds" --site flipkart')
        print("  python main.py list")
        print("  python main.py compare 3")
        print("  python main.py compare 3 --range 50")
        print('  python main.py advise "earbuds for gym" 1500')
        print('  python main.py advise "laptop for college" 55k --deep')
        return

    command = sys.argv[1]

    if command == "scrape":
        if len(sys.argv) < 3:
            print('Give me a search query. Example: python main.py scrape "laptop"')
            sys.exit(1)
        query = sys.argv[2]
        site  = None
        if "--site" in sys.argv:
            site_pos = sys.argv.index("--site")
            site = sys.argv[site_pos + 1]
        cmd_scrape(query, site)

    elif command == "list":
        cmd_list()

    elif command == "compare":
        if len(sys.argv) < 3:
            print("Give me a product number. Example: python main.py compare 3")
            sys.exit(1)
        product_num = int(sys.argv[2])
        band = 25
        if "--range" in sys.argv:
            range_pos = sys.argv.index("--range")
            band = int(sys.argv[range_pos + 1])
        cmd_compare(product_num, band)

    elif command == "advise":
        if len(sys.argv) < 3:
            print('Tell me what you need. Example: python main.py advise "earbuds for gym"')
            sys.exit(1)
        need   = sys.argv[2]
        budget = None
        deep   = False
        if "--deep" in sys.argv:
            deep = True
        # budget is the next argument after the need, but only if it's not a flag
        if len(sys.argv) >= 4 and not sys.argv[3].startswith("--"):
            budget = parse_budget(sys.argv[3])
        cmd_advise(need, budget, deep)

    else:
        print("Unknown command: " + command)
        print("Valid commands: scrape, list, compare, advise")


if __name__ == "__main__":
    main()
