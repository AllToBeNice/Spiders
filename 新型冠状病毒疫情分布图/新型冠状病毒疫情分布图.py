#!usr/bin/env python3
#-*- encoding: utf-8-*-
__author__ = "QCF"

"""
获取丁香园新型冠状病毒疫情分布图及实时消息。

"""

import re
import time
import sqlite3
import requests
import collections

from pyecharts.charts import Map
from pyecharts import options as opts
from bs4 import BeautifulSoup

URL_0 = "https://3g.dxy.cn/newh5/view/pneumonia"
URL_1 = "https://img1.dxycdn.com/2020/0123/683/3392477680837778825-73.jpg"
# URL_1 = "https://img1.dxycdn.com/2020/0123/803/3392477165441658520-73.jpg"
# URL_1 = "https://img1.dxycdn.com/2020/0122/454/3392366606541188279-73.jpg"
# 图片URL暂时只能通过网页获取，构造方式部分未明。但是能够通过数据自行绘制。

sql_count = "CREATE TABLE IF NOT EXISTS Counts " +\
            "(id INT, createTime INTEGER, modifyTime INTEGER, " +\
            "tags TEXT, countryType INT, provinceId INT, " +\
            "provinceName VARCHAR(32), provinceShortName VARCHAR(16), " +\
            "sort INT, operator VARCHAR(32))"

sql_timeinfo = "CREATE TABLE IF NOT EXISTS TimeLine " +\
                "(id INT, pubDate INTEGER, pubDateStr VARCHAR(128), " +\
                "title TEXT, summary TEXT, infoSource VARCHAR(128), " +\
                "sourceUrl TEXT, provinceId VARCHAR(64), " +\
                "createTime INTEGER, " +\
                "modifyTime INTEGER)"
# provinceName VARCHAR(64), 

def get_pic(url):
    """
    获取疫情分布图，写入文件
    返回requests结构体

    """
    image = requests.get(url)
    try:
        fw = open('pneumoniaPic.png', 'wb')
        fw.write(image.content)
        fw.close()
    except Exception as e:
        raise e
    return image


def get_msg(url):
    """
    获取疫情实时消息
    返回script字段字符串

    """
    htmlMsg = requests.get(url)
    # 停止1s
    time.sleep(1)
    soup = BeautifulSoup(htmlMsg.content, "html.parser")
    # 获取body标签里的内容，包含多个script
    # 通过findAll找到的：
    #   第0个是省份疫情数据getListByCountryTypeService1
    #   第1个是界面浏览量getPV
    #   第2个是（重复）基本信息getStatisticsService
    #   第3个是实时通报getTimelineService
    #   第4个是分享链接src
    #   第5个是getListByCountryTypeService2（未知，后续可能加入）
    contents = soup.body
    return contents


def rend_pic(counts, name = "疫情分布图"):
    """
    绘制疫情分布图像。
    
    """
    # 确诊数据y，疑似数据r
    province_y = {}
    province_r = {}
    for k in counts.keys():
        if counts[k][0] != 0:
            province_y[k] = counts[k][0]
        if counts[k][1] != 0:
            province_r[k] = counts[k][1]
    print("确诊：", province_y)
    print("--"*40)
    print("疑似：", province_r)
    print("--"*40)
    # 绘图
    pmap = (
        Map(init_opts = opts.InitOpts(width = "1510px", height = "705px",
                                      page_title = "疫情分布地图"))
        .add("确诊",
             [list(z) for z in zip(province_y.keys(), province_y.values())],
              'china')
        .add("疑似",
             [list(z) for z in zip(province_r.keys(), province_r.values())],
              'china')
        .set_global_opts(
            title_opts = opts.TitleOpts(title = name),
            visualmap_opts = opts.VisualMapOpts(max_ = 600,
                                                is_piecewise = True,
                                                pieces = [
                                                    {"min": 100, "label": ">100"},
                                                    {"min": 10, "max": 100, "label": "10-100"},
                                                    {"min": 1, "max": 9, "label": "1-9"},
                                                    {"min": 0, "max": 0, "label": "0"}
                                                    ]),
            toolbox_opts = opts.ToolboxOpts()
        )
    )
    pmap.render(path = "{}.html".format(name))
    return pmap


