# index.py for search-by-file function
import json
import traceback
import base64
import time  # <--- 新增导入
from tablestore import *
# 假设你的AI模型检测代码在一个名为 bird_detector 的模块中
import bird_detector
# multipart/form-data 解析需要用到这个库
from requests_toolbelt.multipart import decoder

# --- 请确保这些配置与你之前的函数一致 ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.vpc.tablestore.aliyuncs.com"  # <-- 注意：建议使用 ots-internal Endpoint
OTS_INSTANCE_NAME = "n01xiizqc116"
TABLE_NAME = 'media_metadata'


# ---------------------------------------------

def handler(event, context):
    print("Received search-by-file request")

    # 步骤一：【必须先做】解析事件，确保 event_dict 存在
    try:
        event_str = event.decode('utf-8')
        event_dict = json.loads(event_str)
    except Exception as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Failed to parse event data: {e}"})}

    # 步骤二：【第二步】进行Token验证
    try:
        headers = event_dict.get('headers', {})
        token = headers.get('authorization') or headers.get('Authorization')
        if not token:
            raise ValueError("Authorization token is missing.")

        creds = context.credentials
        ots_client = OTSClient(end_point=OTS_ENDPOINT, access_key_id=creds.access_key_id,
                               access_key_secret=creds.access_key_secret, instance_name=OTS_INSTANCE_NAME,
                               sts_token=creds.security_token)

        session_pk = [('token', token)]
        _, row, _ = ots_client.get_row('sessions', session_pk, columns_to_get=['user_email', 'expires_at'])

        if not row or not row.attribute_columns:
            raise ValueError("Invalid token.")

        session_info = {col[0]: col[1] for col in row.attribute_columns}
        expires_at = session_info.get('expires_at')

        if not expires_at or time.time() > expires_at:
            ots_client.delete_row('sessions', Row(session_pk))
            raise ValueError("Token has expired.")

        print(f"Token validation successful for user: {session_info.get('user_email')}")

    except Exception as e:
        return {"statusCode": 401, "body": json.dumps({"error": f"Unauthorized: {e}"})}

    # 步骤三：【Token验证通过后】才执行业务逻辑
    try:
        # 1. 解析 multipart/form-data 请求体
        headers = event_dict.get('headers', {})
        content_type = None
        for key, value in headers.items():
            if key.lower() == 'content-type':
                content_type = value
                break

        if not content_type:
            raise ValueError("'Content-Type' header is missing.")
        body_bytes = base64.b64decode(event_dict['body'])
        multipart_data = decoder.MultipartDecoder(body_bytes, content_type)

        file_content = None
        for part in multipart_data.parts:
            if part.headers[b'Content-Disposition'].decode('utf-8').startswith('form-data; name="file"'):
                file_content = part.content
                break

        if not file_content:
            raise ValueError("Multipart form data with a 'file' part is required.")

        # 2. 调用AI模型分析文件，获取标签
        print("Analyzing uploaded file with AI model...")
        detected_tags = bird_detector.detect_birds_in_image(file_content)
        print(f"Detected tags from file: {detected_tags}")

        if not detected_tags:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Content-Disposition": "inline"},
                "body": json.dumps({"links": []})
            }

        # 3. 使用获取到的标签去数据库中查询 (注意：ots_client在Token验证时已创建)
        results = []
        inclusive_start_primary_key = [('file_url', INF_MIN)]
        exclusive_end_primary_key = [('file_url', INF_MAX)]
        consumed, next_start_primary_key, row_list, next_token = ots_client.get_range(
            TABLE_NAME, Direction.FORWARD, inclusive_start_primary_key, exclusive_end_primary_key, limit=100)

        for row in row_list:
            columns = {col[0]: col[1] for col in row.attribute_columns}
            tags_json = columns.get('tags')
            if tags_json:
                db_tags = json.loads(tags_json)
                is_match = any(tag in db_tags for tag in detected_tags.keys())
                if is_match:
                    file_url = columns.get('thumbnail_url') or row.primary_key[0][1]
                    results.append(file_url)

        # 4. 返回查询结果
        response_body = {"links": results}
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Content-Disposition": "inline"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"An error occurred during business logic execution: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "An internal error occurred during processing."})}