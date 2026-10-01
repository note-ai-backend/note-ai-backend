from flask import Flask, request, jsonify
from flask_cors import CORS

import requests
import json
import time
import os


# =========================================================
# Flask
# =========================================================

app = Flask(__name__)

CORS(app)


# =========================================================
# Configuration
# =========================================================

FIREBASE_KEY = os.getenv(
    "FIREBASE_KEY",
    "AIzaSyA27E7jUV8osRY7NzwP2fZwGoTkp5gJhZw"
)

SEARCH_URL = os.getenv(
    "SEARCH_URL",
    "https://ai-multi-search-backend-321697147922.europe-west6.run.app/ask"
)

APP_VERSION = "1.2.8"

SEARCH_ID = "b2ed082e-5793-4de0-9e42-c8c7fb57b5d5"


# =========================================================
# Firebase Headers
# =========================================================

FIREBASE_HEADERS = {
    "User-Agent": (
        "Dalvik/2.1.0 (Linux; U; Android 16; "
        "2311DRK48G Build/BP2A.250605.031.A3)"
    ),
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json",
    "X-Android-Package": "com.lmtechstudio.aimultisearch",
    "X-Android-Cert": (
        "5D08264B44E0E53FBCCC70B4F016474CC6C5AB5C"
    ),
    "Accept-Language": "ar-EG, en-US",
    "X-Client-Version": (
        "Android/Fallback/X23001000/FirebaseCore-Android"
    ),
    "X-Firebase-GMPID": (
        "1:321697147922:android:"
        "26e6fb8e30dcc23dfffccb"
    ),
    "X-Firebase-Client": (
        "H4sIAAAAAAAA_6tWykhNLCpJSk0sKVayio7VUSpLLSrOzM9TslIyUqoFAFyivEQfAAAA"
    )
}


# =========================================================
# Token
# =========================================================

token = None
token_expiry = 0


def get_token():

    global token
    global token_expiry

    if token and time.time() < token_expiry - 60:
        return token

    response = requests.post(
        "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser",
        params={
            "key": FIREBASE_KEY
        },
        data=json.dumps({
            "clientType": "CLIENT_TYPE_ANDROID"
        }),
        headers=FIREBASE_HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "idToken" not in data:
        raise Exception(
            "Firebase error: " + str(data)
        )

    token = "Bearer " + data["idToken"]

    token_expiry = (
        time.time()
        + int(data.get("expiresIn", 3600))
    )

    return token


# =========================================================
# Note AI Prompt
# =========================================================

def make_fusha_prompt(text):

    return f"""
أنت Note AI، مساعد ذكاء اصطناعي متخصص في تحويل
اللهجة المصرية والعامية العربية إلى العربية الفصحى.

مهمتك:

- افهم المعنى المقصود من النص.
- حوّل العامية إلى عربية فصحى طبيعية.
- حافظ على المعنى الأصلي بالكامل.
- لا تضف معلومات جديدة.
- لا تحذف معلومات من النص.
- صحح الأخطاء الإملائية والنحوية.
- لا تترجم النص إلى لغة أخرى.
- حافظ على أسماء الأشخاص والأماكن والأرقام.
- حافظ على ترتيب الأفكار.
- لا تشرح ما قمت به.
- لا تكتب مقدمة.
- أخرج النص الفصيح النهائي فقط.
- لا تستخدم الجداول.
- لا تستخدم رمز |.

مثال:

العامية:
انا مش عارف اروح فين

الفصحى:
لا أعرف إلى أين أذهب.

مثال:

العامية:
كنت عايز اكلمك امبارح بس كنت مشغول

الفصحى:
كنت أرغب في التحدث إليك أمس، لكنني كنت مشغولًا.

مثال:

العامية:
هو قاللي انه هيخلص الشغل بكرة

الفصحى:
أخبرني أنه سينتهي من العمل غدًا.

النص المطلوب تحويله:

{text}
""".strip()


# =========================================================
# Llama
# =========================================================

def ask_llama(text):

    current_token = get_token()

    payload = {
        "provider": "llama",
        "prompt": make_fusha_prompt(text),
        "plan": "ULTRA",
        "app_version": APP_VERSION
    }

    headers = {
        "User-Agent": "okhttp/4.12.0",
        "Accept-Encoding": "gzip",
        "authorization": current_token,
        "x-plan": "ULTRA",
        "x-app-version": APP_VERSION,
        "x-search-id": SEARCH_ID,
        "x-search-expected": "2",
        "content-type": "application/json; charset=utf-8"
    }

    response = requests.post(
        SEARCH_URL,
        data=json.dumps(payload),
        headers=headers,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    if not data.get("ok"):
        raise Exception(
            data.get(
                "message",
                "Llama server returned an error."
            )
        )

    answer = data.get("answer")

    if not answer:
        raise Exception(
            "لم يرجع نموذج Llama أي نص."
        )

    return answer.strip()


# =========================================================
# Home
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "success": True,
        "service": "Note AI",
        "status": "online"
    })


# =========================================================
# Health
# =========================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify({
        "success": True,
        "service": "Note AI",
        "status": "healthy"
    })


# =========================================================
# Convert
# =========================================================

@app.route("/convert", methods=["POST"])
def convert():

    try:

        if not request.is_json:

            return jsonify({
                "success": False,
                "error": "Request must contain JSON."
            }), 400

        data = request.get_json(silent=True)

        if not data:

            return jsonify({
                "success": False,
                "error": "Invalid JSON."
            }), 400

        text = (
            data.get("text")
            or data.get("message")
            or data.get("prompt")
            or ""
        )

        text = str(text).strip()

        if not text:

            return jsonify({
                "success": False,
                "error": "النص فارغ."
            }), 400

        if len(text) > 10000:

            return jsonify({
                "success": False,
                "error": "النص طويل جدًا."
            }), 400

        result = ask_llama(text)

        return jsonify({
            "success": True,
            "input": text,
            "output": result,
            "answer": result
        })

    except requests.exceptions.Timeout:

        return jsonify({
            "success": False,
            "error": "انتهت مهلة الاتصال."
        }), 504

    except requests.exceptions.ConnectionError:

        return jsonify({
            "success": False,
            "error": "تعذر الاتصال بخادم الذكاء الاصطناعي."
        }), 503

    except requests.exceptions.RequestException as e:

        return jsonify({
            "success": False,
            "error": "خطأ في الاتصال بخادم Llama.",
            "details": str(e)
        }), 502

    except Exception as e:

        print("ERROR:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# Run
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )