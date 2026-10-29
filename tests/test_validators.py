import unittest

from core.models import Build, Category, Component, FormFactor, RamType
from core.validators import (
    FORM_FACTOR_RULE, PSU_RULE, RAM_CAPACITY_RULE, RAM_RULE, SOCKET_RULE,
    STORAGE_KIND_RULE, Status, check_all, check_cpu_socket,
    check_form_factor, check_psu_wattage, check_ram_capacity,
    check_ram_type, check_storage_kind, find_issues, find_warnings,
    psu_headroom_percent, required_psu_wattage,
)
from tests.helpers import (
    make_case, make_complete_build, make_cpu, make_gpu, make_motherboard,
    make_psu, make_ram, make_storage,
)


def build_with(*components: Component) -> Build:
    build = Build()
    for component in components:
        build = build.with_component(component)
    return build


class PsuHeadroomTest(unittest.TestCase):
    def test_headroom_is_the_spare_share_of_the_psu(self) -> None:
        # 424 W de consumo numa fonte de 650 W: sobram 226 W (34,7%)
        headroom = psu_headroom_percent(
            make_cpu(tdp_watts=120), make_gpu(304), make_psu(650)
        )

        self.assertEqual(headroom, 34)

    def test_exact_division(self) -> None:
        headroom = psu_headroom_percent(
            make_cpu(tdp_watts=100), make_gpu(200), make_psu(400)
        )

        self.assertEqual(headroom, 25)

    def test_no_headroom_when_psu_equals_load(self) -> None:
        headroom = psu_headroom_percent(
            make_cpu(tdp_watts=100), make_gpu(200), make_psu(300)
        )

        self.assertEqual(headroom, 0)

    def test_negative_when_psu_is_smaller_than_load(self) -> None:
        # faltam 24 W numa fonte de 400 W: -6%
        headroom = psu_headroom_percent(
            make_cpu(tdp_watts=120), make_gpu(304), make_psu(400)
        )

        self.assertEqual(headroom, -6)


class CpuSocketRuleTest(unittest.TestCase):
    def test_matching_sockets_pass(self) -> None:
        build = build_with(make_cpu("AM5"), make_motherboard("AM5"))

        self.assertIs(check_cpu_socket(build).status, Status.OK)

    def test_different_sockets_fail_with_clear_message(self) -> None:
        build = build_with(make_cpu("AM5"), make_motherboard("LGA1700"))

        result = check_cpu_socket(build)

        self.assertIs(result.status, Status.FAIL)
        self.assertIn("AM5", result.message)
        self.assertIn("LGA1700", result.message)
        self.assertTrue(result.hint)

    def test_is_pending_until_both_parts_are_selected(self) -> None:
        build = build_with(make_cpu("AM5"))

        self.assertIs(check_cpu_socket(build).status, Status.PENDING)


class RamTypeRuleTest(unittest.TestCase):
    def test_matching_ram_type_passes(self) -> None:
        build = build_with(
            make_ram(RamType.DDR4), make_motherboard(ram_type=RamType.DDR4)
        )

        self.assertIs(check_ram_type(build).status, Status.OK)

    def test_ddr5_memory_on_ddr4_board_fails(self) -> None:
        build = build_with(
            make_ram(RamType.DDR5), make_motherboard(ram_type=RamType.DDR4)
        )

        result = check_ram_type(build)

        self.assertIs(result.status, Status.FAIL)
        self.assertIn("DDR5", result.message)
        self.assertIn("DDR4", result.message)

    def test_is_pending_without_motherboard(self) -> None:
        build = build_with(make_ram())

        self.assertIs(check_ram_type(build).status, Status.PENDING)


class PsuWattageRuleTest(unittest.TestCase):
    def test_required_wattage_adds_twenty_percent_margin(self) -> None:
        self.assertEqual(
            required_psu_wattage(make_cpu(tdp_watts=65), make_gpu(115)), 216
        )

    def test_required_wattage_rounds_up(self) -> None:
        # (100 + 201) * 1.2 = 361.2 W -> 362 W
        self.assertEqual(
            required_psu_wattage(make_cpu(tdp_watts=100), make_gpu(201)), 362
        )

    def test_required_wattage_has_no_floating_point_error(self) -> None:
        # Com float, 300 * 1.2 = 360.00000000000006 e o resultado seria 361.
        self.assertEqual(
            required_psu_wattage(make_cpu(tdp_watts=100), make_gpu(200)), 360
        )

    def test_psu_exactly_at_the_minimum_passes(self) -> None:
        build = build_with(
            make_cpu(tdp_watts=100), make_gpu(200), make_psu(360)
        )

        self.assertIs(check_psu_wattage(build).status, Status.OK)

    def test_psu_one_watt_below_the_minimum_fails(self) -> None:
        build = build_with(
            make_cpu(tdp_watts=100), make_gpu(200), make_psu(359)
        )

        result = check_psu_wattage(build)

        self.assertIs(result.status, Status.FAIL)
        self.assertIn("360 W", result.message)
        self.assertIn("360 W", result.hint)

    def test_is_pending_without_gpu(self) -> None:
        build = build_with(make_cpu(), make_psu())

        self.assertIs(check_psu_wattage(build).status, Status.PENDING)


