import re
import time
import math
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BASE = "https://www.avito.ru"


def get_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.set_default_timeout(0)
        context.set_default_navigation_timeout(0)
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=0)

        print("Если появилась капча — пройдите её в этом окне. НЕ закрывайте вкладку/браузер.")
        input("Когда откроется список объявлений — нажмите Enter...")

        last_err = None
        try:
            for _ in range(10):
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=10000)
                    return page.content()
                except Exception as e:
                    last_err = e
                    time.sleep(0.5)
            raise RuntimeError(f"Не удалось взять HTML: {last_err}")
        finally:
            browser.close()


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _extract_title(card) -> str:
    m = card.select_one('meta[itemprop="name"]')
    if m and m.get("content"):
        return _clean(m["content"])

    img = card.find("img", alt=True)
    if img and img.get("alt"):
        return _clean(img["alt"])

    a = card.find("a", href=True)
    if a:
        return _clean(a.get_text(" ", strip=True))

    return ""


CAMERA_WORDS = ["фотоаппарат", "камера", "body", "тушка", "kit", "кит", "зеркал", "беззеркал"]
ACCESSORY_ONLY_WORDS = [
    "объектив", "lens", "стекло", "линза",
    "чехол", "сумка", "ремень", "батарейный блок",
    "крышка", "бленда", "фильтр", "кабель",
    "адаптер", "переходник", "ремень",
    "зарядка", "аккумулятор", "батарея",
    "штатив", "монопод", "вспышка",
    "карта памяти", "sd", "cf", "детали"
]


def looks_like_camera_listing(title: str) -> bool:
    t = (title or "").lower()

    has_camera = any(w in t for w in CAMERA_WORDS)
    if has_camera:
        return True

    if any(w in t for w in ACCESSORY_ONLY_WORDS):
        return False

    return True


def extract_avito_id(url: str) -> str | None:
    m = re.search(r"(\d{6,})", url)
    return m.group(1) if m else None


def parse_search_html(html: str, region_fallback: str, limit: int = 30) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    results: list[dict] = []

    for a in soup.select('a[itemprop="url"][href]'):
        card = a
        for _ in range(10):
            if not getattr(card, "parent", None):
                break
            card = card.parent
            if card.select_one('meta[itemprop="price"][content]'):
                break

        price_meta = card.select_one('meta[itemprop="price"][content]')
        if not price_meta:
            continue

        try:
            price = int(price_meta["content"])
        except (TypeError, ValueError):
            continue

        url = urljoin(BASE, a["href"])
        title = _extract_title(card)

        if not title:
            continue
        if not looks_like_camera_listing(title):
            continue

        external_id = extract_avito_id(url)
        if not external_id:
            continue

        results.append({
            "external_id": external_id,
            "url": url,
            "price": price,
            "title": title,
            "region": region_fallback,
        })

        if len(results) >= limit:
            break

    uniq = {}
    for r in results:
        uniq[r["external_id"]] = r
    return list(uniq.values())


def set_page(url: str, page_num: int) -> str:
    u = urlparse(url)
    qs = parse_qs(u.query)
    if page_num <= 1:
        qs.pop("p", None)
    else:
        qs["p"] = [str(page_num)]
    new_query = urlencode(qs, doseq=True)
    return urlunparse((u.scheme, u.netloc, u.path, u.params, new_query, u.fragment))


def extract_total_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "lxml")

    node = soup.select_one('[data-marker="page-title/count"]')
    if node:
        txt = _clean(node.get_text())
        if txt.isdigit():
            return int(txt)

    text = soup.get_text(" ", strip=True).lower()
    m = re.search(r"(\d[\d\s\u00A0]*)\s+объявлен", text)
    if not m:
        return None
    n = re.sub(r"[^\d]", "", m.group(1))
    return int(n) if n else None


def fetch_avito_search(url: str, region_fallback: str, limit: int = 30) -> list[dict]:
    all_items: list[dict] = []
    seen: set[str] = set()

    html1 = get_html(url)
    total = extract_total_count(html1)

    page1_items = parse_search_html(html1, region_fallback=region_fallback, limit=10**9)
    per_page = max(1, len(page1_items))

    max_pages = math.ceil(total / per_page) if total else 10

    for it in page1_items:
        if it["external_id"] in seen:
            continue
        seen.add(it["external_id"])
        all_items.append(it)
        if len(all_items) >= limit:
            return all_items

    for page_num in range(2, max_pages + 1):
        html = get_html(set_page(url, page_num))
        items = parse_search_html(html, region_fallback=region_fallback, limit=10**9)
        for it in items:
            if it["external_id"] in seen:
                continue
            seen.add(it["external_id"])
            all_items.append(it)
            if len(all_items) >= limit:
                return all_items

    return all_items
