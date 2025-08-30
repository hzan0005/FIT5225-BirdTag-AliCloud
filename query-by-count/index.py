# index.py for query-by-count function
import json
import time  # <--- 新增导入
from tablestore import *

# --- 请确保这些配置与你之前的函数一致 ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.ots-internal.aliyuncs.com"  # <--- 注意：这里建议使用 ots-internal 地址
OTS_INSTANCE_NAME = "n01xiizqc116"
TABLE_NAME = 'media_metadata'


# ---------------------------------------------

def handler(event, context):
    print(f"Received event: {event}")

    # 步骤一：【必须先做】解析事件
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
        ots_client = OTSClient(
            end_point=OTS_ENDPOINT,
            access_key_id=creds.access_key_id,
            access_key_secret=creds.access_key_secret,
            instance_name=OTS_INSTANCE_NAME,
            sts_token=creds.security_token
        )

        session_pk = [('token', token)]
        _, row, _ = ots_client.get_row('sessions', session_pk, columns_to_get=['user_email', 'expires_at'])

        if not row or not row.attribute_columns:
            raise ValueError("Invalid token.")

        session_info = {col[0]: col[1] for col in row.attribute_columns}
        expires_at = session_info.get('expires_at')

        if not expires_at or time.time() > expires_at:
            # （可选）在这里可以从数据库中删除已过期的token
            ots_client.delete_row('sessions', Row(session_pk))
            raise ValueError("Token has expired.")

        current_user_email = session_info.get('user_email')
        print(f"Token validation successful for user: {current_user_email}")

    except Exception as e:
        # Token 验证失败，立即返回 401 错误
        return {"statusCode": 401, "body": json.dumps({"error": f"Unauthorized: {e}"})}

    # 步骤三：【Token验证通过后】才执行业务逻辑

    # 1. 从POST请求的body中解析查询条件
    try:
        query_tags = json.loads(event_dict.get('body', '{}'))
        if not query_tags or not isinstance(query_tags, dict):
            raise ValueError("Query tags must be a non-empty JSON object.")
    except (json.JSONDecodeError, ValueError) as e:
        return {"statusCode": 400, "body": json.dumps({"error": f"Invalid request body: {e}"})}

    print(f"Searching for files matching counts: {query_tags}")

    # 2. 扫描全表并根据数量要求进行过滤 (注意: ots_client 已在上面初始化，无需重复)
    results = []
    try:
        inclusive_start_primary_key = [('file_url', INF_MIN)]
        exclusive_end_primary_key = [('file_url', INF_MAX)]

        # 使用循环来处理可能有多页的扫描结果
        while True:
            consumed, next_start_primary_key, row_list, next_token = ots_client.get_range(
                TABLE_NAME,
                Direction.FORWARD,
                inclusive_start_primary_key,
                exclusive_end_primary_key,
                limit=100
            )

            for row in row_list:
                columns = {col[0]: col[1] for col in row.attribute_columns}
                tags_json = columns.get('tags')

                if tags_json:
                    db_tags = json.loads(tags_json)

                    # --- 核心过滤逻辑 ---
                    is_match = True
                    for species, min_count in query_tags.items():
                        if db_tags.get(species, 0) < min_count:
                            is_match = False
                            break

                    if is_match:
                        file_url = columns.get('thumbnail_url') or row.primary_key[0][1]
                        results.append(file_url)

            if not next_start_primary_key:
                break
            inclusive_start_primary_key = next_start_primary_key

    except Exception as e:
        print(f"Error querying Tablestore: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to query database."})}

    print(f"Found {len(results)} matching files.")

    # 3. 返回结果
    response_body = {"links": results}
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json", "Content-Disposition": "inline"},
        "body": json.dumps(response_body)
    }