class FormFactorRuleTest(unittest.TestCase):
    def test_supported_form_factor_passes(self) -> None:
        build = build_with(
            make_motherboard(form_factor=FormFactor.MATX),
            make_case(
                supported_form_factors=(FormFactor.ATX, FormFactor.MATX)
            ),
        )

        result = check_form_factor(build)

        self.assertIs(result.status, Status.OK)
        self.assertIn("mATX", result.message)

    def test_atx_board_in_small_case_fails_with_clear_message(self) -> None:
        build = build_with(
            make_motherboard(form_factor=FormFactor.ATX),
            make_case(
                supported_form_factors=(FormFactor.MATX, FormFactor.ITX)
            ),
        )

        result = check_form_factor(build)

        self.assertIs(result.status, Status.FAIL)
        self.assertIn("ATX", result.message)
        self.assertIn("mATX, ITX", result.message)
        self.assertIn("ATX", result.hint)

    def test_is_pending_until_both_parts_are_selected(self) -> None:
        self.assertIs(
            check_form_factor(build_with(make_motherboard())).status,
            Status.PENDING,
        )
        self.assertIs(
            check_form_factor(build_with(make_case())).status,
            Status.PENDING,
        )

    def test_involves_motherboard_and_case(self) -> None:
        result = check_form_factor(Build())

        self.assertTrue(result.involves(Category.MOTHERBOARD))
        self.assertTrue(result.involves(Category.CASE))
        self.assertFalse(result.involves(Category.CPU))


class RamCapacityWarningTest(unittest.TestCase):
    def test_sixteen_gb_is_ok(self) -> None:
        result = check_ram_capacity(build_with(make_ram(capacity_gb=16)))

        self.assertIs(result.status, Status.OK)

    def test_less_than_sixteen_gb_is_a_warning(self) -> None:
        result = check_ram_capacity(build_with(make_ram(capacity_gb=8)))

        self.assertIs(result.status, Status.WARNING)
        self.assertTrue(result.warned)
        self.assertFalse(result.failed)
        self.assertIn("8 GB", result.message)
        self.assertIn("16 GB", result.hint)

    def test_is_pending_without_ram(self) -> None:
        self.assertIs(check_ram_capacity(Build()).status, Status.PENDING)

    def test_warning_does_not_count_as_issue(self) -> None:
        build = make_complete_build().with_component(make_ram(capacity_gb=8))

        self.assertEqual(find_issues(build), [])
        warnings = [result.rule for result in find_warnings(build)]
        self.assertEqual(warnings, [RAM_CAPACITY_RULE])

    def test_compatible_build_has_no_warnings(self) -> None:
        self.assertEqual(find_warnings(make_complete_build()), [])


class StorageKindWarningTest(unittest.TestCase):
    def test_ssd_is_ok(self) -> None:
        for kind in ("SSD NVMe", "SSD SATA"):
            with self.subTest(kind=kind):
                result = check_storage_kind(build_with(make_storage(
                    kind=kind
                )))

                self.assertIs(result.status, Status.OK)

    def test_hd_is_a_warning(self) -> None:
        result = check_storage_kind(build_with(make_storage(kind="HD")))

        self.assertIs(result.status, Status.WARNING)
        self.assertFalse(result.failed)
        self.assertIn("HD", result.message)
        self.assertIn("SSD", result.hint)
        self.assertTrue(result.involves(Category.STORAGE))

    def test_is_pending_without_storage(self) -> None:
        self.assertIs(check_storage_kind(Build()).status, Status.PENDING)

    def test_hd_warning_does_not_block_build(self) -> None:
        build = make_complete_build().with_component(
            make_storage(kind="HD")
        )

        self.assertEqual(find_issues(build), [])
        warnings = [result.rule for result in find_warnings(build)]
        self.assertEqual(warnings, [STORAGE_KIND_RULE])

    def test_hd_as_second_disk_is_ok(self) -> None:
        build = build_with(make_storage(kind="SSD NVMe")).with_extra_storage(
            make_storage(kind="HD")
        )

        self.assertIs(check_storage_kind(build).status, Status.OK)

    def test_suggests_swapping_when_second_disk_is_ssd(self) -> None:
        ssd = make_storage(component_id="ssd-2", kind="SSD NVMe")
        build = build_with(make_storage(kind="HD")).with_extra_storage(ssd)

        result = check_storage_kind(build)

        self.assertIs(result.status, Status.WARNING)
        self.assertIn(ssd.name, result.hint)
        self.assertIn("segundo disco", result.hint)


class ValidateBuildTest(unittest.TestCase):
    def test_compatible_build_has_no_issues(self) -> None:
        self.assertEqual(find_issues(make_complete_build()), [])

    def test_check_all_reports_every_rule(self) -> None:
        rules = [result.rule for result in check_all(Build())]

        self.assertEqual(
            rules,
            [SOCKET_RULE, RAM_RULE, PSU_RULE, FORM_FACTOR_RULE,
             RAM_CAPACITY_RULE, STORAGE_KIND_RULE],
        )

    def test_reports_all_issues_at_once(self) -> None:
        build = build_with(
            make_cpu("AM4", tdp_watts=170),
            make_motherboard("AM5", RamType.DDR5),
            make_ram(RamType.DDR4),
            make_gpu(575),
            make_psu(450),
            make_case(supported_form_factors=(FormFactor.ITX,)),
        )

        rules = [issue.rule for issue in find_issues(build)]

        self.assertEqual(
            rules, [SOCKET_RULE, RAM_RULE, PSU_RULE, FORM_FACTOR_RULE]
        )

    def test_issue_knows_which_categories_are_involved(self) -> None:
        build = build_with(make_cpu("AM4"), make_motherboard("AM5"))

        issue = find_issues(build)[0]

        self.assertTrue(issue.involves(Category.CPU))
        self.assertTrue(issue.involves(Category.MOTHERBOARD))
        self.assertFalse(issue.involves(Category.RAM))


if __name__ == "__main__":
    unittest.main()
