#!/usr/bin/env python3
"""namakera — llama.cpp build manager with pytermgui TUI."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytermgui as ptg

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_URL = "https://github.com/ggerganov/llama.cpp.git"
CONFIG_FILE = Path.home() / ".config" / "namakera.conf"
DEFAULT_SOURCE = Path.home() / "src" / "llama.cpp"
DEFAULT_PREFIX = Path.home() / ".local"

# ── Config ────────────────────────────────────────────────────────────────────
config: dict[str, str] = {
    "source_dir": str(DEFAULT_SOURCE),
    "install_dir": str(DEFAULT_PREFIX),
    "cmake_extra": "-DGGML_NATIVE=ON",
}


def load_config() -> None:
    if not CONFIG_FILE.exists():
        return
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip().lower()
        v = v.strip().strip('"')
        if k in config:
            config[k] = v


def save_config() -> None:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# namakera config — auto-generated"]
    for k, v in config.items():
        lines.append(f'{k}="{v}"')
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


# ── Dependency / backend detection ────────────────────────────────────────────
REQUIRED_DEPS = ["git", "cmake", "make", "gcc", "g++"]


def which(cmd: str) -> bool:
    return subprocess.run(["which", cmd], capture_output=True).returncode == 0


def missing_deps() -> list[str]:
    return [d for d in REQUIRED_DEPS if not which(d)]


def detect_backends() -> list[tuple[str, str]]:
    """Return list of (label, cmake_flags) for available backends."""
    backends = [("CPU only (no acceleration)", "-DGGML_NATIVE=ON")]
    if which("nvcc"):
        backends.append(("CUDA  — Nvidia GPU", "-DGGML_NATIVE=ON -DGGML_CUDA=ON"))
    if which("hipcc"):
        backends.append(("HIP   — AMD ROCm GPU", "-DGGML_NATIVE=ON -DGGML_HIP=ON"))
    vulkan_paths = ["/usr/include/vulkan/vulkan.h", "/usr/local/include/vulkan/vulkan.h"]
    if any(Path(p).exists() for p in vulkan_paths):
        backends.append(("Vulkan — cross-vendor GPU", "-DGGML_NATIVE=ON -DGGML_VULKAN=ON"))
    try:
        r = subprocess.run(["pkg-config", "--exists", "openblas"], capture_output=True)
        if r.returncode == 0:
            backends.append(("OpenBLAS — CPU BLAS", "-DGGML_NATIVE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"))
    except FileNotFoundError:
        pass
    return backends


# ── Terminal helpers (run outside TUI) ────────────────────────────────────────
def run_outside_tui(fn):
    """Decorator: exits alt-buffer, runs fn(), waits for Enter, re-enters."""
    def wrapper(manager: ptg.WindowManager, *args, **kwargs):
        ptg.unset_alt_buffer()
        ptg.show_cursor()
        print()
        try:
            fn(*args, **kwargs)
        except KeyboardInterrupt:
            print("\n[interrupted]")
        print()
        input("  Press Enter to return to menu...")
        ptg.set_alt_buffer()
        ptg.hide_cursor()
        manager.draw()
    return wrapper


def shell(cmd: list[str], cwd: str | None = None) -> int:
    """Run a command with live output. Returns exit code."""
    print(f"\n  \033[36m$ {' '.join(cmd)}\033[0m")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def header(text: str) -> None:
    cols = os.get_terminal_size().columns
    print(f"\n\033[1;36m{'─' * cols}\033[0m")
    print(f"\033[1;97m  {text}\033[0m")
    print(f"\033[1;36m{'─' * cols}\033[0m")


# ── Core actions (run in plain terminal) ─────────────────────────────────────
def action_install() -> None:
    header("Install llama.cpp")
    source = Path(config["source_dir"])
    prefix = Path(config["install_dir"])

    missing = missing_deps()
    if missing:
        print(f"\n  \033[31m✘ Missing required tools: {', '.join(missing)}\033[0m")
        print("  Install them and try again.")
        return

    if source.is_dir() and (source / ".git").exists():
        print(f"  \033[33m! Source already exists at {source}\033[0m")
        print("  Skipping clone — proceeding to build.")
    else:
        print(f"  Cloning into {source} …")
        if shell(["git", "clone", REPO_URL, str(source)]) != 0:
            print("\033[31m  Clone failed.\033[0m")
            return

    _build_and_install(source, prefix)


def action_update() -> None:
    header("Update llama.cpp")
    source = Path(config["source_dir"])
    prefix = Path(config["install_dir"])

    if not (source / ".git").exists():
        print(f"  \033[31m✘ Source not found at {source}\033[0m")
        print("  Run Install first.")
        return

    print("  Fetching upstream…")
    shell(["git", "fetch", "origin"], cwd=str(source))

    local = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=str(source)
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "@{u}"], capture_output=True, text=True, cwd=str(source)
    ).stdout.strip()

    if local == remote:
        print("\n  \033[32m✔ Already up to date.\033[0m")
        return

    tag = subprocess.run(
        ["git", "describe", "--tags", "--always"],
        capture_output=True, text=True, cwd=str(source)
    ).stdout.strip()
    print(f"  Current: {tag}")
    print(f"  Update available — pulling…")
    shell(["git", "pull", "--ff-only"], cwd=str(source))
    _build_and_install(source, prefix)


def action_uninstall() -> None:
    header("Uninstall llama.cpp")
    source = Path(config["source_dir"])
    manifest = source / "build" / "install_manifest.txt"

    if not manifest.exists():
        print(f"  \033[33m! No install manifest found at {manifest}\033[0m")
        ans = input("  Remove source directory anyway? [y/N] ").strip().lower()
        if ans == "y":
            import shutil
            shutil.rmtree(source, ignore_errors=True)
            print(f"  \033[32m✔ Removed {source}\033[0m")
        return

    files = manifest.read_text().splitlines()
    print(f"\n  Files to remove ({len(files)} items):")
    for f in files[:10]:
        print(f"    {f}")
    if len(files) > 10:
        print(f"    … and {len(files) - 10} more")

    ans = input("\n  Confirm removal? [y/N] ").strip().lower()
    if ans != "y":
        print("  Cancelled.")
        return

    for f in files:
        p = Path(f)
        if p.exists():
            p.unlink()
            print(f"  removed {p}")

    ans2 = input(f"\n  Also remove source directory {source}? [y/N] ").strip().lower()
    if ans2 == "y":
        import shutil
        shutil.rmtree(source, ignore_errors=True)
        print(f"  \033[32m✔ Removed {source}\033[0m")

    CONFIG_FILE.unlink(missing_ok=True)
    print("\n  \033[32m✔ Uninstall complete.\033[0m")


def action_status() -> None:
    header("Status")
    source = Path(config["source_dir"])
    prefix = Path(config["install_dir"])

    print(f"  Source dir   : {source}")
    print(f"  Install dir  : {prefix}")
    print(f"  CMake flags  : {config['cmake_extra']}")
    print()

    if (source / ".git").exists():
        tag = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True, text=True, cwd=str(source)
        ).stdout.strip()
        print(f"  \033[32m✔ Source cloned — version: {tag}\033[0m")
        behind = subprocess.run(
            ["git", "rev-list", "HEAD..@{u}", "--count"],
            capture_output=True, text=True, cwd=str(source)
        ).stdout.strip()
        if behind and behind != "0":
            print(f"  \033[33m! {behind} commit(s) behind upstream — consider updating.\033[0m")
        elif behind == "0":
            print("  \033[32m✔ Up to date with upstream.\033[0m")
    else:
        print("  \033[33m! Source not found — not installed.\033[0m")

    print()
    for binary in ["llama-cli", "llama", "main"]:
        r = subprocess.run(["which", binary], capture_output=True, text=True)
        if r.returncode == 0:
            path = r.stdout.strip()
            print(f"  \033[32m✔ Binary found: {path}\033[0m")
            subprocess.run([path, "--version"], capture_output=False)
            break
    else:
        print("  \033[33m! llama-cli not found in PATH.\033[0m")
        bin_path = prefix / "bin"
        if str(bin_path) not in os.environ.get("PATH", ""):
            print(f"  \033[33m  Hint: add {bin_path} to your PATH.\033[0m")


def _build_and_install(source: Path, prefix: Path) -> None:
    build_dir = source / "build"
    nproc = os.cpu_count() or 4

    header("Configure")
    flags = config["cmake_extra"].split()
    cmake_cmd = [
        "cmake", "-S", str(source), "-B", str(build_dir),
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_INSTALL_PREFIX={prefix}",
        "-DLLAMA_BUILD_TESTS=OFF",
        *flags,
    ]
    if shell(cmake_cmd) != 0:
        print("\033[31m  Configure failed.\033[0m")
        return

    header(f"Build  ({nproc} threads)")
    if shell(["cmake", "--build", str(build_dir), "--config", "Release", "-j", str(nproc)]) != 0:
        print("\033[31m  Build failed.\033[0m")
        return

    header("Install")
    if shell(["cmake", "--install", str(build_dir)]) != 0:
        print("\033[31m  Install failed.\033[0m")
        return

    print(f"\n  \033[32m✔ Done! Binaries installed to {prefix}/bin/\033[0m")
    bin_path = prefix / "bin"
    if str(bin_path) not in os.environ.get("PATH", ""):
        print(f"\n  \033[33m! {bin_path} is not in PATH.\033[0m")
        print("  Add to your shell config:")
        print(f'    export PATH="{bin_path}:$PATH"')


# ── TUI helpers ───────────────────────────────────────────────────────────────
PALETTE = {
    "surface":   "#1e1e2e",
    "overlay":   "#313244",
    "text":      "#cdd6f4",
    "accent":    "#89b4fa",
    "green":     "#a6e3a1",
    "yellow":    "#f9e2af",
    "red":       "#f38ba8",
}


def _apply_styles() -> None:
    ptg.tim.alias("title",   f"bold {PALETTE['accent']}")
    ptg.tim.alias("label",   PALETTE["text"])
    ptg.tim.alias("dim",     PALETTE["overlay"])
    ptg.tim.alias("ok",      PALETTE["green"])
    ptg.tim.alias("warn",    PALETTE["yellow"])
    ptg.tim.alias("err",     PALETTE["red"])


def _modal(manager: ptg.WindowManager, title: str, body: str, on_yes=None) -> None:
    """Simple yes/no confirmation dialog."""

    def _close(_):
        manager -= win

    def _confirm(_):
        manager -= win
        if on_yes:
            on_yes()

    win = (
        ptg.Window(
            ptg.Label(f"[title]{title}"),
            ptg.Label(""),
            ptg.Label(f"[label]{body}"),
            ptg.Label(""),
            ptg.Splitter(
                ptg.Button("Yes", onclick=_confirm),
                ptg.Button("No",  onclick=_close),
            ),
            box=ptg.boxes.DOUBLE,
            width=52,
        )
        .set_title(f"[title] Confirm ")
        .center()
    )
    manager += win


def _alert(manager: ptg.WindowManager, title: str, lines: list[str]) -> None:
    """Simple info alert."""

    def _close(_):
        manager -= win

    widgets: list = [ptg.Label(f"[title]{title}"), ptg.Label("")]
    for line in lines:
        widgets.append(ptg.Label(f"[label]{line}"))
    widgets += [ptg.Label(""), ptg.Button("OK", onclick=_close)]

    win = (
        ptg.Window(*widgets, box=ptg.boxes.DOUBLE, width=56)
        .set_title(f"[title] Info ")
        .center()
    )
    manager += win


def _input_form(
    manager: ptg.WindowManager,
    title: str,
    fields: list[tuple[str, str]],
    on_submit,
) -> None:
    """Multi-field input form. fields = [(label, default), ...]"""

    inputs = [ptg.InputField(default, prompt=f"[label]{label}: ") for label, default in fields]

    def _submit(_):
        values = [inp.value for inp in inputs]
        manager -= win
        on_submit(values)

    def _cancel(_):
        manager -= win

    widgets: list = [ptg.Label(f"[title]{title}"), ptg.Label("")]
    widgets.extend(inputs)
    widgets += [
        ptg.Label(""),
        ptg.Splitter(
            ptg.Button("Confirm", onclick=_submit),
            ptg.Button("Cancel",  onclick=_cancel),
        ),
    ]

    win = (
        ptg.Window(*widgets, box=ptg.boxes.DOUBLE, width=62)
        .set_title(f"[title] {title} ")
        .center()
    )
    manager += win


def _backend_picker(manager: ptg.WindowManager, on_select) -> None:
    backends = detect_backends()

    def _pick(idx: int):
        def handler(_):
            config["cmake_extra"] = backends[idx][1]
            save_config()
            manager -= win
            on_select()
        return handler

    def _cancel(_):
        manager -= win

    buttons = [ptg.Button(label, onclick=_pick(i)) for i, (label, _) in enumerate(backends)]
    widgets = [ptg.Label("[title]Select compute backend"), ptg.Label("")] + buttons + [
        ptg.Label(""),
        ptg.Button("Cancel", onclick=_cancel),
    ]

    win = (
        ptg.Window(*widgets, box=ptg.boxes.DOUBLE, width=52)
        .set_title("[title] Backend ")
        .center()
    )
    manager += win


# ── Wrapped actions (enter/exit alt-buffer around real terminal output) ───────
def _run_action(manager: ptg.WindowManager, fn) -> None:
    """Exit TUI, run fn, wait for Enter, re-draw."""
    ptg.unset_alt_buffer()
    ptg.show_cursor()
    try:
        fn()
    except KeyboardInterrupt:
        print("\n  [interrupted]")
    print()
    input("  Press Enter to return to menu…")
    ptg.set_alt_buffer()
    ptg.hide_cursor()
    manager.draw()


# ── Main TUI ──────────────────────────────────────────────────────────────────
def build_ui(manager: ptg.WindowManager) -> None:

    # ── Install flow ──────────────────────────────────────────────────────
    def start_install(_):
        def _after_paths(values):
            config["source_dir"], config["install_dir"] = values
            save_config()
            _backend_picker(manager, on_select=lambda: _run_action(manager, action_install))

        _input_form(
            manager,
            "Install paths",
            [("Source directory", config["source_dir"]),
             ("Install prefix",   config["install_dir"])],
            on_submit=_after_paths,
        )

    # ── Update flow ───────────────────────────────────────────────────────
    def start_update(_):
        source = Path(config["source_dir"])
        if not (source / ".git").exists():
            _alert(manager, "Not installed",
                   [f"No source found at {source}.", "Run Install first."])
            return
        _modal(
            manager,
            "Update llama.cpp",
            "Pull latest commits and rebuild?",
            on_yes=lambda: _run_action(manager, action_update),
        )

    # ── Status ────────────────────────────────────────────────────────────
    def show_status(_):
        _run_action(manager, action_status)

    # ── Settings ──────────────────────────────────────────────────────────
    def open_settings(_):
        def _after_paths(values):
            config["source_dir"], config["install_dir"] = values
            save_config()
            _backend_picker(manager, on_select=lambda: None)

        _input_form(
            manager,
            "Settings",
            [("Source directory", config["source_dir"]),
             ("Install prefix",   config["install_dir"])],
            on_submit=_after_paths,
        )

    # ── Uninstall ─────────────────────────────────────────────────────────
    def start_uninstall(_):
        _modal(
            manager,
            "Uninstall llama.cpp",
            "Remove installed files and source?",
            on_yes=lambda: _run_action(manager, action_uninstall),
        )

    # ── Main window ───────────────────────────────────────────────────────
    main = (
        ptg.Window(
            ptg.Label("[title]  🦙 namakera  "),
            ptg.Label("[dim]  llama.cpp build manager  "),
            ptg.Label(""),
            ptg.Button("  Install   (clone → build → install)", onclick=start_install),
            ptg.Button("  Update    (pull → rebuild)",           onclick=start_update),
            ptg.Button("  Status",                               onclick=show_status),
            ptg.Button("  Settings  (paths / backend)",          onclick=open_settings),
            ptg.Button("  Uninstall",                            onclick=start_uninstall),
            ptg.Label(""),
            ptg.Button("  Quit", onclick=lambda _: manager.stop()),
            box=ptg.boxes.DOUBLE,
            width=54,
        )
        .set_title("[title] namakera ")
        .center()
    )

    manager += main


# ── Entry point ───────────────────────────────────────────────────────────────
def main() -> None:
    load_config()
    _apply_styles()

    with ptg.WindowManager() as manager:
        build_ui(manager)


if __name__ == "__main__":
    main()
