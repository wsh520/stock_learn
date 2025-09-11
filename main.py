# This is a sample Python script.
import requests

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# 计算年龄
def calculate_age():
    year = int(input("请输入你的出生年份："))
    current_year = 2025
    print("你今年的年龄是：", current_year - year)


# 输入一个数字，判断它是否为偶数且大于 50。
def is_even_and_greater_than_50(num):
    if num % 2 == 0 and num > 50:
        return True
    else:
        return False


# 打印所有 1~100 中既是 3 的倍数又是 5 的倍数的数。
def print_numbers():
    for i in range(1, 101):
        if i % 3 == 0 and i % 5 == 0:
            print(i)


# 编写一个猜数字游戏，要求用户反复输入直到猜中为止。
def guess_number():
    import random
    number = random.randint(1, 100)
    print("欢迎来到猜数字游戏！目标数字为： ", number)
    while True:
        guess = int(input("请输入你猜的数字："))
        if guess == number:
            print("恭喜你猜对了！")
            break
        else:
            print("猜错了，请再试一次。")


# 🎯 编程练习题（请在下方编写解答）

# 练习题 1：定义一个函数 compare_length(str1, str2)，比较两个字符串长度，返回更长的字符串。
def compare_length(str1, str2):
    if len(str1) > len(str2):
        return str1
    else:
        return str2


# 练习题 2：定义一个函数 average_score(*scores)，接收多个成绩，返回平均分（保留两位小数）。
def average_score(*scores):
    return round(sum(scores) / len(scores), 2)


# 练习题 3：定义一个函数 user_info(name, **kwargs)，接收用户名及任意个额外信息，并打印所有信息。
def user_info(name, **kwargs):
    print("用户名：", name)
    for key, value in kwargs.items():
        print(key, ":", value)


# 练习题 4：定义一个函数 calc(op, *args)，支持加、减、乘、除操作。
def calc(op, *args):
    if op == "+":
        return sum(args)
    elif op == "-":
        return args[0] - sum(args[1:])
    elif op == "*":
        result = 1
        for i in args:
            result *= i
        return result
    elif op == "/":
        result = args[0]
        for i in args[1:]:
            result /= i
        return result


# 编写一个程序，输入一个数字，判断其是否为质数。
def is_prime(num):
    if num == 2:
        return True
    if num < 2:
        return False
    for i in range(2, num):
        if num % i == 0:
            return False


# 使用 while 循环，打印1~50中所有能被7整除的数。
def print_divisible_by_7():
    i = 1
    while i <= 50:
        if i % 7 == 0:
            print(i)
        i += 1


# 使用 for 循环和 break，找出100以内第一个能被9整除的偶数。
def find_first_divisible_by_9():
    for i in range(9, 100):
        if i % 9 == 0 and i % 2 == 0:
            print(i)
            break


# 使用三元表达式，判断一个输入数字是奇数还是偶数，并打印结果。
def is_odd_or_even(num):
    print("奇数" if num % 2 else "偶数")


# Press the green button in the gutter to run the script.


class Car:
    count = 0

    def __init__(self, brand, color):
        print("car is created")
        self.brand = brand
        self.color = color
        Car.count += 1

    @classmethod
    def get_count(cls):
        print("car count is ", cls.count)

    @staticmethod
    def get_info():
        print("this is a car")

    def run(self):
        print(f"{self.brand}牌的{self.color}汽车正在行驶。")


# 创建一个 BankAccount 类
#
# 属性：account_number（账号）、balance（余额，初始为0）
#
# 方法：
#
# deposit(amount)：存款，增加余额
#
# withdraw(amount)：取款，余额不足时打印提示
#
# get_balance()：打印当前余额

class BankAccount:

    def __init__(self, account_number):
        self.account_number = account_number
        self.balance = 0

    def deposit(self, amount):
        self.balance += amount

    def withdraw(self, amount):
        if self.balance >= amount:
            self.balance -= amount
        else:
            print("余额不足")

    def get_balance(self):
        print(f"当前余额为：{self.balance}")


# 创建一个 Student 类
#
# 属性：name、scores（字典，存储科目及分数）
#
# 方法：
#
# add_score(subject, score)：添加科目分数
#
# average_score()：计算并返回平均分
#
# show_info()：打印学生姓名和所有科目分数
#
# 创建一个 Rectangle 类
#
# 属性：width、height
#
# 方法：
#
# area()：计算面积
#
# perimeter()：计算周长
#
# 类属性 count：统计创建的矩形实例数量
#
# 类方法 get_count()：打印创建的矩形数量
#
# 静态方法练习
# 在 Rectangle 类中添加静态方法 is_square(width, height)，判断给定宽高是否构成正方形，返回布尔值。


# class X:
#     def process(self):
#         print("X.process 开始")
#         super().process()
#         print("X.process 结束")
#
# class Y:
#     def process(self):
#         print("Y.process 开始")
#         super().process()
#         print("Y.process 结束")
#
# class Z:
#     def process(self):
#         print("Z.process 被调用")
#
# class A(X, Y):
#     def process(self):
#         print("A.process 开始")
#         super().process()
#         print("A.process 结束")
#
# class B(Y, Z):
#     def process(self):
#         print("B.process 开始")
#         super().process()
#         print("B.process 结束")
#
# class C(A, B):
#     def process(self):
#         print("C.process 开始")
#         super().process()
#         print("C.process 结束")
#
# if __name__ == "__main__":
#     c = C()
#     c.process()
#     print("MRO:", [cls.__name__ for cls in C.__mro__])

class Person:
    def __init__(self, name, age):
        self.name = name              # 公开属性
        self._gender = "male"         # 受保护属性（约定内部使用）
        self.__salary = 50000         # 私有属性（不可外部直接访问）

    def get_salary(self):
        return self.__salary

    def __private_method(self):
        print("这是私有方法")

    def public_method(self):
        print("这是公共方法，内部调用私有方法：")
        self.__private_method()
# if __name__ == '__main__':
#     p = Person("Tom", 30)
#     print(p.name)  # 可以访问
#     print(p._gender)  # 不建议直接访问（受保护）
#     # print(p.__salary)       # AttributeError
#     print(p.get_salary())  # 通过 getter 方法访问私有属性
#     p.public_method()


# 练习题 1：定义一个 Temperature 类，内部使用摄氏度（celsius）存储温度
# 要求：
# - 提供摄氏度属性（getter 与 setter）
# - 提供华氏度属性（getter 与 setter），与摄氏度自动换算
class Temperature:
    def __init__(self, celsius):
        self.celsius = celsius
    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        self._celsius = value

    @property
    def fahrenheit(self):
        return self._celsius * 1.8 + 32

    @fahrenheit.setter
    def fahrenheit(self, value):
        self._celsius = (value - 32) / 1.8

# if __name__ == '__main__':
#     my_car = Car('奔驰', '红色')
#     my_car.run()
#     print(my_car.brand)
#     print(my_car.color)
#     print("car count is ", Car.count)
#     Car.get_info()
#     my_car1 = Car('宝马', '蓝色')
#     my_car1.run()
#     print(my_car.brand)
#     print(my_car.color)
#     print("car count is ", Car.count)
#     Car.get_info()

# 请写一个 Student 类，要求：
#
# 使用类属性统计当前已创建的学生总人数（命名为 total）
#
# 每创建一个学生实例，总人数自动 +1
#
# 每个学生有实例属性：name、score

class Student:
    total = 0
    def __init__(self, name, score):
        self.name = name
        self.score = score
        Student.total += 1

    def show_info(self):
        print(f"姓名：{self.name}，分数：{self.score}")

    @classmethod
    def get_total(cls):
        print(f"当前已创建的学生总人数为：{cls.total}")

class MyRange:
    def __init__(self, start, end):
        self.current = start
        self.end = end

    def __iter__(self):
        return self  # 返回自己作为迭代器对象

    def __next__(self):
        if self.current >= self.end:
            raise StopIteration
        val = self.current
        self.current += 1
        return val

# for num in MyRange(1, 5):
#     print(num)

# 请定义一个类 EvenNumbers，它接收一个 limit 参数，生成从 0 开始到该值之间的所有偶数。
#
# 要求：
#
# 使用 __iter__() 和 __next__() 方法实现；
#
# 使用 for 循环打印前几个偶数。
class EvenNumbers:
    def __init__(self, limit):
        self.current = 0
        self.limit = limit

    def __iter__(self):
        return self

    def __next__(self):
        if self.current >= self.limit:
            raise StopIteration
        val = self.current
        self.current += 2
        return val

# for num in EvenNumbers(10):
#     print(num)

# 请定义一个类 MyRange，它接收一个 limit 参数，生成从 0 开始到该值之间的所有整数。
#
# 要求：
#
# 使用 __iter__() 和 __next__() 方法实现；
#
# 使用 for 循环打印前几个整数。
class MyRange:
    def __init__(self, limit):
        self.limit = limit

    def __iter__(self):
        self.current = 0
        return self

    def __next__(self):
        if self.current >= self.limit:
            raise StopIteration
        val = self.current
        self.current += 1
        return val

# for num in MyRange(10):
#     print(num)

# 请定义一个类 MyRange，它接收一个 limit 参数，生成从 0 开始到该值之间的所有奇数。
#
# 要求：
#
def fibonacci(n):
    a, b = 0, 1
    for count in range(n):
        if a > 1000:
            break
        print(f"执行了{count}次")  # 先打印再yield
        yield a
        a, b = b, a + b








# if __name__ == '__main__':
#     # company, date, others = ['juejin', '20181016', 'morning']
#     # print(company, date, others)
#     s = "Python"
#     print(s[::-1])
    