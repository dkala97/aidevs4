#!/usr/bin/env python3

import csv
import re
from difflib import SequenceMatcher
from pathlib import Path
from flask import Flask, request, jsonify
from collections import defaultdict

app = Flask(__name__)

# Global data structures
ITEMS = {}  # code -> name mapping
ITEMS_BY_NAME = []  # list of (name, code) for fuzzy matching
CITIES = {}  # code -> name mapping
CONNECTIONS = defaultdict(set)  # item_code -> set of city_codes

def load_data():
    """Load CSV data into memory"""
    data_dir = Path(__file__).parent / "data"

    # Load cities
    with open(data_dir / "cities.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            CITIES[row['code']] = row['name']

    # Load items
    with open(data_dir / "items.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row['code']
            name = row['name']
            ITEMS[code] = name
            ITEMS_BY_NAME.append((name, code))

    # Load connections
    with open(data_dir / "connections.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_code = row['itemCode']
            city_code = row['cityCode']
            CONNECTIONS[item_code].add(city_code)

def fuzzy_match_item(query_text, threshold=0.5):
    """
    Find best matching items for natural language query.
    Smart matching that prioritizes category (rezystor, dioda, etc).
    Returns (item_code, match_score, item_name) tuple or None.
    """
    query_lower = query_text.lower().strip()

    # Extract main searchable words (ignore small words, numbers, units)
    query_words = [word for word in query_lower.split() 
                   if len(word) > 2 and not word.replace('.', '').isdigit()]

    if not query_words:
        return None

    matches = []

    for item_name, item_code in ITEMS_BY_NAME:
        item_lower = item_name.lower()

        # Direct substring match gets highest boost
        if query_lower in item_lower:
            matches.append((item_code, 0.95, item_name))
            continue

        # Check how many query keywords appear in item name
        keyword_matches = [w for w in query_words if w in item_lower]
        if keyword_matches:
            # Score based on: number of keywords matched
            keyword_score = 0.6 + (0.15 * len(keyword_matches))
            matches.append((item_code, keyword_score, item_name))
            continue

        # Fallback: sequence match (for typos/variations)
        ratio = SequenceMatcher(None, query_lower, item_lower).ratio()
        if ratio >= 0.55:
            matches.append((item_code, ratio, item_name))

    # Return best match
    if matches:
        matches.sort(key=lambda x: (-x[1], x[2]))
        return matches[0]
    return None

def extract_items_from_query(query_text):
    """
    Extract item descriptions from natural language query.
    Splits by common separators (i, oraz, comma) and attempts to match each part.
    """
    # Split query into parts
    parts = re.split(r'\s+i\s+|oraz|\s*,\s*', query_text.lower())

    matched_items = []
    for part in parts:
        part = part.strip()
        if len(part) > 2:  # Skip very short segments
            result = fuzzy_match_item(part, threshold=0.4)
            if result:
                matched_items.append(result)

    return matched_items

def find_cities_with_all_items(item_codes):
    """
    Find cities that have ALL requested items in stock.
    Returns list of city names.
    """
    if not item_codes:
        return []

    # Get set of cities for each item
    city_sets = []
    for item_code in item_codes:
        cities = CONNECTIONS.get(item_code, set())
        if not cities:
            # Item not found in any city
            return []
        city_sets.append(cities)

    # Find intersection - cities that have ALL items
    common_cities = set.intersection(*city_sets) if city_sets else set()

    # Convert city codes to names
    city_names = sorted([CITIES.get(code, code) for code in common_cities])
    return city_names

def format_response(cities, matched_items, query_text):
    """Format response respecting 4-500 byte constraint"""

    if cities:
        # Success case - list cities
        response_text = ", ".join(cities)
    else:
        # Failure case - provide helpful feedback
        if not matched_items:
            response_text = "Nie znaleziono przedmiotów pasujących do zapytania. Spróbuj bardziej konkretnego opisu."
        else:
            # Items found but no city has all of them
            item_names = [item[2] for item in matched_items]
            response_text = f"Brak miasta z WSZYSTKIMI przedmiotami. Znalezione: {', '.join(item_names[:2])}"

    # Ensure response is within limits
    response_bytes = response_text.encode('utf-8')
    if len(response_bytes) < 4:
        response_text = "Brak"
    elif len(response_bytes) > 500:
        response_text = response_text[:470] + "..."

    return response_text

@app.route('/tool', methods=['POST'])
def tool():
    try:
        data = request.get_json()
        query = data.get("params", "").strip()

        if not query:
            return jsonify({"output": "Brakzapytania"}), 400

        print(f"[QUERY] {query}")

        # Extract and match items
        matched_items = extract_items_from_query(query)
        item_codes = [item[0] for item in matched_items]

        if not item_codes:
            output = "Nie rozpoznano żadnych przedmiotów."
        else:
            # Find cities with all items
            cities = find_cities_with_all_items(item_codes)

            # Format response
            output = format_response(cities, matched_items, query)

        # Validate response size
        output_bytes = output.encode('utf-8')
        if len(output_bytes) < 4 or len(output_bytes) > 500:
            output = "Błąd: nieprawidłowy rozmiar odpowiedzi"

        print(f"[RESPONSE] {output} ({len(output_bytes)} bytes)")
        return jsonify({"output": output})

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"output": "Błąd serwera"}), 500

if __name__ == '__main__':
    load_data()
    print(f"Loaded {len(ITEMS)} items, {len(CITIES)} cities, {len(CONNECTIONS)} connections")
    app.run(debug=True, port=10023)
