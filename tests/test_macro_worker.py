import pytest
from PyQt6.QtCore import QThread
from macro_worker import MacroWorker
from kream_macro import KreamMacro

@pytest.fixture
def mock_kream_macro(mocker):
    mock_macro = mocker.Mock(spec=KreamMacro)
    return mock_macro

@pytest.fixture
def macro_worker(mock_kream_macro):
    return MacroWorker(mock_kream_macro)

def test_macro_worker_run(mocker, macro_worker):
    mock_log = mocker.patch.object(macro_worker, 'log_message')
    macro_worker.is_running = False
    macro_worker.run()
    mock_log.emit.assert_called_with("[00:00:00] 매크로 중지됨", False)