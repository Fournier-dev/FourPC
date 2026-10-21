import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.catalog import Catalog
from core.models import Build


class SavedBuildError(Exception):
    pass


# o que deu pra recuperar do orçamento salvo
@dataclass(frozen=True)
class LoadedBuild:
    build: Build
    # IDs que estavam no arquivo mas não existem mais no catálogo
    missing_ids: list[str] = field(default_factory=list)


# Monta a Build a partir do dicionário gerado pelo to_dict do report.py.
# Uso a peça do catálogo atual (e não os dados do arquivo), assim o preço
# já vem atualizado se ele mudou desde que o orçamento foi salvo.
def build_from_dict(data: Any, catalog: Catalog) -> LoadedBuild:
    if not isinstance(data, Mapping):
        raise SavedBuildError("O arquivo não é um orçamento do FourPC.")
    components = data.get("components")
    if not isinstance(components, list):
        raise SavedBuildError(
            "O arquivo não tem a lista de peças (components)."
        )

    build = Build()
    missing_ids: list[str] = []
    for entry in components:
        if not isinstance(entry, Mapping) or "id" not in entry:
            raise SavedBuildError("Tem uma peça sem ID no arquivo.")
        component_id = str(entry["id"])
        try:
            component = catalog.get(component_id)
        except KeyError:
            missing_ids.append(component_id)
            continue
        # se o ID agora é de outra categoria, não é mais a mesma peça
        category = entry.get("category")
        if category is not None and category != component.category.value:
            missing_ids.append(component_id)
            continue
        build = build.with_component(component)
    return LoadedBuild(build, missing_ids)


def load_build(path: Path, catalog: Catalog) -> LoadedBuild:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SavedBuildError(f"Arquivo não encontrado: {path}") from None
    except (OSError, UnicodeDecodeError) as error:
        raise SavedBuildError(
            f"Não foi possível ler o arquivo: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise SavedBuildError(f"JSON inválido em {path}: {error}") from error
    return build_from_dict(data, catalog)
