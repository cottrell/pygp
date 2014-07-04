"""
Simple wrapper class for a Basic GP.
"""

# future imports
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

# global imports
import numpy as np

# local imports
from .exact import ExactGP
from ..likelihoods import Gaussian
from ..kernels import SE, Matern
from ..utils.models import Printable

# exported symbols
__all__ = ['BasicGP']


# NOTE: in the definition of the BasicGP class Printable has to come first so
# that we use the __repr__ method defined there and override the base method.

class BasicGP(Printable, ExactGP):
    def __init__(self, sn, sf, ell, kernel='SE', ndim=None):
        likelihood = Gaussian(sn)
        kernel = (
            SE(sf, ell, ndim)        if (kernel == 'SE') else
            Matern(sf, ell, 1, ndim) if (kernel == 'Matern1') else
            Matern(sf, ell, 3, ndim) if (kernel == 'Matern3') else
            Matern(sf, ell, 5, ndim) if (kernel == 'Matern5') else None)

        if kernel is None:
            raise RuntimeError('Unknown kernel type')

        super(BasicGP, self).__init__(likelihood, kernel)

    def _params(self):
        # replace the parameters for the base GP model with a simplified
        # structure and rename the likelihood's sigma parameter to sn (ie its
        # the sigma corresponding to the noise).
        return [('sn', 1)] + self._kernel._params()
