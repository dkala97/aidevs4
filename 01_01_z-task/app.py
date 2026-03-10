#!/usr/bin/env python3
"""
Zadanie: people
Filtruje dane CSV, taguje zawody przez LLM (structured output)
i wysyła do HUB osoby pracujące w transporcie.
"""

import csv
import json
import os
import sys
from io import StringIO
from pathlib import Path
from typing import List, Literal

import requests
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

# --- Config -----------------------------------------------------------

CURRENT_YEAR = 2026
AGE_MIN = 20
AGE_MAX = 40
TARGET_GENDER = "M"
TARGET_CITY = "Grudziądz"
TARGET_TAG = "transport"
TASK_NAME = "people"

ALLOWED_TAGS = Literal[
    "IT",
    "transport",
    "edukacja",
    "medycyna",
    "praca z ludźmi",
    "praca z pojazdami",
    "praca fizyczna",
]

SCRIPT_DIR = Path(__file__).parent
ENV_PATH = SCRIPT_DIR.parent / ".env"


# --- Env --------------------------------------------------------------

load_dotenv(ENV_PATH)

AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
HUB_URL = os.getenv("HUB_URL").strip()
HUB_API_KEY = os.getenv("HUB_API_KEY", "").strip()

if AI_PROVIDER == "openrouter":
    api_key = OPENROUTER_API_KEY
    base_url = "https://openrouter.ai/api/v1"
    model = "openai/gpt-4o-mini"
else:
    api_key = OPENAI_API_KEY
    base_url = None  # default OpenAI
    model = "gpt-4o-mini"

if not api_key:
    print(f"Błąd: brak klucza API dla providera '{AI_PROVIDER}'", file=sys.stderr)
    sys.exit(1)

if not HUB_API_KEY:
    print("Błąd: brak HUB_API_KEY w .env", file=sys.stderr)
    sys.exit(1)


# --- Structured output schema -----------------------------------------


class BatchTagItem(BaseModel):
    index: int
    tags: List[ALLOWED_TAGS]


class BatchJobTags(BaseModel):
    items: List[BatchTagItem]


# --- LLM client -------------------------------------------------------

client_kwargs = {"api_key": api_key}
if base_url:
    client_kwargs["base_url"] = base_url

ai = OpenAI(**client_kwargs)


def tag_jobs_batch(job_descriptions: list[str]) -> list[list[str]]:
    """Taguje wiele opisów naraz i zwraca listę tagów w kolejności wejściowej."""
    numbered_jobs = "\n\n".join(
        [f"[{i}] {desc}" for i, desc in enumerate(job_descriptions, start=1)]
    )

    response = ai.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś ekspertem od klasyfikacji zawodów. "
                    "Na podstawie opisu stanowiska pracy przypisz odpowiednie tagi z dozwolonej listy. "
                    "Możesz przypisać wiele tagów. Używaj wyłącznie podanych tagów.\n\n"
                    "Zwróć obiekt zawierający tablicę `items`. "
                    "Każdy element musi mieć: `index` (numer rekordu z wejścia) i `tags` (lista tagów). "
                    "Uwzględnij wszystkie rekordy wejściowe dokładnie raz.\n\n"
                    "Dostępne tagi:\n"
                    "- IT: praca z technologiami informacyjnymi, programowanie, systemy\n"
                    "- transport: przewóz osób lub towarów, kierowcy, logistyka, spedycja\n"
                    "- edukacja: nauczanie, szkolenie, wychowanie\n"
                    "- medycyna: opieka zdrowotna, diagnostyka, leczenie\n"
                    "- praca z ludźmi: bezpośredni kontakt z klientem/pacjentem/uczniem\n"
                    "- praca z pojazdami: obsługa, naprawa lub prowadzenie pojazdów\n"
                    "- praca fizyczna: praca manualna, rzemiosło, budownictwo"
                ),
            },
            {
                "role": "user",
                "content": (
                    "Przypisz tagi do każdego opisu poniżej. "
                    "Lista opisów (ponumerowana):\n\n"
                    f"{numbered_jobs}"
                ),
            },
        ],
        response_format=BatchJobTags,
    )

    parsed = response.choices[0].message.parsed
    if not parsed:
        return [[] for _ in job_descriptions]

    by_index = {item.index: item.tags for item in parsed.items}
    return [by_index.get(i, []) for i in range(1, len(job_descriptions) + 1)]


