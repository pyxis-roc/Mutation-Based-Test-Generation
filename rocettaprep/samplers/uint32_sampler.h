#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint32_t uint32_zero_range = 1;
static uint32_t uint32_zero(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint32_t uint32_one_range = 1;
static uint32_t uint32_one(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint32_t uint32_pos_range = 4294967293;
static uint32_t uint32_pos(uint32_t index) {
    index = index % 4294967293;
    if (index < 4294967293) return index + 2u;
}
static uint32_t uint32_max_range = 1;
static uint32_t uint32_max(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 4294967295u;
}
static uint32_t sample_uint32() {
  union bit2value {
    uint32_t b;
    uint32_t v;
   } v;
  uint32_t br;
  br = uniform_sample(4);
  switch(br) {
  case 0:
      v.b = uint32_zero(uniform_sample(uint32_zero_range));
      break;
  case 1:
      v.b = uint32_one(uniform_sample(uint32_one_range));
      break;
  case 2:
      v.b = uint32_pos(uniform_sample(uint32_pos_range));
      break;
  case 3:
      v.b = uint32_max(uniform_sample(uint32_max_range));
      break;
  }
   return v.v;
}