def get_count(contents):
    """
    针对获取各省份疫情数据进行处理。
    
    """
    counts = collections.Counter()
    data_list = list(map(str, list(contents.findAll("script"))))
    # 寻找目标字符串
    for i in range(len(data_list)):
        if "getListByCountryTypeService1" in data_list[i]:
            # 去掉前面的无关字符串
            data = data_list[i][86:]
            # 去掉后面的无关字符串
            data = data[:-20]
            data = eval(data)
            break
    # 判断是否接收到了该字段。否，则返回-1
    if len(data) == 0:
        return -1
    # 储存进入sqlite3数据库
    curs.execute(sql_count)
    for item in data:
        # 查询是否存在有相同字段的记录
        sql_search = "SELECT * FROM Counts WHERE " +\
                     "id = {} AND createTime = {} AND ".format(item["id"], item["createTime"]) +\
                     "provinceId = {}".format(item["provinceId"])
        search_back = curs.execute(sql_search).fetchall()
        # 若不存在，则加入
        if len(search_back) == 0:
            sql_prot = "INSERT INTO Counts VALUES {}".format((item["id"],\
                                                             item["createTime"],\
                                                             item["modifyTime"],\
                                                             item["tags"],\
                                                             item["countryType"],\
                                                             item["provinceId"],\
                                                             item["provinceName"],\
                                                             item["provinceShortName"],\
                                                             item["sort"],\
                                                             item["operator"]))
            curs.execute(sql_prot)
        # 若存在，则更新记录
        else:
            sql_prot = "UPDATE Counts SET modifyTime = {},".format(item["modifyTime"]) +\
                       "tags = \"{}\", sort = {},".format(item["tags"], item["sort"]) +\
                       "operator = \"{}\" WHERE ".format(item["operator"]) +\
                       "id = {} AND createTime = {} AND ".format(item["id"], item["createTime"]) +\
                       "provinceId = \"{}\"".format(item["provinceId"])
            curs.execute(sql_prot)
        # 数量：(确诊，疑似，治愈，死亡）
        num = [0, 0, 0, 0]
        temp = re.findall(r"确诊 \d* 例", item["tags"])
        if len(temp) != 0:
            num[0] = int(temp[0][3:-2])
        temp = re.findall(r"疑似 \d* 例", item["tags"])
        if len(temp) != 0:
            num[1] = int(temp[0][3:-2])
        temp = re.findall(r"治愈 \d* 例", item["tags"])
        if len(temp) != 0:
            num[2] = int(temp[0][3:-2])
        temp = re.findall(r"死亡 \d* 例", item["tags"])
        if len(temp) != 0:
            num[3] = int(temp[0][3:-2])
        counts[item["provinceShortName"]] = num
    print("统计：", counts)
    print("--"*40)
    # 计算出各省份比例
    countsFre = collections.Counter()
    Sum = sum([i[0] for i in counts.values()])
    print(f"确诊总计：{Sum}")
    for province in counts.keys():
        countsFre[province] = counts[province][0] / Sum
    print("占比前五：", countsFre.most_common(5))###
    print("--"*40)
    return counts


def get_timeinfo(contents):
    """
    针对实时通报数据进行处理

    """
    data_list = list(map(str, list(contents.findAll("script"))))
    # 寻找目标字符串
    for i in range(len(data_list)):
        if "getTimelineService" in data_list[i]:            
            # 去掉前面的无关字符串
            data = data_list[i][113:]
            # 去掉后面的无关字符串
            data = data[:-21]
            data = eval(data)
            break
    # 判断是否接收到了该字段。否，则返回-1
    if len(data) == 0:
        return -1
    # 储存进入sqlite3数据库
    curs.execute(sql_timeinfo)
    for item in data:
        # print(item)
        # 查询是否存在该条数据记录
        sql_search = "SELECT * FROM TimeLine WHERE " +\
                     "id = {} AND modifyTime = {} AND ".format(item["id"], item["modifyTime"]) +\
                     "pubDate = {}".format(item["pubDate"])
        search_back = curs.execute(sql_search).fetchall()
        # 若不存在id相同的记录，则加入
        if len(search_back) == 0:
            sql_prot = "INSERT INTO TimeLine VALUES {}".format((item["id"],\
                                                                item["pubDate"],\
                                                                item["pubDateStr"],\
                                                                item["title"],\
                                                                item["summary"],\
                                                                item["infoSource"],\
                                                                item["sourceUrl"],\
                                                                item["provinceId"],\
                                                                #item["provinceName"],\
                                                                item["createTime"],\
                                                                item["modifyTime"]))
            curs.execute(sql_prot)
        # 若存在id相同的记录，则更新
        else:
            sql_prot = "UPDATE TimeLine SET " +\
                       "id = {}, pubDate = {},".format(item["id"], item["pubDate"]) +\
                       "pubDateStr = \"{}\", title = \"{}\",".format(item["pubDateStr"], item["title"]) +\
                       "summary = \"{}\", ".format(item["summary"]) +\
                       "infoSource= \"{}\", sourceUrl = \"{}\",".format(item["infoSource"], item["sourceUrl"]) +\
                       "provinceId = {}, createTime = {},".format(item["provinceId"], item["createTime"]) +\
                       "modifyTime = {} WHERE ".format(item["modifyTime"]) +\
                       "id = {} AND pubDate = {}".format(item["id"], item["pubDate"])
            curs.execute(sql_prot)
            # 搜索关键词(待续)
            


if __name__ == "__main__":
    filePath = "F:/Python/Project/新型冠状病毒疫情分布图/data/Pneumonia.db"
    try:
        get_pic(URL_1)
        conn = sqlite3.connect(filePath)
        curs = conn.cursor()
        rend_pic(get_count(get_msg(URL_0)), "疫情分布图")
        get_timeinfo(get_msg(URL_0))
    except Exception as e:
        raise e
    try:
        curs.close()
        conn.commit()
        conn.close()
    except Exception as e:
        raise e
