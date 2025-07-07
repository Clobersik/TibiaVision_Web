TibiaVision z Automatycznym Utrzymaniem
Ten projekt zawiera aplikację TibiaVision wraz ze skryptem instalacyjnym, który automatyzuje proces wdrożenia, aktualizacji, restartów i tworzenia kopii zapasowych.

Wymagania wstępne
Przed rozpoczęciem instalacji upewnij się, że posiadasz:

Serwer VPS z systemem operacyjnym opartym na Debianie (np. Ubuntu).

Zainstalowany curl i sudo.

Podstawową wiedzę na temat pracy w terminalu Linux.

Instalacja
Proces instalacji jest w pełni zautomatyzowany. Wystarczy jedna komenda, aby pobrać, zainstalować i uruchomić aplikację oraz skonfigurować zadania cron do jej utrzymania.

Zaloguj się na swój serwer VPS przez SSH.

Wykonaj poniższą komendę, podmieniając [URL_DO_TWOJEGO_SKRYPTU] na bezpośredni link do Twojego pliku install.sh (np. z GitHub Gist).

Bash

curl -sSL [URL_DO_TWOJEGO_SKRYPTU] | sudo bash -s install
Podczas instalacji zostaniesz poproszony o zdefiniowanie interwału dla automatycznych kopii zapasowych.

Co ile godzin chcesz wykonywac automatyczny backup? (np. 6, 12, 24) [6]:
Możesz wpisać własną wartość (w godzinach) lub nacisnąć Enter, aby zaakceptować domyślne 6 godzin.

Po zakończeniu, aplikacja będzie uruchomiona w kontenerach Docker, a zadania cron zostaną dodane do systemu.

Automatyzacja i Zarządzanie
Skrypt instalacyjny konfiguruje dwa kluczowe zadania cron w celu zapewnienia stabilności i bezpieczeństwa danych aplikacji.

Automatyczny restart
Cel: Zapewnienie stabilnego działania aplikacji.

Harmonogram: Codziennie o godzinie 4:00 rano.

Działanie: Skrypt check_active.py sprawdza, czy aplikacja aktualnie przetwarza wideo. Jeśli jest bezczynna, kontenery Docker zostaną bezpiecznie zrestartowane. Jeśli jest aktywna, restart zostanie pominięty.

Automatyczne kopie zapasowe
Cel: Ochrona danych przed utratą.

Harmonogram: Zgodnie z interwałem zdefiniowanym podczas instalacji (np. co 6, 12 lub 24 godziny).

Działanie: Skrypt tworzy skompresowaną kopię zapasową (.tar.gz) całego katalogu z danymi aplikacji.

Logi i Kopie Zapasowe
Wszystkie pliki generowane przez skrypty utrzymania są łatwo dostępne.

Logi z zadań cron: Informacje o wykonanych restartach i backupach znajdziesz w pliku cron.log, który jest zlokalizowany w głównym katalogu aplikacji (tibia-vision-app).

Kopie zapasowe: Wszystkie archiwa z backupami są zapisywane w katalogu tibia-vision-backups, znajdującym się na tym samym poziomie co katalog aplikacji.

Aktualizacja Aplikacji
Aby zaktualizować aplikację do najnowszej wersji z Twojego repozytorium Git, użyj tej samej komendy co przy instalacji, zmieniając jedynie argument z install na update.

Bash

curl -sSL [URL_DO_TWOJEGO_SKRYPTU] | sudo bash -s update
Proces aktualizacji pobierze najnowszy kod, przebuduje kontenery Docker i odświeży zadania cron, aby uwzględnić ewentualne zmiany w logice utrzymania.
