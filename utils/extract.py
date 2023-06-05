import re
import sys


def parse_url(url):
    """
    Parse shopee.vn url to get itemid and shopid

    for example:
    url = https://shopee.vn/Apple-MacBook-Air-(2020)-M1-Chip-13.3-inch-8GB-256GB-SSD-i.88201679.5873954476
    itemid = 5873954476
    shopid = 88201679

    url = https://tiki.vn/api/v2/products/197216291?platform=web&spid=197216310
    itemid = 197216310
    shopid = 197216291
    """
    # is valid url?
    flag = ""
    itemid = ""
    shopid = ""
    
    if re.match(r'^https://shopee.vn/.*[0-9]+\.[0-9]+$', url):
        flag = "shopee"
        url_split = url.split('.')
        itemid = url_split[-1]
        shopid = url_split[-2]
    
    if re.match(r'^https:\/\/tiki.vn\/.*[0-9]+\?platform=web&spid=[0-9]+$', url):
        flag = "tiki"
        url_split = re.findall(".+\/(.*[0-9])+\?platform=web&spid=([0-9])", url)
        itemid = url_split[0][-1]
        shopid = url_split[0][-2]
    
    if flag == "":
        print('Invalid url')
        sys.exit(1)

    return itemid, shopid, flag
