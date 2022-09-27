#pragma once

// returns a number [0, range)
static uint32_t uniform_sample_1(const uint32_t range) {
  // this samples a range that fits in RAND_MAX
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

static uint32_t uniform_sample(const uint32_t range) {
  uint32_t n;

  if(range == 1) return 0;

  if(range <= RAND_MAX)
    return uniform_sample_1(range);

  assert(RAND_MAX <= UINT32_MAX);

  uint32_t range_d = range / RAND_MAX;
  uint32_t range_r = range % RAND_MAX;

  if(range_r > 0) range_d += 1;

  // first pick a range uniformly
  uint32_t range_id = uniform_sample(range_d);

  // then pick a limit
  uint32_t limit;
  if(range_id == (range_d - 1))
    limit = range_r;
  else
    limit = RAND_MAX;

  uint32_t v = uniform_sample(limit);

  return range_id * RAND_MAX + v;
}

static uint64_t uniform_sample_64(const uint64_t range) {
  uint64_t n;

  if(range == 1) return 0;

  if(range <= RAND_MAX)
    return uniform_sample_1(range);

  assert(RAND_MAX <= UINT64_MAX);

  uint64_t range_d = range / RAND_MAX;
  uint64_t range_r = range % RAND_MAX;

  if(range_r > 0) range_d += 1;

  // first pick a range uniformly
  uint64_t range_id = uniform_sample_64(range_d);

  // then pick a limit
  uint64_t limit;
  if(range_id == (range_d - 1))
    limit = range_r;
  else
    limit = RAND_MAX;

  uint64_t v = uniform_sample_64(limit);

  return range_id * RAND_MAX + v;
}
