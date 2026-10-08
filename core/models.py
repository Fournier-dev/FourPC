from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar


# O valor de cada categoria é a chave usada no catalog.json e também
# o nome do campo correspondente na classe Build.
class Category(str, Enum):
    CPU = "cpu"
    MOTHERBOARD = "motherboard"
    RAM = "ram"
    GPU = "gpu"
    PSU = "psu"
    STORAGE = "storage"
    CASE = "case"

    @property
    def label(self) -> str:
        return CATEGORY_LABELS[self]


CATEGORY_LABELS: dict[Category, str] = {
    Category.CPU: "Processador",
    Category.MOTHERBOARD: "Placa-Mãe",
    Category.RAM: "Memória RAM",
    Category.GPU: "Placa de Vídeo",
    Category.PSU: "Fonte",
    Category.STORAGE: "Armazenamento",
    Category.CASE: "Gabinete",
}


class RamType(str, Enum):
    DDR4 = "DDR4"
    DDR5 = "DDR5"


# classe base com o que toda peça tem
@dataclass(frozen=True)
class Component:
    category: ClassVar[Category]

    id: str
    name: str
    price: Decimal

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(f"A peça '{self.id}' está sem nome.")
        if self.price < 0:
            raise ValueError(f"A peça '{self.id}' tem preço negativo.")

    # cada tipo de peça sobrescreve pra mostrar as specs dela
    def specs(self) -> str:
        return ""


@dataclass(frozen=True)
class CPU(Component):
    category: ClassVar[Category] = Category.CPU

    socket: str
    tdp_watts: int

    def specs(self) -> str:
        return f"{self.socket} · {self.tdp_watts} W"


@dataclass(frozen=True)
class Motherboard(Component):
    category: ClassVar[Category] = Category.MOTHERBOARD

    socket: str
    ram_type: RamType

    def specs(self) -> str:
        return f"{self.socket} · {self.ram_type.value}"


@dataclass(frozen=True)
class RAM(Component):
    category: ClassVar[Category] = Category.RAM

    ram_type: RamType
    capacity_gb: int

    def specs(self) -> str:
        return f"{self.ram_type.value} · {self.capacity_gb} GB"


@dataclass(frozen=True)
class GPU(Component):
    category: ClassVar[Category] = Category.GPU

    power_watts: int

    def specs(self) -> str:
        return f"{self.power_watts} W"


@dataclass(frozen=True)
class PSU(Component):
    category: ClassVar[Category] = Category.PSU

    wattage: int

    def specs(self) -> str:
        return f"{self.wattage} W"


@dataclass(frozen=True)
class Storage(Component):
    category: ClassVar[Category] = Category.STORAGE

    kind: str
    capacity_gb: int

    def specs(self) -> str:
        return f"{self.kind} · {format_capacity(self.capacity_gb)}"


@dataclass(frozen=True)
class Case(Component):
    category: ClassVar[Category] = Category.CASE


# 480 -> "480 GB", 1000 -> "1 TB", 1500 -> "1,5 TB"
def format_capacity(capacity_gb: int) -> str:
    if capacity_gb < 1000:
        return f"{capacity_gb} GB"
    terabytes = Decimal(capacity_gb) / 1000
    return f"{terabytes.normalize():f} TB".replace(".", ",")


# A montagem guarda uma peça de cada categoria.
# Deixei ela imutável (frozen=True): pra trocar uma peça eu crio uma Build
# nova. Assim dá pra "testar" uma peça antes de escolher sem mexer na
# montagem atual.
@dataclass(frozen=True)
class Build:
    cpu: CPU | None = None
    motherboard: Motherboard | None = None
    ram: RAM | None = None
    gpu: GPU | None = None
    psu: PSU | None = None
    storage: Storage | None = None
    case: Case | None = None

    def with_component(self, component: Component) -> "Build":
        # se já tiver uma peça dessa categoria, ela é substituída
        changes: dict[str, Any] = {component.category.value: component}
        return replace(self, **changes)

    # mesma ideia do with_component: devolve uma Build nova sem a peça
    def without(self, category: Category) -> "Build":
        changes: dict[str, Any] = {category.value: None}
        return replace(self, **changes)

    def get(self, category: Category) -> Component | None:
        component: Component | None = getattr(self, category.value)
        return component

    def selected(self) -> list[Component]:
        components: list[Component] = []
        for category in Category:
            component = self.get(category)
            if component is not None:
                components.append(component)
        return components

    def missing_categories(self) -> list[Category]:
        return [cat for cat in Category if self.get(cat) is None]

    @property
    def is_complete(self) -> bool:
        return len(self.missing_categories()) == 0

    @property
    def total_price(self) -> Decimal:
        total = Decimal("0")
        for component in self.selected():
            total += component.price
        return total
