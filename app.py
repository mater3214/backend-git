from flask import Flask, jsonify, request
import requests
from flask_cors import CORS 
import psycopg2
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
LINE_ACCESS_TOKEN = "0wrW85zf5NXhGWrHRjwxitrZ33JPegxtB749lq9TWRlrlCvfl0CKN9ceTw+kzPqBc6yjEOlV3EJOqUsBNhiFGQu3asN1y6CbHIAkJINhHNWi5gY9+O3+SnvrPaZzI7xbsBuBwe8XdIx33wdAN+79bgdB04t89/1O/w1cDnyilFU="


app = Flask(__name__)


cors = CORS(app, resources={
    r"/*": {
        "origins": [
            "https://my-frontend-51dy.onrender.com",
            "http://localhost:3000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "expose_headers": ["Content-Type"]
    }
})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://my-frontend-51dy.onrender.com')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Expose-Headers', 'Content-Type')
    return response

# PostgreSQL config
DB_NAME = 'flask_pg'
DB_USER = 'flask_pg_user'
DB_PASSWORD = 'N5U6ELzotV0Zog1lG1pRDzNYtiMzgCQg'
DB_HOST = 'dpg-d18dv3ruibrs73bq92ug-a.singapore-postgres.render.com'
DB_PORT = 5432

# Google Sheets config
SHEET_NAME = 'Tickets'  # ชื่อ Google Sheet ที่มีข้อมูล
WORKSHEET_NAME = 'sheet1'  # หรือชื่อ sheet ที่มีข้อมูล
CREDENTIALS_FILE = 'credentials.json'  # path ไปยังไฟล์ service account

@app.before_request
def log_request_info():
    app.logger.debug('Headers: %s', request.headers)
    app.logger.debug('Body: %s', request.get_data())

def send_textbox_message(user_id, message_text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    # Create a more informative Flex Message
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "flex",
                "altText": "ข้อความจากเจ้าหน้าที่",
                "contents": {
                    "type": "bubble",
                    "size": "giga",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📬 ข้อความจากเจ้าหน้าที่",
                                "weight": "bold",
                                "size": "lg",
                                "color": "#FFFFFF",
                                "align": "center"
                            }
                        ],
                        "backgroundColor": "#005BBB",
                        "paddingAll": "20px"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": message_text,
                                "wrap": True,
                                "margin": "md"
                            },
                            {
                                "type": "separator",
                                "margin": "md"
                            },
                            {
                                "type": "text",
                                "text": "คุณสามารถตอบกลับได้โดยการกดปุ่ม 'เมนูเลือกติดต่อหน้าที่อีกครั้ง' ⚠️หากมีปัญหาสอบถาม",
                                "size": "sm",
                                "color": "#888888",
                                "margin": "md",
                                "wrap": True
                            }
                        ],
                        "paddingAll": "20px"
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ขอบคุณที่ใช้บริการของเรา",
                                "size": "xs",
                                "color": "#888888",
                                "align": "center"
                            }
                        ],
                        "paddingAll": "10px"
                    }
                }
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"LINE API Error: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending LINE message: {str(e)}")
        return False

def notify_user(payload):
    try:
        # Check if user_id exists and LINE_ACCESS_TOKEN is configured
        if not payload.get('user_id') or not LINE_ACCESS_TOKEN:
            print("LINE notification skipped - missing user_id or access token")
            return False

        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
        }

        # Format appointment date if exists
        appointment_date = '-'
        if payload.get('appointment'):
            try:
                dt = datetime.strptime(payload['appointment'], '%Y-%m-%d %H:%M:%S')
                appointment_date = dt.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                appointment_date = payload['appointment']

        # Create flex message
        flex_message = {
            "type": "flex",
            "altText": "Ticket Status Update",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📢 Ticket Status Update",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#005BBB"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "text",
                            "text": f"Ticket ID: {payload.get('ticket_id', 'N/A')}",
                            "margin": "md"
                        },
                        {
                            "type": "text",
                            "text": f"Status: {payload.get('status', 'N/A')}",
                            "margin": "sm"
                        },
                        {
                            "type": "text",
                            "text": f"Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                            "margin": "sm",
                            "size": "sm",
                            "color": "#666666"
                        },
                        {
                            "type": "text",
                            "text": f"Appointment: {appointment_date}",
                            "margin": "sm",
                            "size": "sm"
                        }
                    ]
                }
            }
        }

        # Prepare payload
        message = {
            "to": payload['user_id'],
            "messages": [flex_message]
        }

        response = requests.post(url, headers=headers, json=message, timeout=10)
        
        if response.status_code != 200:
            print(f"LINE API Error: {response.status_code} - {response.text}")
            return False
            
        print(f"Notification sent to user {payload['user_id']}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Request error in notify_user: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error in notify_user: {str(e)}")
        return False



