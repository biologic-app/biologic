"""Black-box tests for the frontend structure rule checkers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY = Path(__file__).resolve().parents[4]
CHECKER_DIR = REPOSITORY / "scripts/rule/structure"


def write_frontend(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a minimal isolated frontend tree containing the supplied files."""
    frontend = tmp_path / "frontend"
    for relative, content in files.items():
        destination = frontend / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    return frontend


def run_checker(name: str, frontend: Path) -> subprocess.CompletedProcess[str]:
    """Run one checker against an isolated frontend and capture output and exit code."""
    environment = os.environ.copy()
    environment["FRONTEND_STRUCTURE_ROOT"] = str(frontend)
    return subprocess.run(
        [sys.executable, str(CHECKER_DIR / f"frontend-{name}.py")],
        cwd=REPOSITORY,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def assert_clean(name: str, frontend: Path) -> None:
    """Assert that a checker accepts an isolated valid frontend."""
    result = run_checker(name, frontend)
    assert result.returncode == 0, result.stdout + result.stderr


def assert_violation(name: str, frontend: Path, rule: str) -> subprocess.CompletedProcess[str]:
    """Assert a rule failure and require its rule name in the diagnostic."""
    result = run_checker(name, frontend)
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"[{rule}]" in result.stdout
    return result


def test_directory_threshold_positive_boundary_and_excluded_directory(tmp_path: Path) -> None:
    """Allow seven files, reject eight, and ignore source-like files in dist/node_modules."""
    valid = {"src/components/file%d.ts" % index: "export const value = 1\n" for index in range(7)}
    valid.update({"src/dist/file%d.ts" % index: "x" for index in range(20)})
    assert_clean("directory-threshold", write_frontend(tmp_path / "valid", valid))
    invalid = dict(valid)
    invalid["src/components/eighth.ts"] = "export const value = 1\n"
    result = assert_violation("directory-threshold", write_frontend(tmp_path / "invalid", invalid), "directory-threshold")
    assert "maximum is 7" in result.stdout


def test_file_naming_positive_and_negative(tmp_path: Path) -> None:
    """Accept normative names and reject a non-kebab-case TypeScript file."""
    valid = write_frontend(tmp_path / "valid", {"src/shared/utils/date-range.ts": "export const x = 1\n"})
    assert_clean("file-naming", valid)
    invalid = write_frontend(tmp_path / "invalid", {"src/shared/utils/dateRange.ts": "export const x = 1\n"})
    result = assert_violation("file-naming", invalid, "file-naming")
    assert "dateRange.ts" in result.stdout


def test_file_placement_positive_and_negative(tmp_path: Path) -> None:
    """Accept recognized layers and reject an unknown top-level source directory."""
    assert_clean("file-placement", write_frontend(tmp_path / "valid", {"src/shared/utils/date-range.ts": "x"}))
    result = assert_violation("file-placement", write_frontend(tmp_path / "invalid", {"src/unknown/file.ts": "x"}), "file-placement")
    assert "unknown" in result.stdout


def test_file_size_positive_boundary_and_technical_exclusion(tmp_path: Path) -> None:
    """Allow exactly 500 lines and ignore oversized generated/vendor files."""
    valid = write_frontend(tmp_path / "valid", {
        "src/shared/utils/ok.ts": (("x\n" * 499) + "x"),
        "src/shared/api/generated/large.gen.ts": ("x\n" * 1000),
        "src/vendor/large.ts": ("x\n" * 1000),
    })
    assert_clean("file-size", valid)
    invalid = write_frontend(tmp_path / "invalid", {"src/shared/utils/too-large.ts": ("x\n" * 501)})
    result = assert_violation("file-size", invalid, "file-size")
    assert "limits are" in result.stdout


def test_allowlist_positive_negative_and_generated_boundary(tmp_path: Path) -> None:
    """Validate required roots and generated filename exceptions."""
    required = {"src/index.ts": "x", "src/app/.keep": "", "src/modules/.keep": "", "src/shared/.keep": "", "tests/.keep": ""}
    assert_clean("allowlist", write_frontend(tmp_path / "valid", required))
    invalid = write_frontend(tmp_path / "invalid", {**required, "src/shared/api/generated/client.ts": "x"})
    result = assert_violation("allowlist", invalid, "allowlist")
    assert "generated API source" in result.stdout


def test_component_naming_positive_and_negative(tmp_path: Path) -> None:
    """Accept PascalCase components and reject lowercase Vue component files."""
    assert_clean("component-naming", write_frontend(tmp_path / "valid", {"src/components/UserCard.vue": "<template />"}))
    result = assert_violation("component-naming", write_frontend(tmp_path / "invalid", {"src/components/user-card.vue": "<template />"}), "component-naming")
    assert "PascalCase" in result.stdout


def test_composable_store_service_rule(tmp_path: Path) -> None:
    """Accept correctly placed composable/store/service and reject misplaced defineStore."""
    valid = write_frontend(tmp_path / "valid", {
        "src/shared/composables/useClock.ts": "export function useClock() { return 1 }\n",
        "src/modules/users/stores/useUsers.ts": "import { defineStore } from 'pinia'; export const useUsers = defineStore('users', () => ({}));\n",
        "src/shared/services/auth.service.ts": "export function refresh() { return 1 }\n",
    })
    assert_clean("composable-store-service", valid)
    invalid = write_frontend(tmp_path / "invalid", {"src/modules/auth/composables/useAuth.ts": "import { defineStore } from 'pinia'; export const useAuth = defineStore('auth', () => ({}));\n"})
    result = assert_violation("composable-store-service", invalid, "composable-store-service")
    assert "stores directory" in result.stdout


def test_direct_side_effects_vue_script_setup_and_regular_script(tmp_path: Path) -> None:
    """Detect direct effects in both Vue script forms and accept a component without them."""
    valid = write_frontend(tmp_path / "valid", {
        "src/components/Setup.vue": "<script setup lang=\"ts\">const value = 1</script><template>{{ value }}</template>",
        "src/components/Regular.vue": "<script lang=\"ts\">export default {}</script><template />",
    })
    assert_clean("direct-side-effects", valid)
    invalid = write_frontend(tmp_path / "invalid", {
        "src/components/Setup.vue": "<script setup lang=\"ts\">localStorage.getItem('x')</script><template />",
        "src/components/Regular.vue": "<script lang=\"ts\">fetch('/api')</script><template />",
    })
    result = assert_violation("direct-side-effects", invalid, "direct-side-effects")
    assert ":1:" in result.stdout


def test_dependency_layers_and_import_forms(tmp_path: Path) -> None:
    """Detect shared imports of modules and cross-feature imports in TS and Vue scripts."""
    valid = write_frontend(tmp_path / "valid", {
        "src/shared/utils/x.ts": "import { ref } from 'vue'; export const x = ref(1);\n",
        "src/modules/users/components/User.vue": "<script setup lang=\"ts\">import { x } from '@/shared/utils/x'</script><template />",
    })
    assert_clean("dependency-layers", valid)
    invalid = write_frontend(tmp_path / "invalid", {
        "src/shared/utils/x.ts": "import { useUsers } from '@/modules/users/stores/useUsers'; export const x = useUsers;\n",
        "src/modules/users/components/User.vue": "<script lang=\"ts\">import { y } from '@/modules/orders/api/orders.api'; export default {}</script><template />",
    })
    result = assert_violation("dependency-layers", invalid, "dependency-layers")
    assert "must not import" in result.stdout


def test_symbol_naming_all_function_forms_and_methods(tmp_path: Path) -> None:
    """Parse declarations, async declarations, arrows, exports, and class methods."""
    source = """
function foo() {}
async function loadData() {}
const buildValue = () => 1;
const fetchValue = async () => 1;
export const createValue = () => 1;
class Example { methodName() {} async loadMore() {} }
"""
    assert_clean("symbol-naming", write_frontend(tmp_path / "valid", {"src/shared/utils/functions.ts": source}))
    invalid = write_frontend(tmp_path / "invalid", {"src/shared/utils/functions.ts": "function BadName() {}\n"})
    result = assert_violation("symbol-naming", invalid, "symbol-naming")
    assert 'function \'BadName\'' in result.stdout


def test_type_naming_interfaces_aliases_enums_and_vue_scripts(tmp_path: Path) -> None:
    """Parse interfaces, aliases, enums, and both Vue TypeScript script forms."""
    valid = write_frontend(tmp_path / "valid", {
        "src/shared/types/models.ts": "interface UserProfile {}\ntype UserId = string;\nenum UserRole { Admin }\n",
        "src/components/Setup.vue": "<script setup lang=\"ts\">interface SetupProps { value: string }</script><template />",
        "src/components/Regular.vue": "<script lang=\"ts\">type RegularOptions = { value: string }</script><template />",
    })
    assert_clean("type-naming", valid)
    invalid = write_frontend(tmp_path / "invalid", {"src/shared/types/models.ts": "interface userProfile {}\ntype userId = string;\nenum userRole { Admin }\n"})
    result = assert_violation("type-naming", invalid, "type-naming")
    assert "PascalCase" in result.stdout
