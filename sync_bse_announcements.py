import urllib.request
import xml.etree.ElementTree as ET
import ssl
import re
import hashlib
import html as html_module
import json
import os
import datetime

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
    "Referer": "https://www.bseindia.com/",
    "Connection": "keep-alive",
}
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE

DATA_DIR = "data"


def clean_text(value):
    if value is None:
        return ""
    text = str(value)
    for old, new in {"\xa0": " ", "\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'", "\u201c": "\"", "\u201d": "\"", "\u00ad": ""}.items():
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def decode_entities(value):
    return html_module.unescape(value or "")


def make_id(scrip, subject, date, link):
    raw = f"{scrip}|{subject}|{date}|{link}"
    return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()


def parse_announcement_date(date_str):
    if not date_str:
        return None
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(date_str.strip(), fmt).timestamp()
        except ValueError:
            continue
    return None


# --- classify() copied verbatim from bse_feed.py as of the Trading Window / AGM additions.
# IMPORTANT: if you change classify() locally in bse_feed.py later, this copy will drift
# out of sync unless you manually update it here too. See the README for this caveat.

def classify(subject, description):
    text = f"{subject} {description}".lower()

    is_mf = (
        bool(re.search(r"\bnav\b", text, flags=re.I))
        or any(term in text for term in [
            "net asset value", "nav as on", "nav as at", "mutual fund", "mutual funds",
            "sbimf", "sbi mutual fund", "fortnightly portfolio", "monthly portfolio",
            "portfolio disclosure", "portfolio statement", "fixed maturity plan",
            "dividend yield fund", "asset management company", "scheme portfolio",
            "scheme factsheet", "scheme disclosure", "unit movement", "expense ratio",
            "idcw", "direct growth", "regular growth", "direct idcw", "regular idcw",
            "idcw reinvestment", "idcw payout", "idcw transfer",
        ])
        or bool(re.search(r"\bfmp\b", text, flags=re.I))
        or bool(re.search(r"\b(?:liquid|equity|debt|multicap|multi\s+asset|index|balanced|hybrid|elss|arbitrage|small\s*cap|mid\s*cap|large\s*cap)\s+fund\b", text, flags=re.I))
    )
    is_sast = (
        bool(re.search(r"\bregulation\s+29(?:\s*\(\s*[12]\s*\))?", text, flags=re.I))
        or bool(re.search(r"\bregulation\s+31(?:\s*\(\s*[12]\s*\))?", text, flags=re.I))
        or bool(re.search(r"\bregulation\s+7\s*\(\s*2\s*\)", text, flags=re.I))
        or any(term in text for term in [
            "substantial acquisition of shares", "substantial acquisition of shares and takeovers",
            "sast regulations", "sast disclosure", "pit disclosure", "prohibition of insider trading",
            "insider trading regulations", "promoter acquired", "promoter acquisition of shares",
            "acquired equity shares through open market", "open market transaction", "open market transactions",
        ])
    )
    is_trading_window = any(term in text for term in [
        "trading window", "closure of the trading window", "trading window closure",
        "trading window shall remain closed", "trading window will remain closed",
        "reopening of trading window", "trading window will open", "trading window opens",
    ])
    is_agm = (
        bool(re.search(r"\bagm\b", text, flags=re.I))
        or "annual general meeting" in text
    )
    is_order = any(term in text for term in [
        "order worth", "order received", "receipt of an order", "received domestic orders",
        "received an order", "letter of award", "secured order", "purchase order", "work order",
        "contract awarded", "new order",
    ])
    is_expansion = any(term in text for term in ["capacity expansion", "capacity addition", "new facility", "manufacturing facility", "tpd", "commissioning", "expansion"])
    is_mna = any(term in text for term in [
        "share purchase agreement", "acquisition", "acquire", "takeover", "open offer", "merger",
        "joint venture", "strategic stake", "strategic equity stake", "business transfer agreement",
        "slump sale", "scheme of arrangement",
    ])
    is_dividend = "dividend" in text
    is_debt = any(term in text for term in [
        "non convertible debentures", "commercial paper", "redemption", "interest payment",
        "private placement", "fund raising", "fundraising",
    ])
    is_legal = any(term in text for term in ["material litigation", "show cause notice", "regulatory order", "court order", "penalty"])
    is_press = any(term in text for term in ["press release", "business update"])

    is_rating_downgrade = (
        bool(re.search(r"rating.{0,40}downgrad", text, flags=re.I))
        or bool(re.search(r"downgrad.{0,40}rating", text, flags=re.I))
    )
    is_credit_rating = (
        is_rating_downgrade
        or any(term in text for term in [
            "credit rating", "rating agency", "rating action", "rating reaffirmed",
            "rating upgraded", "rating assigned", "rating outlook", "long term rating",
            "long-term rating", "short term rating", "short-term rating",
            "crisil", "icra", "care ratings", "care edge", "india ratings", "brickwork",
            "acuite", "infomerics", "fitch", "moody's", "moodys", "standard & poor's", "s&p global",
        ])
    )

    if is_mf:
        category = "Mutual Fund / NAV"
    elif is_order:
        category = "Order / Contract"
    elif is_expansion:
        category = "Expansion / Capacity"
    elif is_trading_window:
        category = "Trading Window"
    elif is_agm:
        category = "AGM / Annual General Meeting"
    elif is_sast:
        category = "SAST / PIT / Disclosure"
    elif is_credit_rating:
        category = "Credit Rating"
    elif is_mna:
        category = "M&A / Strategic"
    elif is_dividend:
        category = "Dividend"
    elif is_debt:
        category = "Fundraising / Debt"
    elif is_legal:
        category = "Legal / Regulatory"
    elif is_press:
        category = "Press Release"
    else:
        category = "General / Other"

    catalyst = "HIGH" if (is_order or is_mna or is_sast or is_rating_downgrade) else ("MEDIUM" if is_expansion else "")
    return {"category": category, "catalyst_level": catalyst, "is_mf_nav": is_mf}