def create_flex_message(payload):
    try:
        appointment_date = '-'
        if payload.get('appointment'):
            try:
                dt = datetime.strptime(payload['appointment'], '%Y-%m-%d %H:%M:%S')
                appointment_date = dt.strftime('%d/%m/%Y %H:%M')
            except ValueError:
                appointment_date = payload['appointment']
        
        status = payload.get('status', 'ไม่ระบุ')
        status_color = {
            'Pending': '#FF9900',
            'Completed': '#00AA00',
            'Rejected': '#FF0000',
            'In Progress': '#0066FF',
            'Waiting': '#8b5cf6'
        }.get(status, '#666666')

        return {
            "type": "flex",
            "altText": "อัปเดตสถานะ Ticket ของคุณ",
            "contents": {
                "type": "bubble",
                "size": "giga",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📢 อัปเดตสถานะ Ticket",
                            "weight": "bold",
                            "size": "lg",
                            "color": "#FFFFFF",
                            "align": "center"
                        }
                    ],
                    "backgroundColor": "#005BBB",
                    "paddingAll": "20px"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "หมายเลข",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": payload.get('ticket_id', ''),
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "ชื่อ",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": payload.get('name', ''),
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "แผนก",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": payload.get('department', ''),
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "เบอร์ติดต่อ",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": payload.get('phone', ''),
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "Type",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": payload.get('type', ''),
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "ปัญหา",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": payload.get('report', 'ไม่มีข้อมูล'),
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end",
                                    "wrap": True
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "separator",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "horizontal",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "วันที่นัดหมาย",
                                    "weight": "bold",
                                    "size": "sm",
                                    "flex": 2,
                                    "color": "#666666"
                                },
                                {
                                    "type": "text",
                                    "text": appointment_date,
                                    "size": "sm",
                                    "flex": 4,
                                    "align": "end"
                                }
                            ],
                            "spacing": "sm",
                            "margin": "md"
                        },
                        {
                            "type": "box",
                            "layout": "vertical",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "สถานะล่าสุด",
                                    "weight": "bold",
                                    "size": "sm",
                                    "color": "#666666",
                                    "margin": "md"
                                },
                                {
                                    "type": "text",
                                    "text": status,
                                    "weight": "bold",
                                    "size": "xl",
                                    "color": status_color,
                                    "align": "center",
                                    "margin": "sm"
                                }
                            ],
                            "backgroundColor": "#F5F5F5",
                            "cornerRadius": "md",
                            "margin": "xl",
                            "paddingAll": "md"
                        }
                    ],
                    "spacing": "md",
                    "paddingAll": "20px"
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ขอบคุณที่ใช้บริการของเรา",
                            "size": "xs",
                            "color": "#888888",
                            "align": "center"
                        }
                    ],
                    "paddingAll": "10px"
                }
            }
        }
    except Exception as e:
        print(f"Error creating flex message: {str(e)}")
        return None


