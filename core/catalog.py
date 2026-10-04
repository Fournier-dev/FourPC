import json
from collections.abc import Callable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

from core.models import (
    CPU, GPU, PSU, RAM, Case, Category, Component, Motherboard, RamType,
    Storage,
)

DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "catalog.json"
)


class CatalogError(Exception):
    pass


# campos que todas as peças têm
def _base_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": str(data["id"]),
        "name": str(data["name"]),
        "price": Decimal(str(data["price"])),
    }


def _parse_cpu(data: Mapping[str, Any]) -> CPU:
    return CPU(
        **_base_fields(data),
        socket=str(data["socket"]),
        tdp_watts=int(data["tdp_watts"]),
    )


def _parse_motherboard(data: Mapping[str, Any]) -> Motherboard:
    return Motherboard(
        **_base_fields(data),
        socket=str(data["socket"]),
        ram_type=RamType(data["ram_type"]),
    )


def _parse_ram(data: Mapping[str, Any]) -> RAM:
    return RAM(
        **_base_fields(data),
        ram_type=RamType(data["ram_type"]),
        capacity_gb=int(data["capacity_gb"]),
    )


def _parse_gpu(data: Mapping[str, Any]) -> GPU:
    return GPU(**_base_fields(data), power_watts=int(data["power_watts"]))


def _parse_psu(data: Mapping[str, Any]) -> PSU:
    return PSU(**_base_fields(data), wattage=int(data["wattage"]))


def _parse_storage(data: Mapping[str, Any]) -> Storage:
    return Storage(
        **_base_fields(data),
        kind=str(data["kind"]),
        capacity_gb=int(data["capacity_gb"]),
    )


def _parse_case(data: Mapping[str, Any]) -> Case:
    return Case(**_base_fields(data))


# qual função usar pra ler cada categoria do JSON
_PARSERS: dict[Category, Callable[[Mapping[str, Any]], Component]] = {
    Category.CPU: _parse_cpu,
    Category.MOTHERBOARD: _parse_motherboard,
    Category.RAM: _parse_ram,
    Category.GPU: _parse_gpu,
    Category.PSU: _parse_psu,
    Category.STORAGE: _parse_storage,
    Category.CASE: _parse_case,
}


def _parse_component(category: Category, entry: Any) -> Component:
    if not isinstance(entry, Mapping):
        raise CatalogError(
            f"Item inválido em '{category.value}': esperado um objeto JSON."
        )
    try:
        return _PARSERS[category](entry)
    except KeyError as error:
        raise CatalogError(
            f"Peça '{entry.get('id', '?')}' em '{category.value}' sem o "
            f"campo obrigatório {error}."
        ) from error
    except (TypeError, ValueError, ArithmeticError) as error:
        raise CatalogError(
            f"Peça '{entry.get('id', '?')}' em '{category.value}' tem "
            f"valores inválidos: {error}"
        ) from error


class Catalog:
    def __init__(self, components: Mapping[Category, list[Component]]) -> None:
        self._by_category: dict[Category, list[Component]] = {}
        self._by_id: dict[str, Component] = {}
        for category in Category:
            self._by_category[category] = list(components.get(category, []))
            for component in self._by_category[category]:
                if component.id in self._by_id:
                    raise CatalogError(
                        f"ID duplicado no catálogo: '{component.id}'."
                    )
                self._by_id[component.id] = component

    @classmethod
    def from_json(cls, path: Path = DEFAULT_CATALOG_PATH) -> "Catalog":
        try:
            # parse_float=Decimal pra não perder precisão nos preços
            raw = json.loads(
                path.read_text(encoding="utf-8"), parse_float=Decimal
            )
        except FileNotFoundError:
            raise CatalogError(
                f"Arquivo de catálogo não encontrado: {path}"
            ) from None
        except json.JSONDecodeError as error:
            raise CatalogError(f"JSON inválido em {path}: {error}") from error

        if not isinstance(raw, dict):
            raise CatalogError(
                "O catálogo deve ser um objeto JSON com uma lista de peças "
                "por categoria."
            )

        components: dict[Category, list[Component]] = {}
        for category in Category:
            entries = raw.get(category.value)
            if not isinstance(entries, list) or len(entries) == 0:
                raise CatalogError(
                    f"A categoria '{category.value}' está ausente ou vazia "
                    "no catálogo."
                )
            components[category] = [
                _parse_component(category, entry) for entry in entries
            ]
        return cls(components)

    def options(self, category: Category) -> list[Component]:
        return list(self._by_category[category])

    def get(self, component_id: str) -> Component:
        return self._by_id[component_id]
