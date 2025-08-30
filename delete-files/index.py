# index.py for delete-files function
import json
import traceback
import oss2
import time
from tablestore import *
from urllib.parse import urlparse

# --- 请确保这些配置与你之前的函数一致 ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.vpc.tablestore.aliyuncs.com"
OTS_INSTANCE_NAME = "n01xiizqc116"
TABLE_NAME = 'media_metadata'


# ---------------------------------------------

def parse_s3_url(url):
    """从 OSS URL 中解析出 Bucket 名称和 Object Key"""
    parsed_url = urlparse(url)
    bucket_name = parsed_url.netloc.split('.')[0]
    object_key = parsed_url.path.lstrip('/')
    return bucket_name, object_key


# ---【 这是修正后的 handler 函数 】---
def handler(event, context):
    print(f"Received event: {event}")

    # 步骤一：【必须先做】解析事件，确保 event_dict 存在
    try:
        event_str = event.decode('utf-8')
        event_dict = json.loads(event_str)
    except Exception as e:
        # 如果连事件本身都无法解析，直接返回一个通用错误
        print(f"FATAL: Could not parse event data. Error: {e}")
        return {"statusCode": 400, "body": json.dumps({"error": "Failed to parse event data."})}

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
        # Token 验证失败，返回 401
        print(f"Authorization failed: {e}")
        return {"statusCode": 401, "body": json.dumps({"error": f"Unauthorized: {e}"})}

    # 步骤三：【Token验证通过后】才执行业务逻辑
    try:
        request_body = json.loads(event_dict.get('body', '{}'))
        urls_to_delete = request_body['urls']
        if not isinstance(urls_to_delete, list):
            raise ValueError("'urls' must be a list.")

        # 初始化OSS客户端 (auth对象需要creds)
        auth = oss2.StsAuth(creds.access_key_id, creds.access_key_secret, creds.security_token)
        oss_endpoint = f"https://oss-{context.region}.aliyuncs.com"

        deleted_count = 0
        errors = []

        for url in urls_to_delete:
            # ... (这里的 for 循环删除逻辑保持不变) ...
            primary_key = [('file_url', url)]
            # ... a, b, c, d 删除步骤 ...

            # (省略了详细的删除步骤以保持简洁，你的原有删除逻辑是正确的)
            _, row, _ = ots_client.get_row(TABLE_NAME, primary_key, columns_to_get=['thumbnail_url'])
            thumbnail_url = None
            if row and row.attribute_columns:
                columns = {col[0]: col[1] for col in row.attribute_columns}
                thumbnail_url = columns.get('thumbnail_url')

            bucket_name, object_key = parse_s3_url(url)
            bucket = oss2.Bucket(auth, oss_endpoint, bucket_name)
            bucket.delete_object(object_key)

            if thumbnail_url:
                thumb_bucket_name, thumb_object_key = parse_s3_url(thumbnail_url)
                bucket.delete_object(thumb_object_key)

            condition = Condition(RowExistenceExpectation.IGNORE)
            ots_client.delete_row(TABLE_NAME, Row(primary_key), condition)

            deleted_count += 1

        response_body = {
            "message": f"Deletion completed. {deleted_count} items processed successfully.",
            "errors": errors
        }
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Content-Disposition": "inline"},
            "body": json.dumps(response_body)
        }

    except Exception as e:
        print(f"An error occurred during business logic execution: {e}")
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": "An internal error occurred."})}
