"""Regras de compatibilidade entre as peças de uma montagem.

Cada regra é uma função pura que recebe uma ``Build`` e devolve um
``RuleResult``. Isso permite validar a montagem a qualquer momento:
regras cujas peças ainda não foram escolhidas ficam como pendentes.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from enum import Enum

from core.models import CPU, GPU, Build, Category

PSU_SAFETY_MARGIN = Decimal("0.20")

SOCKET_RULE = "Soquete CPU x Placa-Mãe"
RAM_RULE = "Tecnologia de RAM x Placa-Mãe"
PSU_RULE = "Dimensionamento da Fonte"


class Status(Enum):
    OK = "ok"
    FAIL = "fail"
    PENDING = "pending"


@dataclass(frozen=True)
class RuleResult:
    """Resultado da avaliação de uma regra sobre uma montagem."""

    rule: str
    categories: tuple[Category, ...]
    status: Status
    message: str
    hint: str = ""

    @property
    def failed(self) -> bool:
        return self.status is Status.FAIL

    def involves(self, category: Category) -> bool:
        """Indica se a regra depende de uma peça da categoria informada."""
        return category in self.categories


Rule = Callable[[Build], RuleResult]


def estimated_load_watts(cpu: CPU, gpu: GPU) -> int:
    """Consumo estimado do sistema: TDP da CPU + consumo da GPU."""
    return cpu.tdp_watts + gpu.power_watts


def required_psu_wattage(cpu: CPU, gpu: GPU) -> int:
    """Potência mínima da fonte: consumo estimado + margem de segurança.

    O cálculo usa ``Decimal`` para evitar erros de ponto flutuante
    (com ``float``, 300 * 1.2 resulta em 360.00000000000006 e o
    arredondamento para cima exigiria 361 W em vez de 360 W).
    """
    load = Decimal(estimated_load_watts(cpu, gpu))
    required = load * (1 + PSU_SAFETY_MARGIN)
    return int(required.to_integral_value(rounding=ROUND_CEILING))


def check_cpu_socket(build: Build) -> RuleResult:
    """Regra 1: o soquete do processador deve ser igual ao da placa-mãe."""
    involved = (Category.CPU, Category.MOTHERBOARD)
    cpu, board = build.cpu, build.motherboard
    if cpu is None or board is None:
        return RuleResult(
            SOCKET_RULE, involved, Status.PENDING,
            "Selecione o processador e a placa-mãe para verificar.",
        )
    if cpu.socket == board.socket:
        return RuleResult(
            SOCKET_RULE, involved, Status.OK,
            f"Processador e placa-mãe usam o soquete {cpu.socket}.",
        )
    return RuleResult(
        SOCKET_RULE, involved, Status.FAIL,
        f"O processador {cpu.name} usa o soquete {cpu.socket}, mas a "
        f"placa-mãe {board.name} é {board.socket}.",
        f"escolha uma placa-mãe {cpu.socket} ou um processador "
        f"{board.socket}.",
    )


def check_ram_type(build: Build) -> RuleResult:
    """Regra 2: o padrão da memória (DDR4/DDR5) deve ser o da placa-mãe."""
    involved = (Category.RAM, Category.MOTHERBOARD)
    ram, board = build.ram, build.motherboard
    if ram is None or board is None:
        return RuleResult(
            RAM_RULE, involved, Status.PENDING,
            "Selecione a memória RAM e a placa-mãe para verificar.",
        )
    if ram.ram_type is board.ram_type:
        return RuleResult(
            RAM_RULE, involved, Status.OK,
            f"Memória e placa-mãe usam o padrão {ram.ram_type.value}.",
        )
    return RuleResult(
        RAM_RULE, involved, Status.FAIL,
        f"A memória {ram.name} é {ram.ram_type.value}, mas a placa-mãe "
        f"{board.name} só aceita {board.ram_type.value}.",
        f"escolha uma memória {board.ram_type.value} ou uma placa-mãe "
        f"compatível com {ram.ram_type.value}.",
    )


def check_psu_wattage(build: Build) -> RuleResult:
    """Regra 3: a fonte deve suportar CPU + GPU com 20% de margem."""
    involved = (Category.CPU, Category.GPU, Category.PSU)
    cpu, gpu, psu = build.cpu, build.gpu, build.psu
    if cpu is None or gpu is None or psu is None:
        return RuleResult(
            PSU_RULE, involved, Status.PENDING,
            "Selecione processador, placa de vídeo e fonte para verificar.",
        )
    load = estimated_load_watts(cpu, gpu)
    required = required_psu_wattage(cpu, gpu)
    if psu.wattage >= required:
        return RuleResult(
            PSU_RULE, involved, Status.OK,
            f"A fonte de {psu.wattage} W atende ao mínimo de {required} W "
            f"(consumo de {load} W + {PSU_SAFETY_MARGIN:.0%} de margem).",
        )
    return RuleResult(
        PSU_RULE, involved, Status.FAIL,
        f"A fonte {psu.name} ({psu.wattage} W) é insuficiente: CPU "
        f"({cpu.tdp_watts} W) + GPU ({gpu.power_watts} W) + "
        f"{PSU_SAFETY_MARGIN:.0%} de margem exigem {required} W.",
        f"escolha uma fonte de pelo menos {required} W.",
    )


RULES: tuple[Rule, ...] = (check_cpu_socket, check_ram_type, check_psu_wattage)


def check_all(build: Build, rules: Iterable[Rule] = RULES) -> list[RuleResult]:
    """Avalia todas as regras, incluindo as aprovadas e as pendentes."""
    return [rule(build) for rule in rules]


def find_issues(
    build: Build, rules: Iterable[Rule] = RULES
) -> list[RuleResult]:
    """Retorna apenas as regras violadas pela montagem."""
    return [result for result in check_all(build, rules) if result.failed]
