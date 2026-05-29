import os
import re
import json
import shutil
from datetime import datetime
from zipfile import ZipFile

# ========================
# CONFIG
# ========================
BASE_SCREENSHOT_DIR = r"C:/Users/SVC-Systems-TestPC/Log_Screenshot_files/screenshots"
LOGS_DIR = r"C:/Users/SVC-Systems-TestPC/Log_Screenshot_files/logs"
REPORT_DIR = r"C:/Users/SVC-Systems-TestPC/ThirdPartyHTMLReport"


os.makedirs(REPORT_DIR, exist_ok=True)

# ========================
# UTIL
# ========================
def timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def get_latest_run_folder(base_dir):
    folders = [
        os.path.join(base_dir, f)
        for f in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, f))
    ]
    folders.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    if not folders:
        raise Exception("No run folders found")

    print("Latest run folder:", folders[0])
    return folders[0]


def get_all_screenshots(dir_path):
    result = []
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.lower().endswith((".png", ".jpg", ".jpeg")):
                result.append(os.path.join(root, f))
    return result


def get_latest_log():
    if not os.path.exists(LOGS_DIR):
        return ""

    logs = [
        os.path.join(LOGS_DIR, f)
        for f in os.listdir(LOGS_DIR)
        if f.endswith(".log")
    ]

    logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)

    if not logs:
        return ""

    print("Latest log:", logs[0])

    with open(logs[0], "r", encoding="utf-8") as f:
        return f.read()


