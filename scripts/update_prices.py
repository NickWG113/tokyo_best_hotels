"""Refresh the "Typical from" prices and guest ratings from Trip.com.

Usage: python3 scripts/update_prices.py

Reads each hotel card in tokyo.html, looks up the hotel's Trip.com page
(in AUD) and rewrites the price and rating in tokyo.html and the featured
cards in index.html. A hotel whose lookup fails keeps its current values.
"""
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"


def fetch(hotel_id):
    url = f"https://www.trip.com/hotels/detail/?hotelId={hotel_id}&curr=AUD&locale=en-AU"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-AU"})
    with urllib.request.urlopen(req, timeout=30) as res:
        page = res.read().decode("utf-8", "replace")
    price = re.search(r'priceRange\\*":\\*"From AU\$([\d,]+)', page)
    rating = re.search(r'ratingValue\\*":\\*"([\d.]+)', page)
    if not price:
        raise ValueError("no price found")
    return "A$" + price.group(1), rating.group(1) if rating else None


def rating_text(value):
    value = f"{float(value):.1f}"
    return f"{value}/10 {'Exceptional' if float(value) >= 9.6 else 'Excellent'}"


def main():
    tokyo_path = os.path.join(ROOT, "tokyo.html")
    index_path = os.path.join(ROOT, "index.html")
    tokyo = open(tokyo_path, encoding="utf-8").read()
    index = open(index_path, encoding="utf-8").read()
    failures = 0

    for card in re.finditer(r'<article id="([^"]+)".*?</article>', tokyo, re.S):
        slug, block = card.group(1), card.group(0)
        hotel_id = re.search(r"hotelId=(\d+)", block)
        if not hotel_id:
            continue
        try:
            price, rating = fetch(hotel_id.group(1))
        except Exception as err:  # keep the old values for this hotel
            failures += 1
            print(f"  {slug}: skipped ({err})", file=sys.stderr)
            continue

        new = re.sub(r"(data-price[^>]*>)A\$[\d,]+", lambda m: m.group(1) + price, block)
        if rating:
            new = re.sub(r"</span> [\d.]+/10 \w+</span>", f"</span> {rating_text(rating)}</span>", new)
        tokyo = tokyo.replace(block, new)

        # Featured card on the homepage, if this hotel has one.
        link = index.find(f'href="tokyo.html#{slug}"')
        if link != -1:
            start = index.rfind("data-price", 0, link)
            end = index.find("</span>", start)
            index = index[:start] + re.sub(r"A\$[\d,]+", price, index[start:end]) + index[end:]
        print(f"  {slug}: {price}" + (f", {rating}/10" if rating else ""))

    open(tokyo_path, "w", encoding="utf-8").write(tokyo)
    open(index_path, "w", encoding="utf-8").write(index)
    if failures:
        print(f"{failures} hotel(s) could not be refreshed.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
