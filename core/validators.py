from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from enum import Enum

from core.models import CPU, GPU, Build, Category

# margem de segurança da fonte (20%)
PSU_SAFETY_MARGIN = Decimal("0.20")

SOCKET_RULE = "Soquete CPU x Placa-Mãe"
RAM_RULE = "Tecnologia de RAM x Placa-Mãe"
PSU_RULE = "Dimensionamento da Fonte"


class Status(Enum):
    OK = "ok"
    FAIL = "fail"
    PENDING = "pending"  # ainda faltam peças pra conseguir verificar


@dataclass(frozen=True)
class RuleResult:
    rule: str
    categories: tuple[Category, ...]  # categorias que a regra usa
    status: Status
    message: str
    hint: str = ""

    @property
    def failed(self) -> bool:
        return self.status is Status.FAIL

    def involves(self, category: Category) -> bool:
        return category in self.categories


def estimated_load_watts(cpu: CPU, gpu: GPU) -> int:
    return cpu.tdp_watts + gpu.power_watts


def required_psu_wattage(cpu: CPU, gpu: GPU) -> int:
    # Usei Decimal em vez de float porque com float 300 * 1.2 dá
    # 360.00000000000006 e, arredondando pra cima, a fonte mínima virava 361 W
    load = Decimal(estimated_load_watts(cpu, gpu))
    required = load * (1 + PSU_SAFETY_MARGIN)
    return int(required.to_integral_value(rounding=ROUND_CEILING))


# Regra 1: o soquete do processador tem que ser igual ao da placa-mãe
def check_cpu_socket(build: Build) -> RuleResult:
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


# Regra 2: a memória tem que ser do mesmo padrão da placa (DDR4 ou DDR5)
def check_ram_type(build: Build) -> RuleResult:
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


# Regra 3: a fonte tem que aguentar CPU + GPU com 20% de folga
def check_psu_wattage(build: Build) -> RuleResult:
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


# pra criar uma regra nova é só escrever a função e colocar nessa lista
RULES: list[Callable[[Build], RuleResult]] = [
    check_cpu_socket,
    check_ram_type,
    check_psu_wattage,
]


def check_all(build: Build) -> list[RuleResult]:
    return [rule(build) for rule in RULES]


# só as regras que deram erro
def find_issues(build: Build) -> list[RuleResult]:
    return [result for result in check_all(build) if result.failed]
