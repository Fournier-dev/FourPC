# funções pra criar peças rápido nos testes
# os valores padrão já são compatíveis entre si

from decimal import Decimal

from core.models import (
    CPU, GPU, PSU, RAM, Build, Case, Motherboard, RamType, Storage,
)


def make_cpu(
    socket: str = "AM5", tdp_watts: int = 65, price: str = "1000.00",
    component_id: str = "cpu-test",
) -> CPU:
    return CPU(component_id, "CPU Teste", Decimal(price), socket, tdp_watts)


def make_motherboard(
    socket: str = "AM5", ram_type: RamType = RamType.DDR5,
    price: str = "800.00", component_id: str = "mb-test",
) -> Motherboard:
    return Motherboard(
        component_id, "Placa-Mãe Teste", Decimal(price), socket, ram_type
    )


def make_ram(
    ram_type: RamType = RamType.DDR5, capacity_gb: int = 16,
    price: str = "400.00", component_id: str = "ram-test",
) -> RAM:
    return RAM(
        component_id, "RAM Teste", Decimal(price), ram_type, capacity_gb
    )


def make_gpu(
    power_watts: int = 115, price: str = "2000.00",
    component_id: str = "gpu-test",
) -> GPU:
    return GPU(component_id, "GPU Teste", Decimal(price), power_watts)


def make_psu(
    wattage: int = 650, price: str = "400.00", component_id: str = "psu-test",
) -> PSU:
    return PSU(component_id, "Fonte Teste", Decimal(price), wattage)


def make_storage(
    capacity_gb: int = 1000, price: str = "500.00",
    component_id: str = "ssd-test",
) -> Storage:
    return Storage(
        component_id, "SSD Teste", Decimal(price), "SSD NVMe", capacity_gb
    )


def make_case(price: str = "300.00", component_id: str = "case-test") -> Case:
    return Case(component_id, "Gabinete Teste", Decimal(price))


# montagem completa e sem erro, total de R$ 5.400,00
def make_complete_build() -> Build:
    build = Build()
    for component in (
        make_cpu(), make_motherboard(), make_ram(), make_gpu(), make_psu(),
        make_storage(), make_case(),
    ):
        build = build.with_component(component)
    return build
