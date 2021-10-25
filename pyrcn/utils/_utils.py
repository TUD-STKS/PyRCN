"""
The :mod:`pyrcn.util` contains utilities for runnung, testing and analyzing the reservoir computing modules
"""

# Author: Peter Steiner <peter.steiner@tu-dresden.de>, Michael Schindler <michael.schindler@maschindler.de>
# License: BSD 3 clause

from sklearn.utils import check_X_y, check_consistent_length
from sklearn.utils.validation import _deprecate_positional_args

import numpy as np


def concatenate_sequences(X, y, sequence_to_value=False):
    if isinstance(X, list):
        X = np.asarray(X)
    if isinstance(y, list):
        y = np.asarray(y)
    if sequence_to_value:
        for k, _ in enumerate(y):
            y[k] = np.repeat(y[k], X[k].shape[0])

    check_consistent_length(X, y)
    sequence_ranges = None
    if X.ndim == 1:
        sequence_ranges = np.zeros((X.shape[0], 2), dtype=int)
        sequence_ranges[:, 1] = np.cumsum([X[k].shape[0] for k, _ in enumerate(X)])
        sequence_ranges[1:, 0] = sequence_ranges[:-1, 1]
        for k, _ in enumerate(X):
            X[k], y[k] = check_X_y(X[k], y[k], multi_output=True)
    return np.concatenate(X), np.concatenate(y), sequence_ranges