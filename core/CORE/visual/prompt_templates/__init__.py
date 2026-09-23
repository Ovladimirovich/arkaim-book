"""Prompt template registry."""
from .comfyui import ComfyUITemplate
from .flux import FluxTemplate
from .runway import RunwayTemplate
from .kling import KlingTemplate
from .hailuo import HailuoTemplate

TEMPLATES = {
    "comfyui": ComfyUITemplate,
    "flux": FluxTemplate,
    "runway": RunwayTemplate,
    "kling": KlingTemplate,
    "hailuo": HailuoTemplate,
}

def get_template(name: str):
    cls = TEMPLATES.get(name)
    if not cls:
        raise ValueError(f"Unknown template: {name}. Available: {list(TEMPLATES.keys())}")
    return cls()
