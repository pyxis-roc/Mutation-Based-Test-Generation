#include "ptxc.h"
#include "unisampler.h"

static struct cc_register sample_cc_register() {
  uint32_t v;
  v = uniform_sample(2);
  return (struct cc_register) { .cf = v };
}
