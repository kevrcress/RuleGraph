"""Graph visualization endpoint — Section 26. TL and Admin only."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models.rule import Rule, Service, RuleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def get_graph(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_roles("tech_lead", "admin")),
):
    """Return nodes and edges for React Flow visualization (technical view)."""
    services_result = await db.execute(select(Service).limit(50))
    services = services_result.scalars().all()

    rules_result = await db.execute(select(Rule).limit(100))
    rules = rules_result.scalars().all()

    links_result = await db.execute(select(RuleService))
    links = links_result.all()

    nodes = []

    # Service nodes — top row
    for i, svc in enumerate(services):
        nodes.append({
            "id": f"service_{svc.id}",
            "type": "service",
            "data": {"label": svc.name, "nodeType": "service"},
            "position": {"x": 280 * (i % 5), "y": 50 + (i // 5) * 100},
        })

    # Rule nodes — rows below services
    for i, rule in enumerate(rules):
        nodes.append({
            "id": f"rule_{rule.id}",
            "type": "rule",
            "data": {
                "label": rule.title,
                "nodeType": "rule",
                "status": rule.status.value,
                "ruleId": str(rule.id),
            },
            "position": {"x": 280 * (i % 4), "y": 250 + (i // 4) * 160},
        })

    edges = [
        {
            "id": f"e_{link.rule_id}_{link.service_id}",
            "source": f"rule_{link.rule_id}",
            "target": f"service_{link.service_id}",
            "label": "IMPLEMENTS",
            "type": "default",
        }
        for link in links
    ]

    return {"nodes": nodes, "edges": edges}
