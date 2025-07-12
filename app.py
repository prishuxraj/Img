# -*- coding: utf-8 -*-
from flask import Flask, render_template_string, request, redirect, url_for, session
import os, uuid, time, json, requests, urllib3
from datetime import datetime
import pytz

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.secret_key = 'secure-hosting-key'

IST = pytz.timezone("Asia/Kolkata")
IMAGES_DB = "images.json"  # Use /tmp for Render compatibility
images = {}
visitors = 0

IMG_API_KEY = "ce8f9e86c9a3257fdb7d19debb609840"
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

def save_data():
    try:
        with open(IMAGES_DB, 'w') as f:
            json.dump(images, f)
    except Exception as e:
        print("Error saving data:", e)

def load_data():
    global images
    if os.path.exists(IMAGES_DB):
        try:
            with open(IMAGES_DB) as f:
                images.update(json.load(f))
        except Exception as e:
            print("Error loading data:", e)
    else:
        with open(IMAGES_DB, "w") as f:
            json.dump({}, f)

@app.before_request
def set_user_id():
    global visitors
    if 'uid' not in session:
        session['uid'] = str(uuid.uuid4())
        session['first_visit'] = True
        visitors += 1

def upload_to_imgbb(file):
    try:
        with file.stream as f:
            res = requests.post(IMGBB_UPLOAD_URL, data={"key": IMG_API_KEY}, files={"image": f}, verify=False)
            if res.ok:
                data = res.json()
                return data["data"]["url"]
            else:
                print("Upload error:", res.status_code, res.text)
    except Exception as e:
        print("Upload exception:", e)
    return None

