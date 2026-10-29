# catálogo pequeno pros testes da API, com 2 opções por categoria.
# As peças "boas" (compatíveis entre si) são: cpu-am5, mb-am5, ram-ddr5,
# gpu-small, psu-650, ssd-1 e case-1. Total: R$ 5.400,00

from core.catalog import Catalog
from core.models import Category, Component, FormFactor, RamType
from tests.helpers import (
    make_case, make_cpu, make_gpu, make_motherboard, make_psu, make_ram,
    make_storage,
)

GOOD_BUILD = {
    "cpu": "cpu-am5",
    "motherboard": "mb-am5",
    "ram": "ram-ddr5",
    "gpu": "gpu-small",
    "psu": "psu-650",
    "storage": "ssd-1",
    "case": "case-1",
}


def web_catalog() -> Catalog:
    components: dict[Category, list[Component]] = {
        Category.CPU: [
            make_cpu("AM5", 65, "1000.00", "cpu-am5"),
            make_cpu("LGA1700", 125, "1200.00", "cpu-intel"),
        ],
        Category.MOTHERBOARD: [
            make_motherboard("AM5", RamType.DDR5, "800.00", "mb-am5"),
            make_motherboard(
                "AM4", RamType.DDR4, "600.00", "mb-am4", FormFactor.MATX
            ),
        ],
        Category.RAM: [
            make_ram(RamType.DDR5, 16, "400.00", "ram-ddr5"),
            make_ram(RamType.DDR4, 8, "200.00", "ram-ddr4"),
        ],
        Category.GPU: [
            make_gpu(115, "2000.00", "gpu-small"),
            make_gpu(575, "9000.00", "gpu-huge"),
        ],
        Category.PSU: [
            make_psu(650, "400.00", "psu-650"),
            make_psu(300, "200.00", "psu-300"),
        ],
        Category.STORAGE: [
            make_storage(1000, "500.00", "ssd-1"),
            make_storage(2000, "300.00", "hd-1", kind="HD"),
        ],
        Category.CASE: [
            make_case("300.00", "case-1"),
            make_case("250.00", "case-itx", (FormFactor.ITX,)),
        ],
    }
    return Catalog(components)