def fetch_feed():
    req = urllib.request.Request(RSS_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60, context=SSL_CONTEXT) as response:
        return response.read()


def parse_feed(raw):
    root = ET.fromstring(raw)
    results = []
    for item in root.findall(".//item"):
        title = clean_text(decode_entities(item.findtext("title", "")))
        description = clean_text(decode_entities(item.findtext("description", "")))
        link = clean_text(decode_entities(item.findtext("link", "")))
        if not link:
            link = clean_text(decode_entities(item.findtext("guid", "")))
        scrip = clean_text(item.findtext("scripcode", ""))
        if not scrip:
            m = re.search(r"(?:Scrip\s*Code\s*[:\]]?\s*)(\d{6})", title, flags=re.I)
            if m:
                scrip = m.group(1)
        date = clean_text(item.findtext("pubDate", ""))
        if not (title or description):
            continue
        company = title
        if scrip:
            company = re.sub(rf"\s*\(\s*{re.escape(scrip)}\s*\)\s*$", "", company, flags=re.I)
            company = re.sub(rf"\s*\[\s*Scrip Code:\s*{re.escape(scrip)}\s*\]\s*$", "", company, flags=re.I)
        if " - " in company:
            company = company.split(" - ", 1)[0]
        classification = classify(title, description)
        results.append({
            "id": make_id(scrip, description, date, link),
            "company": clean_text(company), "symbol": scrip, "subject": description,
            "date": date, "link": link, **classification,
        })
    return results


def day_key_for(date_str):
    ts = parse_announcement_date(date_str)
    if ts is None:
        return "unknown"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def load_existing_ids(filepath):
    ids = set()
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.add(json.loads(line)["id"])
                except Exception:
                    continue
    return ids


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    items = parse_feed(fetch_feed())
    by_day = {}
    for item in items:
        by_day.setdefault(day_key_for(item["date"]), []).append(item)

    total_new = 0
    for day, day_items in by_day.items():
        filepath = os.path.join(DATA_DIR, f"announcements-{day}.jsonl")
        existing_ids = load_existing_ids(filepath)
        new_items = [x for x in day_items if x["id"] not in existing_ids]
        if new_items:
            with open(filepath, "a", encoding="utf-8") as f:
                for item in new_items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            total_new += len(new_items)
            print(f"{day}: +{len(new_items)} new")

    print(f"Done. Total new items this run: {total_new}")


if __name__ == "__main__":
    main()
