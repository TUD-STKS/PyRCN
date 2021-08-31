"""PTDB-TUG: Pitch Tracking Database from Graz University of Technology
The original database is available at

    https://www.spsc.tugraz.at/databases-and-tools/ptdb-tug-pitch-tracking-database-from-graz-university-of-technology.html


"""
from pathlib import Path
from os.path import dirname, exists, join
from os import makedirs, remove, walk

import numpy as np
import pandas as pd
import joblib

from sklearn.datasets import get_data_home
from sklearn.datasets._base import RemoteFileMetadata, _pkl_filepath
from sklearn.utils import _deprecate_positional_args


@_deprecate_positional_args
def fetch_ptdb_tug_dataset(*, data_origin=None, data_home=None, preprocessor=None, 
                           force_preprocessing=False):
    """
    Load the PTDB-TUG: Pitch Tracking Database from Graz University of Technology
    (classification and regression)

    =================   =====================
    Outputs                                 2
    Samples total                        TODO
    Dimensionality                       TODO
    Features                             TODO
    =================   =====================

    Parameters
    ----------
    data_origin : str, default=None
        Specify where the original dataset can be found. By default,
        all pyrcn data is stored in '~/pyrcn_data' and all scikit-learn data in
       '~/scikit_learn_data' subfolders.

    data_home : str, default=None
        Specify another download and cache folder fo the datasets. By default,
        all pyrcn data is stored in '~/pyrcn_data' and all scikit-learn data in
       '~/scikit_learn_data' subfolders.

    preprocessor : default=None,
        Estimator for preprocessing the dataset (create features and targets from 
        audio and label files).

    Returns
    -------
    (X, y) : tuple
    """
    data_home = get_data_home(data_home=data_home)
    if not exists(data_home):
        makedirs(data_home)
    filepath = _pkl_filepath(data_home, 'ptdb_tug.pkz')
    if not exists(filepath) or force_preprocessing:
        print('preprocessing PTDB-TUG database from %s to %s'
              % (data_origin, data_home))
        all_training_files = []
        all_test_files = []
        for root, dirs, files in walk(data_origin):
            for f in files:
                if f.endswith(".wav") and f.startswith("mic"):
                    if "F09" in f or "F10" in f or "M09" in f or "M10" in f:
                        all_test_files.append(join(root, f))
                    else:
                        all_training_files.append(join(root, f))

        X_train = np.empty(shape=(len(all_training_files),), dtype=object)
        y_train = np.empty(shape=(len(all_training_files),), dtype=object)
        X_test = np.empty(shape=(len(all_test_files),), dtype=object)
        y_test = np.empty(shape=(len(all_test_files),), dtype=object)

        for k, f in enumerate(all_training_files):
            X_train[k] = preprocessor.transform(f)
            y_train[k] = pd.read_csv(f.replace("MIC", "REF").replace("mic", "ref").replace(".wav", ".f0"), sep=" ", header=None)
        for k, f in enumerate(all_test_files):
            X_test[k] = preprocessor.transform(f)
            y_test[k] = pd.read_csv(f.replace("MIC", "REF").replace("mic", "ref").replace(".wav", ".f0"), sep=" ", header=None)
        joblib.dump([X_train, X_test, y_train, y_test], filepath, compress=6)
    else:
        X_train, X_test, y_train, y_test = joblib.load(filepath)

    x_shape_zero = np.unique([x.shape[0] for x in X_train] + [x.shape[0] for x in X_test])
    x_shape_one = np.unique([x.shape[1] for x in X_train] + [x.shape[1] for x in X_test])
    if len(x_shape_zero) == 1 and len(x_shape_one) > 1:
        for k in range(len(X_train)):
            X_train[k] = X_train[k].T
            y_train[k] = _get_labels(X_train[k], y_train[k])
        for k in range(len(X_test)):
            X_test[k] = X_test[k].T
            y_test[k] = _get_labels(X_test[k], y_test[k])
    elif len(x_shape_zero) > 1 and len(x_shape_one) == 1:
        for k in range(len(X_train)):
            y_train[k] = _get_labels(X_train[k], y_train[k])
        for k in range(len(X_test)):
            y_test[k] = _get_labels(X_test[k], y_test[k])
    else:
        raise TypeError("Invalid dataformat. Expected at least one equal dimension of all sequences.")

    return X_train, X_test, y_train, y_test


def _get_labels(X, df_label):
    labels = df_label[[0, 1]].to_numpy()
    y = np.zeros(shape=(X.shape[0], 2))
    if X.shape[0] == labels.shape[0]:
        y[:, :] = labels
    else:
        y[1:1+len(labels), :] = labels
    return y
