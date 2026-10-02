"""Reusable six-property implicit-conditioning components.

This module deliberately keeps the existing PolyGen autoregressive MLE path and
changes only the condition encoder. It does not implement auxiliary property
losses or target-dependent filtering.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import torch
from torch import nn

PROPERTY_FIELDS = (
    "conductivity", "li_diffusivity", "tfsi_diffusivity",
    "poly_diffusivity", "transference_number", "molality",
)
LOG_FIELDS = frozenset(PROPERTY_FIELDS[:4])

@dataclass(frozen=True)
class PropertyScaler:
    fields: tuple[str, ...]
    transforms: dict[str, str]
    mean: np.ndarray
    scale: np.ndarray
    train_rows: int
    source_sha256: str

    def transform_frame(self, frame: pd.DataFrame) -> np.ndarray:
        values = []
        for field in self.fields:
            x = pd.to_numeric(frame[field], errors="coerce").to_numpy(float)
            if field in LOG_FIELDS:
                x = np.log10(x)
            values.append(x)
        raw = np.column_stack(values)
        return ((raw - self.mean) / self.scale).astype(np.float32)

    def target(self, values: dict[str, float]) -> np.ndarray:
        raw = []
        for field in self.fields:
            x = float(values[field])
            raw.append(np.log10(x) if field in LOG_FIELDS else x)
        return ((np.asarray(raw) - self.mean) / self.scale).astype(np.float32)

    def manifest(self) -> dict:
        return {
            "fields": list(self.fields), "transforms": self.transforms,
            "mean": self.mean.tolist(), "scale": self.scale.tolist(),
            "train_rows": self.train_rows, "source_sha256": self.source_sha256,
        }

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def fit_scaler(frame: pd.DataFrame, source_path: str | Path) -> PropertyScaler:
    fields = tuple(PROPERTY_FIELDS)
    vals = []
    for field in fields:
        x = pd.to_numeric(frame[field], errors="coerce").to_numpy(float)
        if field in LOG_FIELDS:
            if np.any(~np.isfinite(x)) or np.any(x <= 0):
                raise ValueError(f"non-positive or non-finite values in {field}")
            x = np.log10(x)
        vals.append(x)
    raw = np.column_stack(vals)
    if not np.isfinite(raw).all():
        raise ValueError("non-finite joint property matrix")
    mean = raw.mean(axis=0)
    scale = raw.std(axis=0, ddof=0)
    if np.any(scale <= 0):
        raise ValueError("zero-variance conditioning property")
    return PropertyScaler(fields, {f: ("log10" if f in LOG_FIELDS else "raw") for f in fields}, mean, scale, len(frame), _sha256(Path(source_path)))

class MultiPropertyPrefix(nn.Module):
    """Maps a normalized joint condition vector to one learned prefix embedding."""
    def __init__(self, condition_dim: int, embedding_dim: int):
        super().__init__()
        self.condition_dim = condition_dim
        self.embedding_dim = embedding_dim
        self.net = nn.Sequential(
            nn.Linear(condition_dim, embedding_dim), nn.Tanh(),
            nn.Linear(embedding_dim, embedding_dim),
        )

    def forward(self, condition: torch.Tensor) -> torch.Tensor:
        if condition.ndim != 2 or condition.shape[1] != self.condition_dim:
            raise ValueError(f"expected [batch,{self.condition_dim}] condition, got {tuple(condition.shape)}")
        return self.net(condition)

def write_scaler_manifest(scaler: PropertyScaler, path: str | Path) -> None:
    Path(path).write_text(json.dumps(scaler.manifest(), indent=2) + "\n")
