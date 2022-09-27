#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint8_t uint8_zero_range = 1;
static uint8_t uint8_zero(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint8_t uint8_one_range = 1;
static uint8_t uint8_one(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint8_t uint8_pos_range = 253;
static uint8_t uint8_pos(uint8_t index) {
    index = index % 253;
    if (index < 253) return index + 2u;
}
static uint8_t uint8_max_range = 1;
static uint8_t uint8_max(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 255u;
}
static uint8_t sample_uint8_t() {
  union bit2value {
    uint32_t b;
    uint8_t v;
   } v;
  uint32_t br;
  br = uniform_sample(4);
  switch(br) {
  case 0:
      v.b = uint8_zero(uniform_sample(uint8_zero_range));
      break;
  case 1:
      v.b = uint8_one(uniform_sample(uint8_one_range));
      break;
  case 2:
      v.b = uint8_pos(uniform_sample(uint8_pos_range));
      break;
  case 3:
      v.b = uint8_max(uniform_sample(uint8_max_range));
      break;
  }
   return v.v;
}
