from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ServiceTemplate
from app.schemas import CountryOption, FormFieldOut, MaterialRequirementOut, ServiceOption, TemplateOut

router = APIRouter(prefix="/catalog", tags=["国家服务目录"])

@router.get("/countries", response_model=list[CountryOption])
def countries(db: Session = Depends(get_db)):
    templates = db.scalars(select(ServiceTemplate).where(ServiceTemplate.status == "ACTIVE")).all()
    service_order = {"WEEE": 0, "Battery": 1, "Packaging": 2, "SUP": 3}
    templates.sort(key=lambda item: (item.country, service_order.get(item.service_type, 99)))
    result: dict[str, CountryOption] = {}
    for template in templates:
        if template.country not in result:
            result[template.country] = CountryOption(value=template.country, label=template.country_label, services=[])
        result[template.country].services.append(
            ServiceOption(value=template.service_type, label=template.service_label, description=template.description)
        )
    return list(result.values())


@router.get("/templates/{country}/{service}", response_model=TemplateOut)
def template_detail(country: str, service: str, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    template = db.scalar(select(ServiceTemplate).where(
        ServiceTemplate.country == country,
        ServiceTemplate.service_type == service,
        ServiceTemplate.status == "ACTIVE",
    ).order_by(ServiceTemplate.version.desc()))
    if not template:
        raise HTTPException(status_code=404, detail="服务模板不存在")
    return TemplateOut(
        id=template.id,
        country=template.country,
        service_type=template.service_type,
        version=template.version,
        fields=[FormFieldOut.model_validate(field) for field in sorted(template.form_fields, key=lambda item: item.sort)],
        materials=[MaterialRequirementOut.model_validate(item) for item in sorted(template.material_requirements, key=lambda item: item.sort)],
    )
