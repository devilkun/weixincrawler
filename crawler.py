# -*- coding: utf-8 -*-

import json
import logging
import time
from datetime import datetime

import requests

import utils
from models import Post

requests.packages.urllib3.disable_warnings()
from urllib.parse import urlsplit
import html

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class WeiXinCrawler:
    def crawl(self, offset=0):
        """
        爬取更多文章
        :return:
        """
        url = "https://mp.weixin.qq.com/mp/profile_ext?action=getmsg&__biz=MjM5MTc3OTQ0MQ==&f=json&offset={offset}&count=10&is_ok=1&scene=126&uin=777&key=777&pass_ticket=Bh6wUrwOuRK6bdMZUJLMQVn%2BuWp%2FeYUKJGC8JQi6j9ur9g7M5Dnkqd1IkLMdl9vx&wxtoken=&appmsg_token=981_GjmQKuDAbYludaosjDK2eJpoBUSVE0uYOmI5fw~~&x5=0&f=json".format(offset=offset)  # appmsg_token 是临时的，也需要更新
        # 从 Fiddler 获取最新的请求头参数
        headers = """
Host: mp.weixin.qq.com
Accept-Encoding: br, gzip, deflate
Cookie: devicetype=iOS12.0.1; lang=zh_CN; pass_ticket=Bh6wUrwOuRK6bdMZUJLMQVn+uWp/eYUKJGC8JQi6j9ur9g7M5Dnkqd1IkLMdl9vx; version=16070322; wap_sid2=CPD+necIElxSeFJlQ1U2bm5KRUwxdnJfXzVCTjRrTGVJZlZ6RnAzbVFJVzNFN3UwQ296RmNUbW1YNHFJSUNTQ1dsemZPT0prVkFYYkh2NWVmbS1XMWdEZWZEOFMwTlVEQUFBfjCluOreBTgNQJVO; wxuin=2363981680; rewardsn=; wxtokenkey=777; pgv_pvid=7217329857; _scan_has_moon=1; eas_sid=Z1z5O3U2s463w5G6j5W456a0o7; tvfe_boss_uuid=37f32a121348f925; pgv_pvi=5114346496; sd_cookie_crttime=1525167542515; sd_userid=86141525167542515
Connection: keep-alive
Accept: */*
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 12_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/16A404 MicroMessenger/6.7.3(0x16070321) NetType/WIFI Language/zh_CN
Referer: https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=MjM5MTc3OTQ0MQ==&scene=126&devicetype=iOS12.0.1&version=16070322&lang=zh_CN&nettype=WIFI&a8scene=0&fontScale=100&pass_ticket=Bh6wUrwOuRK6bdMZUJLMQVn%2BuWp%2FeYUKJGC8JQi6j9ur9g7M5Dnkqd1IkLMdl9vx&wx_header=1
Accept-Language: zh-cn
X-Requested-With: XMLHttpRequest



"""
        headers = utils.str_to_dict(headers)
        response = requests.get(url, headers=headers, verify=False)
        result = response.json()
        if result.get("ret") == 0:
            msg_list = result.get("general_msg_list")
            logger.info("抓取数据：offset=%s, data=%s" % (offset, msg_list))
            self.save(msg_list)
            # 递归调用
            has_next = result.get("can_msg_continue")
            if has_next == 1:
                next_offset = result.get("next_offset")
                time.sleep(2)
                self.crawl(next_offset)
        else:
            # 错误消息
            # {"ret":-3,"errmsg":"no session","cookie_count":1}
            logger.error("无法正确获取内容，请重新从Fiddler获取请求参数和请求头")
            exit()

    @staticmethod
    def save(msg_list):

        msg_list = msg_list.replace("\/", "/")
        data = json.loads(msg_list)
        msg_list = data.get("list")
        for msg in msg_list:
            p_date = msg.get("comm_msg_info").get("datetime")
            msg_info = msg.get("app_msg_ext_info")  # 非图文消息没有此字段
            if msg_info:
                WeiXinCrawler._insert(msg_info, p_date)
                multi_msg_info = msg_info.get("multi_app_msg_item_list")
                for msg_item in multi_msg_info:
                    WeiXinCrawler._insert(msg_item, p_date)
            else:
                logger.warning(u"此消息不是图文推送，data=%s" % json.dumps(msg.get("comm_msg_info")))

    @staticmethod
    def _insert(item, p_date):
        keys = ('title', 'author', 'content_url', 'digest', 'cover', 'source_url')
        sub_data = utils.sub_dict(item, keys)
        post = Post(**sub_data)
        p_date = datetime.fromtimestamp(p_date)
        post["p_date"] = p_date
        logger.info('save data %s ' % post.title)
        try:
            post.save()
        except Exception as e:
            logger.error("保存失败 data=%s" % post.to_json(), exc_info=True)

    @staticmethod
    def update_post(post):
        """
        post 参数是从mongodb读取出来的一条数据
        稍后就是对这个对象进行更新保存
        :param post:
        :return:
        """

        # 这个参数是我从Fiddler中拷贝出 URL，然后提取出查询参数部分再转换成字典对象
        # 稍后会作为参数传给request.post方法
        data_url_params = {'__biz': 'MjM5MTc3OTQ0MQ==', 'appmsg_type': '9', 'mid': '2651956908',
                           'sn': '8ee1a65ff1e109e1042fce6ee6915d12', 'idx': '1', 'scene': '4',
                           'title': '%E5%81%87%E5%A6%82%E9%87%91%E5%BA%B8%E6%9D%A5%E5%86%99NBA%EF%BC%8C%E5%90%84%E8%B7%AF%E6%AD%A6%E4%BE%A0%E8%8B%B1%E9%9B%84%E4%BC%9A%E5%8F%98%E6%88%90%E5%93%AA%E4%BD%8D%E7%90%83%E6%98%9F%EF%BC%9F',
                           'ct': '1540976033',
                           'abtest_cookie': 'BAABAAoACwANABMABAAjlx4AV5keAISZHgCKmR4AAAA=',
                           'devicetype': 'iOS12.0.1',
                           'version': '16070322', 'f': 'json',
                           'r': '0.2903370651825036', 'is_need_ad': '1', 'comment_id': '526532160509853696',
                           'is_need_reward': '0', 'both_ad': '0', 'reward_uin_count': '0', 'msg_daily_idx': '1',
                           'is_original': '0', 'uin': '777', 'key': '777',
                           'pass_ticket': 'Bh6wUrwOuRK6bdMZUJLMQVn%252BuWp%252FeYUKJGC8JQi6j9ur9g7M5Dnkqd1IkLMdl9vx',
                           'wxtoken': '777', 'clientversion': '16070322',
                           'appmsg_token': '981_6d7aomE8h60z%2FI6LMRUaIbqpDvs1xB-b4s_1WW3nEzXoHtOjf_r0ZkgOCdoDgg8-BiTuIAE5luqyKgGF',
                           'x5': '0'} # appmsg_token 记得用最新的

        # url转义处理
        content_url = html.unescape(post.content_url)
        # 截取content_url的查询参数部分
        content_url_params = urlsplit(content_url).query
        # 将参数转化为字典类型
        content_url_params = utils.str_to_dict(content_url_params, "&", "=")
        # 更新到data_url
        data_url_params.update(content_url_params)
        body = "is_only_read=1&req_id=0414NBNjylwrVHDydtl3ufse&pass_ticket=zpU4AwNXTGS5LfBXFx4NCyMo5YTpSQo9RarrPG3tjhmMaGfORzykNNviX7IlM4i0&is_temp_url=0"
        data = utils.str_to_dict(body, "&", "=")

        # 通过Fiddler 获取 最新的值
        headers = """
Host: mp.weixin.qq.com
Cookie: devicetype=iOS12.0.1; lang=zh_CN; pass_ticket=Bh6wUrwOuRK6bdMZUJLMQVn+uWp/eYUKJGC8JQi6j9ur9g7M5Dnkqd1IkLMdl9vx; version=16070322; wap_sid2=CPD+necIElxUU3NDTEJnRTJCdTJfVjFpRWhPZ0lhR1pUcHU1YUNlV04yY1h5bmRZcjRlRmVYSERHVmN3blRpa2xGX1R3YXdQQTlRQ2tUS0RrUVJ5R0VQZHhwTC1STlVEQUFBfjCfyereBTgNQJVO; wxuin=2363981680; wxtokenkey=777; rewardsn=; pgv_pvid=7217329857; _scan_has_moon=1; eas_sid=Z1z5O3U2s463w5G6j5W456a0o7; tvfe_boss_uuid=37f32a121348f925; pgv_pvi=5114346496; sd_cookie_crttime=1525167542515; sd_userid=86141525167542515
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
X-WECHAT-KEY: a0cc14df085a9a74023ef29370ae3b8b7e5f555a3602f46cfcd1aa46b37966130e7048379a523d8103d9957e069a9c83f806e2b4062e5262847ebb98b5b30606e0a3fb5fe0d1c7cbd7dd79414222aceb
X-WECHAT-UIN: MjM2Mzk4MTY4MA%3D%3D
If-Modified-Since: Thu, 1 Nov 2018 14:02:05 +0800
User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 12_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/16A404 MicroMessenger/6.7.3(0x16070321) NetType/WIFI Language/zh_CN
Accept-Language: zh-cn
Accept-Encoding: br, gzip, deflate
Connection: keep-alive

        """

        headers = utils.str_to_dict(headers)

        data_url = "https://mp.weixin.qq.com/mp/getappmsgext"

        r = requests.post(data_url, data=data, verify=False, params=data_url_params, headers=headers)

        result = r.json()
        if result.get("appmsgstat"):
            post['read_num'] = result.get("appmsgstat").get("read_num")
            post['like_num'] = result.get("appmsgstat").get("like_num")
            post['reward_num'] = result.get("reward_total_count")
            post['u_date'] = datetime.now()
            logger.info("「%s」read_num: %s like_num: %s reward_num: %s" %
                        (post.title, post['read_num'], post['like_num'], post['reward_num']))
            post.save()
        else:
            logger.warning(u"没有获取的真实数据，请检查请求参数是否正确，返回的数据为：data=%s" % r.text)
            exit()


