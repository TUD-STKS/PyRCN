"""
The :mod:`extreme_learning_machine` contains the ELMRegressor and the ELMClassifier
"""

# Authors: Peter Steiner <peter.steiner@tu-dresden.de>, Michael Schindler <michael.schindler@maschindler.de>
# License: BSD 3 clause

import sys

import numpy as np

from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, MultiOutputMixin, is_regressor
from pyrcn.base import InputToNode
from pyrcn.linear_model import IncrementalRegression
from sklearn.utils import check_random_state
from sklearn.preprocessing import LabelBinarizer
from sklearn.exceptions import NotFittedError
from sklearn.pipeline import FeatureUnion


class ELMRegressor(BaseEstimator, MultiOutputMixin, RegressorMixin):
    """
    Extreme Learning Machine regressor.

    This model optimizes the mean squared error loss function using linear regression.

    Parameters
    ----------
    input_to_nodes : iterable, default=[('default', InputToNode())]
        List of (name, transform) tuples (implementing fit/transform) that are
        chained, in the order in which they are chained, with the last object
        an estimator.
    regressor : object, default=IncrementalRegression(alpha=.0001)
        Regressor object such as derived from ``RegressorMixin``. This
        regressor will automatically be cloned each time prior to fitting.
        regressor cannot be None, omit argument if in doubt
    chunk_size : int, default=None
        if X.shape[0] > chunk_size, calculate results incrementally with partial_fit
    random_state : int, RandomState instance, default=None
    """
    def __init__(self,
                 input_to_nodes=InputToNode(),
                 regressor=IncrementalRegression(alpha=.0001),
                 chunk_size=None,
                 random_state=None):
        self.input_to_nodes = input_to_nodes
        self.random_state = random_state
        self._chunk_size = chunk_size
        self._regressor = regressor

    def partial_fit(self, X, y, n_jobs=None, transformer_weights=None, postpone_inverse=False):
        """
        Fits the regressor partially.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_targets)
            The targets to predict.
        n_jobs : int, default=None
            The number of jobs to run in parallel. ``-1`` means using all processors.
            See :term:`Glossary <n_jobs>` for more details.
        transformer_weights : ignored
        postpone_inverse : bool, default=False
            If output weights have not been fitted yet, regressor might be hinted at
            postponing inverse calculation. Refer to IncrementalRegression for details.

        Returns
        -------
        self : Returns a trained ELMRegressor model.
        """
        if not hasattr(self._regressor, 'partial_fit'):
            raise BaseException('regressor has no attribute partial_fit, got {0}'.format(self._regressor))

        self._validate_hyperparameters()
        self._validate_data(X, y, multi_output=True)

        # input_to_node
        try:
            hidden_layer_state = self._input_to_node.transform(X)
        except NotFittedError as e:
            print('input_to_node has not been fitted yet: {0}'.format(e))
            hidden_layer_state = self._input_to_node.fit_transform(X)
            pass

        # regression
        if self._regressor:
            self._regressor.partial_fit(hidden_layer_state, y, postpone_inverse=postpone_inverse)
        return self

    def fit(self, X, y, n_jobs=None, transformer_weights=None):
        """
        Fits the regressor.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_targets)
            The targets to predict.
        n_jobs : int, default=None
            The number of jobs to run in parallel. ``-1`` means using all processors.
            See :term:`Glossary <n_jobs>` for more details.
        transformer_weights : ignored

        Returns
        -------
        self : Returns a trained ELMRegressor model.
        """
        self._validate_hyperparameters()
        self._validate_data(X, y, multi_output=True)

        self._input_to_node.fit(X)
        self._regressor = self._regressor.__class__()

        if self._chunk_size is None or self._chunk_size >= X.shape[0]:
            # input_to_node
            hidden_layer_state = self._input_to_node.transform(X)

            # regression
            self._regressor.fit(hidden_layer_state, y)
        elif self._chunk_size < X.shape[0]:
            # setup chunk list
            chunks = list(range(0, X.shape[0], self._chunk_size))
            # postpone inverse calculation for chunks n-1
            for idx in chunks[:-1]:
                ELMRegressor.partial_fit(
                    self,
                    X=X[idx:idx + self._chunk_size, ...],
                    y=y[idx:idx + self._chunk_size, ...],
                    n_jobs=n_jobs,
                    transformer_weights=transformer_weights,
                    postpone_inverse=True
                )
            # last chunk, calculate inverse and bias
            ELMRegressor.partial_fit(
                self,
                X=X[chunks[-1]:, ...],
                y=y[chunks[-1]:, ...],
                n_jobs=n_jobs,
                transformer_weights=transformer_weights,
                postpone_inverse=False
            )
        else:
            raise ValueError('chunk_size invalid {0}'.format(self._chunk_size))
        return self

    def predict(self, X):
        """
        Predicts the targets using the trained ELM regressor.
        Parameters

        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)

        Returns
        -------
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_targets)
            The predicted targets
        """
        if self._input_to_node is None or self._regressor is None:
            raise NotFittedError(self)

        hidden_layer_state = self._input_to_node.transform(X)

        return self._regressor.predict(hidden_layer_state)

    def _validate_hyperparameters(self):
        """
        Validates the hyperparameters.

        Returns
        -------
        """
        self.random_state = check_random_state(self.random_state)

        if not (hasattr(self.input_to_nodes, "fit") and hasattr(self.input_to_nodes, "fit_transform") and hasattr(
                self.input_to_nodes, "transform")):
            raise TypeError("All input_to_nodes should be transformers "
                            "and implement fit and transform "
                            "'%s' (type %s) doesn't" % (self.input_to_nodes, type(self.input_to_nodes)))

        if self._chunk_size is not None and (not isinstance(self._chunk_size, int) or self._chunk_size < 0):
            raise ValueError('Invalid value for chunk_size, got {0}'.format(self._chunk_size))

        if not is_regressor(self._regressor):
            raise TypeError("The last step should be a regressor "
                            "and implement fit and predict"
                            "'%s' (type %s) doesn't" % (self._regressor, type(self._regressor)))

    def __sizeof__(self):
        """
        Returns the size of the object in bytes.

        Returns
        -------
        size : int
        Object memory in bytes.
        """
        return object.__sizeof__(self) + \
            sys.getsizeof(self._input_to_node) + \
            sys.getsizeof(self._regressor)

    @property
    def regressor(self):
        """
        Returns the chunk_size, in which X will be chopped.

        Returns
        -------
        chunk_size : int or None
        """
        return self._regressor

    @regressor.setter
    def regressor(self, regressor):
        """
        Sets the regressor.

        Parameters
        ----------
        regressor : regressor or None

        Returns
        -------
        """
        self._regressor = regressor

    @property
    def input_to_nodes(self):
        """
        Returns the input_to_nodes list or the input_to_node Transformer.

        Returns
        -------
        input_to_nodes : Transformer or [Transformer]
        """
        return self._input_to_node

    @input_to_nodes.setter
    def input_to_nodes(self, input_to_nodes, n_jobs=None, transformer_weights=None):
        """
        Sets the input_to_nodes list or the input_to_nodes Transformer.

        Parameters
        ----------
        input_to_nodes : Transformer or [Transformer]
        n_jobs : int, default=None
        Number of jobs to run in parallel.
        None means 1 unless in a joblib.parallel_backend context. -1 means using all processors.
        transformer_weights : dict, default=None
        Multiplicative weights for features per transformer.
        Keys are transformer names, values the weights.
        Raises ValueError if key not present in transformer_list.

        Returns
        -------
        """
        if hasattr(input_to_nodes, '__iter__'):
            # Feature Union of list of input_to_nodes
            self._input_to_node = FeatureUnion(
                transformer_list=input_to_nodes,
                n_jobs=n_jobs,
                transformer_weights=transformer_weights)
        else:
            # single input_to_node
            self._input_to_node = input_to_nodes

    @property
    def chunk_size(self):
        """
        Returns the chunk_size, in which X will be chopped.

        Returns
        -------
        chunk_size : int or None
        """
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, chunk_size):
        """
        Sets the chunk_size, in which X will be chopped.

        Parameters
        ----------
        chunk_size : int or None

        Returns
        -------
        """
        self._chunk_size = chunk_size


