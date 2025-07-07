#!/bin/bash
# Skrypt do automatycznej instalacji, aktualizacji, backupu i konfiguracji cron dla TibiaVision.
# Użycie:
#   Instalacja: curl -sSL [URL] | sudo bash -s install
#   Aktualizacja: curl -sSL [URL] | sudo bash -s update
#   Backup: curl -sSL [URL] | sudo bash -s backup

# Zatrzymaj wykonywanie skryptu w przypadku błędu
set -e

# --- Zmienne Konfiguracyjne ---
GIT_REPO_URL="git@github.com:clobersik/TibiaVision_Webo.git" 
APP_DIR_NAME="TibiaVision_Web"
# Pełna ścieżka do katalogu aplikacji
APP_DIR="$(pwd)/$APP_DIR_NAME"
BACKUP_DIR="$(pwd)/tibia-vision-backups"

# --- Funkcje Pomocnicze ---
print_info() { echo -e "\e[34m[INFO]\e[0m $1"; }
print_success() { echo -e "\e[32m[SUCCESS]\e[0m $1"; }
print_error() { echo -e "\e[31m[ERROR]\e[0m $1"; exit 1; }

# --- Logika Backupu ---
do_backup() {
    print_info "Tworzenie kopii zapasowej..."
    if [ ! -d "$APP_DIR" ]; then print_error "Katalog aplikacji '$APP_DIR' nie znaleziony."; fi
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILENAME="backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    BACKUP_PATH="$BACKUP_DIR/$BACKUP_FILENAME"
    print_info "Kompresowanie danych do pliku: $BACKUP_PATH"
    tar -czf "$BACKUP_PATH" -C "$APP_DIR" app/database app/output
    print_success "Kopia zapasowa została pomyślnie utworzona."
}

# --- Logika Konfiguracji Cron ---
setup_cron_jobs() {
    print_info "Konfigurowanie zadan CRON..."
    
    # Skrypt do bezpiecznego restartu
    cat > "$APP_DIR/restart_safe.sh" <<'EOF'
#!/bin/bash
# Ten skrypt jest wywoływany przez cron.
# Restartuje kontenery Docker tylko wtedy, gdy żadne zadanie nie jest przetwarzane.
cd "$(dirname "$0")"
# Uruchom skrypt sprawdzający wewnątrz kontenera, aby mieć dostęp do zależności
if docker-compose exec -T web python app/check_active.py > /dev/null 2>&1; then
    echo "Brak aktywnych zadan. Restartowanie uslug... $(date)" >> cron.log
    docker-compose restart
else
    echo "Wykryto aktywne zadanie. Pomijanie restartu. $(date)" >> cron.log
fi
EOF
    chmod +x "$APP_DIR/restart_safe.sh"

    # Skrypt do backupu (wywoływany przez cron)
    cat > "$APP_DIR/backup_cron.sh" <<'EOF'
#!/bin/bash
cd "$(dirname "$0")"
# Wywołaj główny skrypt z akcją backup
# Przekieruj wyjście do logu
bash ../install.sh backup >> cron.log 2>&1
EOF
    chmod +x "$APP_DIR/backup_cron.sh"

    # Dodawanie zadań do crontab
    (crontab -l 2>/dev/null | grep -v "TibiaVision") | crontab -
    (crontab -l 2>/dev/null; echo "0 4 * * * $APP_DIR/restart_safe.sh # TibiaVision Daily Safe Restart") | crontab -
    (crontab -l 2>/dev/null; echo "0 */${BACKUP_INTERVAL:-6} * * * $APP_DIR/backup_cron.sh # TibiaVision Periodic Backup") | crontab -

    print_success "Zadania CRON skonfigurowane."
    print_info "Codzienny restart o 4:00 rano."
    print_info "Okresowy backup co ${BACKUP_INTERVAL:-6} godzin."
}

# --- Logika Instalacji ---
do_install() {
    print_info "Rozpoczynanie nowej instalacji TibiaVision..."
    # Instalacja zależności (git, docker, docker-compose)...
    # ... (kod instalacji zależności pozostaje bez zmian) ...
    print_info "Sprawdzanie zależności..."
    if ! command -v git &> /dev/null; then apt-get update > /dev/null && apt-get install -y git; fi
    if ! command -v docker &> /dev/null; then apt-get update > /dev/null && apt-get install -y apt-transport-https ca-certificates curl software-properties-common && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && apt-get update > /dev/null && apt-get install -y docker-ce docker-ce-cli containerd.io && usermod -aG docker ${SUDO_USER:-$USER}; fi
    if ! command -v docker-compose &> /dev/null; then curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose; fi
    print_success "Zależności zainstalowane."

    if [ -d "$APP_DIR_NAME" ]; then print_error "Katalog '$APP_DIR_NAME' już istnieje."; fi
    print_info "Klonowanie repozytorium..."
    git clone "$GIT_REPO_URL" "$APP_DIR_NAME"
    cd "$APP_DIR_NAME" || exit
    if [ ! -f "map.png" ]; then touch map.png; fi
    
    print_info "Budowanie i uruchamianie kontenerów..."
    docker-compose up --build -d
    
    # Konfiguracja Cron po instalacji
    read -p "Co ile godzin chcesz wykonywac automatyczny backup? (np. 6, 12, 24) [6]: " BACKUP_INTERVAL
    setup_cron_jobs
    
    print_success "Aplikacja TibiaVision została pomyślnie zainstalowana!"
    print_info "Dostępna pod adresem: http://$(curl -s ifconfig.me):8080"
}

# --- Logika Aktualizacji ---
do_update() {
    print_info "Rozpoczynanie aktualizacji TibiaVision..."
    do_backup
    cd "$APP_DIR" || print_error "Nie można wejść do katalogu aplikacji."
    print_info "Pobieranie najnowszych zmian z Git..."
    git pull
    print_info "Przebudowywanie i restartowanie kontenerów..."
    docker-compose up --build -d
    # Ponowna konfiguracja crona, na wypadek zmian w skryptach
    setup_cron_jobs
    print_success "Aplikacja TibiaVision została pomyślnie zaktualizowana!"
}

# --- Główny Punkt Wejścia Skryptu ---
main() {
    if [ "$(id -u)" -ne 0 ]; then print_error "Ten skrypt musi być uruchomiony z uprawnieniami roota (sudo)."; fi
    ACTION=${1:-install}
    case "$ACTION" in
        install) do_install ;;
        update) do_update ;;
        backup) do_backup ;;
        *) print_error "Nieznana akcja: '$ACTION'. Użyj 'install', 'update' lub 'backup'." ;;
    esac
}

main "$@"

