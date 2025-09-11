# from enum import Enum, unique
#
# Month = Enum('Month', ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'))
# for name, member in Month.__members__.items():
#     print(name, '=>', member, ',', member.value)
#
# @unique
# class Weekday(Enum):
#     Sun = 0 # Sun的value被设定为0
#     Mon = 1
#     Tue = 2
#     Wed = 3
#     Thu = 4
#     Fri = 5
#     Sat = 6
#
# day1 = Weekday.Mon
# print(day1.value)

class Rectangle :
    def __init__(self, width, height):
        self.width = width
        self.height = height
    def __str__(self):
        return 'Rectangle(width={}, height={})'.format(self.width, self.height)
    def __repr__(self):
        return 'Rectangle(width={}, height={})'.format(self.width, self.height)
    def area(self):
        return self.width * self.height

r = Rectangle(3, 5)
print(r)
print(repr(r))
print(r.area())

try:
    10/0
except ZeroDivisionError as e:
    print(e)