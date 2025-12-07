
import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/accounts/login/"
REPORT_URL = f"{BASE_URL}/download_report/?student_id=4"

def run():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    
    # Login
    try:
        resp = opener.open(LOGIN_URL)
        csrftoken = ""
        for c in cj:
            if c.name == 'csrftoken': csrftoken = c.value
        
        login_data = urllib.parse.urlencode({
            'login': 'admin', 'password': 'testing123', 'csrfmiddlewaretoken': csrftoken
        }).encode('utf-8')
        req = urllib.request.Request(LOGIN_URL, data=login_data)
        req.add_header('Referer', LOGIN_URL)
        opener.open(req)
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # Head Request or Get
    try:
        resp = opener.open(REPORT_URL)
        disp = resp.headers.get('Content-Disposition')
        print(f"Content-Disposition: {disp}")
    except Exception as e:
        print(f"Check failed: {e}")

if __name__ == "__main__":
    run()
