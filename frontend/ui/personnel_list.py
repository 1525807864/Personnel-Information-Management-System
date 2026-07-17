"""人员列表页面 - 表格展示+分页+操作按钮"""
import dash
from dash import html, dcc, Input, Output, State, callback, dash_table, callback_context
import dash_bootstrap_components as dbc
from frontend.components.sidebar import create_sidebar
from frontend.components.navbar import create_navbar
from frontend.utils import api_client
from frontend.utils.auth import save_token

PAGE_SIZE = 20


def layout(**kwargs):
    return html.Div(
        [
            create_sidebar(),
            html.Div(
                [
                    create_navbar(),
                    html.Div(
                        [
                            html.H4("人员信息列表", className="mb-3"),
                            # 顶部搜索和按钮行
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.InputGroup([
                                            dbc.Input(
                                                id="pl-search-input", placeholder="搜索姓名或编号...",
                                                type="text",
                                            ),
                                            dbc.Button("搜索", id="pl-search-btn", color="primary"),
                                        ]),
                                        md=5,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Button(
                                                [html.I(className="fas fa-plus me-1"), "新增人员"],
                                                id="pl-add-btn", color="success", className="me-2",
                                            ),
                                            dbc.Button(
                                                [html.I(className="fas fa-trash me-1"), "批量删除"],
                                                id="pl-batch-delete-btn", color="danger",
                                                className="me-2", disabled=True,
                                            ),
                                            dbc.Button(
                                                [html.I(className="fas fa-eye me-1"),"查看详情"],
                                                id="pl-view-detail-btn",color="info",
                                                className="me-2",disabled=True
                                            ),
                                            dbc.Button(
                                                [html.I(className="fas fa-edit me-1"), "编辑选中"],
                                                id="pl-edit-selected-btn", color="warning",
                                                className="me-2", disabled=True,
                                            ),
                                        ],
                                        md=7, className="text-end",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Spinner(
                                [
                                    # 数据表格（静态骨架，load_table 回调动态填充 data 和 columns）
                                    dash_table.DataTable(
                                        id="pl-data-table",
                                        columns=[],
                                        data=[],
                                        page_size=PAGE_SIZE,
                                        row_selectable="multi",
                                        selected_rows=[],
                                        style_table={"overflowX": "auto", "backgroundColor": "white",
                                                     "borderRadius": "8px"},
                                        style_header={
                                            "backgroundColor": "#f8f9fa", "fontWeight": "bold",
                                            "textAlign": "center", "border": "1px solid #dee2e6",
                                        },
                                        style_cell={
                                            "textAlign": "center", "padding": "10px 8px",
                                            "border": "1px solid #eee", "fontSize": "14px",
                                        },
                                        style_data_conditional=[
                                            {"if": {"row_index": "odd"}, "backgroundColor": "#fcfcfd"},
                                        ],
                                        sort_action="native",
                                        filter_action="native",
                                    ),
                                    # 分页
                                    html.Div(id="pl-pagination", className="mt-3"),
                                ],
                                color="primary"
                            ),

                            # 状态提示
                            html.Div(id="pl-status"),
                            # 删除确认弹窗
                            dbc.Modal(
                                [
                                    dbc.ModalHeader("确认删除"),
                                    dbc.ModalBody(id="pl-delete-message"),
                                    dbc.ModalFooter([
                                        dbc.Button("取消", id="pl-delete-cancel", className="ms-auto",
                                                   color="secondary"),
                                        dbc.Button("确认删除", id="pl-delete-confirm", color="danger"),
                                    ]),
                                ],
                                id="pl-delete-modal", is_open=False,
                            ),
                            # 人员详情弹窗
                            dbc.Modal(
                                [
                                    dbc.ModalHeader("人员详情"),
                                    dbc.ModalBody(id="pl-detail-body"),
                                    dbc.ModalFooter(
                                        dbc.Button("关闭", id="pl-detail-close", className="ms-auto", color="secondary"),
                                    ),
                                ],
                                id="pl-detail-modal", is_open=False, size="lg",
                            ),
                            # 隐藏存储
                            dcc.Store(id="pl-current-page", data=1),
                            dcc.Store(id="pl-delete-target", data=None),
                            # 刷新触发器：删除成功后 +1 触发 load_table 重新加载
                            dcc.Store(id="pl-refresh-trigger", data=0),
                        ],
                        style={
                            "marginLeft": "220px", "marginTop": "56px",
                            "padding": "24px", "minHeight": "calc(100vh - 56px)",
                            "backgroundColor": "#f5f6fa",
                        },
                    ),
                ],
            ),
        ]
    )


