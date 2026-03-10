#!/usr/bin/env python3
"""namakera — llama.cpp build manager with pytermgui TUI."""

from __future__ import annotations

import os
import subprocess
import shutil
from pathlib import Path

import pytermgui as ptg

# ── Constants ─────────────────────────────────────────────────────────────────
REPO_URL = "https://github.com/ggerganov/llama.cpp.git"
CONFIG_FILE = Path.home() / ".config" / "namakera.conf"
DEFAULT_SOURCE = Path.home() / "src" / "llama.cpp"
DEFAULT_PREFIX = Path.home() / ".local"

# ── Cyberpunk palette ─────────────────────────────────────────────────────────
CP = {
    "bg":      "#08000f",   # near-black purple
    "bg2":     "#140028",   # slightly lighter
    "cyan":    "#00e5ff",   # electric cyan
    "pink":    "#ff2d78",   # hot pink
    "yellow":  "#f5ff00",   # acid yellow
    "green":   "#39ff14",   # neon green
    "red":     "#ff003c",   # neon red
    "dim":     "#4a3060",   # muted purple
    "white":   "#e8e0ff",   # soft lavender-white
}

# ANSI shortcuts for terminal output (outside TUI)
A = {
    "rst":    "\033[0m",
    "bold":   "\033[1m",
    "cyan":   "\033[38;2;0;229;255m",
    "pink":   "\033[38;2;255;45;120m",
    "yellow": "\033[38;2;245;255;0m",
    "green":  "\033[38;2;57;255;20m",
    "red":    "\033[38;2;255;0;60m",
    "dim":    "\033[38;2;74;48;96m",
    "white":  "\033[38;2;232;224;255m",
}

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
        k, v = k.strip().lower(), v.strip().strip('"')
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


def _which(cmd: str) -> bool:
    return subprocess.run(["which", cmd], capture_output=True).returncode == 0


def missing_deps() -> list[str]:
    return [d for d in REQUIRED_DEPS if not _which(d)]


def detect_backends() -> list[tuple[str, str]]:
    backends = [("CPU only  (no acceleration)", "-DGGML_NATIVE=ON")]
    if _which("nvcc"):
        backends.append(("CUDA      Nvidia GPU", "-DGGML_NATIVE=ON -DGGML_CUDA=ON"))
    if _which("hipcc"):
        backends.append(("HIP       AMD ROCm GPU", "-DGGML_NATIVE=ON -DGGML_HIP=ON"))
    if any(Path(p).exists() for p in ["/usr/include/vulkan/vulkan.h",
                                       "/usr/local/include/vulkan/vulkan.h"]):
        backends.append(("Vulkan    cross-vendor GPU", "-DGGML_NATIVE=ON -DGGML_VULKAN=ON"))
    try:
        r = subprocess.run(["pkg-config", "--exists", "openblas"], capture_output=True)
        if r.returncode == 0:
            backends.append(("OpenBLAS  CPU BLAS", "-DGGML_NATIVE=ON -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS"))
    except FileNotFoundError:
        pass
    return backends


# ── Terminal output helpers ────────────────────────────────────────────────────
def shell(cmd: list[str], cwd: str | None = None) -> int:
    c, r = A["cyan"], A["rst"]
    print(f"\n  {c}$ {' '.join(cmd)}{r}")
    return subprocess.run(cmd, cwd=cwd).returncode


def header(text: str) -> None:
    cols = os.get_terminal_size().columns
    p, c, r = A["pink"], A["cyan"], A["rst"]
    bar = f"{p}{'▓' * 4}{r} {A['white']}{A['bold']}{text}{r} {p}{'▓' * 4}{r}"
    line = f"{c}{'═' * cols}{r}"
    print(f"\n{line}\n  {bar}\n{line}")


def _ok(msg: str)   -> None: print(f"  {A['green']}✔ {A['white']}{msg}{A['rst']}")
def _warn(msg: str) -> None: print(f"  {A['yellow']}! {A['white']}{msg}{A['rst']}")
def _err(msg: str)  -> None: print(f"  {A['red']}✘ {A['white']}{msg}{A['rst']}")


