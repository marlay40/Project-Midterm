import datetime
from pathlib import Path
import pandas as pd
import pytest
from unittest.mock import Mock, patch, PropertyMock
from decimal import Decimal
from tempfile import TemporaryDirectory
from app.calculator import Calculator
from app.calculator_repl import calculator_repl
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import LoggingObserver, AutoSaveObserver
from app.operations import OperationFactory

# Fixture to initialize Calculator with a temporary directory for file paths
@pytest.fixture
def calculator():
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        config = CalculatorConfig(base_dir=temp_path)

        # Patch properties to use the temporary directory paths
        with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
             patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
             patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
             patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:
            
            # Set return values to use paths within the temporary directory
            mock_log_dir.return_value = temp_path / "logs"
            mock_log_file.return_value = temp_path / "logs/calculator.log"
            mock_history_dir.return_value = temp_path / "history"
            mock_history_file.return_value = temp_path / "history/calculator_history.csv"
            
            # Return an instance of Calculator with the mocked config
            yield Calculator(config=config)

# Test Calculator Initialization

def test_calculator_initialization(calculator):
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []
    assert calculator.operation_strategy is None

# Test Logging Setup

@patch('app.calculator.logging.info')
def test_logging_setup(logging_info_mock):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file:
        mock_log_dir.return_value = Path('/tmp/logs')
        mock_log_file.return_value = Path('/tmp/logs/calculator.log')
        
        # Instantiate calculator to trigger logging
        calculator = Calculator(CalculatorConfig())
        logging_info_mock.assert_any_call("Calculator initialized with configuration")

# Test Adding and Removing Observers

def test_add_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    assert observer in calculator.observers

def test_remove_observer(calculator):
    observer = LoggingObserver()
    calculator.add_observer(observer)
    calculator.remove_observer(observer)
    assert observer not in calculator.observers

# Test Setting Operations

def test_set_operation(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    assert calculator.operation_strategy == operation

# Test Performing Operations

def test_perform_operation_addition(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    result = calculator.perform_operation(2, 3)
    assert result == Decimal('5')

def test_perform_operation_validation_error(calculator):
    calculator.set_operation(OperationFactory.create_operation('add'))
    with pytest.raises(ValidationError):
        calculator.perform_operation('invalid', 3)

def test_perform_operation_operation_error(calculator):
    with pytest.raises(OperationError, match="No operation set"):
        calculator.perform_operation(2, 3)

# Test Undo/Redo Functionality

def test_undo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    assert calculator.history == []

def test_redo(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.undo()
    calculator.redo()
    assert len(calculator.history) == 1

# Test History Management

@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history(mock_to_csv, calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.save_history()
    mock_to_csv.assert_called_once()

# Test that load_history rebuilds calculation history from a CSV file.
@patch('app.calculator.pd.read_csv')
def test_load_history_success(mock_read_csv):
    with patch.object(CalculatorConfig, 'log_dir', new_callable=PropertyMock) as mock_log_dir, \
         patch.object(CalculatorConfig, 'log_file', new_callable=PropertyMock) as mock_log_file, \
         patch.object(CalculatorConfig, 'history_dir', new_callable=PropertyMock) as mock_history_dir, \
         patch.object(CalculatorConfig, 'history_file', new_callable=PropertyMock) as mock_history_file:

        temp_path = Path('/tmp')
        mock_log_dir.return_value = temp_path / "logs"
        mock_log_file.return_value = temp_path / "logs/calculator.log"
        mock_history_dir.return_value = temp_path / "history"

        fake_history_file = Mock()
        fake_history_file.exists.return_value = True
        mock_history_file.return_value = fake_history_file

        mock_read_csv.return_value = pd.DataFrame({
            'operation': ['Addition'],
            'operand1': ['2'],
            'operand2': ['3'],
            'result': ['5'],
            'timestamp': [datetime.datetime.now().isoformat()]
        })

        calc = Calculator(CalculatorConfig(base_dir=temp_path))
        calc.load_history()

        assert len(calc.history) == 1

# Undo returns False when empty

def test_undo_when_empty_returns_false():
    calc = Calculator()
    assert calc.undo() is False        
            
# Test Clearing History

def test_clear_history(calculator):
    operation = OperationFactory.create_operation('add')
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)
    calculator.clear_history()
    assert calculator.history == []
    assert calculator.undo_stack == []
    assert calculator.redo_stack == []

# Test REPL Commands (using patches for input/output handling)
@patch('builtins.input', side_effect=['exit'])
@patch('builtins.print')
def test_calculator_repl_exit(mock_print, mock_input):
    with patch('app.calculator.Calculator.save_history') as mock_save_history:
        calculator_repl()

        mock_save_history.assert_called_once()

        printed = " ".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
        assert "history saved" in printed.lower()
        assert "goodbye" in printed.lower()

# Test that the REPL help command prints available commands.
@patch('builtins.input', side_effect=['help', 'exit'])
@patch('builtins.print')
def test_calculator_repl_help(mock_print, mock_input):
    calculator_repl()

    printed = " ".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "available commands" in printed.lower()

@patch('builtins.input', side_effect=['add', '2', '3', 'exit'])
@patch('builtins.print')
def test_calculator_repl_addition(mock_print, mock_input):
    calculator_repl()
    mock_print.assert_any_call("\nResult: 5")

# Test that observers are notified after a calculation is performed.
def test_notify_observers_calls_update(calculator):
    observer = Mock()
    calculator.add_observer(observer)

    operation = OperationFactory.create_operation("add")
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)

    observer.update.assert_called_once()


# Test that history can be returned as a pandas DataFrame.
def test_get_history_dataframe_returns_dataframe(calculator):
    operation = OperationFactory.create_operation("add")
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)

    df = calculator.get_history_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert list(df.columns) == ["operation", "operand1", "operand2", "result", "timestamp"]


# Test that show_history returns formatted calculation strings.
def test_show_history_returns_formatted_strings(calculator):
    operation = OperationFactory.create_operation("add")
    calculator.set_operation(operation)
    calculator.perform_operation(2, 3)

    history_output = calculator.show_history()

    assert isinstance(history_output, list)
    assert len(history_output) == 1
    assert "2" in history_output[0]
    assert "3" in history_output[0]
    assert "5" in history_output[0]


# Test that redo returns False when there is nothing to redo.
def test_redo_when_empty_returns_false():
    calc = Calculator()
    assert calc.redo() is False


# Test that save_history still writes a CSV when history is empty.
@patch('app.calculator.pd.DataFrame.to_csv')
def test_save_history_with_empty_history(mock_to_csv, calculator):
    calculator.save_history()
    mock_to_csv.assert_called_once()