# ========================
# MAIN
# ========================
def main():
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    screenshots_dir = get_latest_run_folder(BASE_SCREENSHOT_DIR)
    screenshots = get_all_screenshots(screenshots_dir)
    log_content = get_latest_log()

    print("Screenshots found:", len(screenshots))

    # Copy screenshots
    report_screenshot_dir = os.path.join(REPORT_DIR, "screenshots")
    if os.path.exists(report_screenshot_dir):
        shutil.rmtree(report_screenshot_dir)

    os.makedirs(report_screenshot_dir)

    for file in screenshots:
        shutil.copy(file, report_screenshot_dir)

    # Load protocol
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print("BASE_DIR is :", BASE_DIR) 
    PROTOCOL_FILE = os.path.abspath(os.path.join(BASE_DIR,"protocol.json"))
    print("Looking for:", PROTOCOL_FILE)
    print("Exists:", os.path.exists(PROTOCOL_FILE))
    with open(PROTOCOL_FILE, "r") as f:
        protocol = json.load(f)

    pass_count = fail_count = log_missing = screenshot_missing = not_run = 0
    rows = ""
    index = 1

    for group in protocol:
        step = group["step"]

        for case in group["cases"]:
            screenshot = next(
                (f for f in screenshots if os.path.basename(f).startswith(case)),
                None
            )

            screenshot_name = os.path.basename(screenshot) if screenshot else None

            pass_match = re.search(rf"{case}\.png\s*:\s*(PASS|PASSED)", log_content, re.I)
            fail_match = re.search(rf"{case}\.png\s*:\s*(FAIL|FAILED)", log_content, re.I)

            if pass_match and screenshot:
                result = "PASS"
                pass_count += 1
            elif pass_match and not screenshot:
                result = "SCREENSHOT_MISSING"
                screenshot_missing += 1
            elif fail_match and screenshot:
                result = "FAIL"
                fail_count += 1
            elif fail_match and not screenshot:
                result = "SCREENSHOT_MISSING"
                screenshot_missing += 1
            elif not (pass_match or fail_match) and screenshot:
                result = "LOG_MISSING"
                log_missing += 1
            else:
                result = "NOT_RUN"
                not_run += 1

            rows += f"""
<tr class="{result}">
<td>{index}</td>
<td>{now}</td>
<td>{step}</td>
<td>{case}</td>
<td><span class="badge {result}">{result.replace("_"," ")}</span></td>
<td>{
    f'<img src="screenshots/{screenshot_name}" class="thumbnail" onclick="openModal(this.src)">' 
    if screenshot_name 
    else f'<span class="badge {result}">{result.replace("_"," ")}</span>'
}</td>
</tr>
"""
            index += 1

    total = index - 1
    executed = pass_count + fail_count + log_missing + screenshot_missing
    execution_percent = round((executed / total) * 100, 1) if total else 0

    # ========================
    # HTML (FULL UI)
    # ========================
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>Test Execution Report</title>

    <style>
    body {{ font-family: Arial; margin:20px; font-size:13px; }}

    h2 {{
      border-bottom:1px solid #ccc;
      padding-bottom:5px;
    }}

    table {{
      border-collapse: collapse;
      width:100%;
    }}

    th, td {{
      border:1px solid #ddd;
      padding:6px;
    }}

    th {{
      background:#2c3e50;
      color:white;
      position: sticky;
      top: 0;
    }}
    tr:hover {{
        background-color: #dfe6e9 !important;
    }}

    tr:nth-child(even) {{ background:#f9f9f9; }}

    .PASS {{ background:#d4edda; }}
    .FAIL {{ background:#f8d7da; }}
    .LOG_MISSING {{ background:#fff3cd; }}
    .SCREENSHOT_MISSING {{ background:#f5c6cb; }}
    .NOT_RUN {{ background:#e2e3e5; }}

    .badge {{
      padding:4px 8px;
      border-radius:12px;
      font-size:11px;
      font-weight:bold;
    }}

    .badge.PASS {{ background:#28a745; color:white; }}
    .badge.FAIL {{ background:#dc3545; color:white; }}
    .badge.LOG_MISSING {{ background:#ffc107; }}
    .badge.SCREENSHOT_MISSING {{background: #ff5722;color: white; border: 2px solid #d84315;font-weight: bold;}}
    .badge.NOT_RUN {{ background:#6c757d; color:white; }}

    .thumbnail {{
      width:80px;
      cursor:pointer;
    }}

    .card-container {{
      display:flex;
      gap:10px;
      margin-bottom:15px;
    }}

    .card {{
      flex:1;
      padding:10px;
      border-radius:6px;
      color:white;
      text-align:center;
    }}

    .card.total {{ background:#34495e; }}
    .card.pass {{ background:#28a745; }}
    .card.fail {{ background:#dc3545; }}
    .card.log {{ background:#ffc107; color:black; }}
    .card.shot {{ background:#fd7e14; }}
    .card.notrun {{ background:#6c757d; }}

    .btn {{
      padding:5px 10px;
      margin:3px;
      border-radius:20px;
      cursor:pointer;
    }}   
    
    .modal {{
      display: none;            /* ✅ keep hidden initially */
      position: fixed;
      z-index: 9999;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.85);

      overflow: auto;
    }}

    .modal.show {{
      display: flex;            /* ✅ ONLY here */
      justify-content: center;
      align-items: flex-start;
    }}
    
    .modal-content {{
      margin-top: 40px;
      max-width: 70%;       /* reduce size */
      max-height: 80vh;     /* fit inside screen */
      height: auto;
      display: block;
    }}

    .close {{
      position: fixed;
      top: 20px;
      right: 30px;
      color: white;
      font-size: 35px;
      cursor: pointer;
      z-index: 10000;
    }}
    
    .btn.active {{
        background: #2c3e50;
        color: white;
    }}
    
    .filter-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}

    .filters {{
      display: flex;
      gap: 8px;
    }}

    #searchBox {{
      padding: 6px;
      width: 250px;
      border-radius: 5px;
      border: 1px solid #ccc;
    }}
    
    .header {{
      background: #2c3e50;
      color: white;
      padding: 15px 20px;
      border-radius: 10px;
      margin-bottom: 20px;
    }}

    .header h1 {{
      margin: 0;
      font-size: 22px;
      font-weight: bold;
    }}

    .header p {{
      margin: 6px 0 0;
      font-size: 14px;
      opacity: 0.9;
    }}
    
    /* Table layout fix */
    #table {{
      table-layout: fixed;
      width: 100%;
    }}

    /* Column widths */
    #table th:nth-child(1), #table td:nth-child(1) {{ width: 2%; }}   /* S.No */
    #table th:nth-child(2), #table td:nth-child(2) {{ width: 8%; }}  /* Date */
    #table th:nth-child(3), #table td:nth-child(3) {{ width: 34%; }}  /* Test Steps */
    #table th:nth-child(4), #table td:nth-child(4) {{ width: 18%; }}  /* Test Cases */
    #table th:nth-child(5), #table td:nth-child(5) {{ width: 6%; }}   /* Result */
    #table th:nth-child(6), #table td:nth-child(6) {{ width: 10%; }}  /* Screenshot */
    
    /* Center Result column */
    #table td:nth-child(5),
    #table th:nth-child(5) {{
      text-align: center;
      vertical-align: middle;
    }}

    /* Center Screenshot column */
    #table td:nth-child(6),
    #table th:nth-child(6) {{
      text-align: center;
      vertical-align: middle;
    }}
    
    .img-container {{
      width: 100%;
      display: flex;
      justify-content: center;   /* ✅ forces center */
    }}

    </style>

    </head>

    <body>

    <div class="header">
      <h1>Automation Test Execution Report</h1>
      <p>Project Name: NMPHOSPatchAutomation</p>
    </div>
    
    <h2>Test Summary</h2>

    <div class="card-container">
      <div class="card total">Total<br><b>{total}</b></div>
      <div class="card pass">Pass<br><b>{pass_count}</b></div>
      <div class="card fail">Fail<br><b>{fail_count}</b></div>
      <div class="card log">Log Missing<br><b>{log_missing}</b></div>
      <div class="card shot">Screenshot Missing<br><b>{screenshot_missing}</b></div>
      <div class="card notrun">Not Run<br><b>{not_run}</b></div>
      <div class="card total">Execution<br><b>{execution_percent}%</b></div>
    </div>

    <h2>Filters</h2>
    
    <div class="filter-bar">

      <div class="filters">
        <button class="btn" onclick="filterTable('ALL')">All</button>
        <button class="btn" onclick="filterTable('PASS')">Pass</button>
        <button class="btn" onclick="filterTable('FAIL')">Fail</button>
        <button class="btn" onclick="filterTable('LOG_MISSING')">Log Missing</button>
        <button class="btn" onclick="filterTable('SCREENSHOT_MISSING')">Screenshot Missing</button>
        <button class="btn" onclick="filterTable('NOT_RUN')">Not Run</button>
      </div>

      <input 
        type="text" 
        id="searchBox" 
        placeholder="Search..." 
        onkeyup="searchTable()"
      >

    </div>

    <table id="table">
    <tr>
    <th>S.No</th><th>Date</th><th>Test Steps</th><th>Test Cases</th><th>Results</th><th>Screenshots</th>
    </tr>

    {rows}
    </table>

    <div id="imgModal" class="modal">
      <span class="close" onclick="closeModal()">&times;</span>

      <div class="img-container">
        <img class="modal-content" id="modalImg">
      </div>
    </div>

    <script>
    function filterTable(type) {{
      let rows = document.querySelectorAll("#table tr");
      let buttons = document.querySelectorAll(".btn");

      buttons.forEach(btn => btn.classList.remove("active"));

      event.target.classList.add("active");

      rows.forEach((row,i) => {{
        if(i===0) return;
        if(type==="ALL" || row.classList.contains(type)) {{
          row.style.display="";
        }} else {{
          row.style.display="none";
        }}
      }});
    }}

    function searchTable() {{
      let input = document.getElementById("searchBox").value.toLowerCase();
      let rows = document.querySelectorAll("#table tr");

      rows.forEach((row,i) => {{
        if(i===0) return;

        if (row.innerText.toLowerCase().includes(input)) {{
          row.style.display="";
        }} else {{
          row.style.display="none";
        }}
      }});
    }}

    function openModal(src) {{
      let modal = document.getElementById("imgModal");
      let img = document.getElementById("modalImg");

      img.src = src;
      modal.classList.add("show");   // ✅ correct way
    }}

    function closeModal() {{
      document.getElementById("imgModal").classList.remove("show");
    }}
    </script>

    </body>
    </html>
    """

    report_file = os.path.join(REPORT_DIR, f"Report_{timestamp()}.html")

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(html)

    zip_file = report_file.replace(".html", ".zip")

    with ZipFile(zip_file, 'w') as zipf:
        zipf.write(report_file, os.path.basename(report_file))
        for f in os.listdir(report_screenshot_dir):
            zipf.write(os.path.join(report_screenshot_dir, f), f"screenshots/{f}")

    os.remove(report_file)

    print("ZIP created:", zip_file)


if __name__ == "__main__":
    main()