# ── Core actions ──────────────────────────────────────────────────────────────
def action_install() -> None:
    header("INSTALL  //  llama.cpp")
    source = Path(config["source_dir"])
    prefix = Path(config["install_dir"])

    missing = missing_deps()
    if missing:
        _err(f"Missing required tools: {', '.join(missing)}")
        print("  Install them and try again.")
        return

    if source.is_dir() and (source / ".git").exists():
        _warn(f"Source already exists at {source}")
        print("  Skipping clone — proceeding to build.")
    else:
        print(f"  {A['cyan']}Cloning into {source} …{A['rst']}")
        if shell(["git", "clone", REPO_URL, str(source)]) != 0:
            _err("Clone failed.")
            return

    _build_and_install(source, prefix)


def action_update() -> None:
    header("UPDATE  //  llama.cpp")
    source = Path(config["source_dir"])
    prefix = Path(config["install_dir"])

    if not (source / ".git").exists():
        _err(f"Source not found at {source}")
        print("  Run Install first.")
        return

    print(f"  {A['cyan']}Fetching upstream…{A['rst']}")
    shell(["git", "fetch", "origin"], cwd=str(source))

    local  = subprocess.run(["git", "rev-parse", "HEAD"],  capture_output=True, text=True, cwd=str(source)).stdout.strip()
    remote = subprocess.run(["git", "rev-parse", "@{u}"],  capture_output=True, text=True, cwd=str(source)).stdout.strip()

    if local == remote:
        _ok("Already up to date.")
        return

    tag = subprocess.run(["git", "describe", "--tags", "--always"],
                         capture_output=True, text=True, cwd=str(source)).stdout.strip()
    print(f"  {A['dim']}current :{A['rst']} {tag}")
    print(f"  {A['cyan']}Update available — pulling…{A['rst']}")
    shell(["git", "pull", "--ff-only"], cwd=str(source))
    _build_and_install(source, prefix)


def action_uninstall() -> None:
    header("UNINSTALL  //  llama.cpp")
    source   = Path(config["source_dir"])
    manifest = source / "build" / "install_manifest.txt"

    if not manifest.exists():
        _warn(f"No install manifest found at {manifest}")
        ans = input(f"  {A['yellow']}Remove source directory anyway? [y/N]{A['rst']} ").strip().lower()
        if ans == "y":
            shutil.rmtree(source, ignore_errors=True)
            _ok(f"Removed {source}")
        return

    files = manifest.read_text().splitlines()
    print(f"\n  {A['cyan']}Files to remove ({len(files)} items):{A['rst']}")
    for f in files[:10]:
        print(f"    {A['dim']}{f}{A['rst']}")
    if len(files) > 10:
        print(f"    {A['dim']}… and {len(files) - 10} more{A['rst']}")

    ans = input(f"\n  {A['yellow']}Confirm removal? [y/N]{A['rst']} ").strip().lower()
    if ans != "y":
        print("  Cancelled.")
        return

    for f in files:
        p = Path(f)
        if p.exists():
            p.unlink()
            print(f"  {A['dim']}removed {p}{A['rst']}")

    ans2 = input(f"\n  {A['yellow']}Also remove source directory {source}? [y/N]{A['rst']} ").strip().lower()
    if ans2 == "y":
        shutil.rmtree(source, ignore_errors=True)
        _ok(f"Removed {source}")

    CONFIG_FILE.unlink(missing_ok=True)
    _ok("Uninstall complete.")


LLAMA_BINARY_NAMES = [
    "llama-cli", "llama-run", "llama", "main",
    "llama-server", "llama-bench", "llama-embedding",
]

# Common locations to search when binaries aren't in PATH
LLAMA_SEARCH_DIRS = [
    Path.home() / ".local" / "bin",
    Path("/usr/local/bin"),
    Path("/usr/bin"),
    Path("/opt/llama.cpp/bin"),
]


