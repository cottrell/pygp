"""
Meta models which take care of hyperparameter marginalization whenever data is
added.
"""

# future imports
from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

# global imports
import numpy as np

# local imports
from .sampling import sample

# exported symbols
__all__ = []


class SampledGP(object):
    def __init__(self, gp, prior, n=100, burn=0):
        self._gp = gp
        self._prior = prior
        self._samples = []
        self._n = n
        self._burn = burn

        # FIXME: initially we could sample from the prior. It is, however, not
        # even clear that the initial GP is a prior object: ie it could have
        # data already attached to it. So we should probably just sample, and
        # add a flag like `noinit` or something if we want to avoid an initial
        # sample.

        # FIXME: this would also require updating the sampling code for the case
        # that `gp.ndata == 0`.

    def __iter__(self):
        return self._samples.__iter__()

    def _update(self):
        self._samples = sample(self._gp, self._prior, self._n, self._burn, raw=False)
        self._gp = self._samples[-1]

    @property
    def ndata(self):
        return self._gp.ndata

    @property
    def data(self):
        return self._gp.data

    def add_data(self, X, y):
        self._gp.add_data(X, y)
        self._update()

    def posterior(self, X, grad=False):
        parts = map(np.array, zip(*[_.posterior(X, grad) for _ in self._samples]))

        mu_, s2_ = parts[:2]
        mu = np.mean(mu_, axis=0)
        s2 = np.mean(s2_ + (mu_ - mu)**2, axis=0)

        if not grad:
            return mu, s2

        dmu_, ds2_ = parts[2:]
        dmu = np.mean(dmu_, axis=0)
        ds2 = np.mean(ds2_ + 2*dmu_ + 2*dmu - 2*mu_[:,:,None]*dmu[None]
                                            - 2*mu [None,:,None]*dmu_,
                                            axis=0)

        return mu, s2, dmu, ds2
