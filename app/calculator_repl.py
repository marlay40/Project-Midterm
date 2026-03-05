########################
# Calculator REPL       #
########################

from decimal import Decimal
import logging

from app.calculator import Calculator
from app.exceptions import OperationError, ValidationError
from app.history import AutoSaveObserver, LoggingObserver
from app.operations import OperationFactory
from colorama import init, Fore, Back, Style

init(autoreset=True)

def calculator_repl():
    """
    Command-line interface for the calculator.

    Implements a Read-Eval-Print Loop (REPL) that continuously prompts the user
    for commands, processes arithmetic operations, and manages calculation history.
    """
    try:
        # Initialize the Calculator instance
        calc = Calculator()

        # Register observers for logging and auto-saving history
        calc.add_observer(LoggingObserver())
        calc.add_observer(AutoSaveObserver(calc))

        print(Fore.MAGENTA + "Calculator started. Type 'help' for commands.")

        while True:
            try:
                # Prompt the user for a command
                command = input(Fore.BLUE + "\nEnter command: ").lower().strip()

                if command == 'help':
                    # Display available commands
                    print(Fore.YELLOW + "\nAvailable commands:")
                    print(Fore.RED + "  add, subtract, multiply, divide, power, root, modulus, int_divide, percent, abs_diff - Perform calculations")
                    print(Fore.RED + "  clear - Clear calculation history")
                    print(Fore.RED + "  undo - Undo the last calculation")
                    print(Fore.GREEN + "  redo - Redo the last undone calculation")
                    print(Fore.GREEN + "  save - Save calculation history to file")
                    print(Fore.GREEN + "  load - Load calculation history from file")
                    print(Fore.BLUE + "  exit - Exit the calculator")
                    continue

                if command == 'exit':
                    # Attempt to save history before exiting
                    try:
                        calc.save_history()
                        print(Fore.MAGENTA + "History saved successfully.")
                    except Exception as e:  # pragma: no cover
                        print(f"Warning: Could not save history: {e}") 
                    print(Fore.LIGHTBLUE_EX + "Goodbye!")
                    break

                if command == 'history':
                    # Display calculation history
                    history = calc.show_history()
                    if not history:
                        print(Fore.MAGENTA + "No calculations in history")
                    else:
                        print(Fore.LIGHTBLUE_EX + "\nCalculation History:")
                        for i, entry in enumerate(history, 1):
                            print(f"{i}. {entry}")
                    continue

                if command == 'clear':
                    # Clear calculation history
                    calc.clear_history()
                    print(Fore.LIGHTRED_EX + "History cleared")
                    continue

                if command == 'undo':
                    # Undo the last calculation
                    if calc.undo():
                        print("Operation undone")
                    else:
                        print("Nothing to undo")
                    continue

                if command == 'redo':
                    # Redo the last undone calculation
                    if calc.redo():
                        print("Operation redone")
                    else:
                        print("Nothing to redo")
                    continue

                if command == 'save':
                    # Save calculation history to file
                    try:
                        calc.save_history()
                        print("History saved successfully")
                    except Exception as e:  # pragma: no cover
                        print(f"Error saving history: {e}")  
                    continue

                if command == 'load':
                    # Load calculation history from file
                    try:
                        calc.load_history()
                        print("History loaded successfully")
                    except Exception as e:  # pragma: no cover
                        print(f"Error loading history: {e}")  
                    continue

                if command in ['add', 'subtract', 'multiply', 'divide', 'power', 'root', 'modulus', 'int_divide', 'percent', 'abs_diff']:
                    # Perform the specified arithmetic operation
                    try:
                        print("\nEnter numbers (or 'cancel' to abort):")
                        a = input("First number: ")
                        if a.lower() == 'cancel':
                            print("Operation cancelled")
                            continue
                        b = input("Second number: ")
                        if b.lower() == 'cancel':
                            print("Operation cancelled")
                            continue

                        # Create the appropriate operation instance using the Factory pattern
                        operation = OperationFactory.create_operation(command)
                        calc.set_operation(operation)

                        # Perform the calculation
                        result = calc.perform_operation(a, b)

                        # Normalize the result if it's a Decimal
                        if isinstance(result, Decimal):
                            result = result.normalize()

                        print(f"\nResult: {result}")
                    except (ValidationError, OperationError) as e:  # pragma: no cover
                        # Handle known exceptions related to validation or operation errors
                        print(f"Error: {e}")  
                    except Exception as e:  # pragma: no cover
                        # Handle any unexpected exceptions
                        print(f"Unexpected error: {e}")  
                    continue

                # Handle unknown commands
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")

            except KeyboardInterrupt:  # pragma: no cover
                # Handle Ctrl+C interruption gracefully
                print("\nOperation cancelled")  
                continue  
            except EOFError:  # pragma: no cover
                # Handle end-of-file (e.g., Ctrl+D) gracefully
                print("\nInput terminated. Exiting...")  
                break  
            except Exception as e:  # pragma: no cover
                # Handle any other unexpected exceptions
                print(f"Error: {e}")  
                continue  

    except Exception as e:  # pragma: no cover
        # Handle fatal errors during initialization
        print(f"Fatal error: {e}")  
        logging.error(f"Fatal error in calculator REPL: {e}")  
        raise  
