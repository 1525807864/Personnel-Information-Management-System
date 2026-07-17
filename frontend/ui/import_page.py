"""数据导入页面"""
import base64
import io
from datetime import datetime

from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc

from frontend.components.sidebar import create_sidebar
from frontend.components.navbar import create_navbar
from frontend.utils import api_client


def layout(**kwargs):
    return html.Div(
        [
            create_sidebar(),
            html.Div(
                [
                    create_navbar(),
                    html.Div(
                        [
                            html.H4("数据导入", className="mb-3"),
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        html.H5("上传文件", className="mb-3"),
                                        html.P("支持 CSV (.csv) 和 Excel (.xlsx/.xls) 格式", className="text-muted"),
                                        html.P("列名支持中文：人员编号、姓名、性别、年龄、手机号、邮箱、部门、职位、入职日期",
                                               className="text-muted small"),
                                        dcc.Upload(
                                            id="import-upload",
                                            children=html.Div([
                                                html.I(className="fas fa-cloud-upload-alt",
                                                       style={"fontSize": "36px", "color": "#667eea"}),
                                                html.P("拖拽文件到此处或点击选择文件",
                                                       className="mt-3 text-muted"),
                                            ]),
                                            style={
                                                "width": "100%", "height": "120px",
                                                "lineHeight": "40px", "borderWidth": "2px",
                                                "borderStyle": "dashed", "borderRadius": "12px",
                                                "textAlign": "center", "cursor": "pointer",
                                                "borderColor": "#667eea", "backgroundColor": "#f8f9ff",
                                            },
                                            multiple=False,
                                        ),
                                        html.Div(id="import-filename", className="mt-2"),
                                        html.Div(
                                            [
                                                html.Label("重复处理策略:", className="me-2", style={"fontWeight": "600"}),
                                                dcc.RadioItems(
                                                    id="import-strategy",
                                                    options=[
                                                        {"label": "跳过重复数据 (skip)", "value": "skip"},
                                                        {"label": "覆盖已有数据 (overwrite)", "value": "overwrite"},
                                                        {"label": "遇到重复终止 (terminate)", "value": "terminate"},
                                                    ],
                                                    value="skip",
                                                    inline=True,
                                                ),
                                            ],
                                            className="mt-3",
                                        ),
                                        dbc.Button(
                                            [html.I(className="fas fa-upload me-1"), "开始导入"],
                                            id="import-btn", color="primary", className="mt-3",
                                            disabled=True,
                                        ),
                                    ],
                                ),
                                className="shadow-sm mb-3",
                            ),
                            html.Div(id="import-progress"),
                            html.Div(id="import-result"),
                            dcc.Store(id="import-file-content"),
                            dcc.Store(id="import-filename-store"),
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
    Output("import-filename", "children"),
    Output("import-file-content", "data"),
    Output("import-filename-store", "data"),
    Output("import-btn", "disabled"),
    Input("import-upload", "contents"),
    State("import-upload", "filename"),
)
def handle_upload(contents, filename):
    if not contents or not filename:
        return "", None, None, True

    _, content_string = contents.split(",")
    return (
        dbc.Alert(f"已选择文件: {filename}", color="info"),
        content_string,
        filename,
        False,
    )


@callback(
    Output("import-progress", "children"),
    Output("import-result", "children"),
    Input("import-btn", "n_clicks"),
    State("import-file-content", "data"),
    State("import-filename-store", "data"),
    State("import-strategy", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True,
)
def do_import(n_clicks, content_b64, filename, strategy, token):
    if not n_clicks or not content_b64 or not token:
        return "", ""

    try:
        file_content = base64.b64decode(content_b64)
    except Exception as e:
        return "", dbc.Alert(f"文件解码失败: {e}", color="danger")

    result = api_client.upload_file(
        "/api/v1/import/",
        file_content, filename,
        {"strategy": strategy},
    )

    if result.get("code") != 200:
        return "", dbc.Alert(f"导入失败: {result.get('message')}", color="danger")

    data = result["data"]
    stats = [
        dbc.Card(
            dbc.CardBody([
                html.H5(f"共 {data['total_rows']} 条", className="card-title"),
                html.P("总计行数", className="card-text text-muted"),
            ]),
            className="shadow-sm",
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5(f"成功 {data['success_count']} 条", className="card-title text-success"),
                html.P("成功导入", className="card-text text-muted"),
            ]),
            className="shadow-sm",
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5(f"失败 {data['failed_count']} 条", className="card-title text-danger"),
                html.P("导入失败", className="card-text text-muted"),
            ]),
            className="shadow-sm",
        ),
        dbc.Card(
            dbc.CardBody([
                html.H5(f"重复 {data['duplicate_count']} 条", className="card-title text-warning"),
                html.P("重复数据", className="card-text text-muted"),
            ]),
            className="shadow-sm",
        ),
    ]

    error_section = None
    if data.get("error_messages"):
        error_section = dbc.Card(
            dbc.CardBody([
                html.H6("错误详情:"),
                html.Ul([html.Li(msg) for msg in data["error_messages"]]),
            ]),
            className="mt-3 border-danger",
        )

    return "", html.Div([
        html.H5("导入结果", className="mb-3"),
        dbc.Row([dbc.Col(s, md=3) for s in stats]),
        error_section or "",
    ])
