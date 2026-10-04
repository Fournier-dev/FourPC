"""Estruturas de dados das peças de hardware e da montagem (Build)."""

from dataclasses import dataclass, replace
from decimal import Decimal
from enum import Enum
from typing import Any, ClassVar


class Category(str, Enum):
    """Categorias de peças.

    O valor de cada membro é, ao mesmo tempo, a chave da categoria no
    catálogo JSON e o nome do atributo correspondente em ``Build``.
    """

    CPU = "cpu"
    MOTHERBOARD = "motherboard"
    RAM = "ram"
    GPU = "gpu"
    PSU = "psu"
    STORAGE = "storage"
    CASE = "case"

    @property
    def label(self) -> str:
        """Nome da categoria para exibição ao usuário."""
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
    """Padrões de memória RAM suportados."""

    DDR4 = "DDR4"
    DDR5 = "DDR5"


@dataclass(frozen=True)
class Component:
    """Atributos comuns a todas as peças do catálogo."""

    category: ClassVar[Category]

    id: str
    name: str
    price: Decimal

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError(f"A peça '{self.id}' está sem nome.")
        if self.price < 0:
            raise ValueError(f"A peça '{self.id}' tem preço negativo.")

    def specs(self) -> str:
        """Resumo curto das especificações técnicas, exibido junto ao nome."""
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


def format_capacity(capacity_gb: int) -> str:
    """Formata a capacidade em GB ou TB (ex.: 480 GB, 1 TB, 1,5 TB)."""
    if capacity_gb < 1000:
        return f"{capacity_gb} GB"
    terabytes = Decimal(capacity_gb) / 1000
    return f"{terabytes.normalize():f} TB".replace(".", ",")


@dataclass(frozen=True)
class Build:
    """Montagem em andamento, com no máximo uma peça por categoria.

    É imutável: cada seleção gera uma nova ``Build`` através de
    ``with_component``, o que facilita simular trocas de peças sem
    alterar a montagem atual.
    """

    cpu: CPU | None = None
    motherboard: Motherboard | None = None
    ram: RAM | None = None
    gpu: GPU | None = None
    psu: PSU | None = None
    storage: Storage | None = None
    case: Case | None = None

    def with_component(self, component: Component) -> "Build":
        """Retorna uma nova montagem com a peça adicionada (ou substituída)."""
        changes: dict[str, Any] = {component.category.value: component}
        return replace(self, **changes)

    def get(self, category: Category) -> Component | None:
        """Retorna a peça selecionada na categoria, se houver."""
        component: Component | None = getattr(self, category.value)
        return component

    def selected(self) -> list[Component]:
        """Peças selecionadas, na ordem das categorias."""
        return [c for c in map(self.get, Category) if c is not None]

    def missing_categories(self) -> list[Category]:
        """Categorias que ainda não têm peça selecionada."""
        return [cat for cat in Category if self.get(cat) is None]

    @property
    def is_complete(self) -> bool:
        return not self.missing_categories()

    @property
    def total_price(self) -> Decimal:
        return sum((c.price for c in self.selected()), Decimal("0"))