# --- CSV processing ---------------------------------------------------

def birth_year(birth_date_str: str) -> int:
    """Ekstrahuje rok urodzenia z daty w formacie YYYY-MM-DD."""
    return int(birth_date_str.split("-")[0])


def age_in_2026(year: int) -> int:
    return CURRENT_YEAR - year


def load_and_filter_csv(path: Path) -> list[dict]:
    """Wczytuje CSV i filtruje wg płci, miejsca urodzenia i wieku."""
    filtered = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            gender = row.get("gender", "").strip()
            city = row.get("birthPlace", "").strip()
            b_year = birth_year(row.get("birthDate", "1900-01-01"))
            age = age_in_2026(b_year)

            if gender == TARGET_GENDER and city == TARGET_CITY and AGE_MIN <= age <= AGE_MAX:
                filtered.append(row)
    return filtered


def load_and_filter_csv_from_hub() -> list[dict]:
    """Pobiera CSV z HUB i filtruje wg płci, miejsca urodzenia i wieku."""
    data_url = f"{HUB_URL}/data/{HUB_API_KEY}/people.csv"
    response = requests.get(data_url, timeout=30)
    response.raise_for_status()

    filtered = []
    csv_stream = StringIO(response.text)
    reader = csv.DictReader(csv_stream)

    for row in reader:
        gender = row.get("gender", "").strip()
        city = row.get("birthPlace", "").strip()
        b_year = birth_year(row.get("birthDate", "1900-01-01"))
        age = age_in_2026(b_year)

        if gender == TARGET_GENDER and city == TARGET_CITY and AGE_MIN <= age <= AGE_MAX:
            filtered.append(row)

    return filtered


# --- Main -------------------------------------------------------------

def main():
    data_url = f"{HUB_URL}/data/{HUB_API_KEY}/people.csv"
    print(f"1. Pobieranie danych z {data_url}...")
    candidates = load_and_filter_csv_from_hub()
    print(f"   Po filtrze (płeć={TARGET_GENDER}, miasto={TARGET_CITY}, wiek {AGE_MIN}-{AGE_MAX}): {len(candidates)} osób\n")

    if not candidates:
        print("Brak kandydatów po filtrowaniu. Sprawdź plik CSV.")
        sys.exit(0)

    print("2. Tagowanie zawodów przez LLM (structured output, batch)...")
    tagged = []
    batch_size = 20
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start : batch_start + batch_size]
        jobs = [person.get("job", "") for person in batch]
        print(
            f"   Batch {batch_start + 1}-{batch_start + len(batch)}/{len(candidates)}: tagowanie..."
        )
        batch_tags = tag_jobs_batch(jobs)

        for person, tags in zip(batch, batch_tags):
            name_full = f"{person['name']} {person['surname']}"
            print(f"      {name_full}: {tags}")
            tagged.append({**person, "resolved_tags": tags})

    print()
    print("3. Filtrowanie po tagu 'transport'...")
    transport_people = [p for p in tagged if TARGET_TAG in p["resolved_tags"]]
    print(f"   Znaleziono: {len(transport_people)} osób\n")

    if not transport_people:
        print("Żadna osoba nie ma tagu 'transport'. Sprawdź dane i prompty.")
        sys.exit(0)

    # Format odpowiedzi
    answer = [
        {
            "name": p["name"],
            "surname": p["surname"],
            "gender": p["gender"],
            "born": birth_year(p["birthDate"]),
            "city": p["birthPlace"],
            "tags": p["resolved_tags"],
        }
        for p in transport_people
    ]

    print("4. Odpowiedź do wysłania:")
    print(json.dumps(answer, ensure_ascii=False, indent=2))
    print()

    print(f"5. Wysyłanie do {HUB_URL}/verify (task={TASK_NAME})...")
    payload = {
        "task": TASK_NAME,
        "apikey": HUB_API_KEY,
        "answer": answer,
    }
    resp = requests.post(
        f"{HUB_URL}/verify",
        json=payload,
        timeout=30,
        headers={"Content-Type": "application/json"},
    )
    print(f"   Status HTTP: {resp.status_code}")
    try:
        result = resp.json()
        print(f"   Odpowiedź: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception:
        print(f"   Odpowiedź (raw): {resp.text}")


if __name__ == "__main__":
    main()
