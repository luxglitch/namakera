#!/usr/bin/env bash
# llama.cpp build manager — install, update, uninstall via text menus

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_INSTALL_DIR="$HOME/.local"
DEFAULT_SOURCE_DIR="$HOME/src/llama.cpp"
CONFIG_FILE="$HOME/.config/llamacpp-manager.conf"
REPO_URL="https://github.com/ggerganov/llama.cpp.git"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
msg()     { echo -e "${CYAN}${BOLD}==> ${RESET}${BOLD}$*${RESET}"; }
ok()      { echo -e "${GREEN}${BOLD}✔ ${RESET}$*"; }
warn()    { echo -e "${YELLOW}${BOLD}! ${RESET}$*"; }
err()     { echo -e "${RED}${BOLD}✘ ${RESET}$*" >&2; }
die()     { err "$*"; exit 1; }
hr()      { printf '%*s\n' "${COLUMNS:-60}" '' | tr ' ' '─'; }

pause() {
    echo
    read -rp "  Press Enter to continue..."
}

confirm() {
    local prompt="${1:-Are you sure?}"
    local answer
    echo -e "${YELLOW}${BOLD}  ${prompt} [y/N]:${RESET} " >&2
    read -r answer
    [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}

load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$CONFIG_FILE"
    fi
    INSTALL_DIR="${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
    SOURCE_DIR="${SOURCE_DIR:-$DEFAULT_SOURCE_DIR}"
    CMAKE_EXTRA="${CMAKE_EXTRA:-}"
}

save_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" <<EOF
# llama.cpp manager config — auto-generated
INSTALL_DIR="$INSTALL_DIR"
SOURCE_DIR="$SOURCE_DIR"
CMAKE_EXTRA="$CMAKE_EXTRA"
EOF
    ok "Config saved to $CONFIG_FILE"
}

# ── Dependency check ──────────────────────────────────────────────────────────
check_deps() {
    local missing=()
    for cmd in git cmake make gcc g++; do
        command -v "$cmd" &>/dev/null || missing+=("$cmd")
    done
    if (( ${#missing[@]} > 0 )); then
        err "Missing required tools: ${missing[*]}"
        echo "  Install them, e.g.:"
        echo "    sudo pacman -S base-devel cmake git        # Arch"
        echo "    sudo apt install build-essential cmake git # Debian/Ubuntu"
        return 1
    fi
    return 0
}

# ── GPU / backend detection ───────────────────────────────────────────────────
detect_backends() {
    AVAILABLE_BACKENDS=("none (CPU only)")
    command -v nvcc  &>/dev/null && AVAILABLE_BACKENDS+=("CUDA (Nvidia)")
    command -v hipcc &>/dev/null && AVAILABLE_BACKENDS+=("HIP (AMD ROCm)")
    [[ -f /usr/include/vulkan/vulkan.h || -d /usr/include/vulkan ]] \
        && AVAILABLE_BACKENDS+=("Vulkan")
    command -v pkg-config &>/dev/null && pkg-config --exists openblas 2>/dev/null \
        && AVAILABLE_BACKENDS+=("OpenBLAS")
}

# ── Build-option menu ─────────────────────────────────────────────────────────
pick_backend() {
    detect_backends
    echo
    echo -e "${BOLD}  Select compute backend:${RESET}"
    hr
    local i=1
    for b in "${AVAILABLE_BACKENDS[@]}"; do
        printf "   %2d) %s\n" "$i" "$b"
        (( i++ ))
    done
    hr
    local choice
    while true; do
        read -rp "  Choice [1-${#AVAILABLE_BACKENDS[@]}]: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#AVAILABLE_BACKENDS[@]} )); then
            break
        fi
        warn "Enter a number between 1 and ${#AVAILABLE_BACKENDS[@]}"
    done

    local selected="${AVAILABLE_BACKENDS[$((choice-1))]}"
    CMAKE_EXTRA="-DGGML_NATIVE=ON"

    case "$selected" in
        CUDA*)   CMAKE_EXTRA+=" -DGGML_CUDA=ON" ;;
        HIP*)    CMAKE_EXTRA+=" -DGGML_HIP=ON" ;;
        Vulkan*) CMAKE_EXTRA+=" -DGGML_VULKAN=ON" ;;
        OpenBLAS*) CMAKE_EXTRA+=" -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS" ;;
    esac
    ok "Selected: $selected"
    ok "CMake flags: $CMAKE_EXTRA"
}

