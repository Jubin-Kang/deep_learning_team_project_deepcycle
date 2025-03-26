import mysql.connector
import os
from dotenv import load_dotenv

import math

from datetime import datetime, timedelta

load_dotenv()

db_config = {
    'host': os.getenv('MYSQL_HOST'),
    'user': os.getenv('MYSQL_USER'),
    'password': os.getenv('MYSQL_PASSWORD'),
    'database': os.getenv('MYSQL_DATABASE'),
    'auth_plugin': 'mysql_native_password'
}

def get_connection():
    return mysql.connector.connect(**db_config)

def insert_image_result(image_name, deepcycle_center_id, image_size, deepcycle_material_code, confidence, result):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # MySQL에 넣기 위해 문자열 포맷
        save_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        query = """
            INSERT INTO deepcycle_log (image_name, deepcycle_center_id, image_size, deepcycle_material_code, confidence ,detection_info, save_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """


        cursor.execute(query, (image_name, deepcycle_center_id, image_size, deepcycle_material_code, confidence, result, save_date))
        conn.commit()

    except Exception as e:
        print(f"[DB Error] insert_image_result:")
        print(e)

    finally:
        cursor.close()
        conn.close()


def get_stats(start_date, end_date):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT result, COUNT(*) as count 
        FROM image_results
        WHERE created_at BETWEEN %s AND %s
        GROUP BY result
    """
    cursor.execute(query, (start_date, end_date))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results

def get_image_list_with_pagination(start_date, end_date, page, page_size, deepcycle_center_id, code):
    try:
        offset = (page - 1) * page_size

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        # 총 개수 가져오기
        count_sql = """
            SELECT COUNT(*) AS total
            FROM deepcycle_log
            WHERE save_date BETWEEN %s AND %s AND deepcycle_material_code = %s And deepcycle_center_id = %s
        """
        cursor.execute(count_sql, (start_date + ' 00:00:00', end_date + ' 23:59:59', code, deepcycle_center_id))
        total_count = cursor.fetchone()['total']
        total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0

        # 데이터 가져오기
        data_sql = """
            SELECT image_name, save_date, deepcycle_material_code
            FROM deepcycle_log
            WHERE deepcycle_material_code = %s AND deepcycle_center_id = %s AND save_date BETWEEN %s AND %s 
            ORDER BY save_date ASC
            LIMIT %s OFFSET %s
        """
        
        print(data_sql)

        print(start_date + ' 00:00:00', end_date + ' 23:59:59', code, deepcycle_center_id, page_size, offset)

        cursor.execute(data_sql, (code, deepcycle_center_id, start_date + ' 00:00:00', end_date + ' 23:59:59', page_size, offset))
        results = cursor.fetchall()

        # 이미지 리스트 구성
        image_list = []
        for row in results:
            image_url = f"http://192.168.0.48:5000/images/{row['image_name']}"
            image_list.append({
                "image_url": image_url,
                "image_name": row['image_name'],
                "save_date": row['save_date'].strftime("%Y-%m-%d %H:%M:%S")
            })

        print(image_list)

        return {
            "list": image_list,
            "total_count": total_count,
            "total_pages": total_pages
        }

    except Exception as e:
        print(f"[DB Error] get_image_list_with_pagination: {e}")
        return {
            "list": [],
            "total_count": 0,
            "total_pages": 0
        }

def get_material_to_code(material_name):
    material_name_to_code = {
        0: 'paper',
        1: 'can',
        2: 'glass',
        3: 'plastic',
        4: 'etc',
        5: 'general'
    }
    return material_name_to_code.get(material_name.lower(), 999)

def get_statistics(start_date, end_date, deepcycle_center_id, page, page_size):
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        sql = """
            SELECT 
                DATE(save_date) AS date,
                deepcycle_material_code,
                COUNT(*) AS count
            FROM 
                deepcycle_log
            WHERE 
                deepcycle_center_id = %s AND save_date BETWEEN %s AND %s
            GROUP BY 
                DATE(save_date), deepcycle_material_code
            ORDER BY 
                date ASC;
        """

        cursor.execute(sql, (deepcycle_center_id, start_date + ' 00:00:00', end_date + ' 23:59:59'))
        rows = cursor.fetchall()

        # material_code → name 매핑
        material_map = {
            0: 'paper',
            1: 'can',
            2: 'glass',
            3: 'plastic',
            4: 'etc',
            5: 'general'
        }

        # 날짜별로 통계 정리
        stats_dict = {}

        for row in rows:
            if isinstance(row["date"], str):
                date_obj = datetime.strptime(row["date"], "%Y-%m-%d")
            else:
                date_obj = row["date"]

            date_key = date_obj.strftime("%Y-%m-%d")

            material_name = material_map.get(row["deepcycle_material_code"], "unknown")

            if date_key not in stats_dict:
                stats_dict[date_key] = {
                    "date": date_key,
                    "plastic": 0,
                    "glass": 0,
                    "can": 0,
                    "paper": 0,
                    "etc": 0,
                    "general": 0
                }

            stats_dict[date_key][material_name] += row["count"]

        # 리스트 정렬
        all_results = list(stats_dict.values())
        all_results.sort(key=lambda x: x["date"])

        # ✅ 페이지네이션 처리
        total_count = len(all_results)
        total_pages = math.ceil(total_count / page_size) if page_size > 0 else 1
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paged_results = all_results[start_index:end_index]

        return {
            "list": paged_results,
            "total_count": total_count,
            "total_pages": total_pages,
            "page": page,
            "page_size": page_size
        }

    except Exception as e:
        print(f"[DB Error] get_statistics: {e}")
        return {
            "list": [],
            "total_count": 0,
            "total_pages": 0,
            "page": page,
            "page_size": page_size
        }