# =============================================================================
# 回调函数（模块级别，所有回调扁平化，不再嵌套在 load_table 内部）
# =============================================================================

@callback(
    Output("pl-data-table", "data"),
    Output("pl-data-table", "columns"),
    Output("pl-pagination", "children"),
    Output("pl-batch-delete-btn", "disabled"),
    Output("pl-status", "children"),
    Input("pl-current-page", "data"),
    Input("pl-search-btn", "n_clicks"),
    Input("pl-refresh-trigger", "data"),
    State("pl-search-input", "value"),
    State("auth-token", "data"),
)
def load_table(page, n_clicks, _refresh, keyword, token):
    """填充表格数据和分页"""
    if not token:
        return [], [], "", True, "请先登录"

    save_token(token)

    params = {"page": page, "size": PAGE_SIZE}
    if keyword:
        params["keyword"] = keyword

    result = api_client.get("/api/v1/personnel/", params)
    if result.get("code") != 200:
        return [], [], "", True, f"加载失败: {result.get('message')}"

    data = result["data"]
    items = data.get("items", [])
    total = data.get("total", 0)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    columns = [
        {"name": "ID", "id": "id", "type": "numeric"},
        {"name": "人员编号", "id": "employee_id"},
        {"name": "姓名", "id": "name"},
        {"name": "性别", "id": "gender"},
        {"name": "年龄", "id": "age", "type": "numeric"},
        {"name": "部门", "id": "department"},
        {"name": "职位", "id": "position"},
        {"name": "手机号", "id": "phone"},
        {"name": "入职日期", "id": "hire_date"},
    ]

    pagination = dbc.Row(
        [
            dbc.Col(
                dbc.Pagination(
                    id="pl-pagination-component",
                    max_value=total_pages,
                    active_page=page,
                    first_last=True,
                    previous_next=True,
                    fully_expanded=False,
                ),
                className="text-center",
            ),
        ],
    )

    if not items:
        return [], columns, pagination, True, "暂无数据"

    return items, columns, pagination, False, f"共 {total} 条记录，第 {page}/{total_pages} 页"


# 分页点击
@callback(
    Output("pl-current-page", "data"),
    Input("pl-pagination-component", "active_page"),
)
def on_page_change(active_page):
    if active_page:
        return active_page
    return 1


# 新增人员按钮 → 跳转 /add
@callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("pl-add-btn", "n_clicks"),
    prevent_initial_call=True,
)
def go_to_add_page(n_clicks):
    if n_clicks:
        return "/add"
    return dash.no_update



