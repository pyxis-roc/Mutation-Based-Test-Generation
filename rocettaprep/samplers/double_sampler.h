static uint64_t dbl_pzero_range = 1;
static uint64_t dbl_pzero(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint64_t dbl_nzero_range = 1;
static uint64_t dbl_nzero(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 9223372036854775808u;
}
static uint64_t dbl_psubnormal_range = 4503599627370495;
static uint64_t dbl_psubnormal(uint64_t index) {
    index = index % 4503599627370495;
    if (index < 4503599627370495) return index + 1u;
}
static uint64_t dbl_nsubnormal_range = 4503599627370495;
static uint64_t dbl_nsubnormal(uint64_t index) {
    index = index % 4503599627370495;
    if (index < 4503599627370495) return index + 9223372036854775809u;
}
static uint64_t dbl_pinf_range = 1;
static uint64_t dbl_pinf(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 9218868437227405312u;
}
static uint64_t dbl_ninf_range = 1;
static uint64_t dbl_ninf(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 18442240474082181120u;
}
static uint64_t dbl_pqnan_range = 1;
static uint64_t dbl_pqnan(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 9221120237041090560u;
}
static uint64_t dbl_nqnan_range = 1;
static uint64_t dbl_nqnan(uint64_t index) {
    index = index % 1;
    if (index < 1) return index + 18444492273895866368u;
}
static uint64_t dbl_pnormal_range = 9214364837600034816;
static uint64_t dbl_pnormal(uint64_t index) {
    index = index % 9214364837600034816;
    if (index < 9214364837600034816) return index + 4503599627370496u;
}
static uint64_t dbl_nnormal_range = 9214364837600034816;
static uint64_t dbl_nnormal(uint64_t index) {
    index = index % 9214364837600034816;
    if (index < 9214364837600034816) return index + 9227875636482146304u;
}
static double sample_double() {
  union bit2value {
    uint32_t b;
    double v;
   } v;
  uint32_t br;
  br = uniform_sample_64(10);
  switch(br) {
  case 0:
      v.b = dbl_pzero(uniform_sample_64(dbl_pzero_range));
      break;
  case 1:
      v.b = dbl_nzero(uniform_sample_64(dbl_nzero_range));
      break;
  case 2:
      v.b = dbl_psubnormal(uniform_sample_64(dbl_psubnormal_range));
      break;
  case 3:
      v.b = dbl_nsubnormal(uniform_sample_64(dbl_nsubnormal_range));
      break;
  case 4:
      v.b = dbl_pinf(uniform_sample_64(dbl_pinf_range));
      break;
  case 5:
      v.b = dbl_ninf(uniform_sample_64(dbl_ninf_range));
      break;
  case 6:
      v.b = dbl_pqnan(uniform_sample_64(dbl_pqnan_range));
      break;
  case 7:
      v.b = dbl_nqnan(uniform_sample_64(dbl_nqnan_range));
      break;
  case 8:
      v.b = dbl_pnormal(uniform_sample_64(dbl_pnormal_range));
      break;
  case 9:
      v.b = dbl_nnormal(uniform_sample_64(dbl_nnormal_range));
      break;
  }
   return v.v;
}
