#!/usr/bin/env python3
"""
Zadanie: findhim
Podejście agentowe z Function Calling:
- model sam iteruje po podejrzanych,
- pobiera lokalizacje i porównuje je do elektrowni (Haversine),
- ustala najbliższą osobę i elektrownię,
- pobiera accessLevel,
- wysyła odpowiedź do /verify.
"""

from src.config import MODEL, TASK_NAME
from src.executor import process_query
from src.tools import handlers, tools

instructions = """
You are an autonomous investigator solving task 'findhim'.
Use tools to gather data and compute the final answer.

Rules:
1) Start by loading suspects and power plants with tools.
2) For EACH suspect, fetch person locations and compute nearest power plant.
3) Compare all suspects and select the one with globally smallest distance to any power plant.
4) After selecting that person, fetch access level with correct birthYear.
5) Submit exactly one final answer using submit_findhim_answer.
6) Keep your final response concise and include selected person, power plant code and distance.

Do not invent data. Always rely on tool outputs.
""".strip()

query = """
Rozwiąż zadanie findhim end-to-end.
Użyj narzędzi, znajdź osobę najbliżej elektrowni atomowej,
pobierz accessLevel i wyślij odpowiedź do /verify.
""".strip()


if __name__ == "__main__":
    process_query(
        query,
        model=MODEL,
        tools=tools,
        handlers=handlers,
        instructions=instructions,
    )
