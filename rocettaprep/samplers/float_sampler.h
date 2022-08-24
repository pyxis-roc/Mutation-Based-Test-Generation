static uint32_t pzero_range = 1;
static uint32_t pzero(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 0u;
}
static uint32_t nzero_range = 1;
static uint32_t nzero(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 2147483648u;
}
static uint32_t psubnormal_range = 8388607;
static uint32_t psubnormal(uint32_t index) {
    index = index % 8388607;
    if (index < 8388607) return index + 1u;
}
static uint32_t nsubnormal_range = 8388607;
static uint32_t nsubnormal(uint32_t index) {
    index = index % 8388607;
    if (index < 8388607) return index + 2147483649u;
}
static uint32_t pinf_range = 1;
static uint32_t pinf(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 2139095040u;
}
static uint32_t ninf_range = 1;
static uint32_t ninf(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 4286578688u;
}
static uint32_t pqnan_range = 1;
static uint32_t pqnan(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 2143289344u;
}
static uint32_t nqnan_range = 1;
static uint32_t nqnan(uint32_t index) {
    index = index % 1;
    if (index < 1) return index + 4290772992u;
}
static uint32_t pnormal_range = 2130706432;
static uint32_t pnormal(uint32_t index) {
    index = index % 2130706432;
    if (index < 2130706432) return index + 8388608u;
}
static uint32_t nnormal_range = 2130706432;
static uint32_t nnormal(uint32_t index) {
    index = index % 2130706432;
    if (index < 2130706432) return index + 2155872256u;
}
