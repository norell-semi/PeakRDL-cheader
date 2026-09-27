import base

from parameterized import parameterized_class

@parameterized_class(base.get_permutations({
    "rdl_file": ["testcases/arrays.rdl", "testcases/anonymous.rdl", "testcases/widths_and_mem.rdl"],
    "explode_top": [True, False],
    "inst_offset": [0, 0x40000000],
}))
class TestAddrMacros(base.BaseHeaderTestcase):
    addr_macros = True

    def test_addr_macros(self) -> None:
        self.do_test()
