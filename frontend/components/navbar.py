"""顶部导航栏组件"""

import dash_bootstrap_components as dbc
from dash import html


def create_navbar(username: str = "") -> dbc.NavbarSimple:
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            html.Span("人员信息管理系统", className="navbar-brand mb-0 h1",
                                      style={"color": "white", "fontWeight": "700"}),
                        ),
                    ],
                    align="center",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            html.Span(
                                [
                                    html.I(className="fas fa-user-circle me-2"),
                                    f"欢迎, {username or '管理员'}",
                                ],
                                style={"color": "rgba(255,255,255,0.9)"},
                            ),
                        ),
                        dbc.Col(
                            dbc.Button(
                                [html.I(className="fas fa-sign-out-alt me-1"), "退出"],
                                id="logout-btn", color="outline-light", size="sm",
                            ),
                            width="auto",
                        ),
                    ],
                    align="center",
                    className="ms-auto",
                ),
            ],
            fluid=True,
        ),
        color="#16213e",
        dark=True,
        style={
            "position": "fixed", "top": "0", "left": "220px", "right": "0",
            "zIndex": "999", "height": "56px", "padding": "0",
        },
    )
