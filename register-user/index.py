# index.py for register-user function
import json
import traceback
import hashlib # 用于密码哈希
from tablestore import *

# --- 配置信息 ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.vpc.tablestore.aliyuncs.com"
OTS_INSTANCE_NAME = "n01xiizqc116"
USER_TABLE_NAME = 'users'
# ------------------

def handler(event, context):
    try:
        # 1. 解析请求 body
        event_str = event.decode('utf-8')
        event_dict = json.loads(event_str)
        body = json.loads(event_dict.get('body', '{}'))
        email = body['email']
        password = body['password']

        if not email or not password:
            raise ValueError("Email and password are required.")

        # 2. 初始化客户端
        creds = context.credentials
        ots_client = OTSClient(end_point=OTS_ENDPOINT, access_key_id=creds.access_key_id, access_key_secret=creds.access_key_secret, instance_name=OTS_INSTANCE_NAME, sts_token=creds.security_token)

        # 3. 检查用户是否已存在
        primary_key = [('email', email)]
        _, row, _ = ots_client.get_row(USER_TABLE_NAME, primary_key)
        if row:
            return {"statusCode": 409, "body": json.dumps({"error": "User with this email already exists."})}

        # 4. 对密码进行哈希处理 (绝不能明文存储密码！)
        password_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

        # 5. 将新用户信息写入数据库
        attribute_columns = [('password_hash', password_hash)]
        row = Row(primary_key, attribute_columns)
        condition = Condition(RowExistenceExpectation.IGNORE)
        ots_client.put_row(USER_TABLE_NAME, row, condition)

        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "User registered successfully."})
        }

    except Exception as e:
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}