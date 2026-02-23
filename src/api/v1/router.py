from fastapi import APIRouter

from src.api.v1.endpoints.auth import router as auth_router
from src.api.v1.endpoints.branches import router as branches_router
from src.api.v1.endpoints.change_log import router as change_log_router
from src.api.v1.endpoints.conclusion_statuses import router as conclusion_statuses_router
from src.api.v1.endpoints.conclusions import router as conclusions_router
from src.api.v1.endpoints.directions import router as directions_router
from src.api.v1.endpoints.doctors import router as doctors_router
from src.api.v1.endpoints.health import router as health_router
from src.api.v1.endpoints.indicators import router as indicators_router
from src.api.v1.endpoints.labs import router as labs_router
from src.api.v1.endpoints.objects import router as objects_router
from src.api.v1.endpoints.protocol_types import router as protocol_types_router
from src.api.v1.endpoints.protocols import router as protocols_router
from src.api.v1.endpoints.research_goals import router as research_goals_router
from src.api.v1.endpoints.results import router as results_router
from src.api.v1.endpoints.role_permissions import router as role_permissions_router
from src.api.v1.endpoints.roles import router as roles_router
from src.api.v1.endpoints.sample_targets import router as sample_targets_router
from src.api.v1.endpoints.sample_types import router as sample_types_router
from src.api.v1.endpoints.samples import router as samples_router
from src.api.v1.endpoints.statuses import router as statuses_router
from src.api.v1.endpoints.tests import router as tests_router
from src.api.v1.endpoints.user_roles import router as user_roles_router
from src.api.v1.endpoints.users import router as users_router

router = APIRouter()
router.include_router(health_router)
router.include_router(auth_router)
router.include_router(branches_router)
router.include_router(change_log_router)
router.include_router(conclusion_statuses_router)
router.include_router(conclusions_router)
router.include_router(directions_router)
router.include_router(doctors_router)
router.include_router(indicators_router)
router.include_router(labs_router)
router.include_router(objects_router)
router.include_router(protocol_types_router)
router.include_router(protocols_router)
router.include_router(research_goals_router)
router.include_router(results_router)
router.include_router(roles_router)
router.include_router(sample_targets_router)
router.include_router(sample_types_router)
router.include_router(samples_router)
router.include_router(statuses_router)
router.include_router(tests_router)
router.include_router(user_roles_router)
router.include_router(users_router)
router.include_router(role_permissions_router)
