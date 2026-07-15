"""侧边栏导航组件"""

import dash_bootstrap_components as dbc
from dash import html


def create_sidebar() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.H5("人员信息管理系统", style={
                        "color": "white", "textAlign": "center",
                        "padding": "20px 0", "margin": "0",
                        "fontSize": "16px", "fontWeight": "700",
                    }),
                ],
                style={"borderBottom": "1px solid rgba(255,255,255,0.15)", "marginBottom": "8px"},
            ),
            dbc.Nav(
                [
                    dbc.NavLink(
                        [html.I(className="fas fa-home me-2"), "首页"],
                        href="/", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-users me-2"), "人员列表"],
                        href="/personnel", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-search me-2"), "高级搜索"],
                        href="/search", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-plus-circle me-2"), "新增人员"],
                        href="/add", active="exact",
                    ),
                    dbc.NavLink(
                        [html.I(className="fas fa-upload me-2"), "数据导入"],
                        href="/import", active="exact",
                    ),
                ],
                vertical=True,
                pills=True,
            ),
        ],
        id="sidebar",
        style={
            "position": "fixed", "top": "0", "left": "0", "bottom": "0",
            "width": "220px", "padding": "12px 8px",
            "backgroundColor": "#1a1a2e",
            "borderRight": "1px solid #16213e",
            "zIndex": "1000", "overflowY": "auto",
        },
    )
