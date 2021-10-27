"""
The :mod:`echo_state_network` contains the ESNRegressor and the ESNClassifier
"""

# Authors: Peter Steiner <peter.steiner@tu-dresden.de>, Azarakhsh Jalalvand <azarakhsh.jalalvand@ugent.be>
# License: BSD 3 clause

import sys

import numpy as np

from sklearn.base import  ClassifierMixin, RegressorMixin, MultiOutputMixin, is_regressor
from pyrcn.base.blocks import InputToNode, FeedbackNodeToNode
from pyrcn.base import ACTIVATIONS, ACTIVATIONS_INVERSE
from pyrcn.linear_model import IncrementalRegression
from pyrcn.echo_state_network import ESNRegressor
from sklearn.utils.validation import _deprecate_positional_args
from sklearn.preprocessing import LabelBinarizer
from sklearn.exceptions import NotFittedError
from sklearn.pipeline import FeatureUnion


class FeedbackESNRegressor(ESNRegressor):
    """
    Feedback Echo State Network regressor.

    This model optimizes the mean squared error loss function using linear regression.

    Parameters
    ----------
    input_to_node : iterable, default=[('default', InputToNode())]
        List of (name, transform) tuples (implementing fit/transform) that are
        chained, in the order in which they are chained, with the last object
        an estimator.
    node_to_node : iterable, default=[('default', FeedbackNodeToNode())]
        List of (name, transform) tuples (implementing fit/transform) that are
        chained, in the order in which they are chained, with the last object
        an estimator.
    regressor : object, default=IncrementalRegression(alpha=.0001)
        Regressor object such as derived from ``RegressorMixin``. This
        regressor will automatically be cloned each time prior to fitting.
        regressor cannot be None, omit argument if in doubt
    chunk_size : int, default=None
        if X.shape[0] > chunk_size, calculate results incrementally with partial_fit
    kwargs : dict, default = None
        keyword arguments passed to the subestimators if this is desired, default=None
    """
    @_deprecate_positional_args
    def __init__(self, *,
                 input_to_node=None,
                 node_to_node=None,
                 regressor=None,
                 chunk_size=None,
                 verbose=False,
                 **kwargs):
        if node_to_node is None:
            node_to_node = FeedbackNodeToNode()
        super().__init__(input_to_node=input_to_node,
                         node_to_node=node_to_node,
                         regressor=regressor,
                         chunk_size=chunk_size,
                         verbose=verbose,
                         **kwargs)

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

        Returns
        -------
        self : Returns a traines ESNRegressor model.
        """
        if not hasattr(self._regressor, 'partial_fit'):
            raise BaseException('Regressor has no attribute partial_fit, got {0}'.format(self._regressor))

        self._validate_hyperparameters()
        self._validate_data(X, y, multi_output=True)

        # input_to_node
        try:
            hidden_layer_state = self._input_to_node.transform(X)
        except NotFittedError as e:
            if self.verbose:
                print('input_to_node has not been fitted yet: {0}'.format(e))
            hidden_layer_state = self._input_to_node.fit_transform(X)
            pass

        # node_to_node
        try:
            hidden_layer_state = self._node_to_node.transform(hidden_layer_state, y=y)
        except NotFittedError as e:
            if self.verbose:
                print('node_to_node has not been fitted yet: {0}'.format(e))
            self._node_to_node.fit(hidden_layer_state, y=y)
            hidden_layer_state = self._node_to_node.transform(hidden_layer_state, y=y)
            pass

        # regression
        if self._regressor:
            y_scaled = y * self.node_to_node.teacher_scaling + self.node_to_node.teacher_shift
            ACTIVATIONS_INVERSE[self.node_to_node.output_activation](y_scaled)
            self._regressor.partial_fit(hidden_layer_state, y_scaled, postpone_inverse=postpone_inverse)
        if not postpone_inverse:
            self._node_to_node._output_weights = np.vstack((self._regressor.coef_.T, self._regressor.intercept_))
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
        self : Returns a trained ESNRegressor model.
        """
        self._validate_hyperparameters()
        self._validate_data(X, y, multi_output=True)
        self._input_to_node.fit(X)
        self._node_to_node.fit(self._input_to_node.transform(X), y=y)
        self._regressor = self._regressor.__class__()

        if self._chunk_size is None or self._chunk_size > X.shape[0]:
            # input_to_node
            hidden_layer_state = self._input_to_node.transform(X)
            hidden_layer_state = self._node_to_node.transform(hidden_layer_state, y=y)

            # scale teacher
            y_scaled = y * self.node_to_node.teacher_scaling + self.node_to_node.teacher_shift
            ACTIVATIONS_INVERSE[self.node_to_node.output_activation](y_scaled)
            # regression
            self._regressor.fit(hidden_layer_state, y_scaled)

        elif self._chunk_size < X.shape[0]:
            # setup chunk list
            chunks = list(range(0, X.shape[0], self._chunk_size))
            # postpone inverse calculation for chunks n-1
            for idx in chunks[:-1]:
                ESNFeedbackRegressor.partial_fit(
                    self,
                    X=X[idx:idx + self._chunk_size, ...],
                    y=y[idx:idx + self._chunk_size, ...],
                    n_jobs=n_jobs,
                    transformer_weights=transformer_weights,
                    postpone_inverse=True
                )
            # last chunk, calculate inverse and bias
            ESNFeedbackRegressor.partial_fit(
                self,
                X=X[chunks[-1]:, ...],
                y=y[chunks[-1]:, ...],
                n_jobs=n_jobs,
                transformer_weights=transformer_weights,
                postpone_inverse=False
            )
        else:
            raise ValueError('chunk_size invalid {0}'.format(self._chunk_size))
        self._node_to_node._output_weights = np.vstack((self._regressor.coef_.T, self._regressor.intercept_))
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
        hidden_layer_state = self._node_to_node.transform(hidden_layer_state)

        return ((self._node_to_node._y_pred[:-1, :]) - self.node_to_node.teacher_shift) / self.node_to_node.teacher_scaling

    def _validate_hyperparameters(self):
        """Validates the hyperparameters.
        Returns
        -------
        """
        if not (hasattr(self.input_to_node, "fit") and hasattr(self.input_to_node, "fit_transform") and hasattr(
                self.input_to_node, "transform")):
            raise TypeError("All input_to_node should be transformers "
                            "and implement fit and transform "
                            "'%s' (type %s) doesn't" % (self.input_to_node, type(self.input_to_node)))

        if not (hasattr(self.node_to_node, "fit") and hasattr(self.node_to_node, "fit_transform") and hasattr(
                self.node_to_node, "transform")):
            raise TypeError("All node_to_node should be transformers "
                            "and implement fit and transform "
                            "'%s' (type %s) doesn't" % (self.node_to_node, type(self.node_to_node)))

        if self._chunk_size is not None and (not isinstance(self._chunk_size, int) or self._chunk_size < 0):
            raise ValueError('Invalid value for chunk_size, got {0}'.format(self._chunk_size))

        if not is_regressor(self._regressor):
            raise TypeError("The last step should be a regressor "
                            "and implement fit and predict"
                            "'%s' (type %s) doesn't" % (self._regressor, type(self._regressor)))

    def __sizeof__(self):
        """Returns the size of the object in bytes.
        Returns
        -------
        size : int
        Object memory in bytes.
        """
        return object.__sizeof__(self) + \
            sys.getsizeof(self._input_to_node) + \
            sys.getsizeof(self._node_to_node) + \
            sys.getsizeof(self._regressor)

    @property
    def regressor(self):
        """Returns the chunk_size, in which X will be chopped.
        Returns
        -------
        chunk_size : int or None
        """
        return self._regressor

    @regressor.setter
    def regressor(self, regressor):
        """Sets the regressor.
        Parameters
        ----------
        regressor : regressor or None
        Returns
        -------
        """
        self._regressor = regressor

    @property
    def input_to_node(self):
        """Returns the input_to_node list or the input_to_node Transformer.
        Returns
        -------
        input_to_node : Transformer or [Transformer]
        """
        return self._input_to_node

    @input_to_node.setter
    def input_to_node(self, input_to_node, n_jobs=None, transformer_weights=None):
        """Sets the input_to_node list or the input_to_node Transformer.
        Parameters
        ----------
        input_to_node : Transformer or [Transformer]
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
        if hasattr(input_to_node, '__iter__'):
            # Feature Union of list of input_to_node
            self._input_to_node = FeatureUnion(
                transformer_list=input_to_node,
                n_jobs=n_jobs,
                transformer_weights=transformer_weights)
        else:
            # single input_to_node
            self._input_to_node = input_to_node

    @property
    def node_to_node(self):
        """Returns the node_to_node list or the input_to_node Transformer.
        Returns
        -------
        input_to_node : Transformer or [Transformer]
        """
        return self._node_to_node

    @node_to_node.setter
    def node_to_node(self, node_to_node, n_jobs=None, transformer_weights=None):
        """Sets the input_to_node list or the input_to_node Transformer.
        Parameters
        ----------
        node_to_node : Transformer or [Transformer]
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
        if hasattr(node_to_node, '__iter__'):
            # Feature Union of list of input_to_node
            self._node_to_node = FeatureUnion(
                transformer_list=node_to_node,
                n_jobs=n_jobs,
                transformer_weights=transformer_weights)
        else:
            # single input_to_node
            self._node_to_node = node_to_node

    @property
    def chunk_size(self):
        """Returns the chunk_size, in which X will be chopped.
        Returns
        -------
        chunk_size : int or None
        """
        return self._chunk_size

    @chunk_size.setter
    def chunk_size(self, chunk_size):
        """Sets the chunk_size, in which X will be chopped.
        Parameters
        ----------
        chunk_size : int or None
        Returns
        -------
        """
        self._chunk_size = chunk_size
