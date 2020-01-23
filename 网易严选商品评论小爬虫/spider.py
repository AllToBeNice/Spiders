#!usr/bin/env python3
#-*- encoding: utf-8 -*-
__author__ = "QCF"

"""
已实现功能：搜索，获取评论并格式化储存到sqlite3数据库中

"""

import random
import time
import requests
import sqlite3

def search_keyword(keyword, page):
    """
    Search keyword in https://you.163.com/xhr/search/search.json

    :param keyword: The word you want to search.
    :param page: The number of page. 

    :return product_id_list: The list of products' id.
    
    """

    URL = "https://you.163.com/xhr/search/search.json"
    query = {
        "keyword": keyword,
        "page": page
        }
    try:
        # 记录是否为最后一页
        flag = 0
        res = requests.get(URL, params = query).json()
        # 判断是否为最后一页
        if res["data"]["directly"]["searcherResult"]["pagination"]["lastPage"]:
            flag = 1
        result = res["data"]["directly"]["searcherResult"]["result"]
        product_id_list = []
        for item in result:
            product_id_list.append(item["id"])
        return (product_id_list, flag)
    except Exception as e:
        raise e


def isRepeated(item):
    """
    Query whether the data already exists in the data table.
    Return 1 if there is, 0 if it does not exist.

    :param item: A data tuple, the first is the data table's name
                and the second is the current data that conforms to the table.

    :return 1: It means the data already exist in the data table.
    :return 0: It means the data does not exist in the data table.
    
    """

    # 构造查询语句
    search_cmd = "SELECT * FROM {} WHERE ".format(item[0])
    if item[0] == "Users":
        search_cmd = search_cmd +\
                     "UserName = \"{}\" and ".format(item[1][0]) +\
                     "UserAvatar = \"{}\" and ".format(item[1][1]) +\
                     "UserLevel = \"{}\"".format(item[1][2])
    else:
        search_cmd = search_cmd +\
                     "ItemId = \"{}\" and ".format(item[1][0]) +\
                     "SkuInfo = \"{}\"".format(item[1][1])
    # print("[T]", search_cmd)
    # 获得查询结果，为一个列表
    search_back = curs.execute(search_cmd).fetchall()
    # print("[T]", search_back)
    if len(search_back) != 0:
        return 1
    else:
        return 0


def save_to_SQLite3(Info):
    """
    Try to save the json info into the sqlite3 database.

    # global conn and curs

    """

    usersInfo = (Info["frontUserName"],
                 str(Info["frontUserAvatar"]),
                 int(Info["memberLevel"]))
    
    productInfo = (Info["itemId"], str(Info["skuInfo"]), 1)
    
    commentInfo = (Info["itemId"],
                   Info["frontUserName"],
                   int(Info["createTime"]),
                   str(Info["content"]),
                   int(Info["star"]),
                   str(Info["commentReplyVO"]),
                   str(Info["appendCommentVO"]))
    
    picturesInfo = (Info["itemId"],
                    Info["frontUserName"],
                    int(Info["createTime"]),
                    str(Info["picList"]))
    
    cmd_0 = "CREATE TABLE IF NOT EXISTS Users " +\
            "(UserName VARCHAR(32), UserAvatar VARCHAR(255), UserLevel INT)"

    cmd_1 = "CREATE TABLE IF NOT EXISTS Products " +\
            "(ItemId VARCHAR(16), SkuInfo VARCHAR(255), Number INT)"
            
    cmd_2 = "CREATE TABLE IF NOT EXISTS Comments " +\
            "(ItemId VARCHAR(16), UserName VARCHAR(32), CreateTime INTEGER, " +\
            "Comment TEXT, Star INT, ComReply TEXT, AppendCom TEXT)"
            
    cmd_3 = "CREATE TABLE IF NOT EXISTS Pictures " +\
            "(ItemId VARCHAR(16), UserName VARCHAR(32), CreateTime INTEGER, " +\
            "PicList TEXT)"

    cmdList = [cmd_0, cmd_1, cmd_2, cmd_3]
    tableList = ["Users", "Products", "Comments", "Pictures"]
    infoList = [usersInfo, productInfo, commentInfo, picturesInfo]
    
    try:
        # 建立表
        for cmd in cmdList:
            curs.execute(cmd)
        # 查询后插入表
        for item in zip(tableList, infoList):
            # 查询用户是否重复
            if item[0] == "Users":
                if isRepeated(item) == 1:
                    continue
            # 查询商品是否有购买重复，重复则Number字段加1
            elif item[0] == "Products":
                if isRepeated(item) == 1:
                    sql_update = "UPDATE Products SET Number = Number + 1 " +\
                                 "WHERE {} = {} AND {} = \"{}\"".format("itemId", item[1][0], "skuInfo", item[1][1])
                    # print(sql_update)
                    curs.execute(sql_update)
                    continue
            else:
                pass
            # 没有重复记录则插入数据表
            cmd_prototype = "INSERT INTO {} VALUES {}".format(item[0], item[1])
            curs.execute(cmd_prototype)
    except Exception as e:
        raise e


def get_commentList(product_id, totalPages):
    """
    Get the comments of the product useing the id of it.
    
    # The totalPages can be a determined number getting from commentList.

    :param product_id: The is of the product.
    :param totalPages: The number of comment pages you want to get.

    :return
    
    """

    URL = "https://you.163.com/xhr/comment/listByItemByTag.json"
    try:
        print("Product ", product_id)
        for i in range(1, totalPages + 1):
            query = {
                "itemId": product_id,
                "page": i
                }
            res = requests.get(URL, params = query).json()
            if not res["data"]["commentList"]:
                break
            print(" # {:d} page of comments.".format(i))
            commentList =  res["data"]["commentList"][0]
            # print("[T]", res["data"]["commentList"])
            # 上式输出的其实是一个只有一个字典的列表
            try:
                save_to_SQLite3(commentList)
            except Exception as er:
                print("[E] Save Error! ", er)
                continue
    except Exception as e:
        raise e


if __name__ == "__main__":
    keyword = input("Enter the name you want to search in you.163.com: ")
    searchPages = input("Enter the total pages you want to search: ")
    commentPages = input("Enter the total pages of comments you want to get: ")
    searchPages = int(searchPages)
    commentPages = int(commentPages)
    
    try:
        global conn
        global curs
        conn = sqlite3.connect("./data/{:s}.db".format(keyword))
        curs = conn.cursor()
        # Begin search
        for p in range(1, searchPages + 1):
            print("Page # {:d}".format(p))
            product_id_list, flag = search_keyword(keyword, p)
            # print("[T] ", product_id_list)
            for ID in product_id_list:
                get_commentList(ID, commentPages)
                # 爬取完一件商品的评论后，停止1-4秒，防止封IP
                time.sleep(random.randint(1,4))
            # 若为最后一页(flag = 1)，则跳出
            if flag == 1:
                print("# End")
                break
    except Exception as e:
        raise e
    finally:
        curs.close()
        conn.commit()
        conn.close()
