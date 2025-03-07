import pytest
from PyQt6.QtWidgets import QApplication
from main import App

@pytest.fixture
def app(qtbot):
    test_app = App()
    qtbot.addWidget(test_app)
    return test_app

def test_login_button_click(app, mocker, qtbot):
    mocker.patch.object(app.kream_macro, 'login', return_value=True)
    
    app.email_input.setText("test@example.com")
    app.pw_input.setText("password")

    qtbot.mouseClick(app.login_button, 1)
    
    assert app.start_button.isEnabled()  # 로그인 성공하면 매크로 시작 버튼 활성화