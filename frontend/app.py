"""人员信息管理系统-前端入口"""

import logging
import os
import sys
import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
# 确保项目根目录在 sys.path 中（支持 python backend/main.py 和 python -m backend.main 两种启动方式）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)



#初始化Dash应用
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP,"https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"],
    title = "人员信息管理系统",
    update_title="加载中..."
)
#导入页面布局
from frontend.ui.dashboard import layout as dashboard_layout
from frontend.ui.login import layout as login_layout
from frontend.ui.personnel_list import layout as personnel_list_layout
from frontend.ui.search import layout as search_layout
from frontend.ui.import_page import layout as import_layout
from frontend.ui.personnel_form import layout as personnel_form_layout
#全局store
# ─── 全局 Stores ──────────────────────────────────────────────────────────
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="auth-token", storage_type="session"),
    dcc.Store(id="auth-user", storage_type="session"),
    dcc.Store(id="selected-ids", storage_type="session", data=[]),
    html.Div(id="page-content"),
])
PUBLIC_ROUTES = {"/login"}
PROTECTED_ROUTES = {
    "/dashboard": dashboard_layout,
    "/personnel": personnel_list_layout,
    "/search": search_layout,
    "/import": import_layout,
    "/add": personnel_form_layout,
}
#路由回调（带认证守卫）
@app.callback(
    Output("page-content","children"),
    Output("url", "pathname", allow_duplicate=True),
    Input("url","pathname"),
    State("auth-token", "data"),
    prevent_initial_call='initial_duplicate',
)
def render_page(pathname: str, token: str):
    # 公开路由直接放行
    if pathname in PUBLIC_ROUTES:
        return login_layout() if callable(login_layout) else login_layout, dash.no_update

    # 受保护路由：检查 token 是否存在
    if not token:
        return login_layout() if callable(login_layout) else login_layout, "/"

    # 已登录 → 渲染对应页面
    layout_fn = PROTECTED_ROUTES.get(pathname)
    if layout_fn:
        return layout_fn() if callable(layout_fn) else layout_fn, dash.no_update

    # 未知路径 → 默认跳转仪表盘
    return dashboard_layout(), dash.no_update

# 同步 auth Store 到内存缓存（其他模块的 api_client 依赖此缓存获取 token）
@app.callback(
    Output("auth-token", "data", allow_duplicate=True),
    Output("auth-user", "data", allow_duplicate=True),
    Input("auth-token", "data"),
    Input("auth-user", "data"),
    prevent_initial_call='initial_duplicate',
)
def sync_auth_cache(token_data, user_data):
    from frontend.utils.auth import set_cache_from_store
    set_cache_from_store(token_data, user_data)
    return dash.no_update, dash.no_update


#退出登录回调
@app.callback(
    Output("auth-token", "clear_data"),
    Output("auth-user", "clear_data"),
    Output("url", "pathname", allow_duplicate=True),
    Input("logout-btn", "n_clicks"),
    prevent_initial_call=True,
)
def handle_logout(n_clicks):
    if n_clicks:
        from frontend.utils.auth import clear_auth,get_token
        from frontend.utils.api_client import post

        #从内存缓存中取出token
        token = get_token()
        if token:
            try:
                #调用后端/logout 将token的jti写出redis黑名单
                post("/api/v1/auth/logout")
            except Exception:
                pass  #兜底机制 即使后端调用失败 不影响前端逻辑运行
        #清除python内存缓存
        clear_auth()
        #清除浏览器sessionStorage+跳转登录页面
        return True,True,"/"
    return dash.no_update,dash.no_update,dash.no_update

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=" * 60)
    print("人员信息管理系统 - 前端启动")
    print("访问地址: http://localhost:8070")
    print("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=8070)