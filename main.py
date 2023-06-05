import re
import os
import sys
import time
import yaml
import glob
import datetime
import requests
import pandas as pd

from utils.constants import SHOPEE_REQUIRED_FIELDS, TIKI_REQUIRED_FIELDS
from utils import read_config, is_same_row, ensure_dir, parse_url, update_master_file


def fetch_data(itemid, shopid, flag='shopee'):
    """
    Fetch data from shopee.vn api and return json data
    API: https://shopee.vn/api/v4/item/get?itemid={itemid}&shopid={shopid}
    Raise exception if response status code is not 200
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    }
    if flag == 'shopee':
        url = f'https://shopee.vn/api/v4/item/get?itemid={itemid}&shopid={shopid}'
    elif flag == 'tiki':
        url = f'https://tiki.vn/api/v2/products/{shopid}?platform=web&spid={itemid}'
    else:
        # TODO: Developer add logic here
        pass
    
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f'Failed to fetch data from {url}')

    if flag == 'shopee':
        data = response.json().get('data')
    elif flag == 'tiki':
        data = response.json()
    else:
        # TODO: Developer add logic here
        pass

    if not data:
        raise Exception(f'Failed to fetch data from {url}')

    # required_fieds = [
    #     'itemid', 'shopid', 'name', 'description', 'price',
    #     'price_before_discount', 'stock', 'sold', 'item_status', 'image',
    #     'cmt_count', 'liked_count', 'shop_location'
    # ]

    # # validate data must have required fields
    # for field in required_fieds:
    #     if field not in data:
    #         raise Exception(f'Invalid data from {url}, missing {field}')

    shopee_rq = SHOPEE_REQUIRED_FIELDS
    tiki_rq = TIKI_REQUIRED_FIELDS

    if len(SHOPEE_REQUIRED_FIELDS) > len(TIKI_REQUIRED_FIELDS):
        tiki_rq = TIKI_REQUIRED_FIELDS + SHOPEE_REQUIRED_FIELDS[len(TIKI_REQUIRED_FIELDS): len(SHOPEE_REQUIRED_FIELDS)]
    else:
        shopee_rq = SHOPEE_REQUIRED_FIELDS.append(TIKI_REQUIRED_FIELDS[len(SHOPEE_REQUIRED_FIELDS): len(TIKI_REQUIRED_FIELDS)])
        
    # mapping fields to common fields
    data_f = {}
    for x,y in zip(shopee_rq, tiki_rq):
        if y in data:
            data_f[x] = data[y]
        else:
            data_f[x] = ""

    data_f["source"] = flag
    
    return data_f


def update_db(data):
    """
    Store update data info to ./data/info/{itemid}.yaml file in yaml format
    And append history  data to ./data/history/{itemid}.csv file
    Only append new row if new data is not same as last row or if file not exist

    File format {itemid}.yaml:

    ```yaml
    itemid: 5873954476
    shopid: 88201679
    name: Apple MacBook Air (2020) M1 Chip 13.3 inch 8GB 256GB SSD
    image: http://...
    description: ...
    shop_location: Ho Chi Minh City
    updated_at: 2020-05-01T00:00:00+07:00
    ```

    File format {itemid}.csv:

    ```csv
    time,date,itemid,price,discount,price_before_discount,stock,sold,item_status,cmt_count,liked_count
    1610003537,20200101,5873954476,1000000,0,1000000,100,0,normal,100,100
    1638204525,20200102,1587395447,6000000,0,1000000,99,1,normal,100,100
    1638204553,20200102,1587395447,6000000,0,1000000,98,2,normal,100,100
    ````
    """
    current_time = int(time.time())
    current_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))
    itemid = data.get('itemid')
    shopid = data.get('shopid')
    data['date'] = current_date

    # create ./data/info and ./data/history directory if not exist
    ensure_dir('./data/info')
    ensure_dir('./data/history')

    # update history file or create new file if not exist
    history_file = f'./data/history/{itemid}.csv'
    if os.path.exists(history_file):
        df = pd.read_csv(history_file)
    else:
        df = pd.DataFrame(columns=[
            'time', 'date', 'itemid', 'price', 'discount',
            'price_before_discount', 'stock', 'sold', 'item_status',
            'cmt_count', 'liked_count', 'source'
        ])

    # get the last rows of history file and convert to dict
    last_row = df.iloc[-1].to_dict() if len(df) > 0 else None
    if last_row and is_same_row(last_row, data, ignores=['time', 'itemid']):
        print(f'No update for {itemid}')
        return

    # append new row
    update_rows = {
            'time': current_time,
            'date': current_date,
            'itemid': itemid,
            'price': data.get('price'),
            'discount': data.get('discount'),
            'price_before_discount': data.get('price_before_discount'),
            'stock': data.get('stock'),
            'sold': data.get('sold'),
            'item_status': data.get('item_status'),
            'cmt_count': data.get('cmt_count'),
            'liked_count': data.get('liked_count'),
            'source': data.get('source')
        }
    new_update_df = pd.DataFrame(update_rows, index=[0])
    df = pd.concat([df, new_update_df])
    df.to_csv(history_file, index=False)
    print(f'Updated {history_file}')

    info_data = {
        'itemid': itemid,
        'shopid': shopid,
        'name': data.get('name'),
        'image': data.get('image'),
        'shop_location': data.get('shop_location'),
        'updated_at': datetime.datetime.now().isoformat()
    }
    # create or update info file
    info_file = f'./data/info/{itemid}.yaml'
    with open(info_file, 'w') as f:
        yaml.dump(info_data, f)
        print(f'Updated {info_file}')


def main():
    """
    Main function
    """
    # Reading configs
    config = read_config('config.yaml')
    urls = config.get('urls', [])
    print(f'Got {len(urls)} from config file')

    # Fetch data from shopee.vn api and update db
    for url in urls:
        try:
            print(f'Processing: {url}')
            itemid, shopid, flag = parse_url(url)
            data = fetch_data(itemid, shopid, flag)
            update_db(data)
        except Exception as e:
            print(f'Failed to process {url}')
            print(e)

    # This demontrate how to transform data and write to master file (output)
    update_master_file()


if __name__ == '__main__':
    main()
