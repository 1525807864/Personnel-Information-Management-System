"""高级搜索页面"""

from dash import html, dcc, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc

from frontend.components.sidebar import create_sidebar
from frontend.components.navbar import create_navbar
from frontend.utils import api_client

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
                            html.H4("高级搜索", className="mb-3"),
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.InputGroup([
                                                        dbc.InputGroupText("姓名"),
                                                        dbc.Input(id="sr-keyword", placeholder="模糊搜索", type="text"),
                                                    ]),
                                                    md=3, className="mb-2",
                                                ),
                                                dbc.Col(
                                                    dbc.InputGroup([
                                                        dbc.InputGroupText("部门"),
                                                        dcc.Dropdown(
                                                            id="sr-department", placeholder="选择部门",
                                                            clearable=True, style={"flex": "1"},
                                                        ),
                                                    ]),
                                                    md=3, className="mb-2",
                                                ),
                                                dbc.Col(
                                                    dbc.InputGroup([
                                                        dbc.InputGroupText("职位"),
                                                        dcc.Dropdown(
                                                            id="sr-position", placeholder="选择职位",
                                                            clearable=True, style={"flex": "1"},
                                                        ),
                                                    ]),
                                                    md=3, className="mb-2",
                                                ),
                                                dbc.Col(
                                                    [
                                                        dbc.Button(
                                                            [html.I(className="fas fa-search me-1"), "搜索"],
                                                            id="sr-search-btn", color="primary", className="me-2",
                                                        ),
                                                        dbc.Button(
                                                            [html.I(className="fas fa-redo me-1"), "重置"],
                                                            id="sr-reset-btn", color="secondary",
                                                        ),
                                                    ],
                                                    md=3, className="mb-2",
                                                ),
                                            ],
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.InputGroup([
                                                        dbc.InputGroupText("入职日期"),
                                                        dbc.Input(id="sr-start-date", type="date"),
                                                        dbc.InputGroupText("至"),
                                                        dbc.Input(id="sr-end-date", type="date"),
                                                    ]),
                                                    md=6, className="mb-2",
                                                ),
                                                dbc.Col(
                                                    dbc.InputGroup([
                                                        dbc.InputGroupText("排序"),
                                                        dcc.Dropdown(
                                                            id="sr-sort-by",
                                                            options=[
                                                                {"label": "创建时间", "value": "created_at"},
                                                                {"label": "入职日期", "value": "hire_date"},
                                                                {"label": "年龄", "value": "age"},
                                                                {"label": "姓名", "value": "name"},
                                                            ],
                                                            value="created_at",
                                                            clearable=False,
                                                            style={"flex": "1", "minWidth": "120px"},
                                                        ),
                                                        dcc.Dropdown(
                                                            id="sr-sort-order",
                                                            options=[
                                                                {"label": "降序", "value": "desc"},
                                                                {"label": "升序", "value": "asc"},
                                                            ],
                                                            value="desc",
                                                            clearable=False,
                                                            style={"flex": "1", "minWidth": "80px"},
                                                        ),
                                                    ]),
                                                    md=4, className="mb-2",
                                                ),
                                            ],
                                        ),
                                    ],
                                ),
                                className="mb-3 shadow-sm",
                            ),
                            html.Div(id="sr-result-info"),
                            html.Div(id="sr-results"),
                            html.Div(id="sr-pagination"),
                            dcc.Store(id="sr-page", data=1),
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


@callback(
    Output("sr-department", "options"),
    Output("sr-position", "options"),
    Input("sr-search-btn", "n_clicks"),
    State("auth-token", "data"),
)
def load_filter_options(n_clicks, token):
    if not token:
        return [], []
    depts = api_client.get("/api/v1/personnel/departments")
    pos = api_client.get("/api/v1/personnel/positions")
    dept_opts = [{"label": d, "value": d} for d in (depts.get("data") or [])]
    pos_opts = [{"label": p, "value": p} for p in (pos.get("data") or [])]
    return dept_opts, pos_opts


@callback(
    Output("sr-results", "children"),
    Output("sr-result-info", "children"),
    Output("sr-pagination", "children"),
    Input("sr-search-btn", "n_clicks"),
    Input("sr-page", "data"),
    State("sr-keyword", "value"),
    State("sr-department", "value"),
    State("sr-position", "value"),
    State("sr-start-date", "value"),
    State("sr-end-date", "value"),
    State("sr-sort-by", "value"),
    State("sr-sort-order", "value"),
    State("auth-token", "data"),
)
def do_search(n_clicks, page, keyword, department, position, start_date, end_date,
              sort_by, sort_order, token):
    if not token:
        return html.Div("请先登录"), "", ""

    params = {
        "page": page, "size": PAGE_SIZE,
        "sort_by": sort_by or "created_at",
        "sort_order": sort_order or "desc",
        "keyword": keyword or None,
        "department": department or None,
        "position": position or None,
        "start_date": start_date or None,
        "end_date": end_date or None,
    }

    result = api_client.post("/api/v1/personnel/search", params)
    if result.get("code") != 200:
        return html.Div(f"搜索失败: {result.get('message')}"), "", ""

    data = result["data"]
    items = data["items"]
    total = data["total"]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)

    if not items:
        return html.Div("未找到匹配的记录", className="text-center text-muted py-5"), "", ""

    columns = [
        {"name": "编号", "id": "employee_id"},
        {"name": "姓名", "id": "name"},
        {"name": "性别", "id": "gender"},
        {"name": "年龄", "id": "age"},
        {"name": "部门", "id": "department"},
        {"name": "职位", "id": "position"},
        {"name": "手机号", "id": "phone"},
        {"name": "邮箱", "id": "email"},
        {"name": "入职日期", "id": "hire_date"},
    ]

    table = dash_table.DataTable(
        columns=columns,
        data=items,
        page_size=PAGE_SIZE,
        style_table={"overflowX": "auto", "backgroundColor": "white", "borderRadius": "8px"},
        style_header={
            "backgroundColor": "#f8f9fa", "fontWeight": "bold",
            "textAlign": "center", "border": "1px solid #dee2e6",
        },
        style_cell={"textAlign": "center", "padding": "8px", "border": "1px solid #eee", "fontSize": "13px"},
    )

    info = f"共找到 {total} 条记录"
    pagination = dbc.Pagination(
        id="sr-paginator", max_value=total_pages, active_page=page,
        first_last=True, previous_next=True,
    )

    return table, info, pagination


@callback(
    Output("sr-page", "data"),
    Input("sr-paginator", "active_page"),
    prevent_initial_call=True,
)
def on_sr_page_change(active_page):
    return active_page or 1


@callback(
    Output("sr-keyword", "value"),
    Output("sr-department", "value"),
    Output("sr-position", "value"),
    Output("sr-start-date", "value"),
    Output("sr-end-date", "value"),
    Input("sr-reset-btn", "n_clicks"),
    prevent_initial_call=True,
)
def reset_search(n_clicks):
    return "", None, None, "", ""
