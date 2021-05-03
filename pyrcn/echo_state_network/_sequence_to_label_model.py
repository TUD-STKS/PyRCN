"""
Sequence-to-label model
"""

# Authors: Peter Steiner <peter.steiner@tu-dresden.de>
# License: BSD 3 clause

from sklearn.preprocessing import LabelBinarizer
from sklearn.utils.validation import _deprecate_positional_args

from pyrcn.base import InputToNode, NodeToNode
from pyrcn.linear_model import IncrementalRegression
from pyrcn.echo_state_network import ESNClassifier
import numpy as np
from tqdm import tqdm


class SeqToLabelESNClassifier(ESNClassifier):
    """
    A trainer to simplify sequence-to-label classification.
    """
    @_deprecate_positional_args
    def __init__(self, *,
                 input_to_node=InputToNode(),
                 node_to_node=NodeToNode(),
                 regressor=IncrementalRegression(alpha=.0001),
                 chunk_size=None,
                 n_jobs=None,
                 output_strategy="last_state",
                 **kwargs):
        super().__init__(input_to_node=input_to_node, 
                         node_to_node=node_to_node,
                         regressor=regressor,
                         chunk_size=chunk_size,
                         **kwargs)
        self.n_jobs = n_jobs
        self.output_strategy = output_strategy

    def partial_fit(self, X, y, classes=None, n_jobs=None, transformer_weights=None, postpone_inverse=False):
        for X_train, y_train in tqdm(zip(X, y)):
            y_train = np.repeat(y_train, X_train.shape[0])
            super().partial_fit(X_train, y_train, classes=classes, postpone_inverse=True)
        return self

    def fit(self, X, y, n_jobs=None, transformer_weights=None):
        lab = LabelBinarizer().fit(np.concatenate(y))
        if lab.y_type_.startswith('multilabel'):
            classes = np.zeros(shape=(1, y[0].shape[1]))
        else:
            classes = lab.classes_
        for X_train, y_train in tqdm(zip(X[:-1], y[:-1])):
            y_train = np.repeat(y_train, X_train.shape[0])
            super().partial_fit(X_train, y_train, classes=classes, postpone_inverse=True)
        super().partial_fit(X=X[-1], y=np.repeat(y[-1], X[-1].shape[0]), postpone_inverse=False)
        return self

    def predict(self, X):
        y_pred = np.empty(shape=(X.shape[0], ), dtype=object)
        for k, X_test in tqdm(enumerate(X)):
            if self.output_strategy == "winner_takes_all":
                y_pred[k] = np.atleast_1d(np.argmax(np.bincount(super().predict(X_test))))
            elif self.output_strategy == "last_state":
                y_pred[k] = np.atleast_1d(super().predict(X_test)[-1])
            else:
                raise NotImplementedError("Unknown output strategy: {0}".format(self.output_strategy))
        return y_pred

    def predict_proba(self, X):
        y_pred = np.empty(shape=(X.shape[0], ), dtype=object)
        for k, X_test in tqdm(enumerate(X)):
            y_pred[k] = np.mean(super().predict_proba(X_test), axis=0)
        return y_pred

    def predict_log_proba(self, X):
        y_pred = np.empty(shape=(X.shape[0], ), dtype=object)
        for k, X_test in tqdm(enumerate(X)):
            y_pred[k] = np.mean(super().predict_log_proba(X_test), axis=0)
        return y_pred