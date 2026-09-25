from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import warnings
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("DIFFUSERS_VERBOSITY", "error")

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*local_dir_use_symlinks.*")

import torch
from diffusers import AutoPipelineForText2Image, DiffusionPipeline
from diffusers.utils import logging as diffusers_logging
from transformers.utils import logging as transformers_logging

diffusers_logging.set_verbosity_error()
transformers_logging.set_verbosity_error()


MODELS = {
    "fast": {
        "repo": "stabilityai/sdxl-turbo",
        "pipeline": AutoPipelineForText2Image,
        "width": 512,
        "height": 512,
        "steps": 4,
        "guidance": 0.0,
        "description": "SDXL Turbo: fast draft generation, usually 1-4 steps.",
    },
    "quality": {
        "repo": "stabilityai/stable-diffusion-xl-base-1.0",
        "pipeline": DiffusionPipeline,
        "width": 1024,
        "height": 1024,
        "steps": 30,
        "guidance": 7.0,
        "description": "SDXL Base 1.0: higher quality local generation.",
    },
}


def slugify(value: str, max_len: int = 48) -> str:
    value = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return (value or "image")[:max_len]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate images locally with fast and quality SDXL models."
    )
    parser.add_argument("--model", choices=MODELS.keys(), default="fast")
    parser.add_argument("--prompt", help="Text prompt for image generation.")
    parser.add_argument("--negative-prompt", default="")
    parser.add_argument("--output-dir", default="local_outputs/imagegen")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--guidance-scale", type=float)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--num-images", type=int, default=1)
    parser.add_argument(
        "--device",
        choices=("auto", "cuda", "cpu"),
        default="auto",
        help="Use cuda when available by default.",
    )
    parser.add_argument(
        "--cpu-offload",
        action="store_true",
        help="Lower VRAM usage at the cost of speed.",
    )
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download/cache the selected model without generating an image.",
    )
    parser.add_argument("--list-models", action="store_true")
    return parser.parse_args()


def resolve_device(requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is false.")
    return requested


def load_pipeline(model_key: str, device: str, cpu_offload: bool):
    config = MODELS[model_key]
    dtype = torch.float16 if device == "cuda" else torch.float32
    kwargs = {
        "dtype": dtype,
        "use_safetensors": True,
    }
    if model_key == "quality" and device == "cuda":
        kwargs["variant"] = "fp16"

    pipe = config["pipeline"].from_pretrained(config["repo"], **kwargs)

    if device == "cuda":
        torch.backends.cuda.matmul.allow_tf32 = True
        if cpu_offload:
            pipe.enable_model_cpu_offload()
        else:
            pipe.to("cuda")
    else:
        pipe.to("cpu")

    return pipe


def main() -> int:
    args = parse_args()

    if args.list_models:
        for key, config in MODELS.items():
            print(f"{key}: {config['repo']} - {config['description']}")
        return 0

    if not args.prompt and not args.download_only:
        raise SystemExit("--prompt is required unless --download-only is used.")

    config = MODELS[args.model]
    width = args.width or config["width"]
    height = args.height or config["height"]
    steps = args.steps or config["steps"]
    guidance = (
        args.guidance_scale
        if args.guidance_scale is not None
        else config["guidance"]
    )

    if width % 8 or height % 8:
        raise SystemExit("--width and --height must be multiples of 8.")

    device = resolve_device(args.device)
    print(f"Loading {args.model} model: {config['repo']} on {device}")
    pipe = load_pipeline(args.model, device, args.cpu_offload)

    if args.download_only:
        print("Model is cached and ready.")
        return 0

    generator = None
    if args.seed is not None:
        generator = torch.Generator(device="cpu").manual_seed(args.seed)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    call_kwargs = {
        "prompt": args.prompt,
        "width": width,
        "height": height,
        "num_inference_steps": steps,
        "guidance_scale": guidance,
        "num_images_per_prompt": args.num_images,
        "generator": generator,
    }
    if args.negative_prompt and guidance > 0:
        call_kwargs["negative_prompt"] = args.negative_prompt

    print(
        f"Generating {args.num_images} image(s): "
        f"{width}x{height}, steps={steps}, guidance={guidance}"
    )
    result = pipe(**call_kwargs)

    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = slugify(args.prompt or args.model)
    for index, image in enumerate(result.images, start=1):
        path = output_dir / f"{timestamp}_{args.model}_{index:02d}_{stem}.png"
        image.save(path)
        print(path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
