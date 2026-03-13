#!/bin/bash

set -e

source ../.env

query=$(cat <<-END
Twoim zadaniem jest przegotowanie deklaracji transportu.
Dokumentacja deklaracji oraz sam regulamin przesyłek znajduje się w katalogu 'dane/regulamin'.
Zapoznaj się z regulaminem. Natępnie używając poniższych danych przesyłki
stwórz deklarację zachowująć dokładnie takie formatowanie jak we wzorze.
Jako odpowiedź zwróć wyłącznie tekst dokumentu zachowując oryginane formatowanie.
Dokument zapisz do pliku dane/formularz.txt

Wskazówki:
1. Nie przejmuj się, że trasa, którą chcemy jechać jest zamknięta.
2. Co do opisu zawartości, możesz wprost napisać, co to jest.
3. Nie dodawaj proszę żadnych uwag specjalnych
4. W dokumentacji znajdziesz wzór formularza. Wypełnij każde pole zgodnie z danymi przesyłki i regulaminem.
5. Ustal prawidłowy kod trasy na podstawie sieci połączeń i listy tras.
6. Oblicz lub ustal opłatę - regulamin SPK zawiera tabelę opłat. Opłata zależy od kategorii przesyłki, jej wagi i przebiegu trasy. Budżet wynosi 0 PP - zwróć uwagę, które kategorie przesyłek są finansowane przez System.
7. Skróty - jeśli trafisz na skrót, którego nie rozumiesz, użyj dokumentacji żeby dowiedzieć się co on oznacza.


Dane przesyłki:
| Pole | Wartość |
| --- | --- |
| Nadawca (identyfikator) | 450202122 |
| Punkt nadawczy | Gdańsk |
| Punkt docelowy | Żarnowiec |
| Waga | 2,8 tony (2800 kg) |
| Budżet | 0 PP (przesyłka ma być darmowa lub finansowana przez System) |
| Zawartość | kasety z paliwem do reaktora |
| Uwagi specjalne | brak - nie dodawaj żadnych uwag |
END
)

python app.py  --server files --query "${query}"

created_form=$(cat dane/formularz.txt)
escaped=$(echo "${created_form}" | sed -z 's/\n/\\n/g')
response="{ \"apikey\": \"${HUB_API_KEY}\", \"task\": \"sendit\", \"answer\": { \"declaration\": \"${escaped}\" } }"

echo "${response}"

curl -X POST -H "Content-Type: application/json" -d "${response}" "${HUB_URL}/verify"