def find_llama_binary() -> Path | None:
    """Search PATH first, then common build/install dirs, then user's source build dir."""
    # 1. PATH
    for name in LLAMA_BINARY_NAMES:
        r = subprocess.run(["which", name], capture_output=True, text=True)
        if r.returncode == 0:
            return Path(r.stdout.strip())

    # 2. Known install dirs
    for d in LLAMA_SEARCH_DIRS:
        for name in LLAMA_BINARY_NAMES:
            p = d / name
            if p.exists():
                return p

    # 3. Build dir inside the configured source
    build_bin = Path(config["source_dir"]) / "build" / "bin"
    for name in LLAMA_BINARY_NAMES:
        p = build_bin / name
        if p.exists():
            return p

    # 4. Glob for any llama-* under common workspace dirs
    for search_root in [Path.home() / "workspace", Path.home() / "src", Path.home()]:
        if not search_root.exists():
            continue
        for p in sorted(search_root.rglob("llama-cli")) + sorted(search_root.rglob("llama-run")):
            if p.is_file() and os.access(p, os.X_OK):
                return p

    return None


def _detect_shell_configs() -> list[tuple[str, Path, str]]:
    """Return list of (shell_name, config_path, export_line) for detected shells."""
    entries = []
    if Path(Path.home() / ".bashrc").exists():
        entries.append(("bash", Path.home() / ".bashrc", "export PATH=\"{dir}:$PATH\""))
    if Path(Path.home() / ".zshrc").exists():
        entries.append(("zsh", Path.home() / ".zshrc", "export PATH=\"{dir}:$PATH\""))
    fish_conf = Path.home() / ".config" / "fish" / "config.fish"
    if fish_conf.exists():
        entries.append(("fish", fish_conf, "fish_add_path {dir}"))
    # Fallback: current shell
    if not entries:
        shell_name = Path(os.environ.get("SHELL", "/bin/bash")).name
        rc = Path.home() / f".{shell_name}rc"
        entries.append((shell_name, rc, "export PATH=\"{dir}:$PATH\""))
    return entries


def add_to_path(bin_dir: Path) -> None:
    """Interactively offer to add bin_dir to shell config(s)."""
    configs = _detect_shell_configs()
    export_line_str = str(bin_dir)

    print(f"\n  {A['cyan']}Detected shell configs:{A['rst']}")
    for i, (shell, cfg, template) in enumerate(configs):
        line = template.format(dir=bin_dir)
        print(f"    {A['dim']}{i+1}){A['rst']} [{A['yellow']}{shell}{A['rst']}]  {cfg}")
        print(f"       {A['dim']}adds:{A['rst']} {line}")

    print()
    ans = input(f"  {A['yellow']}Add to all detected configs? [Y/n]{A['rst']} ").strip().lower()
    if ans in ("n", "no"):
        print("  Skipped.")
        return

    added_any = False
    for shell, cfg, template in configs:
        line = template.format(dir=bin_dir)
        # Check if already present
        if cfg.exists() and str(bin_dir) in cfg.read_text():
            _warn(f"{cfg.name}: already contains {bin_dir}, skipping.")
            continue
        try:
            with open(cfg, "a") as f:
                f.write(f"\n# added by namakera\n{line}\n")
            _ok(f"Written to {cfg}")
            added_any = True
        except OSError as e:
            _err(f"Could not write {cfg}: {e}")

    if added_any:
        # Apply immediately to the current process so namakera benefits right away
        os.environ["PATH"] = f"{bin_dir}:{os.environ.get('PATH', '')}"
        print()
        _ok("Done! PATH updated for this session.")
        _ok(f"Persistent change written — open a new terminal to apply globally.")
        print(f"  {A['dim']}Or reload now:{A['rst']}  {A['yellow']}export PATH=\"{bin_dir}:$PATH\"{A['rst']}")


