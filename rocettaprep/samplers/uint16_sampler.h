#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint16_t uint16_zero_range = 1;
static uint16_t uint16_zero(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint16_t uint16_one_range = 1;
static uint16_t uint16_one(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint16_t uint16_pos_range = 65533;
static uint16_t uint16_pos(uint16_t index) {
    index = index % 65533;
    if (index < 65533) return index + 2u;
}
static uint16_t uint16_max_range = 1;
static uint16_t uint16_max(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 65535u;
}
static uint16_t sample_uint16_t() {
  union bit2value {
    uint32_t b;
    uint16_t v;
   } v;
  uint32_t br;
  br = uniform_sample(4);
  switch(br) {
  case 0:
      v.b = uint16_zero(uniform_sample(uint16_zero_range));
      break;
  case 1:
      v.b = uint16_one(uniform_sample(uint16_one_range));
      break;
  case 2:
      v.b = uint16_pos(uniform_sample(uint16_pos_range));
      break;
  case 3:
      v.b = uint16_max(uniform_sample(uint16_max_range));
      break;
  }
   return v.v;
}
