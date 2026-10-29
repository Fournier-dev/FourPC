# Formato dos dados que a API devolve. O FastAPI usa essas classes pra
# validar a resposta e pra montar a documentação do /docs sozinho.

from typing import Any

from pydantic import BaseModel, Field

from core.catalog import Catalog
from core.models import Category, Component
from core.report import component_attributes, format_brl


class ComponentOut(BaseModel):
    id: str
    name: str
    category: str = Field(description="Chave da categoria, ex.: 'cpu'")
    category_label: str = Field(
        description="Nome da categoria, ex.: 'Processador'"
    )
    specs: str = Field(description="Resumo das especificações")
    # preço como texto pra não perder os centavos (o JSON não tem Decimal)
    price: str = Field(examples=["1299.90"])
    price_formatted: str = Field(examples=["R$ 1.299,90"])
    attributes: dict[str, Any] = Field(
        description="Dados técnicos da peça (soquete, consumo, formato...)"
    )

    # o label vem de fora porque o segundo disco é "Armazenamento 2"
    @classmethod
    def from_component(
        cls, component: Component, label: str | None = None
    ) -> "ComponentOut":
        return cls(
            id=component.id,
            name=component.name,
            category=component.category.value,
            category_label=label or component.category.label,
            specs=component.specs(),
            price=str(component.price),
            price_formatted=format_brl(component.price),
            attributes=component_attributes(component),
        )


class CategoryOut(BaseModel):
    category: str
    label: str
    components: list[ComponentOut]


class CatalogOut(BaseModel):
    categories: list[CategoryOut]

    # as peças já vêm do catálogo ordenadas do mais barato pro mais caro
    @classmethod
    def from_catalog(cls, catalog: Catalog) -> "CatalogOut":
        return cls(categories=[
            CategoryOut(
                category=category.value,
                label=category.label,
                components=[
                    ComponentOut.from_component(component)
                    for component in catalog.options(category)
                ],
            )
            for category in Category
        ])
