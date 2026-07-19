#include "z3.h"

#include <cstddef>
#include <cstdint>
#include <string>

namespace {

void ignore_error(Z3_context, Z3_error_code) {}

Z3_context make_context() {
    Z3_config config = Z3_mk_config();
    Z3_set_param_value(config, "timeout", "1000");
    Z3_context context = Z3_mk_context(config);
    Z3_del_config(config);
    Z3_set_error_handler(context, ignore_error);
    return context;
}

}  // namespace

extern "C" int LLVMFuzzerTestOneInput(const std::uint8_t* data, std::size_t size) {
    if (size == 0 || size > 1'000'000)
        return 0;

    std::string input(reinterpret_cast<const char*>(data), size);
    Z3_context context = make_context();

    Z3_solver solver = Z3_mk_solver(context);
    Z3_solver_inc_ref(context, solver);
    Z3_solver_from_string(context, solver, input.c_str());
    if (Z3_get_error_code(context) == Z3_OK) {
        Z3_lbool result = Z3_solver_check(context, solver);
        switch (data[0] % 5) {
        case 0:
            Z3_solver_push(context, solver);
            (void)Z3_solver_check(context, solver);
            Z3_solver_pop(context, solver, 1);
            (void)Z3_solver_check(context, solver);
            break;
        case 1:
            Z3_solver_reset(context, solver);
            Z3_solver_from_string(context, solver, input.c_str());
            if (Z3_get_error_code(context) == Z3_OK)
                (void)Z3_solver_check(context, solver);
            break;
        case 2:
            (void)Z3_solver_get_statistics(context, solver);
            if (result == Z3_L_UNDEF)
                (void)Z3_solver_get_reason_unknown(context, solver);
            break;
        case 3:
            (void)Z3_solver_get_assertions(context, solver);
            (void)Z3_solver_to_string(context, solver);
            break;
        case 4:
            if (result == Z3_L_TRUE)
                (void)Z3_solver_get_model(context, solver);
            break;
        }
    }

    Z3_solver_dec_ref(context, solver);
    Z3_del_context(context);
    return 0;
}
