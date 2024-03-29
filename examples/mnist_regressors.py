#!/usr/bin/env python
# coding: utf-8
# MNIST classification using Extreme Learning Machines
import numpy as np
import time
from sklearn.base import clone
from sklearn.datasets import fetch_openml
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import (
    RandomizedSearchCV, GridSearchCV, ParameterGrid,
    cross_validate)
from sklearn.utils.fixes import loguniform
from sklearn.metrics import accuracy_score

from pyrcn.model_selection import SequentialSearchCV
from pyrcn.extreme_learning_machine import ELMClassifier


# Load the dataset
X, y = fetch_openml('mnist_784', version=1, return_X_y=True, as_frame=False)

# Train test split and normalize to a range between [-1, 1].
X = MinMaxScaler(feature_range=(-1, 1)).fit_transform(X=X)
X_train, X_test = X[:60000], X[60000:]
y_train, y_test = y[:60000].astype(int), y[60000:].astype(int)

# # Prepare sequential hyperparameter tuning
initially_fixed_params = {
    'hidden_layer_size': 500,
    'input_activation': 'tanh',
    'k_in': 10,
    'bias_scaling': 0.0,
    'alpha': 1e-5,
    'random_state': 42
}

step1_params = {'input_scaling': loguniform(1e-5, 1e1)}
kwargs1 = {
    'random_state': 42, 'verbose': 1, 'n_jobs': -1, 'n_iter': 5,
    'scoring': 'accuracy'
}
step2_params = {'bias_scaling': np.linspace(0.0, 1.6, 16)}
kwargs2 = {'verbose': 5, 'n_jobs': -1, 'scoring': 'accuracy'}

elm = ELMClassifier(regressor=Ridge(), **initially_fixed_params)

searches = [('step1', RandomizedSearchCV, step1_params, kwargs1),
            ('step2', GridSearchCV, step2_params, kwargs2)]

# # Perform the sequential search
sequential_search = SequentialSearchCV(elm, searches=searches).fit(X_train,
                                                                   y_train)
best_params = sequential_search.best_estimator_.get_params()

# # Test
# Increase reservoir size and compare different regression methods.
# Make sure that you have enough RAM for that, because all regression types
# without chunk size require a lot of memory. This is the reason why,
# especially for large datasets, the incremental regression is recommended.

base_elm_ridge = ELMClassifier(regressor=Ridge(), **best_params)
base_elm_inc = ELMClassifier(**best_params)
base_elm_inc_chunk = clone(base_elm_inc).set_params(chunk_size=6000)

param_grid = {'hidden_layer_size': [500, 1000, 2000, 4000, 8000, 16000]}

print("CV results\tFit time\tInference time\tAccuracy score\tSize[Bytes]")
for params in ParameterGrid(param_grid):
    elm_ridge_cv = cross_validate(clone(base_elm_ridge).set_params(**params),
                                  X=X_train, y=y_train)
    t1 = time.time()
    elm_ridge = clone(base_elm_ridge).set_params(**params).fit(X_train,
                                                               y_train)
    t_fit = time.time() - t1
    mem_size = elm_ridge.__sizeof__()
    t1 = time.time()
    acc_score = accuracy_score(y_test, elm_ridge.predict(X_test))
    t_inference = time.time() - t1
    print("{0}\t{1}\t{2}\t{3}\t{4}"
          .format(elm_ridge_cv, t_fit, t_inference, acc_score, mem_size))
    elm_inc_cv = cross_validate(clone(base_elm_inc).set_params(**params),
                                X=X_train, y=y_train)
    t1 = time.time()
    elm_inc = clone(base_elm_inc).set_params(**params).fit(X_train, y_train)
    t_fit = time.time() - t1
    mem_size = elm_inc.__sizeof__()
    t1 = time.time()
    acc_score = accuracy_score(y_test, elm_inc.predict(X_test))
    t_inference = time.time() - t1
    print("{0}\t{1}\t{2}\t{3}\t{4}"
          .format(elm_inc_cv, t_fit, t_inference, acc_score, mem_size))
    elm_inc_chunk_cv = cross_validate(
        clone(base_elm_inc_chunk).set_params(**params),
        X=X_train, y=y_train)
    t1 = time.time()
    elm_inc_chunk = clone(base_elm_inc_chunk).set_params(**params)\
        .fit(X_train, y_train)
    t_fit = time.time() - t1
    mem_size = elm_inc_chunk.__sizeof__()
    t1 = time.time()
    acc_score = accuracy_score(y_test, elm_inc_chunk.predict(X_test))
    t_inference = time.time() - t1
    print("{0}\t{1}\t{2}\t{3}\t{4}"
          .format(elm_inc_chunk_cv, t_fit, t_inference, acc_score, mem_size))

# In[ ]:
