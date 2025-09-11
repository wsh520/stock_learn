def safe_divide(x, y):
    """This function divides two numbers"""
    try:
        return x / y
    except ZeroDivisionError:
        return "Error: Division by zero"

# 练习2
def parse_and_divide(x, y):
    """This function parses two numbers and divides them"""
    try:
        x = int(x)
        y = int(y)
        return x / y
    except ValueError:
        return "Error: 输入必须是数字"
    except ZeroDivisionError:
        return "Error: 不能除以0"
    finally:
        print("计算结束")

# 练习3
class NegativeValueError(Exception):
    """自定义异常类"""
    pass
def check_negative_value(x):
    """This function checks if a number is negative"""
    if x < 0:
        raise NegativeValueError("Error: 输入的值不能为负数")
    return x

# 练习4
def calculate_square_root(x):
    """This function calculates the square root of a number"""
    try:
        if x < 0:
            raise NegativeValueError("Error: 输入的值不能为负数")
        return x ** 0.5
    except NegativeValueError as e:
        raise RuntimeError("平方根计算失败") from e

if __name__ == "__main__":
    # print(safe_divide(10, 2))  # Output: 5.0
    # print(safe_divide(10, 0))  # Output: Error: Division by zero
    calculate_square_root(-1)  # Output: Error: 平方根计算失败