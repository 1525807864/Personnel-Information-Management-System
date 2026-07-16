"""顶部导航栏组件"""

import dash_bootstrap_components as dbc
from dash import html, callback, Output, Input
from dash_bootstrap_components import Navbar


def create_navbar(username: str = "") -> Navbar:
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
                                    html.Div(id="username-dash",children= f"欢迎, {username or '管理员'}",style={"color": "rgba(255,255,255,0.9)"}),

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
@callback(
    Output("username-dash", "children"),
    Input("auth-user", "data"),
)
def update_navbar_username(auth_user):
    """
    从 dcc.Store("auth-user") 读取当前登录用户信息，更新导航栏用户名。

    auth-user Store 中存储的是 JSON 字符串（login.py 使用 json.dumps 写入），
    而非 dict。Dash 的 dcc.Store 默认不做自动反序列化，所以需要手动 json.loads。
    """
    import json

    # 解析 Store 中的数据：可能是 dict、JSON 字符串、或 None
    if isinstance(auth_user, str):
        try:
            auth_user = json.loads(auth_user)
        except (json.JSONDecodeError, TypeError):
            auth_user = None

    if auth_user and isinstance(auth_user, dict) and auth_user.get("username"):
        return f"欢迎, {auth_user['username']}"
    return "欢迎, 管理员"
