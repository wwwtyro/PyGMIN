#ifndef MINGMIN__NPARRAY_H
#define MINGMIN__NPARRAY_H

#include <boost/python/numeric.hpp>
#include <boost/python.hpp>
#include <numpy/arrayobject.h>

template<int ndims>
class NPArray
{
public:
  NPArray(boost::python::numeric::array& array);
  
  size_t size(int dim) { return _size[dim]; }
  double &operator[](size_t i) { return _data[i]; }
private:
  double *_data;
  size_t _size[ndims];
};

template<int ndims>
NPArray<ndims>::NPArray(boost::python::numeric::array& array)
{
  // Get pointer to np array
  PyArrayObject* a = (PyArrayObject*)PyArray_FROM_O(array.ptr());
  if (a == NULL) {
    throw std::runtime_error("Could not get NP array.");
  }
  if (a->descr->elsize != sizeof(double)) {
    throw std::runtime_error("Must be double ndarray");
  }
  
  if (a->nd != ndims) {
    throw std::runtime_error("Wrong dimension on array.");
  }
  _data = (double*)a->data;
  _size[0] = *(a->dimensions);
}

#endif