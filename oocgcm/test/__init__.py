#!/usr/bin/env python

# mostly taken from xarray

import sys
import warnings
from contextlib import contextmanager

import numpy as np
from numpy.testing import assert_equal,assert_array_equal,assert_allclose

from xarray.core.variable import as_variable

from oocgcm.core.utils import is_xarray

PY3 = sys.version_info[0] >= 3


try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    import xarray
    has_xarray = True
except ImportError:
    has_xarray = False

try:
    import dask.array
    import dask
    dask.set_options(get=dask.get)
    has_dask = True
except ImportError:
    has_dask = False

try:
    import numba
    has_numba = True
except ImportError:
    has_numba = False

try:
    import matplotlib
    has_matplotlib = True
except ImportError:
    has_matplotlib = False


try:
    import bottleneck
    has_bottleneck = True
except ImportError:
    has_bottleneck = False


def requires_xarray(test):
    return test if has_xarray else unittest.skip('requires xarray')(test)


def requires_dask(test):
    return test if has_dask else unittest.skip('requires dask')(test)

def requires_numba(test):
    return test if has_numba else unittest.skip('requires numba')(test)

def requires_matplotlib(test):
    return test if has_matplotlib else unittest.skip('requires matplotlib')(test)


def requires_bottleneck(test):
    return test if has_bottleneck else unittest.skip('requires bottleneck')(test)




def decode_string_data(data):
    if data.dtype.kind == 'S':
        return np.core.defchararray.decode(data, 'utf-8', 'replace')
    return data


def data_allclose_or_equiv(arr1, arr2, rtol=1e-05, atol=1e-08):
    if any(arr.dtype.kind == 'S' for arr in [arr1, arr2]):
        arr1 = decode_string_data(arr1)
        arr2 = decode_string_data(arr2)
    exact_dtypes = ['M', 'm', 'O', 'U']
    if any(arr.dtype.kind in exact_dtypes for arr in [arr1, arr2]):
        return ops.array_equiv(arr1, arr2)
    else:
        return ops.allclose_or_equiv(arr1, arr2, rtol=rtol, atol=atol)


class TestCase(unittest.TestCase):
    if PY3:
        # Python 3 assertCountEqual is roughly equivalent to Python 2
        # assertItemsEqual
        def assertItemsEqual(self, first, second, msg=None):
            return self.assertCountEqual(first, second, msg)

    @contextmanager
    def assertWarns(self, message):
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings('always', message)
            yield
            assert len(w) > 0
            assert all(message in str(wi.message) for wi in w)

    def assertVariableEqual(self, v1, v2):
        assert as_variable(v1).equals(v2), (v1, v2)

    def assertVariableIdentical(self, v1, v2):
        assert as_variable(v1).identical(v2), (v1, v2)

    def assertVariableAllClose(self, v1, v2, rtol=1e-05, atol=1e-08):
        self.assertEqual(v1.dims, v2.dims)
        allclose = data_allclose_or_equiv(
            v1.values, v2.values, rtol=rtol, atol=atol)
        assert allclose, (v1.values, v2.values)

    def assertVariableNotEqual(self, v1, v2):
        self.assertFalse(as_variable(v1).equals(v2))

    def assertArrayEqual(self, a1, a2):
        assert_array_equal(a1, a2)

    def assertArrayClose(self, a1, a2,rtol=1e-05, atol=1e-08):
        assert_allclose(a1, a2,rtol=rtol, atol=atol)

    def assertArray2dCloseInside(self, a1, a2,rtol=1e-05, atol=1e-08,depth=1):
        #- restrict the comparison to point away from boundaries.
        #- assume a1 and a2 are 2d x,y arrays.
        _a1 = a1[...,depth:-1 - depth,depth:-1 - depth]
        _a2 = a2[...,depth:-1 - depth,depth:-1 - depth]
        assert_allclose(_a1, _a2,rtol=rtol, atol=atol)


    def assertEqual(self, a1, a2):
        assert a1 == a2 or (a1 != a1 and a2 != a2)

    def assertDatasetEqual(self, d1, d2):
        # this method is functionally equivalent to `assert d1 == d2`, but it
        # checks each aspect of equality separately for easier debugging
        assert d1.equals(d2), (d1, d2)

    def assertDatasetIdentical(self, d1, d2):
        # this method is functionally equivalent to `assert d1.identical(d2)`,
        # but it checks each aspect of equality separately for easier debugging
        assert d1.identical(d2), (d1, d2)

    def assertDatasetAllClose(self, d1, d2, rtol=1e-05, atol=1e-08):
        self.assertEqual(sorted(d1, key=str), sorted(d2, key=str))
        self.assertItemsEqual(d1.coords, d2.coords)
        for k in d1:
            v1 = d1.variables[k]
            v2 = d2.variables[k]
            self.assertVariableAllClose(v1, v2, rtol=rtol, atol=atol)

    def assertCoordinatesEqual(self, d1, d2):
        self.assertEqual(sorted(d1.coords), sorted(d2.coords))
        for k in d1.coords:
            v1 = d1.coords[k]
            v2 = d2.coords[k]
            self.assertVariableEqual(v1, v2)

    def assertDataArrayHasValues(self,da):
        try:
	    assert(isinstance(float(da[0,0].to_masked_array()),float))
	except:
	    print da
            raise Exception(' This DataArray is empty/not valid.')

    def assertDataArrayEqual(self, ar1, ar2):
        self.assertVariableEqual(ar1, ar2)
        self.assertCoordinatesEqual(ar1, ar2)

    def assertDataArrayIdentical(self, ar1, ar2):
        self.assertEqual(ar1.name, ar2.name)
        self.assertDatasetIdentical(ar1._to_temp_dataset(),
                                    ar2._to_temp_dataset())

    def assertDataArrayAllClose(self, ar1, ar2, rtol=1e-05, atol=1e-08):
        self.assertVariableAllClose(ar1, ar2, rtol=rtol, atol=atol)
        self.assertCoordinatesEqual(ar1, ar2)


class UnexpectedDataAccess(Exception):
    pass



class ReturnItem(object):
    def __getitem__(self, key):
        return key

def print_array_around(expected = None, actual=None,around=(20,20)):
    """Customized print used for debugging tests."""
    j,i = around
    print '\n expected array : '
    if is_xarray(expected):
        print expected.to_masked_array()[j-1:j+2,i-1:i+2]
    else:
        print expected[j-1:j+2,i-1:i+2]
    print 'actual array : '
    if is_xarray(actual):
        print actual.to_masked_array()[j-1:j+2,i-1:i+2]
    else:
        print actual[j-1:j+2,i-1:i+2]


def source_ndarray(array):
    """Given an ndarray, return the base object which holds its memory, or the
    object itself.
    """
    base = getattr(array, 'base', np.asarray(array).base)
    if base is None:
        base = array
    return base
