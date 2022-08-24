#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>

#include "float_sampler.h"
#include "unisampler.h"

union bit2float {
  uint32_t b;
  float f;
};

float sample_float() {
  uint32_t br;

  br = uniform_sample(10);

  union bit2float v;

  switch(br) {
  case 0:
    v.b = pzero(uniform_sample(pzero_range));
    break;
  case 1:
    v.b = nzero(uniform_sample(nzero_range));
    break;
  case 2:
    v.b = nsubnormal(uniform_sample(nsubnormal_range));
    break;
  case 3:
    v.b = psubnormal(uniform_sample(psubnormal_range));
    break;
  case 4:
    v.b = pnormal(uniform_sample(pnormal_range));
    break;
  case 5:
    v.b = nnormal(uniform_sample(nnormal_range));
    break;
  case 6:
    v.b = pqnan(uniform_sample(pqnan_range));
    break;
  case 7:
    v.b = nqnan(uniform_sample(nqnan_range));
    break;
  case 8:
    v.b = ninf(uniform_sample(ninf_range));
    break;
  case 9:
    v.b = pinf(uniform_sample(pinf_range));
    break;
  }

  return v.f;
}
