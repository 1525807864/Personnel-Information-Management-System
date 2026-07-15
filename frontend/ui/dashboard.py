"""主页面 - 侧边栏 + 内容区布局"""

from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

from frontend.components.sidebar import create_sidebar
from frontend.components.navbar import create_navbar


def layout(**kwargs):
    return html.Div(
        [
            create_sidebar(),
            html.Div(
                [
                    create_navbar(),
                    html.Div(
                        [
                            html.H3("欢迎使用人员信息管理系统", className="mb-4"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H5("人员管理", className="card-title"),
                                                    html.P("查看、新增、编辑和删除人员信息",
                                                           className="card-text text-muted"),
                                                    dbc.Button(
                                                        [html.I(className="fas fa-users me-2"), "进入人员列表"],
                                                        href="/personnel", color="primary",
                                                    ),
                                                ]
                                            ),
                                            className="shadow-sm",
                                        ),
                                        md=4, className="mb-3",
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H5("高级搜索", className="card-title"),
                                                    html.P("多条件组合搜索，快速定位人员",
                                                           className="card-text text-muted"),
                                                    dbc.Button(
                                                        [html.I(className="fas fa-search me-2"), "进入搜索"],
                                                        href="/search", color="info",
                                                    ),
                                                ]
                                            ),
                                            className="shadow-sm",
                                        ),
                                        md=4, className="mb-3",
                                    ),
                                    dbc.Col(
                                        dbc.Card(
                                            dbc.CardBody(
                                                [
                                                    html.H5("数据导入", className="card-title"),
                                                    html.P("批量导入 CSV/Excel 人员数据",
                                                           className="card-text text-muted"),
                                                    dbc.Button(
                                                        [html.I(className="fas fa-upload me-2"), "进入导入"],
                                                        href="/import", color="success",
                                                    ),
                                                ]
                                            ),
                                            className="shadow-sm",
                                        ),
                                        md=4, className="mb-3",
                                    ),
                                ],
                            ),
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
