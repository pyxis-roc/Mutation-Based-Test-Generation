#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint64_t int64_min_range = 1;
static uint64_t int64_min(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 18446744073709551615u;
}
static uint64_t int64_zero_range = 1;
static uint64_t int64_zero(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint64_t int64_one_range = 1;
static uint64_t int64_one(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint64_t int64_neg_range = 9223372036854775807;
static uint64_t int64_neg(uint64_t index) {
    index = index % 9223372036854775807;
    if (index < 9223372036854775807) return index + 9223372036854775808u;
}
static uint64_t int64_pos_range = 9223372036854775805;
static uint64_t int64_pos(uint64_t index) {
    index = index % 9223372036854775805;
    if (index < 9223372036854775805) return index + 2u;
}
static uint64_t int64_max_range = 1;
static uint64_t int64_max(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 9223372036854775807u;
}
static int64_t sample_int64_t() {
  union bit2value {
    uint32_t b;
    int64_t v;
   } v;
  uint32_t br;
  br = uniform_sample_64(6);
  switch(br) {
  case 0:
      v.b = int64_min(uniform_sample_64(int64_min_range));
      break;
  case 1:
      v.b = int64_zero(uniform_sample_64(int64_zero_range));
      break;
  case 2:
      v.b = int64_one(uniform_sample_64(int64_one_range));
      break;
  case 3:
      v.b = int64_neg(uniform_sample_64(int64_neg_range));
      break;
  case 4:
      v.b = int64_pos(uniform_sample_64(int64_pos_range));
      break;
  case 5:
      v.b = int64_max(uniform_sample_64(int64_max_range));
      break;
  }
   return v.v;
}
