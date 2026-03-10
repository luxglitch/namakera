# llama.cpp Build Manager

An interactive shell script for building, installing, and updating [llama.cpp](https://github.com/ggerganov/llama.cpp) from source. No flags needed — everything is driven through text menus.

---

## Features

- Clone and build llama.cpp from source
- Auto-detects available compute backends (CUDA, HIP/ROCm, Vulkan, OpenBLAS)
- Update in-place by pulling and rebuilding
- Uninstall via CMake's install manifest
- Saves your config between runs (`~/.config/llamacpp-manager.conf`)

---

## Dependencies

### Required

| Tool | Purpose |
|------|---------|
| `git` | Clone and update the repository |
| `cmake` | Configure the build |
| `make` | Build system |
| `gcc` / `g++` | C/C++ compiler |

### Optional (GPU / accelerated backends)

| Tool / Library | Backend |
|----------------|---------|
| CUDA Toolkit (`nvcc`) | Nvidia GPU acceleration |
| ROCm / HIP (`hipcc`) | AMD GPU acceleration |
| Vulkan headers + SDK | Vulkan GPU backend |
| OpenBLAS | CPU BLAS acceleration |

---

## Installing Dependencies

### Arch Linux

**Required:**
```bash
sudo pacman -S base-devel cmake git
```

**Optional — Nvidia CUDA:**
```bash
sudo pacman -S cuda
```

**Optional — AMD ROCm/HIP:**
```bash
sudo pacman -S rocm-hip-sdk
```

**Optional — Vulkan:**
```bash
sudo pacman -S vulkan-headers vulkan-icd-loader
```

**Optional — OpenBLAS:**
```bash
sudo pacman -S openblas
```

---

### Ubuntu / Debian

**Required:**
```bash
sudo apt update
sudo apt install build-essential cmake git
```

**Optional — Nvidia CUDA:**

Install the CUDA toolkit from Nvidia's package repository. First check your driver version:
```bash
nvidia-smi
```
Then install the matching toolkit:
```bash
sudo apt install nvidia-cuda-toolkit
```
Or follow the [official CUDA install guide](https://developer.nvidia.com/cuda-downloads) for the latest version.

**Optional — AMD ROCm/HIP:**
```bash
sudo apt install rocm-hip-sdk
```
If that's not available, follow the [official ROCm install guide](https://rocm.docs.amd.com/en/latest/deploy/linux/index.html).

**Optional — Vulkan:**
```bash
sudo apt install libvulkan-dev vulkan-tools
```

**Optional — OpenBLAS:**
```bash
sudo apt install libopenblas-dev pkg-config
```

---

## Usage

1. Clone or download this repo, then make the script executable:

```bash
chmod +x llamacpp-manager.sh
```

2. Run it:

```bash
./llamacpp-manager.sh
```

3. Use the menu:

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

### First install

Choose **1) Install**. The script will ask for:

- **Source directory** — where to clone llama.cpp (default: `~/src/llama.cpp`)
- **Install prefix** — where to put the built binaries (default: `~/.local`)
- **Compute backend** — only backends detected on your system are listed

After that it clones, configures, builds, and installs automatically.

### Updating

Choose **2) Update**. The script will:

1. Fetch upstream changes
2. Show the current version vs remote
3. Ask to confirm before pulling and rebuilding
4. Optionally let you switch to a different backend

### PATH setup

If your install prefix is `~/.local` (the default), make sure `~/.local/bin` is in your PATH.

**bash** (`~/.bashrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**zsh** (`~/.zshrc`):
```zsh
export PATH="$HOME/.local/bin:$PATH"
```

**fish** (`~/.config/fish/config.fish`):
```fish
fish_add_path ~/.local/bin
```

Reload your shell or open a new terminal after adding this.

---

## Config file

Settings are saved to `~/.config/llamacpp-manager.conf` after each install or reconfigure. You can edit it directly if needed:

```bash
# llama.cpp manager config — auto-generated
INSTALL_DIR="/home/you/.local"
SOURCE_DIR="/home/you/src/llama.cpp"
CMAKE_EXTRA="-DGGML_NATIVE=ON -DGGML_CUDA=ON"
```

---

## Troubleshooting

**Build fails with CUDA errors**
Make sure `nvcc` is in your PATH and the CUDA version matches your driver. Run `nvidia-smi` to check the driver's max supported CUDA version.

**`llama-cli` not found after install**
Your install prefix's `bin/` directory is not in PATH. See the PATH setup section above.

**Out of memory during build**
The build is parallelized by default (`nproc` threads). If you run out of RAM, set `CMAKE_BUILD_PARALLEL_LEVEL` before running the script:
```bash
export CMAKE_BUILD_PARALLEL_LEVEL=2
./llamacpp-manager.sh
```

**Permission denied on install prefix**
Use a prefix you own (e.g. `~/.local`) rather than `/usr/local`, or run with `sudo` — though using a user-local prefix is recommended.
