#pragma once

static uint32_t uniform_sample(const uint32_t range) {
  // http://www.cs.yale.edu/homes/aspnes/pinewiki/C(2f)Randomization.html
  // essentially rejection sampling
  uint32_t n;

  if(range == 1) return 0;

  assert(range <= RAND_MAX);

  uint32_t limit = RAND_MAX - (RAND_MAX % range);

  n = random();

  while(n >= limit) n = random();

  return n % range;
}