def action_status() -> None:
    header("STATUS")
    source = Path(config["source_dir"])
    prefix = Path(config["install_dir"])

    c, w, d, r = A["cyan"], A["white"], A["dim"], A["rst"]
    print(f"  {d}source dir  :{r} {w}{source}{r}")
    print(f"  {d}install dir :{r} {w}{prefix}{r}")
    print(f"  {d}cmake flags :{r} {A['yellow']}{config['cmake_extra']}{r}")
    print()

    if (source / ".git").exists():
        tag = subprocess.run(["git", "describe", "--tags", "--always"],
                             capture_output=True, text=True, cwd=str(source)).stdout.strip()
        _ok(f"Source cloned — version: {A['cyan']}{tag}{A['rst']}")
        behind = subprocess.run(["git", "rev-list", "HEAD..@{u}", "--count"],
                                capture_output=True, text=True, cwd=str(source)).stdout.strip()
        if behind and behind != "0":
            _warn(f"{behind} commit(s) behind upstream — consider updating.")
        elif behind == "0":
            _ok("Up to date with upstream.")
    else:
        _warn(f"No git source at {source} — may be a pre-existing or package install.")

    print()
    binary = find_llama_binary()
    if binary:
        in_path = _which(binary.name)
        loc_note = "" if in_path else f"{A['yellow']} (not in PATH){A['rst']}"
        _ok(f"Binary found: {A['cyan']}{binary}{A['rst']}{loc_note}")
        subprocess.run([str(binary), "--version"], capture_output=False)
        if not in_path:
            _warn(f"{binary.parent} is not in PATH.")
            ans = input(f"  {A['yellow']}Add it to your shell config(s) now? [Y/n]{A['rst']} ").strip().lower()
            if ans not in ("n", "no"):
                add_to_path(binary.parent)
    else:
        _warn("No llama binary found.")
        bin_path = prefix / "bin"
        if str(bin_path) not in os.environ.get("PATH", ""):
            _warn(f"Hint: add {bin_path} to your PATH.")


def _build_and_install(source: Path, prefix: Path) -> None:
    build_dir = source / "build"
    nproc     = os.cpu_count() or 4
    flags     = config["cmake_extra"].split()

    header("CONFIGURE")
    cmake_cmd = [
        "cmake", "-S", str(source), "-B", str(build_dir),
        "-DCMAKE_BUILD_TYPE=Release",
        f"-DCMAKE_INSTALL_PREFIX={prefix}",
        "-DLLAMA_BUILD_TESTS=OFF",
        *flags,
    ]
    if shell(cmake_cmd) != 0:
        _err("Configure failed.")
        return

    header(f"BUILD  //  {nproc} threads")
    if shell(["cmake", "--build", str(build_dir), "--config", "Release", "-j", str(nproc)]) != 0:
        _err("Build failed.")
        return

    header("INSTALL")
    if shell(["cmake", "--install", str(build_dir)]) != 0:
        _err("Install failed.")
        return

    print()
    _ok(f"Done!  Binaries installed to {A['cyan']}{prefix}/bin/{A['rst']}")
    bin_path = prefix / "bin"
    if str(bin_path) not in os.environ.get("PATH", ""):
        _warn(f"{bin_path} is not in PATH.")
        print(f"  Add to your shell config:")
        print(f"    {A['yellow']}export PATH=\"{bin_path}:$PATH\"{A['rst']}")