configure_paths() {
    echo
    echo -e "${BOLD}  Configure paths${RESET}"
    hr
    echo -e "  Source directory [${CYAN}$SOURCE_DIR${RESET}]:"
    read -rp "  (Enter to keep) > " input
    [[ -n "$input" ]] && SOURCE_DIR="$input"

    echo -e "  Install prefix  [${CYAN}$INSTALL_DIR${RESET}]:"
    read -rp "  (Enter to keep) > " input
    [[ -n "$input" ]] && INSTALL_DIR="$input"
}

# ── Core actions ──────────────────────────────────────────────────────────────
do_install() {
    echo
    msg "Install llama.cpp from source"
    hr

    if [[ -d "$SOURCE_DIR/.git" ]]; then
        warn "Source directory already exists: $SOURCE_DIR"
        if ! confirm "Re-use existing clone (skip git clone)?"; then
            return
        fi
    else
        configure_paths
        pick_backend
        save_config
        msg "Cloning repository..."
        git clone "$REPO_URL" "$SOURCE_DIR"
    fi

    build_and_install
}

do_update() {
    echo
    msg "Update llama.cpp"
    hr

    if [[ ! -d "$SOURCE_DIR/.git" ]]; then
        err "Source not found at $SOURCE_DIR — install first."
        pause; return
    fi

    msg "Fetching latest changes..."
    git -C "$SOURCE_DIR" fetch origin

    local local_ref remote_ref
    local_ref=$(git -C "$SOURCE_DIR" rev-parse HEAD)
    remote_ref=$(git -C "$SOURCE_DIR" rev-parse '@{u}' 2>/dev/null || echo "unknown")

    if [[ "$local_ref" == "$remote_ref" ]]; then
        ok "Already up to date ($(git -C "$SOURCE_DIR" describe --tags --always))"
        pause; return
    fi

    echo
    echo "  Current: $(git -C "$SOURCE_DIR" describe --tags --always)"
    echo "  Remote:  $(git -C "$SOURCE_DIR" describe --tags --always FETCH_HEAD 2>/dev/null || echo 'newer')"
    echo

    if ! confirm "Pull and rebuild?"; then
        return
    fi

    msg "Pulling..."
    git -C "$SOURCE_DIR" pull --ff-only

    # Optionally re-pick backend
    echo
    echo -e "  Current CMake flags: ${CYAN}${CMAKE_EXTRA}${RESET}"
    if confirm "Change compute backend / build flags?"; then
        pick_backend
        save_config
    fi

    build_and_install
}

build_and_install() {
    local build_dir="$SOURCE_DIR/build"

    msg "Configuring with CMake..."
    # shellcheck disable=SC2086
    cmake -S "$SOURCE_DIR" -B "$build_dir" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$INSTALL_DIR" \
        -DLLAMA_BUILD_TESTS=OFF \
        $CMAKE_EXTRA

    local nproc
    nproc=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)

    msg "Building with $nproc threads..."
    cmake --build "$build_dir" --config Release -j "$nproc"

    msg "Installing to $INSTALL_DIR ..."
    cmake --install "$build_dir"

    echo
    ok "Build complete!"
    ok "Binaries installed to: $INSTALL_DIR/bin/"

    # Hint if install dir not in PATH
    if ! echo ":$PATH:" | grep -q ":$INSTALL_DIR/bin:"; then
        warn "$INSTALL_DIR/bin is not in your PATH."
        echo "  Add to your shell config:"
        echo "    export PATH=\"$INSTALL_DIR/bin:\$PATH\""
    fi
    pause
}

