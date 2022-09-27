#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint32_t int8_min_range = 1;
static uint8_t int8_min(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 255u;
}
static uint32_t int8_zero_range = 1;
static uint8_t int8_zero(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint32_t int8_one_range = 1;
static uint8_t int8_one(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint32_t int8_neg_range = 127;
static uint8_t int8_neg(uint8_t index) {
    index = index % 127;
    if (index < 127) return index + 128u;
}
static uint32_t int8_pos_range = 125;
static uint8_t int8_pos(uint8_t index) {
    index = index % 125;
    if (index < 125) return index + 2u;
}
static uint32_t int8_max_range = 1;
static uint8_t int8_max(uint8_t index) {
    index = index % 1;
    if (index < 1) return index + 127u;
}
static int8_t sample_int8_t() {
  union bit2value {
    uint32_t b;
    int8_t v;
   } v;
  uint32_t br;
  br = uniform_sample(6);
  switch(br) {
  case 0:
      v.b = int8_min(uniform_sample(int8_min_range));
      break;
  case 1:
      v.b = int8_zero(uniform_sample(int8_zero_range));
      break;
  case 2:
      v.b = int8_one(uniform_sample(int8_one_range));
      break;
  case 3:
      v.b = int8_neg(uniform_sample(int8_neg_range));
      break;
  case 4:
      v.b = int8_pos(uniform_sample(int8_pos_range));
      break;
  case 5:
      v.b = int8_max(uniform_sample(int8_max_range));
      break;
  }
   return v.v;
}