def sync_google_sheet_to_postgres():
    new_tickets = []
    
    try:
        # 1. Connect to Google Sheets only if credentials exist
        if not os.path.exists('credentials.json'):
            print("❌ credentials.json not found, skipping Google Sheets sync")
            return []
            
        scope = ['https://spreadsheets.google.com/feeds', 
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Open Sheet and Worksheet with error handling
        try:
            sheet = client.open('Tickets').worksheet('sheet1')
            records = sheet.get_all_records()
        except gspread.exceptions.SpreadsheetNotFound:
            print("❌ Google Sheet 'Tickets' not found")
            return []
        except gspread.exceptions.WorksheetNotFound:
            print("❌ Worksheet 'sheet1' not found")
            return []
        
        if not records:
            print("⚠️ No data found in Google Sheet")
            return []
            
        # 2. Connect to PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # 3. Get existing ticket IDs from PostgreSQL for comparison
        cur.execute("SELECT ticket_id FROM tickets")
        existing_tickets = {row[0] for row in cur.fetchall()}
        
        # 4. Process each row from Google Sheets
        for row in records:
            try:
                ticket_id = str(row.get('Ticket ID', ''))
                if not ticket_id:
                    continue

                # Get current textbox value from PostgreSQL
                cur.execute("SELECT textbox FROM tickets WHERE ticket_id = %s", (ticket_id,))
                current_textbox = cur.fetchone()
                current_textbox = current_textbox[0] if current_textbox else None
                
                new_textbox = str(row.get('TEXTBOX', '')) if row.get('TEXTBOX') else None
                
                # Check if textbox has changed and is not empty
                if new_textbox and new_textbox != current_textbox:
                    # If message is from User (not Admin)
                    if not new_textbox.startswith("Admin:"):
                        user_name = str(row.get('ชื่อ', 'Unknown')) if row.get('ชื่อ') else 'Unknown'
                        cur.execute("""
                            INSERT INTO messages (
                                ticket_id, sender_name, message, is_admin_message
                            ) VALUES (%s, %s, %s, %s)
                        """, (ticket_id, user_name, new_textbox, False))
                        
                        # Create notification
                        notification_msg = f"New message from {user_name} for ticket {ticket_id}: {new_textbox}"
                        cur.execute("INSERT INTO notifications (message) VALUES (%s)", (notification_msg,))

                # Prepare data for upsert
                ticket_data = (
                    ticket_id,
                    row.get('User ID', ''),
                    row.get('อีเมล', ''),
                    row.get('ชื่อ', ''),
                    row.get('เบอร์ติดต่อ', ''),
                    row.get('แผนก', ''),
                    parse_datetime(row.get('วันที่แจ้ง', '')),
                    row.get('สถานะ', ''),
                    row.get('Appointment', ''),
                    row.get('Requeste', ''),
                    row.get('Report', ''),
                    row.get('Type', ''),
                    new_textbox
                )

                # Upsert ticket data
                cur.execute("""
                    INSERT INTO tickets (
                        ticket_id, user_id, email, name, phone,
                        department, created_at, status, appointment,
                        requested, report, type, textbox
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticket_id) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        email = EXCLUDED.email,
                        name = EXCLUDED.name,
                        phone = EXCLUDED.phone,
                        department = EXCLUDED.department,
                        created_at = EXCLUDED.created_at,
                        status = EXCLUDED.status,
                        appointment = EXCLUDED.appointment,
                        requested = EXCLUDED.requested,
                        report = EXCLUDED.report,
                        type = EXCLUDED.type,
                        textbox = CASE 
                            WHEN EXCLUDED.textbox != '' THEN EXCLUDED.textbox 
                            ELSE tickets.textbox 
                        END
                """, ticket_data)

                # Check if this is a new ticket
                if ticket_id not in existing_tickets:
                    new_tickets.append(row)
                    message = f"New ticket created: #{ticket_id} - {row.get('ชื่อ', '')} ({row.get('แผนก', '')})"
                    cur.execute("INSERT INTO notifications (message) VALUES (%s)", (message,))

            except Exception as e:
                print(f"❌ Error syncing row {row.get('Ticket ID', 'N/A')}: {str(e)}")
                conn.rollback()
                continue

        conn.commit()
        print(f"✅ Synced {len(records)} rows from Google Sheets")
        
    except gspread.exceptions.APIError as e:
        print(f"❌ Google Sheets API Error: {str(e)}")
        return []
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {str(e)}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error in sync_google_sheet_to_postgres: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()
    
    return new_tickets

def parse_datetime(date_str):
    """Helper function to parse datetime from string with multiple format support"""
    if not date_str:
        return None
        
    # Try multiple datetime formats
    formats = [
        '%Y-%m-%d %H:%M:%S',  # 2023-01-01 12:34:56
        '%Y-%m-%d',            # 2023-01-01
        '%d/%m/%Y %H:%M',      # 01/01/2023 12:34
        '%d/%m/%Y',            # 01/01/2023
        '%m/%d/%Y %H:%M:%S',   # 01/01/2023 12:34:56 (US format)
        '%m/%d/%Y %H:%M',      # 01/01/2023 12:34 (US format)
        '%m/%d/%Y',            # 01/01/2023 (US format)
        '%Y/%m/%d %H:%M:%S',   # 2023/01/01 12:34:56
        '%Y/%m/%d %H:%M',      # 2023/01/01 12:34
        '%Y/%m/%d',            # 2023/01/01
        '%d-%m-%Y %H:%M:%S',   # 01-01-2023 12:34:56
        '%d-%m-%Y %H:%M',      # 01-01-2023 12:34
        '%d-%m-%Y',            # 01-01-2023
        '%Y%m%d%H%M%S',        # 20230101123456 (compact format)
        '%Y%m%d'               # 20230101 (compact format)
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
            
    print(f"⚠️ Could not parse date string: {date_str}")
    return None

@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, message, timestamp, read 
            FROM notifications 
            ORDER BY timestamp DESC 
            LIMIT 20
        """)
        
        notifications = []
        for row in cur.fetchall():
            notifications.append({
                "id": row[0],
                "message": row[1],
                "timestamp": row[2].isoformat(),
                "read": row[3]
            })
        
        return jsonify(notifications)
    except Exception as e:
        print(f"Error in get_notifications: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# Add a route to mark notifications as read
@app.route('/mark-notification-read', methods=['POST'])
def mark_notification_read():
    data = request.json
    notification_id = data.get('id')
    
    if not notification_id:
        return jsonify({"error": "Notification ID required"}), 400
    
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET read = TRUE WHERE id = %s", (notification_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

# Add a route to mark all notifications as read
@app.route('/mark-all-notifications-read', methods=['POST'])
def mark_all_notifications_read():
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET read = TRUE WHERE read = FALSE")
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

def create_tickets_table():
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets (
        ticket_id TEXT PRIMARY KEY,
        user_id TEXT,
        email TEXT,
        name TEXT,
        phone TEXT,
        department TEXT,
        created_at TIMESTAMP,
        status TEXT,
        appointment TEXT,
        requested TEXT,
        report TEXT,
        type TEXT,
        textbox TEXT
    );
    """)
    
    # Add notifications table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read BOOLEAN DEFAULT FALSE
    );
    """)
    
    # เพิ่มตาราง messages สำหรับเก็บประวัติการสนทนา
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        ticket_id TEXT REFERENCES tickets(ticket_id),
        admin_id TEXT,
        sender_name TEXT,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_read BOOLEAN DEFAULT FALSE,
        is_admin_message BOOLEAN DEFAULT FALSE
    );
    """)
    
    conn.commit()
    conn.close()


