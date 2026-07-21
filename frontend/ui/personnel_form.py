"""新增/编辑人员表单页面"""

import re
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import regex
from frontend.components.sidebar import create_sidebar
from frontend.components.navbar import create_navbar
from frontend.utils import api_client
from frontend.utils.auth import save_token

# 校验规则
_RE_EMPLOYEE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,20}$")
_RE_PHONE = re.compile(r"^1[3-9]\d{9}$")
_RE_SAFE_TEXT = regex.compile(r"^[\p{L}\p{N}\s\-\_()（）]{1,50}$")
_RE_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def _build_field(label: str, field_id: str, placeholder: str = "", field_type: str = "text",
                 options: list = None, required: bool = True):
    """构建表单字段"""
    if options:
        input_el = dcc.Dropdown(
            id=f"form-{field_id}",
            options=options,
            placeholder=placeholder,
            clearable=False,
        )
    elif field_type == "date":
        input_el = dbc.Input(id=f"form-{field_id}", type="date", placeholder=placeholder)
    else:
        input_el = dbc.Input(id=f"form-{field_id}", type=field_type, placeholder=placeholder)

    return dbc.Col(
        dbc.FormFloating([
            input_el,
            html.Label(label, style={"fontSize": "12px", "color": "#888", "marginTop": "-12px"}),
        ]),
        md=6, className="mb-3",
    )


# ─── 模块级回调 — 必须在 layout() 外部，确保 import 时即注册到 Dash ───

@callback(
    Output("form-alert", "children"),
    Output("form-submit-btn", "disabled"),
    Input("form-submit-btn", "n_clicks"),
    State("form-edit-id", "data"),
    State("form-employee_id", "value"),
    State("form-name", "value"),
    State("form-gender", "value"),
    State("form-age", "value"),
    State("form-phone", "value"),
    State("form-email", "value"),
    State("form-department", "value"),
    State("form-position", "value"),
    State("form-hire_date", "value"),
    State("auth-token", "data"),
    prevent_initial_call=True,
)
def submit_form(n_clicks, edit_id, employee_id, name, gender, age, phone, email,
                department, position, hire_date, token):
    if not n_clicks:
        return "", False
    if not token:
        return dbc.Alert("请先登录", color="danger"), False

    save_token(token)

    required = {
        "人员编号": employee_id, "姓名": name, "性别": gender, "年龄": age,
        "手机号": phone, "邮箱": email, "部门": department, "职位": position,
        "入职日期": hire_date,
    }
    for field_name, value in required.items():
        if not value:
            return dbc.Alert(f"请填写{field_name}", color="warning"), False

    # 前端本地校验（格式检查）
    errors = []
    if not _RE_EMPLOYEE_ID.match(employee_id):
        errors.append("人员编号仅支持字母、数字、下划线和连字符，1-20位")
    if not _RE_SAFE_TEXT.match(name):
        errors.append("姓名格式不正确")
    if not _RE_PHONE.match(phone):
        errors.append("手机号格式不正确，请输入11位手机号")
    if not _RE_EMAIL.match(email):
        errors.append("邮箱格式不正确")
    if errors:
        return dbc.Alert("；".join(errors), color="warning"), False

    data = {
        "employee_id": employee_id, "name": name, "gender": gender,
        "age": int(age), "phone": phone, "email": email,
        "department": department, "position": position, "hire_date": hire_date,
    }

    if edit_id:
        result = api_client.put(f"/api/v1/personnel/{edit_id}", data)
    else:
        result = api_client.post("/api/v1/personnel/", data)

    if result.get("code") == 200:
        msg = "修改成功" if edit_id else "新增成功"
        return dbc.Alert(msg, color="success", dismissable=True), False
    return dbc.Alert(f"提交失败: {result.get('message')}", color="danger"), False


@callback(
    Output("form-page-title", "children"),
    Output("form-edit-id", "data"),
    Output("form-employee_id", "value"),
    Output("form-name", "value"),
    Output("form-gender", "value"),
    Output("form-age", "value"),
    Output("form-phone", "value"),
    Output("form-email", "value"),
    Output("form-department", "value"),
    Output("form-position", "value"),
    Output("form-hire_date", "value"),
    Output("selected-ids", "data", allow_duplicate=True),
    Input("selected-ids", "data"),
    State("auth-token", "data"),
    prevent_initial_call='initial_duplicate',
)
def load_edit_data(selected_ids, token):
    if not selected_ids or not token:
        return ("新增人员", None, "", "", "", "", "", "", "", "", "", [])

    edit_id = selected_ids[0]
    save_token(token)
    result = api_client.get(f"/api/v1/personnel/{edit_id}")
    if result.get("code") != 200:
        return ("编辑人员", edit_id, "", "", "", "", "", "", "", "", "", [])

    person = result["data"]
    return (
        "编辑人员",
        edit_id,
        person.get("employee_id", ""),
        person.get("name", ""),
        person.get("gender", ""),
        person.get("age", ""),
        person.get("phone", ""),
        person.get("email", ""),
        person.get("department", ""),
        person.get("position", ""),
        person.get("hire_date", ""),
        [],
    )


def layout(personnel_id: str = None, **kwargs):
    """新增/编辑页面布局"""
    return html.Div(
        [
            create_sidebar(),
            html.Div(
                [
                    create_navbar(),
                    html.Div(
                        [
                            html.H4(id="form-page-title", children="新增人员", className="mb-4"),
                            html.Div(id="form-alert"),
                            dbc.Card(
                                dbc.CardBody(
                                    [
                                        dbc.Row([
                                            _build_field("人员编号", "employee_id", "请输入人员编号"),
                                            _build_field("姓名", "name", "请输入姓名"),
                                            _build_field("性别", "gender", "", "text",
                                                         [{"label": "男", "value": "男"}, {"label": "女", "value": "女"}]),
                                            _build_field("年龄", "age", "18-65", "number"),
                                            _build_field("手机号", "phone", "11位手机号"),
                                            _build_field("邮箱", "email", "example@company.com"),
                                            _build_field("部门", "department", "请输入部门"),
                                            _build_field("职位", "position", "请输入职位"),
                                            _build_field("入职日期", "hire_date", "", "date"),
                                        ]),
                                        dbc.Row([
                                            dbc.Col(
                                                [
                                                    dbc.Button(
                                                        "提交", id="form-submit-btn", color="primary",
                                                        className="me-2", n_clicks=0,
                                                    ),
                                                    dbc.Button(
                                                        "重置", id="form-reset-btn", color="secondary",
                                                        className="me-2",
                                                    ),
                                                    dbc.Button(
                                                        "返回列表", id="form-back-btn", color="light",
                                                        href="/personnel",
                                                    ),
                                                ],
                                                className="text-center",
                                            ),
                                        ]),
                                    ],
                                ),
                                className="shadow-sm",
                            ),
                            dcc.Store(id="form-edit-id", data=personnel_id),
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
