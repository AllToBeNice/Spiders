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
# 图片URL暂时只能通过网页获取，构造方式部分未明。但是能够通过数据自行绘制。

sql_count = "CREATE TABLE IF NOT EXISTS Counts " +\
            "(id INT, createTime INTEGER, modifyTime INTEGER, " +\
            "tags TEXT, countryType INT, provinceId INT, " +\
            "provinceName VARCHAR(32), provinceShortName VARCHAR(16), " +\
            "sort INT, operator VARCHAR(32))"

sql_count_n = "CREATE TABLE IF NOT EXISTS CountsNew " +\
              "(provinceName VARCHAR(32), provinceShortName VARCHAR(16), " +\
              "confirmedCount INT, suspectedCount INT, curedCount INT, deadCount INT," +\
              "comment TEXT, cities TEXT)"

sql_timeinfo = "CREATE TABLE IF NOT EXISTS TimeLine " +\
                "(id INT, pubDate INTEGER, pubDateStr VARCHAR(128), " +\
                "title TEXT, summary TEXT, infoSource VARCHAR(128), " +\
                "sourceUrl TEXT, provinceId VARCHAR(64), " +\
                "createTime INTEGER, " +\
                "modifyTime INTEGER)"
# 各省/自治区/特别行政区的“省会”对照字典
S2city = {"山东":"济南", "河北":"石家庄", "吉林":"长春",
          "黑龙江":"哈尔滨", "辽宁":"沈阳", "内蒙古":"呼和浩特",
          "新疆":"乌鲁木齐", "甘肃":"兰州", "宁夏":"银川",
          "山西":"太原", "陕西":"西安", "河南":"郑州",
          "安徽":"合肥", "江苏":"南京", "浙江":"杭州",
          "福建":"福州", "广东":"广州", "江西":"南昌",
          "海南":"海口", "广西":"南宁", "贵州":"贵阳",
          "湖南":"长沙", "湖北":"武汉", "四川":"成都",
          "云南":"昆明", "西藏":"拉萨", "青海":"西宁",
          "天津":"天津", "上海":"上海", "重庆":"重庆",
          "北京":"北京", "台湾":"台北", "香港":"香港",
          "澳门":"澳门"}


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
    #   第0个是地区详细疫情数据getAreaStat
    #   第1个是实时通报getTimelineService
    #   第2个是界面浏览量getPV
    #   第3个是基本信息getStatisticsService
    #   第4个是getListByCountryTypeService1
    #   第5个是getListByCountryTypeService2（未知，后续可能加入）
    #   第6个是防爬组件PuppeteerUA（showPuppeteerUA）
    #   第7个是分享链接src
    contents = soup.body
    return contents


