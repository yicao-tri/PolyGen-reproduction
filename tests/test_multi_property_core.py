import numpy as np
import pandas as pd
import torch

from scripts.multi_property_core import PROPERTY_FIELDS, MultiPropertyPrefix, fit_scaler

def frame():
    return pd.DataFrame({
        "conductivity": [1e-5, 2e-5, 4e-5],
        "li_diffusivity": [1e-8, 2e-8, 3e-8],
        "tfsi_diffusivity": [2e-8, 3e-8, 4e-8],
        "poly_diffusivity": [1e-9, 2e-9, 5e-9],
        "transference_number": [0.1, 0.2, 0.3],
        "molality": [1.3, 1.4, 1.5],
    })

def test_scaler_is_six_dimensional_and_finite(tmp_path):
    p = tmp_path / "source.csv"
    d = frame(); d.to_csv(p, index=False)
    s = fit_scaler(d, p)
    z = s.transform_frame(d)
    assert s.fields == PROPERTY_FIELDS
    assert z.shape == (3, 6)
    assert np.isfinite(z).all()
    assert np.allclose(z.mean(0), 0, atol=1e-6)

def test_prefix_rejects_scalar_or_wrong_width_condition():
    m = MultiPropertyPrefix(6, 16)
    assert m(torch.zeros(4, 6)).shape == (4, 16)
    try:
        m(torch.zeros(4, 1))
    except ValueError:
        pass
    else:
        raise AssertionError("scalar condition must not silently enter multi-property arm")