class ELMClassifier(ELMRegressor, ClassifierMixin):
    """
    Extreme Learning Machine classifier.

    This model optimizes the mean squared error loss function using linear regression.

    Parameters
    ----------
    input_to_nodes : iterable, default=[('default', InputToNode())]
        List of (name, transform) tuples (implementing fit/transform) that are
        chained, in the order in which they are chained, with the last object
        an estimator.
    regressor : object, default=IncrementalRegression(alpha=.0001)
        Regressor object such as derived from ``RegressorMixin``. This
        regressor will automatically be cloned each time prior to fitting.
        regressor cannot be None, omit argument if in doubt
    chunk_size : int, default=None
        if X.shape[0] > chunk_size, calculate results incrementally with partial_fit
    random_state : int, RandomState instance, default=None
    """
    def __init__(self,
                 input_to_nodes=InputToNode(),
                 regressor=IncrementalRegression(alpha=.0001),
                 chunk_size=None,
                 random_state=None):
        super().__init__(input_to_nodes=input_to_nodes, regressor=regressor, chunk_size=chunk_size, random_state=random_state)
        self._encoder = None

    def partial_fit(self, X, y, n_jobs=None, transformer_weights=None, postpone_inverse=False):
        """Fits the regressor partially.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_classes)
            The targets to predict.
        n_jobs : int, default=None
            The number of jobs to run in parallel. ``-1`` means using all processors.
            See :term:`Glossary <n_jobs>` for more details.
        transformer_weights : ignored
        postpone_inverse : bool, default=False
            If output weights have not been fitted yet, regressor might be hinted at
            postponing inverse calculation. Refer to IncrementalRegression for details.

        Returns
        -------
        self : returns a trained ELMClassifier model
        """
        self._validate_data(X, y, multi_output=True)

        if self._encoder is None:
            self._encoder = LabelBinarizer().fit(y)

        return super().partial_fit(X, self._encoder.transform(y), n_jobs=n_jobs, transformer_weights=None)

    def fit(self, X, y, n_jobs=None, transformer_weights=None):
        """
        Fits the regressor.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
        y : {ndarray, sparse matrix} of shape (n_samples,) or (n_samples, n_classes)
            The targets to predict.
        n_jobs : int, default=None
            The number of jobs to run in parallel. ``-1`` means using all processors.
            See :term:`Glossary <n_jobs>` for more details.
        transformer_weights : ignored

        Returns
        -------
        self : Returns a trained ELMClassifier model.
        """
        self._validate_data(X, y, multi_output=True)
        self._encoder = LabelBinarizer().fit(y)

        return super().fit(X, self._encoder.transform(y), n_jobs=n_jobs, transformer_weights=None)

    def predict(self, X):
        """
        Predict the classes using the trained ELM classifier.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)

        Returns
        -------
        y_pred : ndarray of shape (n_samples,) or (n_samples, n_classes)
            The predicted classes.
        """
        return self._encoder.inverse_transform(super().predict(X), threshold=.0)

    def predict_proba(self, X):
        """
        Predict the probability estimated using the trained ELM classifier.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
            The input data.

        Returns
        -------
        y_pred : ndarray of shape (n_samples,) or (n_samples, n_classes)
            The predicted probability estimated.
        """
        # for single dim proba use np.amax
        # predicted_positive = np.subtract(predicted.T, np.min(predicted, axis=1))
        predicted_positive = np.clip(super().predict(X), a_min=0, a_max=None).T
        return np.divide(predicted_positive, np.sum(predicted_positive, axis=0)).T

    def predict_log_proba(self, X):
        """
        Predict the logarithmic probability estimated using the trained ELM classifier.

        Parameters
        ----------
        X : {ndarray, sparse matrix} of shape (n_samples, n_features)
            The input data.

        Returns
        -------
        y_pred : ndarray of shape (n_samples,) or (n_samples, n_classes)
            The predicted logarithmic probability estimated.
        """
        return np.log(self.predict_proba(X=X))