if __name__ == '__main__':
    # 直接运行这份代码很定或报错，或者根本抓不到数据
    # 因为header里面的cookie信息已经过去，还有URL中的appmsg_token也已经过期
    # 你需要配合Fiddler或者charles通过手机重新加载微信公众号的更多历史消息
    # 从中获取最新的headers和appmsg_token替换上面
    crawler = WeiXinCrawler()
    crawler.crawl()
    # s = "__biz=MjM5MzgyODQxMQ==&appmsg_type=9&mid=2650367540&sn=ef9c6353a9255dbc00e2beac7f449dad&idx=1&scene=27&title=Python%E5%A5%87%E6%8A%80%E6%B7%AB%E5%B7%A7%EF%BC%8C%E7%9C%8B%E7%9C%8B%E4%BD%A0%E7%9F%A5%E9%81%93%E5%87%A0%E4%B8%AA&ct=1511410410&abtest_cookie=AwABAAoADAANAAcAJIgeAGSIHgD8iB4A7IkeAAaKHgAPih4AU4oeAAAA&devicetype=android-24&version=/mmbizwap/zh_CN/htmledition/js/appmsg/index3a9713.js&f=json&r=0.04959653583814139&is_need_ad=0&comment_id=1411699821&is_need_reward=1&both_ad=0&reward_uin_count=24&msg_daily_idx=1&is_original=0&uin=777&key=777&pass_ticket=zpU4AwNXTGS5LfBXFx4NCyMo5YTpSQo9RarrPG3tjhmMaGfORzykNNviX7IlM4i0&wxtoken=1922467438&devicetype=android-24&clientversion=26051732&appmsg_token=938_0n0in1TAhMHhtZ7zXIOyxTxYXZEFW7ez7tXTmochNzKXa19P3wxK6-C-yM1omM_h7gSMZJmyv7glw98g&x5=1&f=json"
    # print(utils.str_to_dict(s, "&", "="))
    #
    for post in Post.objects(reward_num=0):
        crawler.update_post(post)
        time.sleep(1)

