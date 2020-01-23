#!usr/bin/env python3
#-*- encoding: utf-8 -*-
__author__ = "QCF"

"""
对商品（文胸）的特殊分析

"""

import re
import sqlite3
import collections
import matplotlib.pyplot as plt

import jieba

# 解决中文显示问题
# 指定默认字体
plt.rcParams['font.sans-serif'] = ['KaiTi'] 
# 解决保存图像负号'-'显示为方块的问题
plt.rcParams['axes.unicode_minus'] = False

# 路径变量
databaseName = "文胸.db"
databasePath = "./data/"

# sqlite3 查询语句
sql_cmd_0 = "SELECT * FROM Products"

# 连接数据库
try:
    conn = sqlite3.connect(databasePath + databaseName)
    curs = conn.cursor()
except Exception as e:
    raise e

# 罩杯数据
item = curs.execute(sql_cmd_0)
info_dic = collections.Counter()
info_dic["color"] = collections.Counter()
info_dic["size"] = collections.Counter()
# 正则表达式取词
for info in item:
    skuInfo = ", ".join(eval(info[1]))
    number = info[2]
    # print(skuInfo)
    color = re.findall(r"颜色:.*,", skuInfo)
    if len(color) == 0:
        color = re.findall(r", 颜色:.*", skuInfo)
        if len(color) == 0:
            continue
        else:
            color = color[0][4:]
    else:
        color = color[0][3:-1]
    # print(color)
    size = re.findall(r"尺码:\w*", skuInfo)
    if len(size) == 0:
        size = re.findall(r"杯码:\w*", skuInfo)
        if len(size) == 0:
            size = re.findall(r"尺寸:\w*\*\w*\*\w* \w*", skuInfo)
            if len(size) == 0:
                continue
        else:
            size = size[0][3:]
    else:
        size = size[0][3:]
    # print(size)
    
    # 未收录该颜色
    if info_dic["color"].get(color) is None:
        info_dic["color"][color] = 1 
    else:
        info_dic["color"][color] += 1
    # 未收录该尺码
    if info_dic["size"].get(size) is None:
        info_dic["size"][size] = 1 
    else:
        info_dic["size"][size] += 1
# 颜色柱状图
print("TOP20: ", info_dic["color"].most_common(20))
kind_color = info_dic["color"].keys()
x_color = [i for i in range(1, 2*len(kind_color)+1, 2)]
count_color = info_dic["color"].values()
plt.bar(x_color, count_color)
plt.title("颜色偏好图")
plt.xticks(x_color, kind_color, rotation = 80)
plt.xlabel("颜色")
plt.ylabel("数量")
for x, y in enumerate(count_color):
    plt.text(2*(x+0.25), y+0.5, "{:d}".format(y))
plt.show()

# 尺寸柱状图
print("TOP20: ", info_dic["size"].most_common(20))
kind_size = info_dic["size"].keys()
x_size = [i for i in range(1, 2*len(kind_size)+1, 2)]
count_size = info_dic["size"].values()
plt.bar(x_size, count_size)
plt.title("尺寸偏好图")
plt.xticks(x_size, kind_size, rotation = 80)
plt.xlabel("尺寸")
plt.ylabel("数量")
for x, y in enumerate(count_size):
    plt.text(2*(x+0.35), y+0.25, "{:d}".format(y))
plt.show()
# 关闭数据库
try:
    curs.close()
    conn.commit()
    conn.close()
except Exception as e:
    raise e
