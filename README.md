Jak zarządzać aplikacją TibiaVision z automatycznym utrzymaniem
Skrypt instalacyjny został rozbudowany o funkcje automatycznego restartu i tworzenia kopii zapasowych za pomocą zadań cron.
Krok 1: Przygotowanie (bez zmian)
Kod w Git: Upewnij się, że cały kod aplikacji, włączając w to nowy plik app/check_active.py, znajduje się w Twoim repozytorium na GitHubie.
Skrypt install.sh: Skopiuj powyższy, zaktualizowany kod skryptu, wklej w nim URL do swojego repozytorium i udostępnij go online (np. przez GitHub Gist).
Krok 2: Instalacja i konfiguracja Cron
Zaloguj się na swój serwer VPS i wykonaj komendę instalacyjną:
curl -sSL [URL_DO_TWOJEGO_SKRYPTU] | sudo bash -s install


Podczas instalacji, skrypt poprosi Cię o podanie interwału (w godzinach) dla automatycznych kopii zapasowych.
Co ile godzin chcesz wykonywac automatyczny backup? (np. 6, 12, 24) [6]:


Możesz wcisnąć Enter, aby zaakceptować domyślną wartość (6 godzin), lub wpisać własną.
Po zakończeniu, skrypt automatycznie doda dwa zadania do systemu cron na Twoim serwerze:
Codzienny, bezpieczny restart: Każdego dnia o 4:00 rano, skrypt sprawdzi, czy aplikacja nie przetwarza wideo. Jeśli jest bezczynna, zrestartuje kontenery Docker.
Okresowy backup: Zgodnie z wybranym przez Ciebie interwałem, skrypt będzie tworzył spakowaną kopię zapasową danych.
Krok 3: Aktualizacja
Proces aktualizacji pozostaje taki sam. Użyj komendy:
curl -sSL [URL_DO_TWOJEGO_SKRYPTU] | sudo bash -s update


Podczas aktualizacji, skrypt również odświeży zadania cron, na wypadek gdybyś wprowadził zmiany w logice restartu lub backupu.
Gdzie są logi i backupy?
Logi z zadań cron: W katalogu tibia-vision-app pojawi się plik cron.log, w którym znajdziesz informacje o wykonanych restartach i backupach.
Kopie zapasowe: Wszystkie backupy będą zapisywane w katalogu tibia-vision-backups (na tym samym poziomie co katalog aplikacji).
Dzięki tym zmianom, Twoja aplikacja jest teraz nie tylko łatwa do wdrożenia, ale również wyposażona w mechanizmy zapewniające jej długoterminową stabilność i bezpieczeństwo danych.
