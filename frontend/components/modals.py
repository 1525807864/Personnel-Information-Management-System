"""弹窗组件"""
import dash_bootstrap_components as dbc
from dash import html

def create_confirm_modal(modal_id:str,title:str,message:str)->dbc.Modal:
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle(title)),
            dbc.ModalBody(message),
            dbc.ModalFooter(
                dbc.Button("取消",id=f"{modal_id}-cancel",color="Dark",className="ms-auto"),
                dbc.Button("确认", id=f"{modal_id}-confirm", color="primary",className="ms-auto")
            ),
        ],
        id = modal_id,
        is_open = False,
    )
def create_alert(message:str,color:str="success",alert_id:str="alert")->dbc.Alert:
    return dbc.Alert(
    [
        html.H4("新的一条消息", className="alert-heading"),
        html.P(
            message = message,
            id = alert_id,
            color=color,
            dismissable = True,
            is_open = bool(message),
            style={"marginTop":"12px"}
        ),
        html.Hr(),
    ]
)