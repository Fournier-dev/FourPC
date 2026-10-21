import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.catalog import Catalog
from core.models import Build, Category

DEFAULT_PRESETS_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "presets.json"
)


class PresetError(Exception):
    pass


@dataclass(frozen=True)
class Preset:
    name: str
    description: str
    build: Build


# No presets.json cada montagem tem um ID de peça por categoria. Aqui eu
# troco os IDs pelas peças do catálogo, então o preço é sempre o atual.
def _parse_preset(entry: Any, catalog: Catalog) -> Preset:
    if not isinstance(entry, Mapping):
        raise PresetError("Montagem pronta inválida: esperado um objeto.")
    name = str(entry.get("name", "")).strip()
    if not name:
        raise PresetError("Tem uma montagem pronta sem nome.")
    components = entry.get("components")
    if not isinstance(components, Mapping):
        raise PresetError(f"A montagem '{name}' não tem a lista de peças.")

    build = Build()
    for key, component_id in components.items():
        try:
            category = Category(key)
        except ValueError:
            raise PresetError(
                f"Categoria desconhecida '{key}' na montagem '{name}'."
            ) from None
        try:
            component = catalog.get(str(component_id))
        except KeyError:
            raise PresetError(
                f"A montagem '{name}' usa a peça '{component_id}', que não "
                "está no catálogo."
            ) from None
        if component.category is not category:
            raise PresetError(
                f"Na montagem '{name}', a peça '{component_id}' não é da "
                f"categoria {category.label}."
            )
        build = build.with_component(component)
    description = str(entry.get("description", "")).strip()
    return Preset(name, description, build)


def presets_from_dict(data: Any, catalog: Catalog) -> list[Preset]:
    if not isinstance(data, Mapping) or not isinstance(
        data.get("presets"), list
    ):
        raise PresetError("O arquivo não tem a lista de montagens (presets).")
    return [_parse_preset(entry, catalog) for entry in data["presets"]]


def load_presets(
    catalog: Catalog, path: Path = DEFAULT_PRESETS_PATH
) -> list[Preset]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PresetError(f"Arquivo não encontrado: {path}") from None
    except (OSError, UnicodeDecodeError) as error:
        raise PresetError(
            f"Não foi possível ler o arquivo: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise PresetError(f"JSON inválido em {path}: {error}") from error
    return presets_from_dict(data, catalog)
