# This is a stupid workaround for crappy deep-reload behavior in python. While
# developing I often want to reload the entire package I'm working on... so if
# fnames contains a depth-first traversal of the modules contained in the
# package this will import and reload all of them.

fnames = """
pygp.utils.exceptions
pygp.utils.models
pygp.utils.iters
pygp.utils
pygp.kernels._base
pygp.kernels._distances
pygp.kernels.periodic
pygp.kernels.se
pygp.kernels
pygp.likelihoods._base
pygp.likelihoods.gaussian
pygp.likelihoods
pygp.hyper.ml
pygp.hyper
pygp.inference._base
pygp.inference.exact
pygp.inference.basic
pygp.inference
pygp.extra.fourier
pygp.extra
pygp.plotting
pygp
""".split()

import importlib

for fname in list(reversed(fnames)) + fnames:
    module = importlib.import_module(fname)
    reload(module)