# ── Cyberpunk TUI styles ───────────────────────────────────────────────────────
def _apply_styles() -> None:
    bg, bg2   = CP["bg"], CP["bg2"]
    cyan, pink = CP["cyan"], CP["pink"]
    yellow    = CP["yellow"]
    dim       = CP["dim"]

    # Window border: neon cyan unfocused, hot pink when focused
    ptg.Window.set_style("border",
        ptg.MarkupFormatter(f"[{cyan}]{{item}}"))
    ptg.Window.set_style("corner",
        ptg.MarkupFormatter(f"[{cyan}]{{item}}"))
    ptg.Window.set_style("border_focused",
        ptg.MarkupFormatter(f"[bold {pink}]{{item}}"))
    ptg.Window.set_style("corner_focused",
        ptg.MarkupFormatter(f"[bold {pink}]{{item}}"))
    ptg.Window.set_style("border_blurred",
        ptg.MarkupFormatter(f"[{dim}]{{item}}"))
    ptg.Window.set_style("corner_blurred",
        ptg.MarkupFormatter(f"[{dim}]{{item}}"))

    # Buttons: dark bg + cyan text; pink bg + dark text when highlighted
    ptg.Button.set_style("label",
        ptg.MarkupFormatter(f"[@{bg2} bold {cyan}]{{item}}"))
    ptg.Button.set_style("highlight",
        ptg.MarkupFormatter(f"[@{pink} bold {bg}]{{item}}"))

    # InputField: dark bg, yellow prompt, cyan text
    ptg.InputField.set_style("value",
        ptg.MarkupFormatter(f"[@{bg} {yellow}]{{item}}"))
    ptg.InputField.set_style("prompt",
        ptg.MarkupFormatter(f"[@{bg} {cyan}]{{item}}"))
    ptg.InputField.set_style("cursor",
        ptg.MarkupFormatter(f"[@{pink} {bg}]{{item}}"))

    # TIM aliases used in markup strings
    ptg.tim.alias("cp.title",  f"bold {pink}")
    ptg.tim.alias("cp.label",  CP["white"])
    ptg.tim.alias("cp.cyan",   cyan)
    ptg.tim.alias("cp.yellow", yellow)
    ptg.tim.alias("cp.green",  CP["green"])
    ptg.tim.alias("cp.dim",    dim)
    ptg.tim.alias("cp.err",    CP["red"])


# ── TUI widgets ────────────────────────────────────────────────────────────────
def _run_action(manager: ptg.WindowManager, fn) -> None:
    ptg.unset_alt_buffer()
    ptg.show_cursor()
    try:
        fn()
    except KeyboardInterrupt:
        print(f"\n  {A['dim']}[interrupted]{A['rst']}")
    print()
    input(f"  {A['pink']}// press Enter to jack back in //{A['rst']}  ")
    ptg.set_alt_buffer()
    ptg.hide_cursor()
    manager.compositor.redraw()


def _modal(manager: ptg.WindowManager, title: str, body: str, on_yes=None) -> None:
    def _close(_):   manager.remove(win)
    def _confirm(_):
        manager.remove(win)
        if on_yes:
            on_yes()

    win = (
        ptg.Window(
            ptg.Label(f"[cp.title]{title}"),
            ptg.Label(""),
            ptg.Label(f"[cp.label]{body}"),
            ptg.Label(""),
            ptg.Splitter(
                ptg.Button("  YES  ", onclick=_confirm),
                ptg.Button("  NO   ", onclick=_close),
            ),
            box=ptg.boxes.DOUBLE,
            width=52,
        )
        .set_title(f"[cp.title] ▓▓ CONFIRM ▓▓ ")
        .center()
    )
    manager += win
    win.select(1)  # default to NO


def _alert(manager: ptg.WindowManager, title: str, lines: list[str]) -> None:
    def _close(_): manager.remove(win)

    widgets: list = [ptg.Label(f"[cp.title]{title}"), ptg.Label("")]
    for line in lines:
        widgets.append(ptg.Label(f"[cp.label]{line}"))
    widgets += [ptg.Label(""), ptg.Button("  OK  ", onclick=_close)]

    win = (
        ptg.Window(*widgets, box=ptg.boxes.DOUBLE, width=58)
        .set_title(f"[cp.title] ▓▓ ALERT ▓▓ ")
        .center()
    )
    manager += win


def _input_form(
    manager: ptg.WindowManager,
    title: str,
    fields: list[tuple[str, str]],
    on_submit,
) -> None:
    inputs = [ptg.InputField(default, prompt=f"[cp.cyan]{label}: ") for label, default in fields]

    def _submit(_):
        manager.remove(win)
        on_submit([inp.value for inp in inputs])

    def _cancel(_):
        manager.remove(win)

    widgets: list = [ptg.Label(f"[cp.title]{title}"), ptg.Label("")]
    widgets.extend(inputs)
    widgets += [
        ptg.Label(""),
        ptg.Splitter(
            ptg.Button("  CONFIRM  ", onclick=_submit),
            ptg.Button("  CANCEL   ", onclick=_cancel),
        ),
    ]

    win = (
        ptg.Window(*widgets, box=ptg.boxes.DOUBLE, width=64)
        .set_title(f"[cp.title] ▓▓ {title.upper()} ▓▓ ")
        .center()
    )
    manager += win
    win.select(len(inputs) + 1)  # default to CANCEL (skip inputs + splitter)


