#!usr/bin/env python3
#-*- encoding: utf-8 -*-
__author__ = "QCF"

"""
对获取到的数据进行分析

"""

import sys
from PIL import Image
import numpy as np
import collections
import matplotlib.pyplot as plt
import sqlite3

import jieba
import wordcloud

# 解决中文显示问题
# 指定默认字体
plt.rcParams['font.sans-serif'] = ['KaiTi'] 
# 解决保存图像负号'-'显示为方块的问题
plt.rcParams['axes.unicode_minus'] = False

# 路径变量
databaseName = "文胸.db"
databasePath = "./data/"
stopwordsPath = "F:/Python/stopwords/stopwords1897.txt"
# sqlite3语句
sql_cmd_tables = "SELECT name FROM sqlite_master " +\
                 "WHERE TYPE = 'table' ORDER BY NAME"
sql_cmd_users_1  = "SELECT COUNT(1) FROM Users GROUP BY UserLevel"
sql_cmd_comments = "SELECT ItemId, Comment, Star, AppendCom FROM Comments"
# 解决特殊字符编码问题
# 建立字符映射字典
non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

# 连接数据库
try:
    conn = sqlite3.connect(databasePath + databaseName)
    curs = conn.cursor()
except Exception as e:
    raise e
# 获取数据库中所有表名
table_names = curs.execute(sql_cmd_tables).fetchall()
table_names = list(sum(table_names, ()))
print("Existing table: {}".format(", ".join(table_names)))
# 获取各个表的字段信息
for i in range(len(table_names)):
    print("# {}: {}".format(i, table_names[i]))
    table_info = curs.execute("PRAGMA table_info({})".format(table_names[i])).fetchall()
    for info in table_info:
        print(" {:d}: {:10s} {:15} {} {} {}"\
              .format(info[0], info[1], info[2], info[3], info[4], info[5]))
    print()

# 用户数据统计
starList = [1, 2, 3, 4, 5, 6]
userStar = curs.execute(sql_cmd_users_1)
    # 扁平化
userStar = list(sum(userStar, ()))
    # 转为频率列表
temp_sum = sum(userStar)
userStarFre = [i/temp_sum for i in userStar]
userStarFre = dict(zip(starList, userStarFre))
    # 输出数据及图像
print("Users Star Data: ", userStarFre)
plt.bar(starList, userStarFre.values())
plt.title("用户星级分布柱状图")
plt.xlabel("星级")
plt.ylabel("频率")
for x, y in enumerate(userStarFre.values()):
    plt.text(x+0.8, y+0.005, str("{:.2f}".format(100 * y) + "%"))
plt.show()

# 用户评价分析
starInfo = dict()
commentsInfo = dict()
comments = curs.execute(sql_cmd_comments)
for item in comments:
    # 存在商品item[0]
    if starInfo.get(item[0]) is not None:
        # 存在星级
        if starInfo[item[0]].get(item[2]) is not None:
            starInfo[item[0]][item[2]] += 1
        # 不存在该星级，建立并赋值
        else:
            starInfo[item[0]][item[2]] = 1
    # 不存在该商品，建立商品和星级并赋值
    else:
        starInfo[item[0]] = {item[2]: 1}

    # 存在商品item[0]
    if commentsInfo.get(item[0]) is not None:
        commentsInfo[item[0]].append(item[1].translate(non_bmp_map))
    # 不存在该商品，建立商品并添加评论
    else:
        commentsInfo[item[0]] = [item[1].translate(non_bmp_map)]
    # 附加评论不为空
    if item[-1] != "None":
        commentsInfo[item[0]].append(item[1].translate(non_bmp_map))
        # eval()安全隐患
        commentsInfo[item[0]].append(eval(item[-1])["content"].translate(non_bmp_map))
"""
for product in starInfo.keys():
    labels = starInfo[product].keys()
    # 转为频率列表
    productStarFre = starInfo[product].values()
    temp_sum = sum(productStarFre)
    productStarFre = [i/temp_sum for i in productStarFre]
    # 绘出饼图
    plt.title("{}商品评价图（1-5星）\n{}人".format(product, temp_sum))
    plt.pie(productStarFre, labels = labels, autopct = '%1.2f%%')
    plt.show()
"""
# jieba分词，绘制词云图
# 载入停用词表
with open(stopwordsPath, 'r', encoding = "utf-8") as fr:
    stopwords = fr.readlines()
# 各个商品的评论词云图
for product in commentsInfo.keys():
    # 评论分词计算字典
    comment_counts = collections.Counter()
    for text in commentsInfo[product]:
        words = jieba.cut(text)
        # 加入分词计算字典
        for word in words:
            if (word+'\n') in stopwords or len(word) == 1:
                continue
            if comment_counts.get(word) is None:
                comment_counts[word] = 1
            else:
                comment_counts[word] += 1
    counts_top20 = comment_counts.most_common(20)
    # print(counts_top20)
    # 词频图展示
    # 定义词频背景
    mask = np.array(Image.open('wordcloud.png'))
    # 设置字体格式、背景图、显示词数、字体最大值
    wc = wordcloud.WordCloud(
        scale = 4,
        font_path = "C:/Windows/Fonts/simhei.ttf",
        mask = mask,
        max_words = 200,
        max_font_size = 100
        )
    # 从字典生成词云
    wc.generate_from_frequencies(comment_counts)
    # 从背景图建立颜色方案
    image_colors = wordcloud.ImageColorGenerator(mask)
    # 将词云颜色设置为背景图方案
    wc.recolor(color_func = image_colors)
    # 显示词云
    plt.title("{}".format(product))
    plt.imshow(wc)
    # 关闭坐标轴
    plt.axis('off')
    # 显示图像
    plt.show()

# 商品数据分析


# 关闭连接
try:
    curs.close()
    conn.commit()
    conn.close()
except Exception as e:
    raise e