html_template = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Free Image Hosting By Prishu</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background: #fff;
      margin: 0;
      padding: 0 10px;
      text-align: center;
    }
    h1 { margin-top: 20px; color: #007BFF; }
    .info-bar {
      display: flex;
      justify-content: space-between;
      max-width: 700px;
      margin: 10px auto;
      padding: 10px;
      background: #f2f2f2;
      border-radius: 8px;
      font-size: 0.9em;
    }
    .upload-box, .preview {
      background: #f9f9f9;
      padding: 20px;
      margin: 20px auto;
      border-radius: 12px;
      max-width: 700px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .btn {
      padding: 8px 14px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.9em;
      margin: 4px;
    }
    .btn.copy { background: #ffc107; color: black; }
    .btn.download { background: #28a745; color: white; }
    .btn.link { background: #007bff; color: white; }
    input[type=file] { margin: 10px; }
    .link-box {
      background: #eee;
      padding: 6px;
      border-radius: 5px;
      margin: 10px 0;
      font-size: 0.9em;
      word-break: break-word;
    }
    .image-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      background: #fff;
      padding: 10px;
      margin: 15px auto;
      border-radius: 10px;
      border: 1px solid #ddd;
      box-shadow: 0 2px 6px rgba(0,0,0,0.05);
      max-width: 90%;
      width: 100%;
    }
    .image-box img {
      width: 100%;
      max-width: 300px;
      height: auto;
      border-radius: 10px;
      margin-bottom: 8px;
    }
    #loader-overlay {
      position: absolute;
      top: 0; left: 0;
      width: 100%; height: 100%;
      background: rgba(255,255,255,0.7);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 10;
    }
    #preview-wrapper { position: relative; }
    #previewArea img {
      width: 100px;
      height: 100px;
      margin: 5px;
      border-radius: 8px;
      border: 1px solid #ccc;
    }
    .album-link {
      background: #e6f7ff;
      border: 1px dashed #007bff;
      padding: 10px;
      margin-bottom: 15px;
      border-radius: 6px;
    }
    footer {
      text-align: center;
      font-size: 0.8em;
      color: #aaa;
      margin: 20px 0;
    }
  </style>
  <script>
    function copyToClipboard(id) {
      const text = document.getElementById(id).innerText;
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      alert("Copied to clipboard!");
    }

    function previewImages(input) {
      const preview = document.getElementById('previewArea');
      preview.innerHTML = '';
      const files = input.files;
      if (files) {
        for (let i = 0; i < files.length; i++) {
          const reader = new FileReader();
          reader.onload = function (e) {
            const img = document.createElement('img');
            img.src = e.target.result;
            preview.appendChild(img);
          };
          reader.readAsDataURL(files[i]);
        }
      }
    }

    function showLoader() {
      document.getElementById("loader-overlay").style.display = "flex";
    }

    function updateTime() {
      const now = new Date();
      document.getElementById("live-time").textContent = now.toLocaleTimeString();
    }
    setInterval(updateTime, 1000);
    window.onload = updateTime;
  </script>
</head>
<body>
  <h1>Free Image Hosting By Prishu</h1>

  <div class="info-bar">
    <div>👥 Visitors: {{ total_visitors }}</div>
    <div>⏰ <span id="live-time">{{ current_time.strftime('%H:%M:%S') }}</span></div>
    <div>📅 {{ current_time.strftime('%Y-%m-%d') }}</div>
  </div>

  {% if uploaded %}
    <div class="preview">
      {% if uploaded|length > 1 %}
        <div class="album-link">
          📁 Album Link:
          <div class="link-box" id="album_link">{{ request.host_url }}album/{{ album_id }}</div>
          <button class="btn copy" onclick="copyToClipboard('album_link')">Copy Album Link</button>
        </div>
      {% endif %}
      <h2>Uploaded Image{{ 's' if uploaded|length > 1 else '' }}</h2>
      {% for img in uploaded %}
        <div class="image-box">
  <img src="{{ img['url'] }}">
  {% set preview_link = request.host_url + 'view/' + img['fid'] %}
<div class="link-box" id="preview_{{ loop.index }}">{{ preview_link }}</div>
<button class="btn copy" onclick="copyToClipboard('preview_{{ loop.index }}')">Copy Preview Link</button>
<a class="btn download" href="{{ img['url'] }}" download target="_blank">Download</a>
</div>
      {% endfor %}
      <a href="{{ url_for('index') }}"><button class="btn link">⬅ Upload New Images</button></a>
    </div>
  {% endif %}

  <div class="upload-box">
    <form method="POST" enctype="multipart/form-data" onsubmit="showLoader()">
      <input type="file" name="images" multiple required onchange="previewImages(this)">
      <div id="preview-wrapper">
        <div id="loader-overlay">
          <img src="https://i.gifer.com/ZZ5H.gif" width="40" height="40">
        </div>
        <div id="previewArea" style="display:flex; flex-wrap:wrap; justify-content:center;"></div>
      </div>
      <button class="btn link" type="submit">Upload</button>
    </form>
  </div>

<footer>
  © {{ current_time.year }} Prisha Free Image Hosting. All rights reserved.<br>
  Developed by <a href="https://www.facebook.com/profile.php?id=61553498316814" target="_blank" style="color:inherit; text-decoration:none; font-weight:bold;">PRIISHU</a> | 
  For any help and support, <a href="https://www.facebook.com/Ramrajkumawat01" target="_blank" style="color:inherit; text-decoration:none; font-weight:bold;">Contact</a> us.
</footer>
</body>
</html>
"""

album_template = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Album Preview</title>
  <style>
    body {
      font-family: 'Segoe UI', sans-serif;
      background: #fff;
      margin: 0;
      padding: 20px;
      text-align: center;
      color: #333;
    }
    h2 { color: #007bff; }
    .image-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      background: #fff;
      padding: 10px;
      margin: 15px auto;
      border-radius: 10px;
      border: 1px solid #ddd;
      box-shadow: 0 2px 6px rgba(0,0,0,0.05);
      max-width: 90%;
      width: 100%;
    }
    .image-box img {
      width: 100%;
      max-width: 300px;
      height: auto;
      border-radius: 10px;
      margin-bottom: 8px;
    }
    .link-box {
      background: #eee;
      padding: 6px;
      margin: 10px 0;
      border-radius: 5px;
      font-size: 0.9em;
      word-break: break-word;
    }
    .btn {
      padding: 8px 14px;
      border: none;
      border-radius: 5px;
      cursor: pointer;
      font-size: 0.9em;
      margin: 4px;
    }
    .btn.copy { background: #ffc107; color: black; }
    .btn.download { background: #28a745; color: white; }
    .btn.link { background: #007bff; color: white; }
    footer {
      text-align: center;
      font-size: 0.8em;
      color: #aaa;
      margin: 20px 0;
    }
  </style>
  <script>
    function copyToClipboard(id) {
      const text = document.getElementById(id).innerText;
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      alert("Copied to clipboard!");
    }
  </script>
</head>
<body>
  <h2>📁 Album Preview</h2>
  {% for img in album_images %}
    <div class="image-box">
      <img src="{{ img['url'] }}">
      <div class="link-box" id="link_{{ loop.index }}">{{ img['url'] }}</div>
      <button class="btn copy" onclick="copyToClipboard('link_{{ loop.index }}')">Copy Link</button>
      <a class="btn download" href="{{ img['url'] }}" target="_blank" download>Download</a>
    </div>
  {% endfor %}
  <a href="{{ url_for('index') }}"><button class="btn link">⬅ Upload New Images</button></a>

  <footer>© 2025 | Prisha Free Image Hosting. All rights reserved.</footer>
</body>
</html>
"""

@app.route("/view/<fid>")
def view_image(fid):
    current_time = datetime.now(IST)
    img = images.get(fid)
    if not img:
        return "Not Found", 404
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Image Preview</title>
      <style>
        body {
          font-family: 'Segoe UI', sans-serif;
          background: #fff;
          margin: 0;
          padding: 0 10px;
          text-align: center;
        }
        h1 { margin-top: 20px; color: #007BFF; }
        .info-bar {
          display: flex;
          justify-content: space-between;
          max-width: 700px;
          margin: 10px auto 20px auto;
          padding: 10px;
          background: #f2f2f2;
          border-radius: 8px;
          font-size: 0.9em;
        }
        .btn {
          padding: 8px 14px;
          border: none;
          border-radius: 5px;
          cursor: pointer;
          font-size: 0.9em;
          margin: 10px 6px;
          font-weight: bold;
        }
        .btn.link {
          background: #007bff;
          color: white;
          margin-bottom: 20px;
        }
        .btn.download {
          background: #28a745;
          color: white;
        }
        .image-box {
          display: flex;
          flex-direction: column;
          align-items: center;
          background: #fff;
          padding: 20px;
          margin: 20px auto;
          border-radius: 10px;
          border: 1px solid #ddd;
          box-shadow: 0 4px 10px rgba(0,0,0,0.1);
          max-width: 700px;
          width: 100%;
        }
        .image-box img {
          width: 100%;
          max-width: 300px;
          height: auto;
          border-radius: 10px;
          margin-bottom: 12px;
        }
      </style>
      <script>
        function updateTime() {
          const now = new Date();
          document.getElementById("live-time").textContent = now.toLocaleTimeString();
        }
        setInterval(updateTime, 1000);
        window.onload = updateTime;
      </script>
    </head>
    <body>
      <h1>Free Image Hosting By Prishu</h1>

      <div class="info-bar" style="margin-bottom: 20px;">
        <div>👥 Visitors: {{ total_visitors }}</div>
        <div>⏰ <span id="live-time">{{ current_time.strftime('%H:%M:%S') }}</span></div>
        <div>📅 {{ current_time.strftime('%Y-%m-%d') }}</div>
      </div>

      <a class="btn link" style="margin-bottom: 20px;" href="{{ url_for('index') }}">⬅ Upload New Images</a>

      <div class="image-box">
        <img src="{{ img['url'] }}" alt="Preview">
        <a class="btn download" href="{{ img['url'] }}" download>⬇ Download in HD</a>
      </div>
    </body>
    </html>
    """, img=img, current_time=current_time, total_visitors=visitors)


@app.route("/", methods=["GET", "POST"])
def index():
    current_time = datetime.now(IST)
    if request.method == "POST":
        files = request.files.getlist("images")
        uploaded = []
        album_id = str(uuid.uuid4())
        for file in files:
            url = upload_to_imgbb(file)
            if url:
                fid = str(uuid.uuid4())
                images[fid] = {
                    "url": url,
                    "uploaded": time.time(),
                    "uploader": session['uid'],
                    "album": album_id
                }
                uploaded.append({"fid": fid, "url": url})
        save_data()
        return render_template_string(html_template, uploaded=uploaded, current_time=current_time, total_visitors=visitors, album_id=album_id)
    return render_template_string(html_template, uploaded=None, current_time=current_time, total_visitors=visitors)

@app.route("/album/<album_id>")
def album(album_id):
    album_images = [img for img in images.values() if img.get("album") == album_id]
    return render_template_string(album_template, album_images=album_images)

if __name__ == "__main__":
    load_data()
    app.run(debug=True, host="0.0.0.0", port=10000)
            
