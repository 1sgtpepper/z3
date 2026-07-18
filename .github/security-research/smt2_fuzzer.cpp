#include "z3.h"

#include <cstddef>
#include <cstdint>
#include <string>

namespace {

void ignore_error(Z3_context, Z3_error_code) {}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
    if (size == 0 || size > 1'000'000)
        return 0;

    std::string input(reinterpret_cast<const char*>(data), size);
    Z3_config config = Z3_mk_config();
    Z3_context context = Z3_mk_context(config);
    Z3_del_config(config);
    Z3_set_error_handler(context, ignore_error);

    Z3_solver solver = Z3_mk_solver(context);
    Z3_solver_inc_ref(context, solver);
    Z3_solver_from_string(context, solver, input.c_str());
    if (Z3_get_error_code(context) == Z3_OK)
        (void)Z3_solver_check(context, solver);

    Z3_solver_dec_ref(context, solver);
    Z3_del_context(context);
    return 0;
}
