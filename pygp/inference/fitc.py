"""
FITC approximation for sparse pseudo-input GPs.
"""

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import numpy as np
import scipy.linalg as sla
import itertools as it

from ._base import GP
from ..likelihoods import Gaussian

__all__ = ['FITC']


class FITC(GP):
    """
    GP inference using sparse pseudo-inputs.
    """
    def __init__(self, likelihood, kernel, mean, U):
        # NOTE: exact FITC inference will only work with Gaussian likelihoods.
        if not isinstance(likelihood, Gaussian):
            raise ValueError('exact inference requires a Gaussian likelihood')

        super(FITC, self).__init__(likelihood, kernel, mean)

        # save the pseudo-input locations.
        self._U = np.array(U, ndmin=2, dtype=float, copy=True)

        # sufficient statistics that we'll need.
        self._L = None
        self._R = None
        self._b = None

        # these are useful in computing the loglikelihood and updating the
        # sufficient statistics.
        self._A = None
        self._a = None

    def reset(self):
        for attr in 'LRbAa':
            setattr(self, '_' + attr, None)
        super(FITC, self).reset()

    @property
    def pseudoinputs(self):
        """The pseudo-input points."""
        return self._U

    def _update(self):
        sn2 = self._likelihood.s2
        su2 = sn2 / 1e6

        # kernel wrt the inducing points.
        Kuu = self._kernel.get(self._U)
        p = self._U.shape[0]

        # cholesky for the information gain. note that we only need to compute
        # this once as it is independent from the data.
        self._L = sla.cholesky(Kuu + su2*np.eye(p))

        # evaluate the kernel and residuals at the new points
        Kux = self._kernel.get(self._U, self._X)
        kxx = self._kernel.dget(self._X)
        r = self._y - self._mean

        # the cholesky of Q.
        V = sla.solve_triangular(self._L, Kux, trans=True)

        # rescale everything by the diagonal matrix ell.
        ell = np.sqrt(kxx + sn2 - np.sum(V**2, axis=0))
        Kux /= ell
        V /= ell
        r /= ell

        # NOTE: to update things incrementally all we need to do is store these
        # components. A just needs to be initialized at the identity and then
        # we just accumulate here.
        self._A = np.eye(p) + np.dot(V, V.T)
        self._a = np.dot(Kux, r)

        # update the posterior.
        self._R = np.dot(sla.cholesky(self._A), self._L)
        self._b = sla.solve_triangular(self._R, self._a, trans=True)

    def _full_posterior(self, X):
        mu = np.full(X.shape[0], self._mean)
        Sigma = self._kernel.get(X)

        if self._X is not None:
            # get the kernel and do two backsolves by the lower-dimensional
            # choleskys that we've stored.
            K = self._kernel.get(self._U, X)
            LK = sla.solve_triangular(self._L, K, trans=True)
            RK = sla.solve_triangular(self._R, K, trans=True)

            # add on the posterior mean contribution and reduce the variance
            # based on the information that we gain from the posterior but add
            # additional uncertainty the further away we are from the inducing
            # points.
            mu += np.dot(RK.T, self._b)
            Sigma += np.dot(RK.T, RK) - np.dot(LK.T, LK)

        return mu, Sigma

    def _marg_posterior(self, X, grad=False):
        # grab the prior mean and variance.
        mu = np.full(X.shape[0], self._mean)
        s2 = self._kernel.dget(X)

        if self._X is not None:
            # get the kernel and do two backsolves by the lower-dimensional
            # choleskys that we've stored.
            K = self._kernel.get(self._U, X)
            LK = sla.solve_triangular(self._L, K, trans=True)
            RK = sla.solve_triangular(self._R, K, trans=True)

            # add on the posterior mean contribution and reduce the variance
            # based on the information that we gain from the posterior but add
            # additional uncertainty the further away we are from the inducing
            # points.
            mu += np.dot(RK.T, self._b)
            s2 += np.sum(RK**2, axis=0) - np.sum(LK**2, axis=0)

        if not grad:
            return (mu, s2)

        # Get the prior gradients. Note that this assumes a constant mean and
        # stationary kernel.
        dmu = np.zeros_like(X)
        ds2 = np.zeros_like(X)

        if self._X is not None:
            p = self._U.shape[0]
            dK = self._kernel.grady(self._U, X)
            dK = dK.reshape(p, -1)

            LdK = sla.solve_triangular(self._L, dK, trans=True)
            RdK = sla.solve_triangular(self._R, dK, trans=True)

            dmu += np.dot(RdK.T, self._b).reshape(X.shape)

            LdK = np.rollaxis(np.reshape(LdK, (p,) + X.shape), 2)
            RdK = np.rollaxis(np.reshape(RdK, (p,) + X.shape), 2)

            ds2 += 2 * np.sum(RdK * RK, axis=1).T
            ds2 -= 2 * np.sum(LdK * LK, axis=1).T

        return (mu, s2, dmu, ds2)

    def loglikelihood(self, grad=False):
        # noise hyperparameters
        sn2 = self._likelihood.s2
        su2 = sn2 / 1e6

        # get the rest of the kernels and the residual.
        Kux = self._kernel.get(self._U, self._X)
        kxx = self._kernel.dget(self._X)
        r = self._y - self._mean

        # the cholesky of Q.
        V = sla.solve_triangular(self._L, Kux, trans=True)

        # rescale everything by the diagonal matrix ell.
        ell = np.sqrt(kxx + sn2 - np.sum(V**2, axis=0))
        V /= ell
        r /= ell

        # Note this A corresponds to chol(A) from _update.
        A = sla.cholesky(self._A)
        beta = sla.solve_triangular(A, V.dot(r), trans=True)
        alpha = (r - V.T.dot(sla.solve_triangular(A, beta))) / ell

        lZ = -np.sum(np.log(np.diag(A))) - np.sum(np.log(ell))
        lZ -= 0.5 * (np.inner(r, r) - np.inner(beta, beta))
        lZ -= 0.5 * ell.shape[0] * np.log(2*np.pi)

        if not grad:
            return lZ

        B = sla.solve_triangular(self._L, V*ell)
        W = sla.solve_triangular(A, V/ell, trans=True)
        w = B.dot(alpha)
        v = 2*su2*np.sum(B**2, axis=0)

        # allocate space for the gradients.
        dlZ = np.zeros(self.nhyper)

        # gradient wrt the noise parameter.
        dlZ[0] = (
            - sn2 * (np.sum(1/ell**2) - np.sum(W**2) - np.inner(alpha, alpha))
            - su2 * (np.sum(w**2) + np.sum(B.dot(W.T)**2))
            + 0.5 * (
                np.inner(alpha, v*alpha) + np.inner(np.sum(W**2, axis=0), v)))

        # iterator over gradients of the kernels
        dK = it.izip(
            self._kernel.grad(self._U),
            self._kernel.grad(self._U, self._X),
            self._kernel.dgrad(self._X))

        # gradient wrt the kernel hyperparameters.
        i = 1
        for i, (dKuu, dKux, dkxx) in enumerate(dK, i):
            M = 2*dKux - dKuu.dot(B)
            v = dkxx - np.sum(M*B, axis=0)
            dlZ[i] = (
                - np.sum(dkxx/ell**2)
                - np.inner(w, dKuu.dot(w) - 2*dKux.dot(alpha))
                + np.inner(alpha, v*alpha) + np.inner(np.sum(W**2, axis=0), v)
                + np.sum(M.dot(W.T) * B.dot(W.T))) / 2.0

        # gradient wrt the constant mean.
        dlZ[-1] = np.sum(alpha)

        return lZ, dlZ