# 删除确认弹窗
@callback(
    Output("pl-delete-modal", "is_open"),
    Output("pl-delete-target", "data"),
    Output("pl-delete-message", "children"),
    Input("pl-batch-delete-btn", "n_clicks"),
    Input("pl-delete-cancel", "n_clicks"),
    State("pl-data-table", "selected_rows"),
    State("pl-data-table", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True,
)
def toggle_delete_modal(batch_clicks, cancel_clicks,
                        selected_rows, table_data, token):
    ctx = callback_context
    if not ctx.triggered or not ctx.triggered[0]:
        return False, None, ""

    trigger = ctx.triggered[0]["prop_id"]

    if "pl-delete-cancel" in trigger:
        return False, None, ""

    # 批量删除：通过表格多选勾选行 + 点击"批量删除"按钮触发
    if "pl-batch-delete-btn" in trigger:
        if not selected_rows or not table_data:
            return False, None, ""
        ids = [table_data[i]["id"] for i in selected_rows if i < len(table_data)]
        if not ids:
            return False, None, ""
        return True, {"ids": ids}, f"确定要删除选中的 {len(ids)} 条人员信息吗？"

    return False, None, ""


# 执行删除
@callback(
    Output("pl-refresh-trigger", "data"),
    Output("pl-delete-modal", "is_open", allow_duplicate=True),
    Output("pl-status", "children", allow_duplicate=True),
    Input("pl-delete-confirm", "n_clicks"),
    State("pl-delete-target", "data"),
    State("pl-refresh-trigger", "data"),
    State("auth-token", "data"),
    prevent_initial_call=True,
)
def do_delete(n_clicks, target, refresh_count, token):
    if not n_clicks or not target:
        return dash.no_update, dash.no_update, dash.no_update

    save_token(token)

    ids = target.get("ids", [])
    if not ids:
        return dash.no_update, False, dash.no_update

    if len(ids) == 1:
        result = api_client.delete(f"/api/v1/personnel/{ids[0]}")
    else:
        result = api_client.post("/api/v1/personnel/batch", ids)

    if result.get("code") == 200:
        return (refresh_count or 0) + 1, False, dbc.Alert(
            result.get("message", "删除成功"), color="success", dismissable=True,
        )
    return dash.no_update, False, dbc.Alert(
        result.get("message", "删除失败"), color="danger", dismissable=True,
    )


# 选中行 → 启用/禁用查看、编辑、删除按钮
@callback(
    Output("pl-view-detail-btn", "disabled"),
    Output("pl-edit-selected-btn", "disabled"),
    Output("pl-batch-delete-btn", "disabled", allow_duplicate=True),
    Input("pl-data-table", "selected_rows"),
    prevent_initial_call='initial_duplicate',
)
def toggle_action_buttons(selected_rows):
    """勾选行时启用操作按钮，未勾选时禁用"""
    if not selected_rows or len(selected_rows) == 0:
        return True, True, True
    return False, False, False


# 查看详情 → 打开弹窗
@callback(
    Output("pl-detail-modal", "is_open"),
    Output("pl-detail-body", "children"),
    Input("pl-view-detail-btn", "n_clicks"),
    State("pl-data-table", "selected_rows"),
    State("pl-data-table", "data"),
    prevent_initial_call=True,
)
def view_personnel_detail(n_clicks, selected_rows, table_data):
    """展示选中人员的完整信息"""
    if not n_clicks or not selected_rows or not table_data:
        return False, ""

    row = table_data[selected_rows[0]]
    body = dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("基本信息"),
            dbc.CardBody([
                html.P([html.Strong("人员编号："), str(row.get("employee_id", ""))]),
                html.P([html.Strong("姓名："), str(row.get("name", ""))]),
                html.P([html.Strong("性别："), str(row.get("gender", ""))]),
                html.P([html.Strong("年龄："), str(row.get("age", ""))]),
                html.P([html.Strong("手机号："), str(row.get("phone", ""))]),
                html.P([html.Strong("邮箱："), str(row.get("email", ""))]),
            ]),
        ]), md=6),
        dbc.Col(dbc.Card([
            dbc.CardHeader("工作信息"),
            dbc.CardBody([
                html.P([html.Strong("部门："), str(row.get("department", ""))]),
                html.P([html.Strong("职位："), str(row.get("position", ""))]),
                html.P([html.Strong("入职日期："), str(row.get("hire_date", ""))]),
                html.P([html.Strong("创建时间："), str(row.get("created_at", ""))]),
                html.P([html.Strong("更新时间："), str(row.get("updated_at", ""))]),
            ]),
        ]), md=6),
    ])
    return True, body


# 关闭详情弹窗
@callback(
    Output("pl-detail-modal", "is_open", allow_duplicate=True),
    Input("pl-detail-close", "n_clicks"),
    prevent_initial_call=True,
)
def close_detail_modal(n_clicks):
    """关闭详情弹窗"""
    if n_clicks:
        return False
    return dash.no_update


# 编辑选中 → 将人员 ID 写入 Store，跳转 /add
@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("selected-ids", "data", allow_duplicate=True),
    Input("pl-edit-selected-btn", "n_clicks"),
    State("pl-data-table", "selected_rows"),
    State("pl-data-table", "data"),
    prevent_initial_call=True,
)
def edit_selected_personnel(n_clicks, selected_rows, table_data):
    """将选中的人员 ID 存入全局 Store，跳转到编辑页面"""
    if not n_clicks or not selected_rows or not table_data:
        return dash.no_update, dash.no_update

    row = table_data[selected_rows[0]]
    return "/add", [row["id"]]
