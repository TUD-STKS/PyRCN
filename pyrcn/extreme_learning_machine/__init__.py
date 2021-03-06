"""
The :mod:`pyrcn.elm` module includes Extreme Learning Machine algorithms.
"""

# See https://github.com/TUD-STKS/PyRCN for complete
# documentation.

# Author: Michael Schindler <michael.schindler1@mailbox.tu-dresden.de> with help from
#         the pyrcn community. ELM are copyright of their respective owners.
# License: BSD 3-Clause (C) TU Dresden 2020

from pyrcn.extreme_learning_machine._extreme_learning_machine import ELMClassifier, ELMRegressor

__all__ = ['ELMClassifier',
           'ELMRegressor'
           ]
