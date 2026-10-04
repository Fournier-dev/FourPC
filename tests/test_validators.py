import unittest

from core.models import Build, Category, Component, RamType
from core.validators import (
    PSU_RULE, RAM_RULE, SOCKET_RULE, Status, check_all, check_cpu_socket,
    check_psu_wattage, check_ram_type, find_issues, required_psu_wattage,
)
from tests.helpers import (
    make_complete_build, make_cpu, make_gpu, make_motherboard, make_psu,
    make_ram,
)


def build_with(*components: Component) -> Build:
    build = Build()
    for component in components:
        build = build.with_component(component)
    return build


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


class ValidateBuildTest(unittest.TestCase):
    def test_compatible_build_has_no_issues(self) -> None:
        self.assertEqual(find_issues(make_complete_build()), [])

    def test_check_all_reports_every_rule(self) -> None:
        rules = [result.rule for result in check_all(Build())]

        self.assertEqual(rules, [SOCKET_RULE, RAM_RULE, PSU_RULE])

    def test_reports_all_issues_at_once(self) -> None:
        build = build_with(
            make_cpu("AM4", tdp_watts=170),
            make_motherboard("AM5", RamType.DDR5),
            make_ram(RamType.DDR4),
            make_gpu(575),
            make_psu(450),
        )

        rules = [issue.rule for issue in find_issues(build)]

        self.assertEqual(rules, [SOCKET_RULE, RAM_RULE, PSU_RULE])

    def test_issue_knows_which_categories_are_involved(self) -> None:
        build = build_with(make_cpu("AM4"), make_motherboard("AM5"))

        issue = find_issues(build)[0]

        self.assertTrue(issue.involves(Category.CPU))
        self.assertTrue(issue.involves(Category.MOTHERBOARD))
        self.assertFalse(issue.involves(Category.RAM))


if __name__ == "__main__":
    unittest.main()
