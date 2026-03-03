from fastapi import APIRouter

from src.api.v1.endpoints.auth import router as auth_router
from src.api.v1.endpoints.branches import router as branches_router
from src.api.v1.endpoints.change_log import router as change_log_router
from src.api.v1.endpoints.conclusions import router as conclusions_router
from src.api.v1.endpoints.dashboard import router as dashboard_router
from src.api.v1.endpoints.direction_statuses import router as direction_statuses_router
from src.api.v1.endpoints.directions import router as directions_router
from src.api.v1.endpoints.doctors import router as doctors_router
from src.api.v1.endpoints.health import router as health_router
from src.api.v1.endpoints.indicators import router as indicators_router
from src.api.v1.endpoints.labs import router as labs_router
from src.api.v1.endpoints.objects import router as objects_router
from src.api.v1.endpoints.permissions import router as permissions_router
from src.api.v1.endpoints.protocol_types import router as protocol_types_router
from src.api.v1.endpoints.protocols import router as protocols_router
from src.api.v1.endpoints.research import router as research_router
from src.api.v1.endpoints.research_goals import router as research_goals_router
from src.api.v1.endpoints.research_statuses import router as research_statuses_router
from src.api.v1.endpoints.role_permissions import router as role_permissions_router
from src.api.v1.endpoints.roles import router as roles_router
from src.api.v1.endpoints.sample_statuses import router as sample_statuses_router
from src.api.v1.endpoints.sample_types import router as sample_types_router
from src.api.v1.endpoints.samples import router as samples_router
from src.api.v1.endpoints.test_statuses import router as test_statuses_router
from src.api.v1.endpoints.tests import router as tests_router
from src.api.v1.endpoints.user_scopes import router as user_scopes_router
from src.api.v1.endpoints.users import router as users_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(dashboard_router)
router.include_router(branches_router)
router.include_router(change_log_router)
router.include_router(conclusions_router)
router.include_router(direction_statuses_router)
router.include_router(directions_router)
router.include_router(doctors_router)
router.include_router(indicators_router)
router.include_router(labs_router)
router.include_router(objects_router)
router.include_router(permissions_router)
router.include_router(protocol_types_router)
router.include_router(protocols_router)
router.include_router(research_router)
router.include_router(research_goals_router)
router.include_router(research_statuses_router)
router.include_router(roles_router)
router.include_router(sample_statuses_router)
router.include_router(sample_types_router)
router.include_router(samples_router)
router.include_router(test_statuses_router)
router.include_router(tests_router)
router.include_router(user_scopes_router)
router.include_router(users_router)
router.include_router(role_permissions_router)
