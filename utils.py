from dash import callback_context

def log_callback_trigger(func):
    def wrapper(*args, **kwargs):
        # Get the name of the function
        function_name = func.__name__

        # Get the triggered context
        triggered = callback_context.triggered

        # Print the log message
        print(f"The function {function_name} was triggered by {triggered}")

        # Call the original function
        return func(*args, **kwargs)

    return wrapper