"""
Basic demo showing how to instantiate a simple GP model, add data to it, and
optimize its hyperparameters.
"""

# global imports.
import os
import numpy as np

# local imports
import pygp
import pygp.priors
import pygp.plotting


if __name__ == '__main__':
    # load the data.
    cdir = os.path.abspath(os.path.dirname(__file__))
    data = np.load(os.path.join(cdir, 'xy.npz'))
    X = data['X']
    y = data['y']

    # create the model and add data to it.
    model = pygp.BasicGP(sn=.1, sf=1, ell=.1)
    model.add_data(X, y)

    # find the ML hyperparameters and plot the predictions.
    pygp.optimize(model)
    pygp.plotting.plot(model,
                       ymin=-3, ymax=3,
                       figure=1, subplot=131, title='ML posterior')

    # create a prior structure.
    priors = dict(
        sn=pygp.priors.Uniform(0.01, 1.0),
        sf=pygp.priors.Uniform(0.01, 5.0),
        ell=pygp.priors.Uniform(0.01, 1.0))

    # create a meta-model which samples hyperparameters via MCMC.
    meta_mcmc = pygp.meta.MCMC(model, priors, n=200, burn=100)

    # plot the fully Bayesian predictions.
    pygp.plotting.plot(meta_mcmc,
                       ymin=-3, ymax=3,
                       figure=1, subplot=132, title='Bayes posterior (MCMC)')

    # create a meta-model which samples hyperparameters via SMC.
    meta_smc = pygp.meta.SMC(model, priors, n=200)

    # plot the fully Bayesian predictions.
    pygp.plotting.plot(meta_smc,
                       ymin=-3, ymax=3,
                       figure=1, subplot=133, legend=True,
                       title='Bayes posterior (SMC)')
