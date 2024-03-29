"""The :mod:`normal_distribution` contains a class for NormalDistribution."""

# Authors: Peter Steiner <peter.steiner@tu-dresden.de>,
# License: BSD 3 clause

from __future__ import annotations

from typing import Union, Any
import scipy
import scipy.stats
import numpy as np

from sklearn.base import BaseEstimator, TransformerMixin


class NormalDistribution(BaseEstimator, TransformerMixin):
    """
    Transform an input distribution to a normal distribution.

    Parameters
    ----------
    size : Union[int, np.integer], default=1
        Defining number of random variates
    """

    def __init__(self, size: Union[int, np.integer] = 1):
        """Construct the NormalDistribution."""
        self._transformer = scipy.stats.norm
        self._mean = 0
        self._std = 0
        self._size = size

    def fit(self, X: np.ndarray, y: None = None) -> NormalDistribution:
        """
        Fit the NormalDistribution.

        Parameters
        ----------
        X : np.ndarray of shape(n_samples, n_features)
            The input features
        y : None
            ignored

        Returns
        -------
        self : returns a trained NormalDistribution.
        """
        self._mean, self._std = self._transformer.fit(X=X, y=y)
        return self

    def transform(self, X: np.ndarray, y: None = None) -> np.ndarray:
        """
        Transform the input matrix X.

        Parameters
        ----------
        X : ndarray of size (n_samples, n_features)

        Returns
        -------
        y: ndarray of size (n_samples, )
        """
        return self._transformer.rvs(
            loc=self._mean, scale=self._std, size=self._size)

    def fit_transform(self, X: np.ndarray, y: None = None, **fit_params: Any)\
            -> np.ndarray:
        """
        Fit the Estimator and transforms the input matrix X.

        Parameters
        ----------
        X : ndarray of size (n_samples, n_features)
        y : None
            ignored
        fit_params : Union[Dict, None]
            ignored

        Returns
        -------
        y: ndarray of size (n_samples, )
        """
        self.fit(X=X, y=y)
        return self.transform(X=X, y=y)
