#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint32_t int32_min_range = 1;
static uint32_t int32_min(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 4294967295u;
}
static uint32_t int32_zero_range = 1;
static uint32_t int32_zero(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint32_t int32_one_range = 1;
static uint32_t int32_one(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint32_t int32_neg_range = 2147483647;
static uint32_t int32_neg(uint32_t index) {
    index = index % 2147483647;
    if (index < 2147483647) return index + 2147483648u;
}
static uint32_t int32_pos_range = 2147483645;
static uint32_t int32_pos(uint32_t index) {
    index = index % 2147483645;
    if (index < 2147483645) return index + 2u;
}
static uint32_t int32_max_range = 1;
static uint32_t int32_max(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 2147483647u;
}
static int32_t sample_int32_t() {
  union bit2value {
    uint32_t b;
    int32_t v;
   } v;
  uint32_t br;
  br = uniform_sample(6);
  switch(br) {
  case 0:
      v.b = int32_min(uniform_sample(int32_min_range));
      break;
  case 1:
      v.b = int32_zero(uniform_sample(int32_zero_range));
      break;
  case 2:
      v.b = int32_one(uniform_sample(int32_one_range));
      break;
  case 3:
      v.b = int32_neg(uniform_sample(int32_neg_range));
      break;
  case 4:
      v.b = int32_pos(uniform_sample(int32_pos_range));
      break;
  case 5:
      v.b = int32_max(uniform_sample(int32_max_range));
      break;
  }
   return v.v;
}