def rend_pic(counts, name = "疫情分布图"):
    """
    绘制全国/各省市疫情分布图像。
    
    """
    # 确诊数据y，疑似数据r
    province_y = {}
    province_r = {}
    for k in counts.keys():
        if counts[k][0] != 0:
            province_y[k] = counts[k][0]
        if counts[k][1] != 0:
            province_r[k] = counts[k][1]
    # 绘图
        """
        .add("疑似",
             [list(z) for z in zip(province_r.keys(), province_r.values())],
              'china')
        """
    # 数据来源于国家卫健委，暂无疑似病例的省市分布情况
    pmap = (
        Map(init_opts = opts.InitOpts(width = "1510px", height = "705px",
                                      page_title = "疫情分布地图"))
        .add("确诊",
             [list(z) for z in zip(province_y.keys(), province_y.values())],
              'china')
        .set_global_opts(
            title_opts = opts.TitleOpts(title = name),
            visualmap_opts = opts.VisualMapOpts(max_ = 1000,
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


def get_count_n(contents):
    """
    针对获取各省份疫情数据进行处理，返回省份数据和城市数据元组。
    (Update)The Last Time: 2020-01-24, 使用getAreaStat中更详细的格式化数据
    
    """
    counts = collections.Counter()
    temp_detail = {}
    counts_detail = {}
    data_list = list(map(str, list(contents.findAll("script"))))
    # 寻找目标字符串
    for i in range(len(data_list)):
        if "getAreaStat" in data_list[i]:
            # 去掉前面和后面的无关字符串
            data = data_list[i][52:-20]
            data = eval(data)
            break
    # 判断是否接收到了该字段。否，则返回-1
    if len(data) == 0:
        return -1
    # 储存进入sqlite3数据库
    curs.execute(sql_count_n)
    for item in data:
        # 查询是否存在有相同字段的记录
        sql_search = "SELECT * FROM CountsNew WHERE " +\
                     "provinceName = \"{}\"".format(item["provinceName"])
        search_back = curs.execute(sql_search).fetchall()
        # 若不存在，则加入
        if len(search_back) == 0:
            sql_prot = "INSERT INTO CountsNew VALUES {}".format((item["provinceName"],\
                                                                 item["provinceShortName"],\
                                                                 item["confirmedCount"],\
                                                                 item["suspectedCount"],\
                                                                 item["curedCount"],\
                                                                 item["deadCount"],\
                                                                 str([item["comment"]]),\
                                                                 str(item["cities"])))
            curs.execute(sql_prot)
        # 若存在，则更新记录
        else:
            sql_prot = "UPDATE CountsNew SET confirmedCount = {},".format(item["confirmedCount"]) +\
                       "suspectedCount = {}, curedCount = {},".format(item["suspectedCount"], item["curedCount"]) +\
                       "deadCount = {}, comment = \"{}\",".format(item["deadCount"], item["comment"]) +\
                       "cities = \"{}\" WHERE ".format(str(item["cities"])) +\
                       "provinceName = \"{}\"".format(item["provinceName"])
            curs.execute(sql_prot)
        # 省份数据
        # 数量：(确诊，疑似，治愈，死亡）
        num = [0, 0, 0, 0]
        num[0] = item["confirmedCount"]
        num[1] = item["suspectedCount"]
        num[2] = item["curedCount"]
        num[3] = item["deadCount"]
        counts[item["provinceShortName"]] = num
        # 城市数据
        # counts_detail: {province:{cities:[]}}
        # temp_detail: {cities:[]}
        item_detail = eval(str(item["cities"]))
        counts_detail[item["provinceShortName"]] = {}
        # 说明该区域的数据还没有详细到地级市，则以该区域数据代替
        if len(item_detail) == 0:
            num = [0, 0, 0, 0]
            num[0] = item["confirmedCount"]
            num[1] = item["suspectedCount"]
            num[2] = item["curedCount"]
            num[3] = item["deadCount"]
            temp_detail[S2city[item["provinceShortName"]]] = num
            counts_detail[item["provinceShortName"]][S2city[item["provinceShortName"]]] = num
        for i in range(len(item_detail)):
            num = [0, 0, 0, 0]
            num[0] = item_detail[i]["confirmedCount"]
            num[1] = item_detail[i]["suspectedCount"]
            num[2] = item_detail[i]["curedCount"]
            num[3] = item_detail[i]["deadCount"]
            temp_detail[item_detail[i]["cityName"]] = num
            counts_detail[item["provinceShortName"]][item_detail[i]["cityName"]] = num
    # 控制台输出各省数据
    print("各省统计:")
    print("           确诊  疑似  治愈  死亡")
    for p in counts.keys():
        print("  {:3s} {:6d}{:6d}{:6d}{:6d}".format(p, counts[p][0], counts[p][1], counts[p][2], counts[p][3]))
    print("--"*40)
        # 计算出各省份比例
    countsFre = collections.Counter()
    Sum = sum([i[0] for i in counts.values()])
    print(f"各省确诊总计：{Sum}")
    print()
    for province in counts.keys():
        countsFre[province] = counts[province][0] / Sum
    print("各省占比前五：")
    for p in countsFre.most_common(5):
        print("    {}: {:>5.2f} %".format(p[0], 100 * p[1]))
    print("--"*40)
    # 控制台输出各城数据
    print("各城统计:")
    print("             确诊  疑似  治愈  死亡")
    for c in temp_detail.keys():
        print("  {:6s} {:6d}{:6d}{:6d}{:6d}".format(c, temp_detail[c][0], temp_detail[c][1], temp_detail[c][2], temp_detail[c][3]))
    print("--"*40)
        # 计算出各城市比例
    countsFre_detail = collections.Counter()
    Sum = sum([i[0] for i in temp_detail.values()])
    print(f"各城确诊总计：{Sum}")
    print()
    for city in temp_detail.keys():
        countsFre_detail[city] = temp_detail[city][0] / Sum
    print("各城占比前二十:")
    for c in countsFre_detail.most_common(20):
        print("    {:>8s}: {:>5.2f} %".format(c[0], 100 * c[1]))
    print("--"*40)
    return (counts, counts_detail)


def get_timeinfo(contents):
    """
    针对实时通报数据进行处理
    (Update)The Last Time: 2020-1-24

    """
    data_list = list(map(str, list(contents.findAll("script"))))
    # 寻找目标字符串
    for i in range(len(data_list)):
        if "getTimelineService" in data_list[i]:            
            # 去掉前面的无关字符串
            data = data_list[i][67:]
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
        temp = get_count_n(get_msg(URL_0))
        rend_pic(temp[0], "疫情分布图")
        get_timeinfo(get_msg(URL_0))
    except Exception as e:
        raise e
    finally:
        curs.close()
        conn.commit()
        conn.close()
