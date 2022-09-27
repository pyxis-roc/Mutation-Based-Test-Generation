#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint64_t uint64_zero_range = 1;
static uint64_t uint64_zero(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint64_t uint64_one_range = 1;
static uint64_t uint64_one(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint64_t uint64_pos_range = 18446744073709551613;
static uint64_t uint64_pos(uint64_t index) {
    index = index % 18446744073709551613;
    if (index < 18446744073709551613) return index + 2u;
}
static uint64_t uint64_max_range = 1;
static uint64_t uint64_max(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 18446744073709551615u;
}
static uint64_t sample_uint64_t() {
  union bit2value {
    uint32_t b;
    uint64_t v;
   } v;
  uint32_t br;
  br = uniform_sample_64(4);
  switch(br) {
  case 0:
      v.b = uint64_zero(uniform_sample_64(uint64_zero_range));
      break;
  case 1:
      v.b = uint64_one(uniform_sample_64(uint64_one_range));
      break;
  case 2:
      v.b = uint64_pos(uniform_sample_64(uint64_pos_range));
      break;
  case 3:
      v.b = uint64_max(uniform_sample_64(uint64_max_range));
      break;
  }
   return v.v;
}
