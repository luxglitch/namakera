<div align="center">

```
 ███╗   ██╗ █████╗ ███╗   ███╗ █████╗ ██╗  ██╗███████╗██████╗  █████╗
 ████╗  ██║██╔══██╗████╗ ████║██╔══██╗██║ ██╔╝██╔════╝██╔══██╗██╔══██╗
 ██╔██╗ ██║███████║██╔████╔██║███████║█████╔╝ █████╗  ██████╔╝███████║
 ██║╚██╗██║██╔══██║██║╚██╔╝██║██╔══██║██╔═██╗ ██╔══╝  ██╔══██╗██╔══██║
 ██║ ╚████║██║  ██║██║ ╚═╝ ██║██║  ██║██║  ██╗███████╗██║  ██║██║  ██║
 ╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝
```

**Build, install, and update [llama.cpp](https://github.com/ggerganov/llama.cpp) from source — no flags, just menus.**

![Platform](https://img.shields.io/badge/platform-linux-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)
![pytermgui](https://img.shields.io/badge/TUI-pytermgui-blueviolet?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

</div>

---

## 🦙 What is this?

A single bash script that handles the full lifecycle of llama.cpp — clone, configure, build, install, update, and uninstall — all through an interactive menu. No memorizing cmake flags, no hunting for the right options. Just run it and pick what you want.

```
  ╔══════════════════════════════╗
  ║   llama.cpp Build Manager    ║
  ╚══════════════════════════════╝

   1) Install  (clone + build + install)
   2) Update   (pull + rebuild)
   3) Status
   4) Change paths / backend flags
   5) Uninstall
   q) Quit
```

---

## ✨ Features

- 🔧 **Builds from source** — always gets the latest llama.cpp
- 🎮 **Auto-detects your GPU** — only shows backends that are actually available on your machine
- 🔄 **One-step updates** — pulls upstream and rebuilds, optionally switching backends
- 💾 **Remembers your settings** — config saved to `~/.config/llamacpp-manager.conf`
- 🗑️ **Clean uninstall** — removes exactly what was installed via CMake's manifest

---

## ⚡ Quick Start

```bash
git clone https://github.com/luxglitch/namakera.git
cd namakera
python3 -m venv .venv
.venv/bin/pip install pytermgui
.venv/bin/python3 namakera.py
```

That's it. Pick **Install** and follow the prompts.

---

## 📦 Dependencies

### Required

| Tool | What it does |
|------|-------------|
| `git` | Clones and updates the llama.cpp repo |
| `cmake` | Configures the build |
| `make` | Runs the build |
| `gcc` / `g++` | Compiles the C/C++ code |

### Optional — GPU & accelerated backends

| Tool / Library | Backend | Good for |
|----------------|---------|----------|
| CUDA Toolkit (`nvcc`) | CUDA | Nvidia GPUs |
| ROCm / HIP (`hipcc`) | HIP | AMD GPUs |
| Vulkan headers + SDK | Vulkan | Cross-vendor GPU |
| OpenBLAS | BLAS | Faster CPU inference |

> The script auto-detects which of these are installed and only shows you what's available.

---

## 🏗️ Installing Dependencies

<details>
<summary><b>🐧 Arch Linux</b></summary>

### Required

```bash
sudo pacman -S base-devel cmake git
```

### Optional — Nvidia CUDA

```bash
sudo pacman -S cuda
```

### Optional — AMD ROCm / HIP

```bash
sudo pacman -S rocm-hip-sdk
```

### Optional — Vulkan

```bash
sudo pacman -S vulkan-headers vulkan-icd-loader
```

### Optional — OpenBLAS

```bash
sudo pacman -S openblas
```

</details>

<details>
<summary><b>🟠 Ubuntu / Debian</b></summary>

### Required

```bash
sudo apt update
sudo apt install build-essential cmake git
```

### Optional — Nvidia CUDA

Check your driver version first:
```bash
nvidia-smi
```

Then install the toolkit:
```bash
sudo apt install nvidia-cuda-toolkit
```

> For the absolute latest CUDA version, use [Nvidia's official installer](https://developer.nvidia.com/cuda-downloads) instead.

### Optional — AMD ROCm / HIP

```bash
sudo apt install rocm-hip-sdk
```

> If that's not available for your distro version, see the [official ROCm install guide](https://rocm.docs.amd.com/en/latest/deploy/linux/index.html).

### Optional — Vulkan

```bash
sudo apt install libvulkan-dev vulkan-tools
```

### Optional — OpenBLAS

```bash
sudo apt install libopenblas-dev pkg-config
```

</details>

---

## 🎮 Usage

### First install

Run `namakera.py` and click **Install**. A form will ask for:

- **Source directory** — where to clone llama.cpp *(default: `~/src/llama.cpp`)*
- **Install prefix** — where to put the binaries *(default: `~/.local`)*
- **Compute backend** — pick from whatever's detected on your system

The TUI closes, shows live build output in your terminal, then returns to the menu when done. Go grab a coffee ☕ — the first build takes a few minutes.

### Updating

Click **Update**. It:
1. Confirms before doing anything
2. Fetches upstream and shows current vs remote version
3. Pulls and rebuilds

### PATH setup

If you install to `~/.local` (the default), make sure `~/.local/bin` is in your PATH or the binaries won't be found.

<details>
<summary>How to add it</summary>

**bash** — add to `~/.bashrc`:
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**zsh** — add to `~/.zshrc`:
```zsh
export PATH="$HOME/.local/bin:$PATH"
```

**fish** — run once:
```fish
fish_add_path ~/.local/bin
```

Then open a new terminal or reload your shell.

</details>

---

## ⚙️ Config file

Your choices are saved automatically after each install or settings change:

```
~/.config/namakera.conf
```

```bash
# namakera config — auto-generated
source_dir="/home/you/src/llama.cpp"
install_dir="/home/you/.local"
cmake_extra="-DGGML_NATIVE=ON -DGGML_CUDA=ON"
```

You can edit this by hand or use the **Settings** menu to update it interactively.

---

## 🔥 Troubleshooting

**Build fails with CUDA errors**
> Make sure `nvcc` is in your PATH and the CUDA toolkit version is compatible with your driver. Run `nvidia-smi` — the top right shows the max CUDA version your driver supports.

**`llama-cli` not found after install**
> Your install prefix's `bin/` isn't in PATH. See the [PATH setup](#-usage) section above.

**Running out of RAM during the build**
> The build uses all your CPU threads by default. Dial it back:
> ```bash
> export CMAKE_BUILD_PARALLEL_LEVEL=2
> ./llamacpp-manager.sh
> ```

**Permission denied on the install prefix**
> Stick to a prefix you own like `~/.local`. Using `/usr/local` requires `sudo`, which is generally not recommended for user installs.

---

<div align="center">

built with 🦙 and bash

</div>
