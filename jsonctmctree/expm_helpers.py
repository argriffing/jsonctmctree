"""
Implement various strategies to compute functions related to matrix exponential.

Some of these do precalculations, so they are not pure functions.

"""
from __future__ import division, print_function

import numpy as np
from numpy.testing import assert_equal, assert_

import scipy.linalg
import scipy.sparse.linalg
from scipy.sparse import coo_matrix

__all__ = ['PadeExpm', 'EigenExpm', 'ActionExpm']


def create_sparse_rate_matrix(state_space_shape, row, col, rate):
    """
    Create the rate matrix.

    """
    # check conformability of input arrays
    ndim = len(state_space_shape)
    assert_equal(len(row.shape), 2)
    assert_equal(len(col.shape), 2)
    assert_equal(len(rate.shape), 1)
    assert_equal(row.shape[0], rate.shape[0])
    assert_equal(col.shape[0], rate.shape[0])
    assert_equal(row.shape[1], ndim)
    assert_equal(col.shape[1], ndim)

    # Define the transition rate matrix after the multivariate process
    # is collapsed to a univariate process.
    nstates = np.prod(state_space_shape)
    mrow = np.ravel_multi_index(row.T, state_space_shape)
    mcol = np.ravel_multi_index(col.T, state_space_shape)

    # self-transitions are not allowed
    assert_(not np.any(mrow == mcol))

    # create the sparse Q matrix from the sparse arrays
    Q = coo_matrix((rate, (mrow, mcol)), (nstates, nstates))

    # get the dense array of exit rates, and set the diagonal
    exit_rates = Q.sum(axis=1).A.flatten()
    assert_equal(exit_rates.shape[0], nstates)

    # FIXME
    # Temporarily disabling the setdiag of coo_matrix.
    # When it is OK to use new scipy, use the setdiag path instead.
    if False:
        Q.setdiag(-exit_rates)
    else:
        Q.row = np.concatenate((Q.row, np.arange(nstates)))
        Q.col = np.concatenate((Q.col, np.arange(nstates)))
        Q.data = np.concatenate((Q.data, -exit_rates))

    return Q


def create_dense_rate_matrix(state_space_shape, row, col, rate):
    """
    Create the rate matrix.

    """
    return create_sparse_rate_matrix(state_space_shape, row, col, rate).A


class PadeExpm(object):
    """
    This requires lower memory than EigenExpm.
    The implementation is the simplest because it does not cache anything.

    """
    def __init__(self, state_space_shape, row, col, rate):
        self.Q = create_sparse_rate_matrix(state_space_shape, row, col, rate)

    def expm_mul(self, rate_scaling_factor, A):
        """
        Compute exp(Q * r) * A.

        """
        return scipy.linalg.expm(self.Q.A * rate_scaling_factor).dot(A)

    def rate_mul(self, rate_scaling_factor, PA):
        """
        Compute Q * r * PA.
        This is for gradient calculation.

        """
        return rate_scaling_factor * self.Q.dot(PA)


#TODO more carefully treat matrices that can be permuted to block diagonal
#     with zeros on one of the diagonals.
class EigenExpm(object):
    def __init__(self, state_space_shape, row, col, rate):
        self.Q = create_dense_rate_matrix(state_space_shape, row, col, rate)
        self.w, self.U = scipy.linalg.eig(self.Q)
        self.V = scipy.linalg.inv(self.U)

    def expm_mul(self, rate_scaling_factor, A):
        """
        Compute exp(Q * r) * A.

        """
        w_exp = np.exp(self.w * rate_scaling_factor)
        VA = self.V.dot(A)
        return (self.U * w_exp).dot(VA).real

    def rate_mul(self, rate_scaling_factor, PA):
        """
        Compute Q * r * PA.
        This is for gradient calculation.

        """
        return rate_scaling_factor * self.Q.dot(PA)


class ActionExpm(object):
    def __init__(self, state_space_shape, row, col, rate):
        self.Q = create_sparse_rate_matrix(state_space_shape, row, col, rate)

    def expm_mul(self, rate_scaling_factor, A):
        """
        Compute exp(Q * r) * A.

        """
        return scipy.sparse.linalg.expm_multiply(
                rate_scaling_factor * self.Q, A)

    def rate_mul(self, rate_scaling_factor, PA):
        """
        Compute Q * r * PA.
        This is for gradient calculation.

        """
        return rate_scaling_factor * self.Q.dot(PA)