def parse_datetime(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None
  
@app.route('/api/data', methods=['GET'])
def get_data():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT ticket_id, email, name, phone, department, 
                   created_at, status, appointment, 
                   requested, report, type, textbox 
            FROM tickets;
        """)
        rows = cur.fetchall()
        conn.close()
        
        result = [
            {
                "Ticket ID": row[0],
                "อีเมล": row[1],
                "ชื่อ": row[2],
                "เบอร์ติดต่อ": row[3],
                "แผนก": row[4],
                "วันที่แจ้ง": row[5].isoformat() if row[5] else "",
                "สถานะ": row[6],
                "Appointment": row[7],
                "Requeste": row[8],
                "Report": row[9],
                "Type": row[10],
                "TEXTBOX": row[11]
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_data: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

@app.route('/sync-tickets', methods=['GET'])
def sync_tickets():
    try:
        create_tickets_table()
        sync_google_sheet_to_postgres()
        
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT ticket_id, email, name, phone, department, 
                   created_at, status, appointment, 
                   requested, report, type, textbox 
            FROM tickets;
        """)
        rows = cur.fetchall()
        conn.close()
        
        result = [
            {
                "Ticket ID": row[0],
                "อีเมล": row[1],
                "ชื่อ": row[2],
                "เบอร์ติดต่อ": row[3],
                "แผนก": row[4],
                "วันที่แจ้ง": row[5].isoformat() if row[5] else "",
                "สถานะ": row[6],
                "Appointment": row[7],
                "Requeste": row[8],
                "Report": row[9],
                "Type": row[10],
                "TEXTBOX": row[11]
            }
            for row in rows
        ]
        return jsonify(result)
    except Exception as e:
        print(f"Error in sync_tickets: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/update-status', methods=['POST'])
def update_status():
    data = request.json
    ticket_id = data.get("ticket_id")
    new_status = data.get("status")

    if not ticket_id or not new_status:
        return jsonify({"error": "ticket_id and status required"}), 400

    conn = None
    try:
        # 1. Update PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, 
            host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()

        # Get current status and user info
        cur.execute("""
            SELECT status, user_id, name, email, phone, department, 
                   created_at, appointment, requested, report, type, textbox 
            FROM tickets WHERE ticket_id = %s
        """, (ticket_id,))
        
        result = cur.fetchone()
        if not result:
            return jsonify({"error": "Ticket not found"}), 404
            
        current_status = result[0]
        ticket_data = {
            'ticket_id': ticket_id,
            'user_id': result[1],
            'name': result[2],
            'email': result[3],
            'phone': result[4],
            'department': result[5],
            'created_at': result[6],
            'appointment': result[7],
            'requested': result[8],
            'report': result[9],
            'type': result[10],
            'textbox': result[11]
        }

        # Only proceed if status is actually changing
        if current_status != new_status:
            # Update status in database
            cur.execute("""
                UPDATE tickets SET status = %s 
                WHERE ticket_id = %s
                RETURNING status
            """, (new_status, ticket_id))
            
            updated_status = cur.fetchone()[0]
            
            # Create notification
            message = f"Ticket #{ticket_id} ({ticket_data['name']}) changed from {current_status} to {updated_status}"
            cur.execute("INSERT INTO notifications (message) VALUES (%s)", (message,))
            
            conn.commit()
            
            # 2. Update Google Sheets if credentials exist
            if os.path.exists('credentials.json'):
                scope = ['https://spreadsheets.google.com/feeds', 
                        'https://www.googleapis.com/auth/drive']
                creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
                client = gspread.authorize(creds)
                
                try:
                    sheet = client.open('Tickets').worksheet('sheet1')
                    cell = sheet.find(ticket_id)
                    
                    if cell:
                        headers = sheet.row_values(1)
                        if "สถานะ" in headers:
                            status_col = headers.index("สถานะ") + 1
                            sheet.update_cell(cell.row, status_col, new_status)
                            
                            # Prepare payload for LINE notification
                            ticket_data['status'] = new_status
                            notify_user(ticket_data)
                            
                            return jsonify({
                                "message": "✅ Updated both PostgreSQL and Google Sheets",
                                "status": new_status
                            })
                    return jsonify({"error": "Ticket ID not found in sheet"}), 404
                except Exception as e:
                    print(f"Google Sheets update error: {str(e)}")
                    return jsonify({
                        "message": "✅ Updated PostgreSQL but failed to update Google Sheets",
                        "status": new_status
                    })
            else:
                print("⚠️ credentials.json not found, skipping Google Sheets update")
                return jsonify({
                    "message": "✅ Updated PostgreSQL only",
                    "status": new_status
                })
        else:
            return jsonify({"message": "Status unchanged", "status": current_status})
            
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/delete-ticket', methods=['POST'])
def delete_ticket():
    data = request.json
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        return jsonify({"error": "Ticket ID is required"}), 400

    try:
        # 1. ลบจาก PostgreSQL
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, 
            host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()
        
        # ตรวจสอบว่ามี ticket นี้หรือไม่
        cur.execute('SELECT ticket_id FROM tickets WHERE ticket_id = %s', (ticket_id,))
        if not cur.fetchone():
            conn.close()
            return jsonify({"error": "Ticket not found in database"}), 404
        
        # ลบจาก PostgreSQL
        cur.execute('DELETE FROM tickets WHERE ticket_id = %s', (ticket_id,))
        conn.commit()
        conn.close()

        # 2. ลบจาก Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        # หาแถวที่ต้องการลบ
        try:
            cell = sheet.find(ticket_id)
            if cell:
                # ลบแถวใน Google Sheets
                sheet.delete_rows(cell.row)
                
                # สร้าง notification
                conn = psycopg2.connect(
                    dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, 
                    host=DB_HOST, port=DB_PORT
                )
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO notifications (message) VALUES (%s)",
                    (f"Ticket {ticket_id} has been deleted",)
                )
                conn.commit()
                conn.close()
                
                return jsonify({"success": True, "message": "Ticket deleted from both PostgreSQL and Google Sheets"})
            else:
                return jsonify({"error": "Ticket not found in Google Sheets"}), 404
        except gspread.exceptions.CellNotFound:
            return jsonify({"error": "Ticket not found in Google Sheets"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/delete', methods=['POST'])
def delete_messages():
    data = request.json
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        return jsonify({"error": "Ticket ID is required"}), 400

    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    
    try:
        # ลบข้อความทั้งหมดที่เกี่ยวข้องกับ ticket_id นี้
        cur.execute("""
            DELETE FROM messages 
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        conn.commit()
        return jsonify({"success": True, "message": "Messages deleted successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/auto-clear-textbox', methods=['POST'])
def auto_clear_textbox():
    data = request.json
    ticket_id = data.get('ticket_id')

    if not ticket_id:
        return jsonify({"error": "Ticket ID is required"}), 400

    try:
        # เชื่อมต่อกับฐานข้อมูล
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, 
            password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()

        # ลบข้อมูลในตาราง tickets
        cur.execute("""
            UPDATE tickets 
            SET textbox = '' 
            WHERE ticket_id = %s
        """, (ticket_id,))

        # อัปเดต Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        cell = sheet.find(ticket_id)
        if cell:
            headers = sheet.row_values(1)
            if "TEXTBOX" in headers:
                textbox_col = headers.index("TEXTBOX") + 1
                sheet.update_cell(cell.row, textbox_col, '')

        conn.commit()
        return jsonify({"success": True, "message": "Textbox cleared automatically"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/clear-textboxes', methods=['POST'])
def clear_textboxes():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, 
            password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()

        # 1. ค้นหา tickets ที่มี textbox ไม่ว่าง
        cur.execute("""
            SELECT ticket_id FROM tickets 
            WHERE textbox IS NOT NULL AND textbox != ''
        """)
        tickets_with_textbox = [row[0] for row in cur.fetchall()]

        # 2. ลบ textbox ใน PostgreSQL
        cur.execute("""
            UPDATE tickets 
            SET textbox = '' 
            WHERE textbox IS NOT NULL AND textbox != ''
        """)

        # 3. อัปเดต Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # ตรวจสอบว่าไฟล์ credentials.json มีอยู่
        if not os.path.exists('credentials.json'):
            print("❌ credentials.json not found, skipping Google Sheets update")
            conn.commit()
            return jsonify({
                "success": True,
                "cleared_count": len(tickets_with_textbox),
                "message": f"Cleared {len(tickets_with_textbox)} textboxes in database only"
            })
            
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        headers = sheet.row_values(1)
        if "TEXTBOX" in headers:
            textbox_col = headers.index("TEXTBOX") + 1
            
            for ticket_id in tickets_with_textbox:
                try:
                    cell = sheet.find(ticket_id)
                    if cell:
                        sheet.update_cell(cell.row, textbox_col, '')
                except gspread.exceptions.CellNotFound:
                    continue

        conn.commit()
        return jsonify({
            "success": True,
            "cleared_count": len(tickets_with_textbox),
            "message": f"Cleared {len(tickets_with_textbox)} textboxes"
        })

    except Exception as e:
        print(f"Error in clear_textboxes: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
            

@app.route('/refresh-messages', methods=['POST'])
def refresh_messages():
    data = request.json
    ticket_id = data.get('ticket_id')
    admin_id = data.get('admin_id')

    if not ticket_id:
        return jsonify({"error": "Ticket ID is required"}), 400

    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    
    try:
        # ดึงข้อความล่าสุด
        cur.execute("""
            SELECT id, ticket_id, admin_id, sender_name, message, 
                   timestamp, is_read, is_admin_message
            FROM messages
            WHERE ticket_id = %s
            ORDER BY timestamp ASC
        """, (ticket_id,))
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                "id": row[0],
                "ticket_id": row[1],
                "admin_id": row[2],
                "sender_name": row[3],
                "message": row[4],
                "timestamp": row[5].isoformat(),
                "is_read": row[6],
                "is_admin_message": row[7]
            })
        
        # ทำเครื่องหมายว่าข้อความถูกอ่านแล้ว
        if admin_id:
            cur.execute("""
                UPDATE messages
                SET is_read = TRUE
                WHERE ticket_id = %s 
                AND (admin_id IS NULL OR admin_id = %s)
                AND is_read = FALSE
            """, (ticket_id, admin_id))
        
        conn.commit()
        return jsonify({"messages": messages, "success": True})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/update-textbox', methods=['POST', 'OPTIONS'])
def update_textbox():
    if request.method == 'OPTIONS':
        return '', 200

    if request.content_type != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.json
    ticket_id = data.get("ticket_id")
    new_text = data.get("textbox")
    is_announcement = data.get("is_announcement", False)

    if not ticket_id or new_text is None:
        return jsonify({"error": "ticket_id and text required"}), 400

    # 1. Update PostgreSQL
    try:
        with psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, 
            host=DB_HOST, port=DB_PORT
        ) as conn:
            with conn.cursor() as cur:
                # Get current textbox value for comparison
                cur.execute("SELECT textbox, user_id, name FROM tickets WHERE ticket_id = %s", (ticket_id,))
                result = cur.fetchone()
                
                if not result:
                    return jsonify({"error": "Ticket not found"}), 404
                    
                current_text, user_id, name = result
                
                # Only proceed if text is actually changing
                if current_text != new_text:
                    # Update textbox
                    cur.execute("UPDATE tickets SET textbox = %s WHERE ticket_id = %s", (new_text, ticket_id))
                    
                    # Create notification (ไม่สร้าง notification สำหรับประกาศ)
                    if not is_announcement:
                        message = f"New message for ticket {ticket_id} ({name}): {new_text}"
                        cur.execute("INSERT INTO notifications (message) VALUES (%s)", (message,))
                    
                    # Send LINE message if user_id exists
                    if user_id and not is_announcement:
                        send_textbox_message(user_id, new_text)
                        
                    conn.commit()
    except psycopg2.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    # 2. Update Google Sheets
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        cell = sheet.find(ticket_id)
        if cell:
            headers = sheet.row_values(1)
            if "TEXTBOX" in headers:
                textbox_col = headers.index("TEXTBOX") + 1
                sheet.update_cell(cell.row, textbox_col, new_text)
            return jsonify({"message": "✅ Updated textbox in PostgreSQL and Google Sheets"})
        return jsonify({"error": "Ticket ID not found in sheet"}), 404
    except Exception as e:
        return jsonify({"error": f"Google Sheets error: {str(e)}"}), 500

@app.route('/api/email-rankings', methods=['GET'])
def get_email_rankings():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, 
            user=DB_USER, 
            password=DB_PASSWORD, 
            host=DB_HOST, 
            port=DB_PORT
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT email, COUNT(*) as ticket_count
            FROM tickets
            WHERE email IS NOT NULL AND email != ''
            GROUP BY email
            ORDER BY ticket_count DESC
            LIMIT 5
        """)
        
        rankings = [
            {"email": row[0], "count": row[1]}
            for row in cur.fetchall()
        ]
        
        return jsonify(rankings)
    except Exception as e:
        print(f"Error in get_email_rankings: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/send-announcement', methods=['POST'])
def send_announcement():
    data = request.json
    announcement_message = data.get('message')

    if not announcement_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()

        # 1. ดึงรายชื่อผู้ใช้ทั้งหมดที่ต้องการส่งประกาศ
        cur.execute("""
            SELECT ticket_id, user_id, email, name 
            FROM tickets 
            WHERE type = 'Information' 
            AND user_id IS NOT NULL
        """)
        recipients = cur.fetchall()

        recipient_count = 0
        full_message = f"{announcement_message}"

        # 2. อัปเดต TEXTBOX และส่ง LINE Message
        for recipient in recipients:
            ticket_id, user_id, email, name = recipient
            
            # อัปเดต TEXTBOX ใน PostgreSQL
            cur.execute(
                "UPDATE tickets SET textbox = %s WHERE ticket_id = %s",
                (full_message, ticket_id)
            )

            # ส่ง LINE Message
            if user_id:
                send_announcement_message(user_id, full_message, name)
                recipient_count += 1

        # 3. อัปเดต Google Sheets
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        headers = sheet.row_values(1)
        if "TEXTBOX" in headers:
            textbox_col = headers.index("TEXTBOX") + 1
            # หาแถวทั้งหมดที่ต้องการอัปเดต
            for recipient in recipients:
                ticket_id = recipient[0]
                try:
                    cell = sheet.find(ticket_id)
                    if cell:
                        sheet.update_cell(cell.row, textbox_col, full_message)
                except gspread.exceptions.CellNotFound:
                    continue

        # 4. สร้าง notification ในระบบ
        cur.execute(
            "INSERT INTO notifications (message) VALUES (%s)",
            (f"ประกาศใหม่: {announcement_message}",)
        )

        conn.commit()
        return jsonify({
            "success": True,
            "recipient_count": recipient_count,
            "message": "Announcement sent successfully"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()




def send_announcement_message(user_id, message, recipient_name=None):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    # สร้าง Flex Message สำหรับประกาศ
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "flex",
                "altText": "ประกาศจากระบบ",
                "contents": {
                    "type": "bubble",
                    "size": "giga",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📢 ประกาศจากระบบ",
                                "weight": "bold",
                                "size": "lg",
                                "color": "#FFFFFF",
                                "align": "center"
                            }
                        ],
                        "backgroundColor": "#FF6B6B",  # สีแดงสำหรับประกาศ
                        "paddingAll": "20px"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": message,
                                "wrap": True,
                                "margin": "md"
                            },
                            {
                                "type": "separator",
                                "margin": "md"
                            },
                            {
                                "type": "text",
                                "text": "นี่คือข้อความประกาศจากระบบ กรุณาอ่านให้ละเอียด",
                                "size": "sm",
                                "color": "#888888",
                                "margin": "md",
                                "wrap": True
                            }
                        ],
                        "paddingAll": "20px"
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ขอบคุณที่ใช้บริการของเรา",
                                "size": "xs",
                                "color": "#888888",
                                "align": "center"
                            }
                        ],
                        "paddingAll": "10px"
                    }
                }
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"LINE API Error: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending LINE announcement: {str(e)}")
        return False

