from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import AgentScalarConfig, Layout, Theme, get_scalar_api_reference

SCALAR_DIR = Path(__file__).resolve().parent


@dataclass
class ScalarUIOptions:
    title: str = "API Reference"
    agent: AgentScalarConfig = field(default_factory=lambda: AgentScalarConfig(disabled=True))
    show_sidebar: bool = True
    show_developer_tools: Literal["always", "localhost", "never"] = "localhost"
    hide_dark_mode_toggle: bool = True
    hide_search: bool = False
    hide_client_button: bool = True
    hide_test_request_button: bool = False
    hide_download_button: bool = False
    with_default_fonts: bool = True
    default_open_all_tags: bool = True
    expand_all_model_sections: bool = True
    expand_all_responses: bool = True
    scalar_js_url: str = "/scalar-assets/scalar-api-reference.js"
    scalar_favicon_url: str = "data:,"
    telemetry: bool = False
    theme: Theme = Theme.DEFAULT
    layout: Layout = Layout.MODERN


def register(app: FastAPI, options: ScalarUIOptions = ScalarUIOptions()) -> None:
    app.mount(
        "/scalar-assets",
        StaticFiles(directory=SCALAR_DIR / "assets"),
        name="scalar-assets",
    )

    scalar_html = get_scalar_api_reference(
        title=options.title,
        openapi_url=app.openapi_url,
        agent=options.agent,
        show_sidebar=options.show_sidebar,
        show_developer_tools=options.show_developer_tools,
        hide_dark_mode_toggle=options.hide_dark_mode_toggle,
        hide_search=options.hide_search,
        hide_client_button=options.hide_client_button,
        hide_test_request_button=options.hide_test_request_button,
        hide_download_button=options.hide_download_button,
        with_default_fonts=options.with_default_fonts,
        default_open_all_tags=options.default_open_all_tags,
        expand_all_model_sections=options.expand_all_model_sections,
        expand_all_responses=options.expand_all_responses,
        scalar_js_url=options.scalar_js_url,
        scalar_favicon_url=options.scalar_favicon_url,
        telemetry=options.telemetry,
        theme=options.theme,
        layout=options.layout,
    )
    app.add_api_route("/docs", lambda: scalar_html, include_in_schema=False, methods=["GET"])
