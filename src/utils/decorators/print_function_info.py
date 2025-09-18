from functools import wraps


def print_function_args(additional_info=None):
    """
    함수의 위치인자, 키워드인자, 추가정보를 출력하는 데코레이터
    print_function_args() 형태로 사용할 수 있음

    Args:
        additional_info (Any, optional): 아무 형태로 추가적인 정보를 구성해 로그에 추가할 수 있음. Defaults to None.

    Examples:
    >>> @print_function_args()
    ... def dummy_function(name, age):
    ...     pass
    >>> dummy_function("John", age=25)
    {'excuting_function': 'dummy_function', 'positional_arguments': ('John',), 'keyword_arguments': {'age': 25}, 'additional_info': None}}
    >>>
    >>> @print_function_args("This is a dummy function")
    ... def dummy_function(name, age):
    ...     pass
    >>> dummy_function("John", age=25)
    >>> {'excuting_function': 'dummy_function', 'positional_arguments': ('John',), 'keyword_arguments': {'age': 25}, 'additional_info': 'This is a dummy function'}
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 함수명, 위치인자, 키워드인자, 추가정보를 딕셔너리로 만들어 출력
            log_dict = dict(
                excuting_function=func.__name__,
                positional_arguments=args,
                keyword_arguments=kwargs,
                additional_info=additional_info,
            )
            print(log_dict)

            # 함수 실행
            result = func(*args, **kwargs)

            return result

        return wrapper

    return decorator


def print_function_result(additional_info=None):
    """
    함수의 결과값, 추가정보를 출력하는 데코레이터
    print_function_result() 형태로 사용할 수 있음

    Args:
        additional_info (Any, optional): 아무 형태로 추가적인 정보를 구성해 로그에 추가할 수 있음. Defaults to None.

    Examples:
    >>> @print_function_result()
    ... def dummy_function(name, age):
    ...     pass
    >>> dummy_function("John", age=25)
    {'excuting_function': 'dummy_function', 'result': None, 'additional_info': None}
    >>>
    >>> @print_function_result("This is a dummy function")
    ... def dummy_function(name, age):
    ...     return name, age
    >>> dummy_function("John", age=25)
    >>> {'excuting_function': 'dummy_function', 'result': ('John', 25), 'additional_info': 'This is a dummy function'}
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 함수 실행
            result = func(*args, **kwargs)

            log_dict = dict(
                excuting_function=func.__name__,
                result=result,
                additional_info=additional_info,
            )
            print(log_dict)

            return result

        return wrapper

    return decorator
