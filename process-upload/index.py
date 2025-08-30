# index.py
import oss2
import json
from tablestore import *
from PIL import Image
import io
import bird_detector  # Import our refactored detection module
import time  # Import the time module for timestamps
import traceback  # Import traceback for detailed error logging

# --- CONFIGURATION ---
OTS_ENDPOINT = "https://n01xiizqc116.cn-hangzhou.vpc.tablestore.aliyuncs.com"
OTS_INSTANCE_NAME = "n01xiizqc116"
TABLE_NAME = 'media_metadata'
SESSION_TABLE_NAME = 'sessions'  # Added for authentication


# ---------------------

def create_thumbnail(image_bytes):
    """Generates a 200x200 thumbnail from image bytes."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((200, 200))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


def handler(event, context):
    """
    This is the main handler function that gets triggered by an OSS event.
    """
    # 1. Parse event and get OSS info
    evt = json.loads(event)
    bucket_name = evt['events'][0]['oss']['bucket']['name']
    object_key = evt['events'][0]['oss']['object']['key']
    region = evt['events'][0]['region']

    # Ignore files outside the 'uploads/' directory
    if not object_key.startswith('uploads/'):
        print(f"Object {object_key} is not in uploads/ directory, skipping.")
        return "Skipped"

    # 2. Initialize Tablestore client for authentication
    creds = context.credentials
    ots_client = OTSClient(
        end_point=OTS_ENDPOINT,
        access_key_id=creds.access_key_id,
        access_key_secret=creds.access_key_secret,
        instance_name=OTS_INSTANCE_NAME,
        sts_token=creds.security_token
    )

    # --- [START] NEW TOKEN AUTHENTICATION LOGIC ---
    try:
        print("Authenticating request...")
        # Get custom metadata from the OSS event
        user_meta = evt['events'][0]['oss']['object'].get('userMeta', {})
        token = user_meta.get('token')

        if not token:
            raise ValueError("Authorization token is missing from file metadata (x-oss-meta-token).")

        # Query the sessions table to validate the token
        session_pk = [('token', token)]
        _, row, _ = ots_client.get_row(SESSION_TABLE_NAME, session_pk, columns_to_get=['user_email', 'expires_at'])

        if not row or not row.attribute_columns:
            raise ValueError("Invalid token.")

        # Check if the token has expired
        session_info = {col[0]: col[1] for col in row.attribute_columns}
        expires_at = session_info.get('expires_at')

        if not expires_at or time.time() > expires_at:
            # Optionally, delete the expired token from the database
            ots_client.delete_row(SESSION_TABLE_NAME, Row(session_pk))
            raise ValueError("Token has expired.")

        current_user_email = session_info.get('user_email')
        print(f"Authentication successful for user: {current_user_email}")

    except Exception as e:
        # If authentication fails, log the error and stop execution.
        # We don't return an HTTP 401 because this is not a direct API call,
        # but we can log a clear error message.
        error_message = f"UNAUTHORIZED: {e}. File processing aborted for {object_key}."
        print(error_message)
        # Optionally, you could move the unauthorized file to a different prefix.
        return error_message
    # --- [END] NEW TOKEN AUTHENTICATION LOGIC ---

    # 3. Initialize OSS client and download the file
    auth = oss2.StsAuth(creds.access_key_id, creds.access_key_secret, creds.security_token)
    bucket = oss2.Bucket(auth, f'https://oss-{region}.aliyuncs.com', bucket_name)

    try:
        print(f"Processing file: {object_key}")
        remote_stream = bucket.get_object(object_key)
        file_content = remote_stream.read()
    except oss2.exceptions.NoSuchKey as e:
        print(f"Error: The object {object_key} does not exist. {e}")
        return "Failed: Object not found"

    # 4. Process the file: Detect birds and create thumbnail
    detected_tags = bird_detector.detect_birds_in_image(file_content)
    thumbnail_bytes = create_thumbnail(file_content)

    # 5. Upload thumbnail back to OSS
    thumbnail_url = None
    if thumbnail_bytes:
        thumbnail_key = object_key.replace('uploads/', 'thumbnails/').rsplit('.', 1)[0] + '-thumb.png'
        bucket.put_object(thumbnail_key, thumbnail_bytes)
        thumbnail_url = f'https://{bucket_name}.oss-{region}.aliyuncs.com/{thumbnail_key}'
        print(f"Thumbnail created and uploaded to: {thumbnail_key}")

    # 6. Save metadata to Tablestore
    original_file_url = f'https://{bucket_name}.oss-{region}.aliyuncs.com/{object_key}'
    primary_key = [('file_url', original_file_url)]

    attribute_columns = [
        ('tags', json.dumps(detected_tags)),
        ('file_type', 'image'),
        ('uploader', current_user_email)  # Add the uploader's email
    ]
    if thumbnail_url:
        attribute_columns.append(('thumbnail_url', thumbnail_url))

    row = Row(primary_key, attribute_columns)
    try:
        ots_client.put_row(TABLE_NAME, row)  # The condition is not needed for put_row
        print(f"Successfully saved metadata to Tablestore for: {original_file_url}")
    except Exception as e:
        print(f"Error saving metadata to Tablestore: {e}")
        return "Failed: Could not save metadata"

    # 7. Check subscriptions and generate notifications
    try:
        print("Checking subscriptions to generate notifications...")
        for tag in detected_tags.keys():
            inclusive_start_primary_key = [('tag', tag), ('user_email', INF_MIN)]
            exclusive_end_primary_key = [('tag', tag), ('user_email', INF_MAX)]

            _, _, subscribers, _ = ots_client.get_range('subscriptions', Direction.FORWARD, inclusive_start_primary_key,
                                                        exclusive_end_primary_key, limit=100)

            if subscribers:
                for subscriber_row in subscribers:
                    recipient_email = subscriber_row.primary_key[1][1]
                    notification_message = f"A new file with the tag '{tag}' has been added by {current_user_email}. URL: {original_file_url}"
                    timestamp_ms = int(time.time() * 1000)
                    notification_pk = [('recipient_email', recipient_email), ('timestamp', timestamp_ms)]
                    notification_cols = [('message', notification_message), ('is_sent', 'false')]
                    notification_row = Row(notification_pk, notification_cols)
                    condition = Condition(RowExistenceExpectation.IGNORE)
                    ots_client.put_row('notifications', notification_row, condition)
                    print(f"Successfully created notification for {recipient_email} for tag '{tag}'.")
    except Exception as e:
        print(f"[WARNING] Failed to generate notifications: {e}")
        traceback.print_exc()

    return 'Processing complete'