def _backend_picker(manager: ptg.WindowManager, on_select) -> None:
    backends = detect_backends()

    def _pick(idx: int):
        def handler(_):
            config["cmake_extra"] = backends[idx][1]
            save_config()
            manager.remove(win)
            on_select()
        return handler

    def _cancel(_): manager.remove(win)

    buttons  = [ptg.Button(f"  {label}  ", onclick=_pick(i)) for i, (label, _) in enumerate(backends)]
    widgets  = [
        ptg.Label("[cp.title]Select compute backend"),
        ptg.Label(f"[cp.dim]detected on this system"),
        ptg.Label(""),
        *buttons,
        ptg.Label(""),
        ptg.Button("  CANCEL  ", onclick=_cancel),
    ]

    win = (
        ptg.Window(*widgets, box=ptg.boxes.DOUBLE, width=54)
        .set_title("[cp.title] ▓▓ BACKEND ▓▓ ")
        .center()
    )
    manager += win


# ── Main TUI ──────────────────────────────────────────────────────────────────
def build_ui(manager: ptg.WindowManager) -> None:

    def start_install(_):
        def _after_paths(values):
            config["source_dir"], config["install_dir"] = values
            save_config()
            _backend_picker(manager, on_select=lambda: _run_action(manager, action_install))

        _input_form(
            manager, "Install paths",
            [("Source directory", config["source_dir"]),
             ("Install prefix",   config["install_dir"])],
            on_submit=_after_paths,
        )

    def start_update(_):
        source = Path(config["source_dir"])
        if not (source / ".git").exists():
            _alert(manager, "NOT INSTALLED",
                   [f"No source found at:", str(source), "", "Run Install first."])
            return
        _modal(manager, "UPDATE  //  llama.cpp",
               "Pull latest commits and rebuild?",
               on_yes=lambda: _run_action(manager, action_update))

    def show_status(_):
        _run_action(manager, action_status)

    def open_settings(_):
        def _after_paths(values):
            config["source_dir"], config["install_dir"] = values
            save_config()
            _backend_picker(manager, on_select=lambda: None)

        _input_form(
            manager, "Settings",
            [("Source directory", config["source_dir"]),
             ("Install prefix",   config["install_dir"])],
            on_submit=_after_paths,
        )

    def start_uninstall(_):
        _modal(manager, "UNINSTALL  //  llama.cpp",
               "Remove installed files and source?",
               on_yes=lambda: _run_action(manager, action_uninstall))

    main = (
        ptg.Window(
            ptg.Label(f"[bold {CP['pink']}]  ▓ NAMAKERA ▓  "),
            ptg.Label(f"[{CP['dim']}]  llama.cpp build manager  "),
            ptg.Label(""),
            ptg.Button("  INSTALL    clone → build → install  ", onclick=start_install),
            ptg.Button("  UPDATE     pull  → rebuild           ", onclick=start_update),
            ptg.Button("  STATUS                               ", onclick=show_status),
            ptg.Button("  SETTINGS   paths / backend           ", onclick=open_settings),
            ptg.Button("  UNINSTALL                            ", onclick=start_uninstall),
            ptg.Label(""),
            ptg.Button("  QUIT                                 ", onclick=lambda _: manager.stop()),
            box=ptg.boxes.DOUBLE,
            width=54,
        )
        .set_title(f"[bold {CP['cyan']}] ▓▓ NAMAKERA ▓▓ ")
        .center()
    )

    manager += main


# ── Entry ─────────────────────────────────────────────────────────────────────
def main() -> None:
    load_config()
    _apply_styles()
    with ptg.WindowManager() as manager:
        build_ui(manager)


if __name__ == "__main__":
    main()
