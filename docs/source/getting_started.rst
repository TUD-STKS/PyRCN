===============
Getting started
===============

Before getting started with PyRCN, make sure you have correctly installed
the package and all its dependencies by looking at the :ref:`installation guide`.

PyRCN is an open-source project which aims to provide a framework for developing
Reservoir Computing Networks (RCNs) transparently and without using any heavy 
machine learning library or framework.

To learn more about the theoretical aspects of reservoir computing, you can read the
page :ref:`whats rc`.

Playing with blocks -- Building blocks of Reservoir Computing
=============================================================

In the recent years, several groups have built toolboxes for Reservoir Computing. 
However, they were mostly able to implement one specific type of RCNs from
- Echo State Networks
- Extreme Learning Machines
- Liquid State Machines

Problem is that, despite the similarities of different RCN architectures, nobody has
decomposed RCNs in building blocks. Together with PyRCN, we aim to do that and provide
building blocks with which almost any RCN structure can be composed.

Building your first Reservoir Computing Network
-----------------------------------------------

    Essentially, with only one command, an Echo State Network can be defined 
    using the :py:class:`pyrcn.echo_state_network.ESNRegressor` or 
    :py:class:`pyrcn.echo_state_network.ESNClassifier` class:

    .. doctest::

        >>> from pyrcn.echo_state_network import ESNRegressor, ESNClassifier
        >>> 
        >>> 
        >>> esn = ESNRegressor()
        >>> esn
        ESNRegressor(input_to_node=InputToNode(), node_to_node=NodeToNode(),
                     regressor=IncrementalRegression())

    As we can see, the  ``esn`` consists of different building blocks, e.g. 
    :py:class:`pyrcn.base.InputToNode` :py:class:`pyrcn.base.NodeToNode`.  
    The first one is used to define the connections between the hidden neurons and the inputs,
    the second building block defines how the connections inside the hidden neurons are
    organized. By default, all connections are randomly initialized and fixed. 

    In case one would like to customize the building blocks, you can have a look at the included 
    modules of ``pyrcn.base``.

    .. doctest::

        >>> import pyrcn.base
        >>> from inspect import getmembers, isclass
        >>> getmembers(pyrcn.base, isclass)
        [..., ('BatchIntrinsicPlasticity', <class 'pyrcn.base.BatchIntrinsicPlasticity'>), 
         ('FeedbackNodeToNode', <class 'pyrcn.base.FeedbackNodeToNode'>), ('HebbianNodeToNode', <class 'pyrcn.base.HebbianNodeToNode'>), 
         ('InputToNode', <class 'pyrcn.base.InputToNode'>), ('NodeToNode', <class 'pyrcn.base.NodeToNode'>), 
         ('PredefinedWeightsInputToNode', <class 'pyrcn.base.PredefinedWeightsInputToNode'>), 
         ('PredefinedWeightsNodeToNode', <class 'pyrcn.base.PredefinedWeightsNodeToNode'>), ...]

    Obviously, there are a lot of derived modules from the basic building blocks available. 
    Look their functions up in the documentation or in examples!

Training a RCN
--------------

    RCNs can be trained on different kinds of data. In particular, ESNs can then be trained on 
    sequential data, such as timeseries, especially chaotic ones. In PyRCN, we have implemented the
    Mackey-Glass time-series, which is a common demonstration for ESNs:

    .. doctest::

        >>> from pyrcn.datasets import mackey_glass
        >>> # some dummy sequential data
        >>> X, y = mackey_glass(n_timesteps=8000)

    The result is displayed below: A Mackey-Glass time-series.
    The ESN will have to predict their future values one timestep ahead:

    .. image:: _static/img/getting_started_mackey_glass.svg

    To train the ESN, only two steps are required:
    
    1. Computing the reservoir states, 
    2. compute a linear regression betweeen the reservoir states and the target output
    
    These two steps are handled by the function :py:func:`pyrcn.echo_state_network.ESNRegressor.fit` :

    .. doctest::

        >>> # Fit the ESN model
        >>> esn.fit(X[:4000].reshape(-1, 1), y[:4000])
        ESNRegressor(input_to_node=InputToNode(), node_to_node=NodeToNode(),
             regressor=IncrementalRegression(), requires_sequence=False)

    That's it! The ESN model is now ready for prediction.

Testing and predict using the ESN
---------------------------------

    Finally, we use the :py:func:`pyrcn.echo_state_network.ESNRegressor.predict` function to use the freshly
    trained ESN to predict the test data:

    .. doctest::

        >>> y_pred = esn.predict(X[:4000])

    .. image:: _static/img/getting_started_mackey_glass_predicted.svg

    Not so bad! Of course this example is trivial, and the ESN can be used on much more
    complicated tasks, like speech recognition or chaotic timeseries prediction. 

Going further
=============

To handle more complicated and realistic cases, you will probably need to pay a particular attention to
how the reservoir and input matrix are built, how the readout matrix is trained, and how to evaluate
your model to find the best parameters. All these aspects of reservoir computing are covered in the following tutorials:

- :doc:`tutorials <tutorial>`, to go deeper into ReservoirPy API and see more realistc examples and applications