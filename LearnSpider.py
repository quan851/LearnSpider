import requests
from urllib.parse import urlencode
from requests.exceptions import RequestException
import json
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from json import JSONDecodeError
browser = webdriver.Chrome()


from config import *
import pymongo
from hashlib import md5
import os
from multiprocessing import Pool

KEYWORD = '街拍'

client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]

def get_page_index(offset, keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': 20,
        'cur_tab': 1,
        'from': 'gallery'
        }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print("请求索引页错误")
        return None

def parse_page_index(html):
    data  = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')

def get_page_detail(url):
     try:
        browser.get(url)
        text =  browser.page_source
        return text
     except RequestException:
        print("请求详情页错误", url)
        return None

def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title  = soup.select('title')[0].get_text()
    print(title)
    images_pattern = re.compile('gallery: JSON.parse\(\"(.*?)\"\),', re.S)
    result = re.search(images_pattern, html)
    if result:
        print(result.group(1))
        string = str(result.group(1))
        comareString = "url_list(.*?)\\\"},"
        url_pattern = re.compile(comareString, re.S)
        urlResult = re.findall(url_pattern, string)
        images = []
        if len(urlResult) > 0:
            for urlitem in urlResult:
                urlitem = urlitem[15:]
                urlitem = urlitem.replace('\\','')
                print(urlitem)
                download_image(urlitem)
                images.append(urlitem)
            return {
                        'title':title,
                        'images':images,
                        'url':url
                    }
    return None   

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False

def download_image(url):
    print('正在下载',url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content)
            return response.text
        return None
    except RequestException:
        print("请求图片错误")
        return None

def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(), 'jpg')
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()

def main(offset):
    html = get_page_index(offset,KEYWORD)
    for url in parse_page_index(html):
        if url:
            print(url)
            strUrl = str(url)
            strUrl = strUrl.replace(r'group/', 'a')
            print('new url:',strUrl)
            html = get_page_detail(strUrl)
            if html:
                result = parse_page_detail(html, url)
                if result:
                    save_to_mongo(result)



if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START,GROUP_END)]
    pool = Pool()
    pool.map(main,groups)
    #for item in groups:
    #    main(item)
    browser.close()