def send_textbox_message(user_id, message_text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }

    # Create a more informative Flex Message
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "flex",
                "altText": "ข้อความจากเจ้าหน้าที่",
                "contents": {
                    "type": "bubble",
                    "size": "giga",
                    "header": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "📬 ข้อความจากเจ้าหน้าที่",
                                "weight": "bold",
                                "size": "lg",
                                "color": "#FFFFFF",
                                "align": "center"
                            }
                        ],
                        "backgroundColor": "#005BBB",
                        "paddingAll": "20px"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": message_text,
                                "wrap": True,
                                "margin": "md"
                            },
                            {
                                "type": "separator",
                                "margin": "md"
                            },
                            {
                                "type": "text",
                                "text": "คุณสามารถตอบกลับได้โดยการกดปุ่ม 'เมนูเลือกติดต่อหน้าที่อีกครั้ง' ⚠️หากมีปัญหาสอบถาม",
                                "size": "sm",
                                "color": "#888888",
                                "margin": "md",
                                "wrap": True
                            }
                        ],
                        "paddingAll": "20px"
                    },
                    "footer": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ขอบคุณที่ใช้บริการของเรา",
                                "size": "xs",
                                "color": "#888888",
                                "align": "center"
                            }
                        ],
                        "paddingAll": "10px"
                    }
                }
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"LINE API Error: {response.status_code} - {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending LINE message: {str(e)}")
        return False

