from fastapi import APIRouter

from app.api.v1 import analytics, audit, auth, billing, catalog, companies, customers, portal, pricing, sales, settings, staff, workspace

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(workspace.router, prefix="/workspace", tags=["company workspace"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(sales.router, prefix="/sales", tags=["quotations and subscriptions"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(portal.router, prefix="/my", tags=["customer portal"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(pricing.router, prefix="/pricing", tags=["pricing"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
