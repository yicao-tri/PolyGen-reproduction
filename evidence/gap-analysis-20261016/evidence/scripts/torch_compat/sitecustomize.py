"""Compatibility shims for the isolated MolMiner training environment.

Two behaviors in the current reproducibility environment need containment:

* the checked-in MolMiner packed loader passes ``mmap=`` to ``torch.load``;
  PyTorch >=2.1 consumes that keyword, while PyTorch 2.0.1 rejects it;
* PyTorch 2.0.1's native ``MultiheadAttention`` fast path mishandles the
  float ``-1e9`` padding mask used by MolMiner when the model is in
  ``eval()+no_grad`` mode.  It interprets the float mask as a boolean mask,
  fully masks padded query rows, and returns NaNs from softmax.

The second shim makes self-attention take the numerically correct fallback
path during evaluation by breaking the ``query is key is value`` identity.
The tensor values and mask are unchanged.  The upstream MolMiner checkout and
the canonical PolyGen repository remain untouched.
"""

from __future__ import annotations

import torch


_ORIGINAL_TORCH_LOAD = torch.load


def _torch_load_compat(*args, **kwargs):
    kwargs.pop("mmap", None)
    return _ORIGINAL_TORCH_LOAD(*args, **kwargs)


torch.load = _torch_load_compat


# PyTorch 2.0.1 has no public switch for disabling the native MHA fast path.
# Passing a cloned query forces the documented general path while preserving
# the same self-attention inputs.  Limit the compatibility change to the old
# runtime and evaluation mode; training already bypasses this path.
if str(torch.__version__).startswith("2.0"):
    _ORIGINAL_MHA_FORWARD = torch.nn.MultiheadAttention.forward

    def _mha_eval_mask_compat(self, query, key, value, *args, **kwargs):
        if not self.training and query is key and key is value:
            query = query.clone()
        return _ORIGINAL_MHA_FORWARD(self, query, key, value, *args, **kwargs)

    torch.nn.MultiheadAttention.forward = _mha_eval_mask_compat
