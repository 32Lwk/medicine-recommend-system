# Local Image Generation CLI

This folder provides a small CLI for local image generation from Codex or a terminal.

## Models

- `fast`: `stabilityai/sdxl-turbo`
- `quality`: `stabilityai/stable-diffusion-xl-base-1.0`

## Setup

```powershell
python -m venv .venv-imagegen
.\.venv-imagegen\Scripts\python.exe -m pip install --upgrade pip
.\.venv-imagegen\Scripts\python.exe -m pip install -r tools\local_imagegen\requirements.txt
```

## Usage

```powershell
.\tools\local_imagegen\imagegen.ps1 -Model fast -Prompt "A clean app icon for a medicine recommendation AI, white background"
```

```powershell
.\tools\local_imagegen\imagegen.ps1 -Model quality -Prompt "A high quality product shot of a friendly medicine recommendation app on a smartphone, soft studio lighting" -CpuOffload
```

Outputs are written to `local_outputs/imagegen/`.