@app.route('/delete-notification', methods=['POST'])
def delete_notification():
    data = request.json
    notification_id = data.get('id')
    
    if not notification_id:
        return jsonify({"error": "Notification ID required"}), 400
    
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("DELETE FROM notifications WHERE id = %s", (notification_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/api/data-by-date', methods=['GET'])
def get_data_by_date():
    date_str = request.args.get('date')
    
    
    if not date_str:
        return jsonify({"error": "Date parameter is required"}), 400
    
    try:
        # แปลงวันที่เป็นรูปแบบที่ PostgreSQL เข้าใจ
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # กำหนดช่วงเวลาเป็นทั้งวัน (00:00:00 - 23:59:59)
        start_datetime = datetime.combine(selected_date, datetime.min.time())
        end_datetime = datetime.combine(selected_date, datetime.max.time())
        
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, 
            host=DB_HOST, port=DB_PORT
        )
        cur = conn.cursor()
        
        # คิวรี่ข้อมูลโดยใช้ created_at
        cur.execute("""
            SELECT ticket_id, email, name, phone, department, 
                   created_at, status, appointment, 
                   requested, report, type, textbox 
            FROM tickets 
            WHERE created_at BETWEEN %s AND %s
            ORDER BY created_at DESC
        """, (start_datetime, end_datetime))
        
        rows = cur.fetchall()
        result = [
            {
                "Ticket ID": row[0],
                "อีเมล": row[1],
                "ชื่อ": row[2],
                "เบอร์ติดต่อ": row[3],
                "แผนก": row[4],
                "วันที่แจ้ง": row[5].isoformat() if row[5] else "",
                "สถานะ": row[6],
                "Appointment": row[7],
                "Requeste": row[8],
                "Report": row[9],
                "Type": row[10],
                "TEXTBOX": row[11]
            }
            for row in rows
        ]
        if not rows:
            return jsonify({"message": "No data found for the selected date", "data": []})
        return jsonify(result)
    
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()  

@app.route('/update-ticket', methods=['POST', 'OPTIONS'])
def update_ticket():
    if request.method == 'OPTIONS':
        return '', 200  # สำหรับ CORS preflight

    if request.content_type != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.json
    ticket_id = data.get("ticket_id")
    new_status = data.get("status")
    new_textbox = data.get("textbox")

    if not ticket_id:
        return jsonify({"error": "ticket_id is required"}), 400

    # --- 1. อัปเดต PostgreSQL ---
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    if new_status is not None:
        cur.execute("UPDATE tickets SET status = %s WHERE ticket_id = %s;", (new_status, ticket_id))
    if new_textbox is not None:
        cur.execute("UPDATE tickets SET textbox = %s WHERE ticket_id = %s;", (new_textbox, ticket_id))
    conn.commit()
    conn.close()

    # --- 2. อัปเดต Google Sheets ---
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

    try:
        cell = sheet.find(ticket_id)
        headers = sheet.row_values(1)
        if new_status is not None and "สถานะ" in headers:
            status_col = headers.index("สถานะ") + 1
            sheet.update_cell(cell.row, status_col, new_status)
        if new_textbox is not None and "TEXTBOX" in headers:
            textbox_col = headers.index("TEXTBOX") + 1
            sheet.update_cell(cell.row, textbox_col, new_textbox)
    except gspread.exceptions.CellNotFound:
        return jsonify({"error": "Ticket ID not found in sheet"}), 404

    return jsonify({"message": "✅ Ticket updated in PostgreSQL and Google Sheets"})

@app.route('/api/messages', methods=['GET'])
def get_messages():
    ticket_id = request.args.get('ticket_id')
    
    if ticket_id == "announcement":
        return jsonify([])
        
    if not ticket_id:
        return jsonify({"error": "Ticket ID is required"}), 400

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, ticket_id, admin_id, sender_name, 
                   message, timestamp, is_read, is_admin_message
            FROM messages
            WHERE ticket_id = %s
            ORDER BY timestamp ASC
        """, (ticket_id,))
        
        messages = []
        for row in cur.fetchall():
            messages.append({
                "id": row[0],
                "ticket_id": row[1],
                "admin_id": row[2],
                "sender_name": row[3],
                "message": row[4],
                "timestamp": row[5].isoformat(),
                "is_read": row[6],
                "is_admin_message": row[7]
            })
        
        return jsonify(messages)
    except Exception as e:
        print(f"Error in get_messages: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/messages', methods=['POST'])
def add_message():
    data = request.json
    ticket_id = data.get('ticket_id')
    admin_id = data.get('admin_id')
    sender_name = data.get('sender_name')
    message = data.get('message')
    is_admin_message = data.get('is_admin_message', False)

    if not all([ticket_id, sender_name, message]):
        return jsonify({"error": "Missing required fields"}), 400

    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    
    try:
        # เพิ่มข้อความใหม่
        cur.execute("""
            INSERT INTO messages (ticket_id, admin_id, sender_name, message, is_admin_message)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, timestamp
        """, (ticket_id, admin_id, sender_name, message, is_admin_message))
        
        new_message = cur.fetchone()
        
        # อัปเดต TEXTBOX ในตาราง tickets เป็นค่าว่างทันที
        cur.execute("""
            UPDATE tickets 
            SET textbox = '' 
            WHERE ticket_id = %s
        """, (ticket_id,))
        
        conn.commit()
        
        # อัปเดต Google Sheets ให้ textbox เป็นค่าว่าง
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

        try:
            cell = sheet.find(ticket_id)
            headers = sheet.row_values(1)
            if "TEXTBOX" in headers:
                textbox_col = headers.index("TEXTBOX") + 1
                sheet.update_cell(cell.row, textbox_col, '')
        except gspread.exceptions.CellNotFound:
            pass  # ไม่ต้องทำอะไรถ้าไม่พบ ticket ใน sheet
        
        return jsonify({
            "id": new_message[0],
            "timestamp": new_message[1].isoformat(),
            "success": True
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route('/api/messages/mark-read', methods=['POST'])
def mark_messages_read():
    data = request.json
    ticket_id = data.get('ticket_id')
    admin_id = data.get('admin_id')

    if not ticket_id:
        return jsonify({"error": "Ticket ID is required"}), 400

    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    
    # ทำเครื่องหมายว่าข้อความถูกอ่านแล้ว
    if admin_id:
        # ถ้ามี admin_id ให้ทำเครื่องหมายเฉพาะข้อความที่ admin นี้ยังไม่ได้อ่าน
        cur.execute("""
            UPDATE messages
            SET is_read = TRUE
            WHERE ticket_id = %s 
            AND (admin_id IS NULL OR admin_id = %s)
            AND is_read = FALSE
        """, (ticket_id, admin_id))
    else:
        # ถ้าไม่มี admin_id ให้ทำเครื่องหมายทุกข้อความ
        cur.execute("""
            UPDATE messages
            SET is_read = TRUE
            WHERE ticket_id = %s
            AND is_read = FALSE
        """, (ticket_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True})

@app.route('/sync-tickets')
def sync_route():
    create_tickets_table()
    new_tickets = sync_google_sheet_to_postgres()
    # Return all tickets after sync
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor()
    cur.execute("""SELECT ticket_id, email, name, phone, department, created_at, status, 
                  appointment, requested, report, type, textbox FROM tickets;""")
    rows = cur.fetchall()
    conn.close()
    
    result = [
        {
            "Ticket ID": row[0],
            "อีเมล": row[1],
            "ชื่อ": row[2],
            "เบอร์ติดต่อ": row[3],
            "แผนก": row[4],
            "วันที่แจ้ง": row[5].isoformat() if row[5] else "",
            "สถานะ": row[6],
            "Appointment": row[7],
            "Requeste": row[8],
            "Report": row[9],
            "Type": row[10],
            "TEXTBOX": row[11]
        }
        for row in rows
    ]
    return jsonify(result)

if __name__ == '__main__':
    create_tickets_table()
    sync_google_sheet_to_postgres()
    app.run(debug=True)