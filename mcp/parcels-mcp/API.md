#### API paczek

Zewnętrzne API paczek dostępne pod adresem: `${HUB_URL}/api/packages`

Obsługuje dwie akcje (obie metodą `POST`, body jako raw JSON):

**Sprawdzenie statusu paczki (check):**

```json
{
  "apikey": "tutaj-twoj-klucz-api",
  "action": "check",
  "packageid": "PKG12345678"
}
```

Zwraca informacje o statusie i lokalizacji paczki.

**Przekierowanie paczki (redirect):**

```json
{
  "apikey": "tutaj-twoj-klucz-api",
  "action": "redirect",
  "packageid": "PKG12345678",
  "destination": "PWR3847PL",
  "code": "tutaj-wklej-kod-zabezpieczajacy"
}
```

Pole `code` to kod zabezpieczający, który operator poda podczas rozmowy. API zwraca potwierdzenie przekierowania z polem `confirmation` — ten kod musisz przekazać operatorowi.
