# Formato dos dados que a API devolve. O FastAPI usa essas classes pra
# validar a resposta e pra montar a documentação do /docs sozinho.

from typing import Any, Literal

from pydantic import BaseModel, Field

from core.catalog import Catalog
from core.models import Build, Category, Component
from core.presets import Preset
from core.pricing import PIX_DISCOUNT, payment_options
from core.report import component_attributes, format_brl, status_message
from core.validators import (
    RuleResult, check_all, estimated_load_watts, find_issues,
    psu_headroom_percent, required_psu_wattage,
)


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


# o que o site manda pra validar: o ID escolhido em cada categoria
class BuildIn(BaseModel):
    components: dict[str, str] = Field(
        default_factory=dict,
        description="ID da peça escolhida em cada categoria",
        examples=[{
            "cpu": "cpu-r5-7600",
            "motherboard": "mb-b650m-pro-rs",
            "ram": "ram-ddr5-32",
            "gpu": "gpu-rtx4060",
            "psu": "psu-a650bn",
            "storage": "ssd-sn770-1tb",
            "case": "case-lancool216",
        }],
    )
    extra_storage: str | None = Field(
        default=None, description="ID do segundo disco (opcional)"
    )


class RuleOut(BaseModel):
    rule: str
    status: Literal["ok", "fail", "warning", "pending"]
    message: str
    hint: str
    categories: list[str] = Field(
        description="Categorias das peças que essa regra verifica"
    )

    @classmethod
    def from_result(cls, result: RuleResult) -> "RuleOut":
        return cls(
            rule=result.rule,
            status=result.status.value,
            message=result.message,
            hint=result.hint,
            categories=[category.value for category in result.categories],
        )


class PowerOut(BaseModel):
    estimated_load_watts: int
    required_psu_watts: int
    psu_watts: int | None
    psu_headroom_percent: int | None


class PaymentOut(BaseModel):
    total: str
    total_formatted: str
    pix_discount_percent: int
    pix_price: str
    pix_price_formatted: str
    installments: int
    installment_price: str
    installment_price_formatted: str


class ValidationOut(BaseModel):
    components: list[ComponentOut]
    rules: list[RuleOut]
    missing: list[str] = Field(description="Categorias ainda sem peça")
    is_complete: bool
    can_finalize: bool = Field(
        description="Completa e sem incompatibilidade (aviso não impede)"
    )
    status_message: str
    power: PowerOut | None = Field(
        description="Só vem quando já tem processador e placa de vídeo"
    )
    payment: PaymentOut

    # toda a conta é feita pelo core/, aqui só junto as respostas
    @classmethod
    def from_build(cls, build: Build) -> "ValidationOut":
        power = None
        cpu, gpu, psu = build.cpu, build.gpu, build.psu
        if cpu is not None and gpu is not None:
            power = PowerOut(
                estimated_load_watts=estimated_load_watts(cpu, gpu),
                required_psu_watts=required_psu_wattage(cpu, gpu),
                psu_watts=None if psu is None else psu.wattage,
                psu_headroom_percent=(
                    None if psu is None
                    else psu_headroom_percent(cpu, gpu, psu)
                ),
            )
        payment = payment_options(build.total_price)
        return cls(
            components=[
                ComponentOut.from_component(component, label)
                for label, component in build.labeled_components()
            ],
            rules=[RuleOut.from_result(result) for result in check_all(build)],
            missing=[cat.value for cat in build.missing_categories()],
            is_complete=build.is_complete,
            can_finalize=build.is_complete and not find_issues(build),
            status_message=status_message(build),
            power=power,
            payment=PaymentOut(
                total=str(payment.total),
                total_formatted=format_brl(payment.total),
                pix_discount_percent=int(PIX_DISCOUNT * 100),
                pix_price=str(payment.pix_price),
                pix_price_formatted=format_brl(payment.pix_price),
                installments=payment.installments,
                installment_price=str(payment.installment_price),
                installment_price_formatted=format_brl(
                    payment.installment_price
                ),
            ),
        )


class PresetOut(BaseModel):
    name: str
    description: str
    components: dict[str, str] = Field(
        description="ID da peça de cada categoria (mesmo formato do BuildIn)"
    )
    extra_storage: str | None
    total: str
    total_formatted: str

    @classmethod
    def from_preset(cls, preset: Preset) -> "PresetOut":
        build = preset.build
        components: dict[str, str] = {}
        for category in Category:
            component = build.get(category)
            if component is not None:
                components[category.value] = component.id
        extra = build.extra_storage
        return cls(
            name=preset.name,
            description=preset.description,
            components=components,
            extra_storage=None if extra is None else extra.id,
            total=str(build.total_price),
            total_formatted=format_brl(build.total_price),
        )
