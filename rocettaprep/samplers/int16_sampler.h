#pragma once
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include "unisampler.h"
static uint32_t int16_min_range = 1;
static uint16_t int16_min(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 65535u;
}
static uint32_t int16_zero_range = 1;
static uint16_t int16_zero(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint32_t int16_one_range = 1;
static uint16_t int16_one(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 1u;
}
static uint32_t int16_neg_range = 32767;
static uint16_t int16_neg(uint16_t index) {
    index = index % 32767;
    if (index < 32767) return index + 32768u;
}
static uint32_t int16_pos_range = 32765;
static uint16_t int16_pos(uint16_t index) {
    index = index % 32765;
    if (index < 32765) return index + 2u;
}
static uint32_t int16_max_range = 1;
static uint16_t int16_max(uint16_t index) {
    index = index % 1;
    if (index < 1) return index + 32767u;
}
static int16_t sample_int16_t() {
  union bit2value {
    uint32_t b;
    int16_t v;
   } v;
  uint32_t br;
  br = uniform_sample(6);
  switch(br) {
  case 0:
      v.b = int16_min(uniform_sample(int16_min_range));
      break;
  case 1:
      v.b = int16_zero(uniform_sample(int16_zero_range));
      break;
  case 2:
      v.b = int16_one(uniform_sample(int16_one_range));
      break;
  case 3:
      v.b = int16_neg(uniform_sample(int16_neg_range));
      break;
  case 4:
      v.b = int16_pos(uniform_sample(int16_pos_range));
      break;
  case 5:
      v.b = int16_max(uniform_sample(int16_max_range));
      break;
  }
   return v.v;
}
