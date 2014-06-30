"""
Implementation of the squared-exponential kernels.
"""

# future imports
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

# global imports
import numpy as np

# local imports
from ._base import RealKernel
from ._distances import rescale, diff, sqdist, sqdist_foreach

from ..utils.random import rstate
from ..utils.models import Printable

# exported symbols
__all__ = ['SE']


class SE(RealKernel, Printable):
    def __init__(self, sf, ell, ndim=None):
        self._logsf = np.log(float(sf))
        self._logell = np.log(np.ravel(ell))
        self._iso = False
        self.ndim = self._logell.size
        self.nhyper = 1 + self._logell.size

        if ndim is not None:
            if self._logell.size == 1:
                self._logell = float(self._logell)
                self._iso = True
                self.ndim = ndim
            else:
                raise ValueError('ndim only usable with scalar lengthscales')

    def _params(self):
        return [
            ('sf',  1),
            ('ell', self.nhyper-1),]

    def get_hyper(self):
        return np.r_[self._logsf, self._logell]

    def set_hyper(self, hyper):
        self._logsf  = hyper[0]
        self._logell = hyper[1] if self._iso else hyper[1:]

    def get(self, X1, X2=None):
        X1, X2 = rescale(np.exp(self._logell), X1, X2)
        return np.exp(self._logsf*2 - sqdist(X1, X2)/2)

    def grad(self, X1, X2=None):
        X1, X2 = rescale(np.exp(self._logell), X1, X2)
        D = sqdist(X1, X2)
        K = np.exp(self._logsf*2 - D/2)
        yield 2*K                               # derivative wrt logsf
        if self._iso:
            yield K*D                           # derivative wrt logell (iso)
        else:
            for D in sqdist_foreach(X1, X2):
                yield K*D                       # derivative wrt logell (ard)

    def gradx(self, X1, X2=None):
        """
        Derivatives of the kernel with respect to its second argument. This
        corresponds to the covariance between function values evaluated at X1
        and gradients evaluated at X2. Returns an (m,n,d)-array.
        """
        ell = np.exp(self._logell)
        X1, X2 = rescale(ell, X1, X2)

        D = diff(X1, X2)
        K = np.exp(self._logsf*2 - np.sum(D**2, axis=-1)/2)
        G = -K[:,:,None] * D / ell
        return G

    def dget(self, X1):
        return np.exp(self._logsf*2) * np.ones(len(X1))

    def dgrad(self, X):
        yield 2 * self.dget(X)
        for i in xrange(self.nhyper-1):
            yield np.zeros(len(X))

    def sample_spectrum(self, N, rng=None):
        rng = rstate(rng)
        sf2 = np.exp(self._logsf*2)
        ell = np.exp(self._logell)
        W = rng.randn(N, self.ndim) / ell
        return W, sf2