do_uninstall() {
    echo
    msg "Uninstall llama.cpp"
    hr

    local build_dir="$SOURCE_DIR/build"
    local manifest="$build_dir/install_manifest.txt"

    if [[ ! -f "$manifest" ]]; then
        warn "No install manifest found at $manifest"
        warn "Cannot determine which files were installed."
        if confirm "Remove source directory $SOURCE_DIR anyway?"; then
            rm -rf "$SOURCE_DIR"
            ok "Source directory removed."
        fi
        pause; return
    fi

    echo "  Files to remove:"
    cat "$manifest" | sed 's/^/    /'
    echo

    if ! confirm "Remove these files + source directory?"; then
        return
    fi

    while IFS= read -r f; do
        [[ -f "$f" ]] && rm -f "$f" && echo "  removed $f"
    done < "$manifest"

    if confirm "Also remove source directory $SOURCE_DIR?"; then
        rm -rf "$SOURCE_DIR"
        ok "Source directory removed."
    fi

    rm -f "$CONFIG_FILE"
    ok "Uninstall complete."
    pause
}

show_status() {
    echo
    msg "Status"
    hr
    echo -e "  Source dir   : ${CYAN}$SOURCE_DIR${RESET}"
    echo -e "  Install dir  : ${CYAN}$INSTALL_DIR${RESET}"
    echo -e "  CMake flags  : ${CYAN}${CMAKE_EXTRA:-'(default)'}${RESET}"
    echo

    if [[ -d "$SOURCE_DIR/.git" ]]; then
        local tag
        tag=$(git -C "$SOURCE_DIR" describe --tags --always 2>/dev/null || echo "unknown")
        ok "Source cloned — version: $tag"

        local behind
        git -C "$SOURCE_DIR" fetch origin --dry-run &>/dev/null 2>&1 || true
        behind=$(git -C "$SOURCE_DIR" rev-list HEAD..@{u} --count 2>/dev/null || echo "?")
        if [[ "$behind" != "0" && "$behind" != "?" ]]; then
            warn "$behind commit(s) behind upstream — consider updating."
        elif [[ "$behind" == "0" ]]; then
            ok "Up to date with upstream."
        fi
    else
        warn "Source not found — not installed."
    fi

    echo
    local llama_bin
    if llama_bin=$(command -v llama-cli 2>/dev/null || command -v llama 2>/dev/null || command -v main 2>/dev/null); then
        ok "Executable found: $llama_bin"
        "$llama_bin" --version 2>/dev/null || true
    else
        warn "llama-cli / llama not found in PATH."
    fi
    pause
}

# ── Main menu ─────────────────────────────────────────────────────────────────
main_menu() {
    while true; do
        clear
        echo
        echo -e "${BOLD}${CYAN}  ╔══════════════════════════════╗${RESET}"
        echo -e "${BOLD}${CYAN}  ║   llama.cpp Build Manager    ║${RESET}"
        echo -e "${BOLD}${CYAN}  ╚══════════════════════════════╝${RESET}"
        echo
        echo -e "   ${BOLD}1)${RESET} Install  (clone + build + install)"
        echo -e "   ${BOLD}2)${RESET} Update   (pull + rebuild)"
        echo -e "   ${BOLD}3)${RESET} Status"
        echo -e "   ${BOLD}4)${RESET} Change paths / backend flags"
        echo -e "   ${BOLD}5)${RESET} Uninstall"
        echo -e "   ${BOLD}q)${RESET} Quit"
        echo
        hr
        read -rp "  Choice: " choice
        case "$choice" in
            1) check_deps && do_install ;;
            2) check_deps && do_update ;;
            3) show_status ;;
            4)
                configure_paths
                pick_backend
                save_config
                pause
                ;;
            5) do_uninstall ;;
            q|Q|quit|exit) echo; ok "Bye!"; exit 0 ;;
            *) warn "Invalid choice" ;;
        esac
    done
}

# ── Entry point ───────────────────────────────────────────────────────────────
load_config
main_menu
