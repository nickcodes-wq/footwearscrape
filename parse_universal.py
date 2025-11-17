"""
BULLETPROOF Universal Footwear Parser
Handles ALL price formats and scenarios across footwear brands
"""

from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse


def extract_price_bulletproof(text):
    """
    Bulletproof price extraction handling ALL formats.
    Tested against: Nike, Adidas, Wolverine, Merrell, Under Armour, HOKA, UGG, Puma, etc.
    """
    if not text:
        return None

    text = str(text).strip()

    # Skip non-price indicators
    skip_indicators = [
        'off', 'save', 'discount', 'free', 'shipping', 'member', 'employee',
        'review', 'rating', 'star', 'sold', 'available', 'stock',
        'color', 'size', 'width', 'length', 'style'
    ]

    text_lower = text.lower()

    # Skip if contains percentage without dollar sign (it's a discount label)
    if '%' in text and '$' not in text:
        return None

    # Skip obvious non-price text
    if any(indicator in text_lower for indicator in skip_indicators):
        if not any(symbol in text for symbol in ['$', '€', '£']):
            return None

    # Price extraction patterns (in order of specificity)
    patterns = [
        r'\$\s*(\d{1,4}(?:,\d{3})*(?:\.\d{2}))',  # $99.99 or $1,299.99
        r'\$\s*(\d{1,4}(?:,\d{3})*)',  # $99 or $1,299
        r'(\d{1,4}(?:,\d{3})*(?:\.\d{2}))\s*\$',  # 99.99$ (some EU sites)
        r'€\s*(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',  # €99.99 or €99
        r'£\s*(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)',  # £99.99 or £99
        r'(\d{1,4}(?:,\d{3})*(?:\.\d{2}))\s*USD',  # 175.00 USD (HOKA format)
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            for match in matches:
                try:
                    # Clean and convert
                    price_str = match.replace(',', '').replace(' ', '')
                    price = float(price_str)
                    # Reasonable footwear price range (global)
                    if 5 <= price <= 2000:
                        return price
                except:
                    continue

    return None


def is_promotional_text(text):
    """
    Detect promotional discount amounts (not actual prices)
    Fixes Under Armour "$10 Off" being mistaken for sale price
    Returns True if it's promotional text to ignore
    """
    if not text:
        return False

    text_lower = text.lower().strip()

    # Promotional patterns to ignore
    promo_patterns = [
        r'\$\d+\s*off',  # "$10 Off"
        r'\d+\s*off',  # "10 Off"
        r'save\s*\$?\d+',  # "Save $10"
        r'extra\s*\$?\d+',  # "Extra $10"
        r'limited\s*time',  # "Limited Time: $10"
        r'discount\s*\$?\d+',  # "Discount $10"
        r'member\s*\$?\d+',  # "Member $10"
        r'get\s*\$?\d+\s*off',  # "Get $10 Off"
    ]

    for pattern in promo_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def calculate_discount(original, sale):
    """Calculate discount percentage"""
    if original and sale and original > sale > 0:
        discount = ((original - sale) / original) * 100
        return f"{discount:.1f}%"
    return "N/A"


def is_invalid_product_name(product_name):
    """
    Check if the extracted "name" is actually just price text or invalid.
    Returns True if the name is INVALID and should be rejected.
    """
    if not product_name:
        return True

    name_lower = product_name.lower().strip()

    # If the "name" is actually just price information
    price_text_indicators = [
        'original price:',
        'sale price:',
        'regular price:',
        'was:',
        'now:',
        'price:',
    ]

    # Check if the name starts with price indicators
    if any(name_lower.startswith(indicator) for indicator in price_text_indicators):
        return True

    # If the name starts with a dollar sign
    if product_name.strip().startswith('$'):
        return True

    # If the name is ONLY prices and symbols (no actual words)
    name_stripped = name_lower
    for char in ['$', '€', '£', ',', '.', ':', '-', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
        name_stripped = name_stripped.replace(char, ' ')

    # What's left should have actual words
    words = [w for w in name_stripped.split() if len(w) > 2]

    # If mostly price-related words
    if words:
        price_words = ['original', 'price', 'sale', 'was', 'now', 'regular', 'save', 'off']
        price_word_count = sum(1 for w in words if w in price_words)
        if price_word_count / len(words) > 0.6:  # More than 60% are price words
            return True

    # If there are barely any alphabetic characters (mostly numbers/symbols)
    alpha_chars = sum(1 for c in product_name if c.isalpha())
    total_chars = len(product_name)
    if total_chars > 0 and (alpha_chars / total_chars) < 0.3:  # Less than 30% letters
        return True

    return False


def is_non_footwear_item(product_name):
    """
    Filter out gift cards, non-footwear items, and navigation/UI elements.
    Returns True if item should be EXCLUDED.
    """
    if not product_name:
        return False

    name_lower = product_name.lower()

    # NON-FOOTWEAR PRODUCTS
    exclude_keywords = [
        'gift', 'gift card', 'giftcard', 'gift certificate',
        'e-gift', 'egift', 'gift voucher', 'store credit',
        'shopping card', 'prepaid card', 'digital gift', 'gift pack',
        'care kit', 'cleaning kit', 'laces only', 'insole only',
        'accessory kit', 'water repellent', 'shoe cleaner',
        'protective spray', 'subscription', 'membership'
    ]

    # NAVIGATION & UI ELEMENTS
    navigation_keywords = [
        'sign in', 'sign up', 'log in', 'login', 'register',
        'create account', 'my account', 'account', 'cart', 'checkout',
        'wishlist', 'favorites', 'did you mean', 'search results',
        'filter by', 'sort by', 'product type', 'category', 'breadcrumb',
        'menu', 'navigation', 'back to', 'view all', 'shop now',
        'learn more', 'find out', 'discover', 'explore',
        'add a promotion', 'add promotion', 'add discount',
        'promo code', 'coupon code', 'subscribe', 'newsletter',
        'email signup', 'gifts by price', 'gifts under', 'price range',
        'shop by price', '$85 and up', '$75+', 'sale items',
        'clearance items', 'new arrivals', 'best sellers', 'top rated',
        'customer service', 'help center', 'contact us',
        'store locator', 'find a store',
        'keep up with', 'follow us', 'stay connected', 'join us',
        'connect with', 'social media', 'follow along'
    ]

    # PROMOTIONAL PHRASES
    promo_patterns = [
        'free', 'save', 'off', 'discount', 'promotion', 'offer',
        'deal', 'special', 'sale', 'clearance', 'collection'
    ]

    # Specific promotional text patterns to exclude
    promotional_exact = [
        'keep up with us',
        '20% off boots',
        '30% off boots',
        '40% off boots',
        '50% off boots',
        'x collection',
    ]

    # Check for exact promotional matches
    for promo in promotional_exact:
        if promo in name_lower:
            return True

    # Check if it's a collection announcement (brand x brand)
    if ' x ' in name_lower and 'collection' in name_lower:
        return True

    # Check if it's percentage-based promotional text
    if re.search(r'\d+%\s*off', name_lower):
        return True

    # Check if it's just "% off [category]" format
    if re.match(r'^\d+%?\s+off\s+\w+', name_lower):
        return True

    # Check if it's a short promotional phrase (likely a banner)
    word_count = len(product_name.split())
    if word_count <= 8:
        if any(promo in name_lower for promo in promo_patterns):
            if not any(
                    shoe_word in name_lower for shoe_word in ['boot', 'shoe', 'sneaker', 'sandal', 'slipper', 'clog']):
                return True
            # Exception: "20% off boots" has "boot" but is still promotional
            if re.search(r'\d+%\s*off', name_lower):
                return True

    # Check all exclusion keywords
    if any(keyword in name_lower for keyword in exclude_keywords + navigation_keywords):
        return True

    # PATTERN-BASED FILTERS
    if len(product_name.strip()) < 8:
        return True

    if word_count <= 3:
        footwear_indicators = ['boot', 'shoe', 'sneaker', 'sandal', 'slipper', 'oxford', 'loafer', 'clog', 'runner',
                               'trainer', 'heel', 'wedge', 'moccasin']
        if not any(indicator in name_lower for indicator in footwear_indicators):
            return True

    # All caps promotional text (like "WOLVERINE x JORDANDAVIS COLLECTION")
    if product_name.isupper() and word_count <= 6:
        if not any(word in name_lower for word in ['boot', 'shoe', 'sneaker', 'work', 'steel', 'toe']):
            return True

    question_patterns = ['?', 'did you', 'do you', 'how to', 'why', 'what is', 'sign up', 'click here']
    if any(pattern in name_lower for pattern in question_patterns):
        return True

    return False


def extract_site_promotions(html_content):
    """
    SIMPLE promotion extraction - looks for:
    - Free shipping thresholds ($75, $100, etc.)
    - Percent discounts (20% off, 30% off select styles, etc.)
    - Clearance mentions
    Returns list of simple promotional strings
    """
    promotions = []

    # Pattern 1: Free shipping with dollar amount
    free_ship_pattern = r'free\s+shipping[^.!?\n]{0,50}\$\s*(\d+)'
    matches = re.findall(free_ship_pattern, html_content, re.IGNORECASE)
    for amount in set(matches):
        promotions.append(f"Free Shipping: ${amount}+")

    # Pattern 2: Percent discount
    percent_pattern = r'(\d+)%\s*off'
    matches = re.findall(percent_pattern, html_content, re.IGNORECASE)
    if matches:
        unique_percents = sorted(set(matches), reverse=True)
        for percent in unique_percents[:3]:  # Top 3 discounts
            promotions.append(f"{percent}% Off")

    # Pattern 3: Clearance
    if re.search(r'\bclearance\b', html_content, re.IGNORECASE):
        promotions.append("Clearance Available")

    # Pattern 4: Select styles discount
    if re.search(r'select\s+styles', html_content, re.IGNORECASE):
        promotions.append("Sale on Select Styles")

    return promotions[:10]  # Return up to 10


def get_domain(url):
    """Extract clean domain"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return ""


def score_as_product_container(element):
    """
    Score element likelihood of being a product container.
    Returns score (higher = more likely).
    """
    if not element.name or element.name not in ['div', 'article', 'li', 'section', 'a']:
        return 0

    score = 0

    classes = ' '.join(element.get('class', [])).lower()
    elem_id = element.get('id', '').lower()
    data_attrs = ' '.join([str(v).lower() for k, v in element.attrs.items() if k.startswith('data-')])

    product_keywords = ['product', 'item', 'card', 'tile']
    for keyword in product_keywords:
        if keyword in classes:
            score += 3
        if keyword in elem_id:
            score += 2
        if keyword in data_attrs:
            score += 2

    if element.find('a', href=True):
        score += 2
    if element.find('img'):
        score += 1

    text = element.get_text()
    if '$' in text or '€' in text or '£' in text or 'USD' in text:
        score += 3

    if len(text.strip()) > 5:
        score += 1

    return score


def find_product_name(container):
    """Extract product name with comprehensive fallbacks."""
    # Strategy 1: Look for specific product name classes
    name_selectors = [
        {'class': re.compile(r'product.*name|item.*name|card.*title', re.I)},
        {'class': re.compile(r'product.*title|item.*title', re.I)},
    ]

    for selector in name_selectors:
        elements = container.find_all(**selector)
        for elem in elements:
            text = elem.get_text(strip=True)
            if 10 <= len(text) <= 250:
                return text

    # Strategy 2: Header tags
    for tag in ['h1', 'h2', 'h3', 'h4', 'h5']:
        elements = container.find_all(tag)
        for elem in elements:
            text = elem.get_text(strip=True)
            if 10 <= len(text) <= 250:
                if not any(word in text.lower() for word in ['cart', 'menu', 'sign in', 'account']):
                    return text

    # Strategy 3: Links with substantial text
    links = container.find_all('a', href=True)
    for link in links:
        text = link.get_text(strip=True)
        if 10 <= len(text) <= 250:
            if not any(word in text.lower() for word in ['view', 'shop', 'cart', 'wishlist']):
                return text

    # Strategy 4: Any substantial text in spans/divs
    for tag in ['span', 'div', 'p']:
        elements = container.find_all(tag)
        for elem in elements:
            text = elem.get_text(strip=True)
            if 15 <= len(text) <= 200:
                if re.search(r'[a-zA-Z]{3,}', text):
                    return text

    return None


def find_product_link(container, base_url):
    """Extract product URL"""
    links = container.find_all('a', href=True)
    best_link = None
    best_score = 0

    for link in links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        score = 0

        if any(word in href.lower() for word in ['cart', 'checkout', 'account', 'login', 'javascript:', '#']):
            continue

        if any(pattern in href.lower() for pattern in [
            '/product/', '/p/', '/item/', '/dp/', '.html',
            '-shoe', '-boot', '-sneaker', '/men/', '/women/'
        ]):
            score += 3

        if 5 <= len(text) <= 200:
            score += 1

        if score > best_score:
            best_score = score
            best_link = href

    if best_link:
        return urljoin(base_url, best_link)

    if links:
        return urljoin(base_url, links[0].get('href', ''))

    return None


def find_prices_bulletproof(container):
    """
    BULLETPROOF price extraction with promotional text filtering.
    Handles all scenarios: strikethrough, multiple prices, member prices, etc.
    Returns: (original_price, sale_price)
    """
    original_price = None
    sale_price = None
    all_prices = []

    # ========== STEP 1: Find STRIKETHROUGH prices (original/was price) ==========
    strikethrough_elements = []

    strikethrough_elements += container.find_all(['del', 's', 'strike'])
    strikethrough_elements += container.find_all(style=re.compile(r'line-through', re.I))

    strikethrough_classes = [
        'strike', 'strikethrough', 'was-price', 'original-price',
        'regular-price', 'compare-at', 'msrp', 'list-price'
    ]

    for cls in strikethrough_classes:
        strikethrough_elements += container.find_all(class_=re.compile(cls, re.I))

    for elem in strikethrough_elements:
        price = extract_price_bulletproof(elem.get_text())
        if price:
            original_price = price
            break

    # ========== STEP 2: Find ALL other prices ==========
    price_elements = []

    price_classes = ['price', 'cost', 'amount', 'pricing', 'sale', 'current', 'now']
    for cls in price_classes:
        price_elements += container.find_all(class_=re.compile(cls, re.I))

    price_elements += container.find_all(attrs={'data-price': True})
    price_elements += container.find_all(attrs={'data-product-price': True})
    price_elements += container.find_all(attrs={'data-test-price': True})

    # Method 3: Elements containing currency symbols (with promotional filter)
    for tag in ['span', 'div', 'p', 'strong', 'b']:
        elements = container.find_all(tag)
        for elem in elements:
            text = elem.get_text(strip=True)

            # Skip promotional discount amounts
            if is_promotional_text(text):
                continue

            if ('$' in text or '€' in text or '£' in text or 'USD' in text) and len(text) < 100:
                if elem not in price_elements:
                    price_elements.append(elem)

    # Extract all prices (skip strikethrough elements and promotional text)
    for elem in price_elements:
        if elem in strikethrough_elements:
            continue

        if elem.parent and elem.parent in strikethrough_elements:
            continue

        if elem.name in ['del', 's', 'strike']:
            continue

        style = elem.get('style', '')
        if 'line-through' in style.lower():
            continue

        # Skip promotional discount text
        elem_text = elem.get_text(strip=True)
        if is_promotional_text(elem_text):
            continue

        price = extract_price_bulletproof(elem_text)
        if price and price not in all_prices:
            all_prices.append(price)

    # ========== STEP 3: Determine final prices ==========
    if original_price:
        if all_prices:
            sale_price = min(all_prices)
        else:
            sale_price = original_price
            original_price = None
    else:
        if len(all_prices) >= 2:
            all_prices.sort()
            sale_price = all_prices[0]
            original_price = all_prices[-1]
        elif len(all_prices) == 1:
            sale_price = all_prices[0]

    return original_price, sale_price


def extract_products_from_price_patterns(html_content, base_url):
    """
    FALLBACK parser for JavaScript-heavy sites where products don't have names in HTML.
    Extracts products by finding price patterns and attempting to construct names.
    Used when traditional parsing finds no products.
    """
    print("\n🎯 FALLBACK: Using price-pattern extraction for JavaScript site...")

    soup = BeautifulSoup(html_content, 'html.parser')
    products = []
    seen_prices = set()

    all_links = soup.find_all('a', href=True)

    for link in all_links:
        try:
            href = link.get('href', '')

            if any(skip in href.lower() for skip in ['cart', 'checkout', 'account', 'login', 'javascript:', '#']):
                continue

            container = link.parent
            if container:
                container_text = container.get_text(separator=' ', strip=True)

                price_patterns = [
                    r'(\d+\.\d{2})\s*USD',
                    r'\$\s*(\d+\.\d{2})',
                    r'(\d{1,3},\d{3}\.\d{2})',
                ]

                prices = []
                for pattern in price_patterns:
                    matches = re.findall(pattern, container_text)
                    for match in matches:
                        try:
                            price_str = match.replace(',', '').replace(' ', '')
                            price = float(price_str)
                            if 5 < price < 2000:
                                prices.append(price)
                        except:
                            continue

                if not prices:
                    continue

                price_key = tuple(sorted(prices))
                if price_key in seen_prices:
                    continue
                seen_prices.add(price_key)

                if len(prices) >= 2:
                    prices_sorted = sorted(prices)
                    sale_price = prices_sorted[0]
                    original_price = prices_sorted[-1]
                else:
                    sale_price = prices[0]
                    original_price = None

                name = None

                link_text = link.get_text(strip=True)
                if link_text and 5 < len(link_text) < 200:
                    if not re.match(r'^\$?\d+\.?\d*', link_text):
                        name = link_text

                if not name and href:
                    path_parts = href.rstrip('/').split('/')
                    for part in reversed(path_parts):
                        if part and len(part) > 3 and not part.startswith('?'):
                            name = part.replace('-', ' ').replace('_', ' ').title()
                            if len(name) > 10:
                                break

                if not name:
                    for tag in ['h2', 'h3', 'h4']:
                        heading = container.find(tag)
                        if heading:
                            potential_name = heading.get_text(strip=True)
                            if potential_name and 5 < len(potential_name) < 100:
                                name = potential_name
                                break

                if not name or len(name) < 5:
                    domain = get_domain(base_url)
                    brand = domain.split('.')[0].upper() if domain else "Product"
                    name = f"{brand} Footwear - ${sale_price:.2f}"

                full_link = urljoin(base_url, href) if href else 'N/A'
                discount = calculate_discount(original_price, sale_price)

                product = {
                    'Product Name': name,
                    'Product URL': full_link,
                    'Original Price': f"${original_price:.2f}" if original_price else 'N/A',
                    'Sale Price': f"${sale_price:.2f}",
                    'Discount %': discount,
                    'Brand': get_domain(base_url).split('.')[0].title() if get_domain(base_url) else 'N/A',
                    'Category': 'Footwear'
                }

                products.append(product)

        except Exception:
            continue

    print(f"✓ Price-pattern extraction found {len(products)} products")
    return products


def parse_products_universal(html_content, source_url=""):
    """
    Universal parser with bulletproof price extraction.
    Works on ANY footwear website.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    print("\n" + "=" * 60)
    print("UNIVERSAL PARSER - BULLETPROOF EDITION")
    print("=" * 60)

    domain = get_domain(source_url)
    print(f"Domain: {domain or 'Unknown'}")

    if source_url:
        parsed = urlparse(source_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
    else:
        base_url = ""

    print(f"Base URL: {base_url}")

    # ========== FIND PRODUCT CONTAINERS ==========
    print("\nStep 1: Finding product containers...")

    all_elements = soup.find_all(['div', 'article', 'li', 'section', 'a'])
    print(f"  Analyzing {len(all_elements)} elements...")

    scored_elements = []
    for elem in all_elements:
        score = score_as_product_container(elem)
        if score >= 5:
            scored_elements.append((score, elem))

    scored_elements.sort(reverse=True, key=lambda x: x[0])
    product_containers = [elem for score, elem in scored_elements[:300]]

    print(f"  Found {len(product_containers)} high-confidence product containers")

    # ========== PARSE PRODUCTS ==========
    print("\nStep 2: Extracting product data...")

    products = []
    seen_names = set()
    products_with_prices = 0
    filtered_count = 0

    for i, container in enumerate(product_containers, 1):
        try:
            name = find_product_name(container)

            if not name or len(name) < 5:
                continue

            if is_invalid_product_name(name):
                filtered_count += 1
                continue

            if is_non_footwear_item(name):
                filtered_count += 1
                continue

            name_key = name.lower().strip()[:100]
            if name_key in seen_names:
                continue
            seen_names.add(name_key)

            link = find_product_link(container, base_url)

            original, sale = find_prices_bulletproof(container)

            if sale:
                products_with_prices += 1

            discount = calculate_discount(original, sale)

            product = {
                'Product Name': name,
                'Product URL': link or 'N/A',
                'Original Price': f"${original:.2f}" if original else 'N/A',
                'Sale Price': f"${sale:.2f}" if sale else 'N/A',
                'Discount %': discount,
                'Brand': domain.split('.')[0].title() if domain else 'N/A',
                'Category': 'Footwear'
            }

            products.append(product)

            if i % 50 == 0:
                print(f"  Processed {i}/{len(product_containers)} containers...")

        except Exception as e:
            continue

    # ========== FALLBACK: JavaScript site handling ==========
    if len(products) == 0:
        print("\n⚠ No products found with traditional parsing")
        print("Attempting fallback for JavaScript-rendered sites...")
        products = extract_products_from_price_patterns(html_content, base_url or source_url)

    # ========== EXTRACT SITE PROMOTIONS ==========
    print("\nStep 3: Extracting site-wide promotions...")
    site_promotions = extract_site_promotions(html_content)

    if site_promotions:
        print(f"  Found {len(site_promotions)} promotions:")
        for promo in site_promotions:
            print(f"    - {promo}")
    else:
        print("  No site promotions found")

    # ========== RESULTS ==========
    products_with_discounts = sum(1 for p in products if p['Discount %'] != 'N/A')

    print(f"\n{'=' * 60}")
    print(f"PARSING COMPLETE")
    print(f"{'=' * 60}")
    print(f"Total products found: {len(products)}")

    if filtered_count > 0:
        print(f"Items filtered out: {filtered_count}")

    if len(products) > 0:
        price_rate = (products_with_prices / len(products)) * 100
        discount_rate = (products_with_discounts / len(products)) * 100
        print(f"Products with prices: {products_with_prices} ({price_rate:.1f}%)")
        print(f"Products with discounts: {products_with_discounts} ({discount_rate:.1f}%)")

        if price_rate < 50:
            print(f"\n⚠ LOW PRICE EXTRACTION RATE")
            print(f"Possible causes:")
            print(f"  - Prices loaded via JavaScript (increase wait time)")
            print(f"  - Site uses non-standard price format")
            print(f"  - Not a product listing page")
    else:
        print(f"\n⚠ NO PRODUCTS FOUND")
        print(f"Troubleshooting:")
        print(f"  1. Verify URL is a product listing page")
        print(f"  2. Increase max pages setting")
        print(f"  3. Try increasing wait time in scraper")

    print(f"{'=' * 60}\n")

    return products, site_promotions


def products_to_csv(products):
    """Convert to CSV"""
    if not products:
        return "No products found"

    import csv
    import io

    output = io.StringIO()
    fieldnames = ['Product Name', 'Product URL', 'Original Price', 'Sale Price', 'Discount %', 'Brand', 'Category']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(products)

    return output.getvalue()
