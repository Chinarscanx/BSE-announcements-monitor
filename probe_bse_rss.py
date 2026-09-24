import urllib.request, ssl, sys

RSS_URL = "https://www.bseindia.com/data/xml/announcements.xml"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml,application/xml,text/xml,*/*",
    "Referer": "https://www.bseindia.com/",
    "Connection": "keep-alive",
}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request(RSS_URL, headers=HEADERS)
try:
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        data = resp.read()
        print(f"SUCCESS: status={resp.status}, bytes={len(data)}")
        print("First 300 chars:")
        print(data[:300].decode("utf-8", errors="replace"))
except Exception as exc:
    print(f"FAILED: {type(exc).__name__}: {exc}")
    sys.exit(1)
