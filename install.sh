#!/bin/bash
# Skrypt do automatycznej instalacji, aktualizacji i backupu aplikacji TibiaVision.
# Wersja poprawiona - rozwiązuje problem uprawnień Docker i inteligentnie wykrywa wersję docker-compose.

# Zatrzymaj wykonywanie skryptu w przypadku błędu
set -e

# --- Zmienne Konfiguracyjne ---
GIT_REPO_URL="https://github.com/Clobersik/TibiaVision_Web.git"
APP_DIR_NAME="TibiaVision_Web" 
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
    
    # Wykryj poprawną komendę docker compose
    COMPOSE_CMD="docker-compose"
    if ! command -v docker-compose &> /dev/null && docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    fi

    # Skrypt do bezpiecznego restartu
    cat > "$APP_DIR/restart_safe.sh" <<EOF
#!/bin/bash
cd "$(dirname "\$0")"
# Uruchom skrypt sprawdzający wewnątrz kontenera, aby mieć dostęp do zależności
if sudo $COMPOSE_CMD exec -T web python app/check_active.py > /dev/null 2>&1; then
    echo "Brak aktywnych zadan. Restartowanie uslug... \$(date)" >> cron.log
    sudo $COMPOSE_CMD restart
else
    echo "Wykryto aktywne zadanie. Pomijanie restartu. \$(date)" >> cron.log
fi
EOF
    chmod +x "$APP_DIR/restart_safe.sh"

    # Skrypt do backupu (wywoływany przez cron)
    cat > "$APP_DIR/backup_cron.sh" <<'EOF'
#!/bin/bash
INSTALL_SCRIPT_PATH="$(dirname "$0")/../install.sh"
bash "$INSTALL_SCRIPT_PATH" backup >> "$(dirname "$0")/cron.log" 2>&1
EOF
    chmod +x "$APP_DIR/backup_cron.sh"

    # Dodawanie zadań do crontab
    (crontab -l 2>/dev/null | grep -v "TibiaVision") | crontab -
    (crontab -l 2>/dev/null; echo "0 4 * * * $APP_DIR/restart_safe.sh # TibiaVision Daily Safe Restart") | crontab -
    (crontab -l 2>/dev/null; echo "0 */${BACKUP_INTERVAL:-6} * * * $APP_DIR/backup_cron.sh # TibiaVision Periodic Backup") | crontab -

    print_success "Zadania CRON skonfigurowane."
}

# --- Logika Instalacji ---
do_install() {
    print_info "Rozpoczynanie nowej instalacji TibiaVision..."
    print_info "Sprawdzanie zależności..."
    if ! command -v git &> /dev/null; then apt-get update > /dev/null && apt-get install -y git; fi
    
    if ! command -v docker &> /dev/null; then
        print_info "Instalowanie Docker za pomocą oficjalnego skryptu..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        usermod -aG docker ${SUDO_USER:-$USER}
        print_info "Użytkownik ${SUDO_USER:-$USER} dodany do grupy docker. Zmiany będą aktywne po ponownym zalogowaniu."
    fi
    
    if ! docker compose version &> /dev/null && ! command -v docker-compose &> /dev/null; then
        print_info "Instalowanie Docker Compose (standalone)..."
        curl -L "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    print_success "Zależności zainstalowane."

    if [ -d "$APP_DIR_NAME" ]; then print_error "Katalog '$APP_DIR_NAME' już istnieje."; fi
    print_info "Klonowanie repozytorium (przez HTTPS)..."
    git clone "$GIT_REPO_URL" "$APP_DIR_NAME"
    cd "$APP_DIR_NAME" || exit
    if [ ! -f "map.png" ]; then touch map.png; fi
    
    # Wykryj poprawną komendę docker compose
    COMPOSE_CMD="docker-compose"
    if ! command -v docker-compose &> /dev/null && docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    fi

    print_info "Budowanie i uruchamianie kontenerów (z sudo)..."
    sudo $COMPOSE_CMD up --build -d
    
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
    
    # Wykryj poprawną komendę docker compose
    COMPOSE_CMD="docker-compose"
    if ! command -v docker-compose &> /dev/null && docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    fi

    print_info "Przebudowywanie i restartowanie kontenerów (z sudo)..."
    sudo $COMPOSE_CMD up --build -d
    
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
