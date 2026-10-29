from collections.abc import Mapping

from core.catalog import Catalog
from core.models import Build, Category, Component, Storage


class SelectionError(ValueError):
    pass


def _find(catalog: Catalog, component_id: str) -> Component:
    try:
        return catalog.get(component_id)
    except KeyError:
        raise SelectionError(
            f"A peça '{component_id}' não existe no catálogo."
        ) from None


# Monta a Build a partir dos IDs escolhidos, ex.: {"cpu": "cpu-r5-5600"}.
# É o que a API usa. Diferente do saved_build (que só avisa das peças que
# sumiram do catálogo), aqui qualquer ID errado já é erro.
def build_from_ids(
    catalog: Catalog,
    component_ids: Mapping[str, str],
    extra_storage_id: str | None = None,
) -> Build:
    build = Build()
    for key, component_id in component_ids.items():
        try:
            category = Category(key)
        except ValueError:
            raise SelectionError(f"Categoria desconhecida: '{key}'.") from None
        component = _find(catalog, component_id)
        if component.category is not category:
            raise SelectionError(
                f"A peça '{component_id}' não é da categoria "
                f"{category.label}."
            )
        build = build.with_component(component)

    if extra_storage_id is not None:
        extra = _find(catalog, extra_storage_id)
        if not isinstance(extra, Storage):
            raise SelectionError(
                f"A peça '{extra_storage_id}' não é de armazenamento, então "
                "não pode ser o segundo disco."
            )
        if build.storage is None:
            raise SelectionError(
                "Escolha o disco principal antes do segundo disco."
            )
        build = build.with_extra_storage(extra)
    return build
