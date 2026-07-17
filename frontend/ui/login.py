"""登录页面"""
import json

# 流程：
#   1. 用户点击"登录"按钮 → 触发表单提交
#   2. 前端调用后端 POST /api/v1/auth/login 验证凭证
#   3. 后端验证通过 → 签发 JWT Token → 返回 {code:200, data:{token,
#username, role, user_id}}
#   4. 前端将 token + user 写入 dcc.Store（自动持久化到浏览器
#LocalStorage）
#   5. 前端跳转到 /dashboard 仪表盘页面
#   6. 后端验证失败 → 返回 401 → 前端显示错误消息

from dash import html,dcc,Input,Output,State,callback
import dash_bootstrap_components as dbc
import dash
from frontend.utils import api_client
PAGE_SIZE = 20
def layout(**kwargs):
    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.I(className="fas fa-users-cog", style={"fontSize": "48px", "color": "#667eea"}),
                            html.H2("人员信息管理系统", style={"fontWeight": "700", "color": "#333", "marginTop": "12px"}),
                        ],
                        style={"textAlign": "center", "marginBottom": "30px"},
                    ),
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H4("用户登录", className="text-center mb-4", style={"color": "#333"}),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText(html.I(className="fas fa-user")),
                                        dbc.Input(
                                            id="login-username",
                                            placeholder="用户名",
                                            type="text",
                                            autoComplete="username",
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText(html.I(className="fas fa-lock")),
                                        dbc.Input(
                                            id="login-password",
                                            placeholder="密码",
                                            type="password",
                                            autoComplete="current-password",
                                        ),
                                    ],
                                    className="mb-3",
                                ),
                                html.Div(id="login-error", style={"minHeight": "24px", "color": "#dc3545", "fontSize": "14px"}),
                                dbc.Spinner(
                                    dbc.Button(
                                        "登 录",
                                        id="login-btn",
                                        color="primary",
                                        className="w-100",
                                        style={"borderRadius": "8px", "padding": "12px", "fontWeight": "600"},
                                    ),
                                    color="#FF364B",
                                    size="sm",
                                    spinner_class_name="me-1",
                                ),
                            ],
                            style={"padding": "20px 30px 30px"},
                        ),
                        style={
                            "maxWidth": "420px", "margin": "0 auto",
                            "borderRadius": "16px",
                            "boxShadow": "0 8px 32px rgba(0,0,0,0.12)",
                            "border": "1px solid #eee",
                        },
                    ),
                ],
                style={
                    "display": "flex", "flexDirection": "column", "justifyContent": "center",
                    "minHeight": "100vh", "padding": "40px",
                    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                },
            ),
        ]
    )
#登录逻辑的回调
@callback(
 Output("auth-token", "data", allow_duplicate=True),
    Output("auth-user", "data", allow_duplicate=True),
    Output("url", "pathname", allow_duplicate=True),
    Output("login-error", "children"),
    Output("login-btn", "disabled"),
    Input("login-btn", "n_clicks"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def handle_login(n_clicks, username, password):
    if not n_clicks:
        return dash.no_update, dash.no_update,dash.no_update,"",False
    if not username or not password:
        return dash.no_update, dash.no_update, dash.no_update, "请输入用户名和密码", False
    try:
        result = api_client.post("/api/v1/auth/login", {"username": username, "password": password})
    except Exception as e:
        return dash.no_update, dash.no_update, dash.no_update, f"登录失败，网络异常，请稍后再试", False
    if result.get("code") == 200:
        data = result["data"]
        token = data["token"]
        user_json = json.dumps({
            "username": data["username"],
            "role": data["role"],
        }, ensure_ascii=False)
        return token, user_json, "/dashboard", "", False
    return dash.no_update, dash.no_update, dash.no_update, result.get("message", "登录失败"), False