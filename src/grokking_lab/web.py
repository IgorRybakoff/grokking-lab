from __future__ import annotations

import os
import shutil
import tempfile
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .audit import audit_run
from .evidence import export_evidence_package

try:
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.responses import FileResponse, HTMLResponse
except ImportError:  # pragma: no cover - web extra is optional
    FastAPI = File = HTTPException = UploadFile = None  # type: ignore[assignment]
    FileResponse = HTMLResponse = None  # type: ignore[assignment]

MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_ZIP_ENTRIES = 5000

HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="theme-color" content="#070b10" />
  <title>Grokking Lab — Experiment Audit</title>
  <style>
    :root {
      color-scheme: dark;
      --bg:#070b10;
      --panel:#0d131a;
      --panel-2:#101820;
      --line:#24303d;
      --line-soft:#18222d;
      --text:#f4f7fa;
      --muted:#8f9dad;
      --accent:#a8c7ff;
      --ok:#78e6ad;
      --bad:#ff8f8f;
      --warn:#f5d26f;
      --shadow:0 24px 70px rgba(0,0,0,.34);
    }
    * { box-sizing:border-box; }
    html { scroll-behavior:smooth; }
    body {
      margin:0;
      min-height:100vh;
      background:
        linear-gradient(rgba(255,255,255,.018) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.018) 1px, transparent 1px),
        radial-gradient(circle at 50% -20%, #162130 0, var(--bg) 43%);
      background-size:40px 40px,40px 40px,auto;
      color:var(--text);
      font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    }
    a { color:inherit; }
    .shell { width:min(1120px,calc(100% - 32px)); margin:0 auto; padding:30px 0 86px; }
    .topbar { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:4px 2px 36px; }
    .brand { display:flex; align-items:center; gap:11px; font-weight:760; letter-spacing:-.02em; }
    .mark { width:28px; height:28px; border:1px solid #44607c; border-radius:8px; display:grid; place-items:center; position:relative; background:#0b1118; }
    .mark:before,.mark:after { content:""; position:absolute; border:1px solid #7999ba; inset:6px; transform:rotate(45deg); }
    .mark:after { inset:10px; border-color:#b7d0e9; }
    .version { color:var(--muted); font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.08em; }
    .hero { display:grid; grid-template-columns:1.18fr .82fr; gap:34px; align-items:end; padding:28px 0 38px; }
    .eyebrow { color:var(--accent); font:700 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.16em; text-transform:uppercase; }
    h1 { max-width:790px; font-size:clamp(42px,7vw,82px); line-height:.95; letter-spacing:-.06em; margin:14px 0 18px; font-weight:760; }
    .lead { color:#aab6c3; font-size:18px; line-height:1.65; max-width:760px; }
    .promise { border-left:1px solid var(--line); padding-left:24px; color:var(--muted); line-height:1.6; font-size:14px; }
    .promise b { display:block; color:var(--text); font-size:13px; margin-bottom:8px; letter-spacing:.03em; }
    .pipeline { display:grid; grid-template-columns:repeat(4,1fr); margin:8px 0 30px; border:1px solid var(--line); border-radius:14px; overflow:hidden; background:rgba(9,14,20,.72); }
    .step { padding:14px 16px; border-right:1px solid var(--line-soft); min-width:0; }
    .step:last-child { border-right:0; }
    .step small { display:block; color:#637183; font:700 10px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace; margin-bottom:6px; }
    .step span { font-size:13px; font-weight:650; }
    .workbench { display:grid; grid-template-columns:1.05fr .95fr; gap:18px; }
    .panel { background:linear-gradient(180deg,rgba(15,22,30,.97),rgba(11,17,23,.97)); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow); overflow:hidden; }
    .panel-head { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:16px 18px; border-bottom:1px solid var(--line-soft); }
    .panel-title { font-size:13px; font-weight:720; letter-spacing:.01em; }
    .panel-kicker { color:var(--muted); font:600 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; }
    .upload-body { padding:18px; }
    .drop { position:relative; border:1px dashed #3a5066; border-radius:14px; min-height:238px; display:grid; place-items:center; text-align:center; background:#0a1016; transition:.2s ease; cursor:pointer; }
    .drop:hover,.drop.drag { border-color:#7897b8; background:#0d151e; }
    .drop-inner { padding:30px; }
    .upload-icon { width:54px; height:54px; margin:0 auto 17px; border:1px solid var(--line); border-radius:15px; display:grid; place-items:center; color:var(--accent); font-size:25px; background:#101820; }
    .drop strong { display:block; font-size:18px; margin-bottom:8px; }
    .drop span { display:block; color:var(--muted); font-size:13px; line-height:1.55; }
    input[type=file] { position:absolute; inset:0; opacity:0; width:100%; cursor:pointer; }
    .file-name { margin-top:12px; min-height:20px; color:#bac6d2; font:600 12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; overflow-wrap:anywhere; }
    .actions { display:flex; gap:10px; margin-top:16px; flex-wrap:wrap; }
    button,.download { border-radius:10px; min-height:43px; padding:0 16px; font-weight:750; font-size:12px; letter-spacing:.035em; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; border:1px solid transparent; }
    button.primary,.download { background:var(--text); color:#060b10; }
    button.secondary { background:#121b24; color:var(--text); border-color:var(--line); }
    button:hover,.download:hover { filter:brightness(1.05); }
    button:disabled { opacity:.48; cursor:progress; }
    .safety { margin-top:16px; padding-top:14px; border-top:1px solid var(--line-soft); display:flex; gap:9px; align-items:flex-start; color:var(--muted); font-size:12px; line-height:1.5; }
    .safety i { width:8px; height:8px; margin-top:5px; border-radius:50%; background:var(--ok); box-shadow:0 0 14px rgba(120,230,173,.5); flex:none; }
    .status-panel { min-height:100%; }
    .empty { min-height:365px; display:grid; place-items:center; padding:30px; text-align:center; color:var(--muted); }
    .empty .radar { width:108px; height:108px; border:1px solid #263644; border-radius:50%; margin:0 auto 18px; position:relative; background:radial-gradient(circle,#13202a 0 2px,transparent 3px); }
    .radar:before,.radar:after { content:""; position:absolute; inset:25%; border:1px solid #263644; border-radius:50%; }
    .radar:after { inset:49% 0 auto 0; border:0; border-top:1px solid #263644; border-radius:0; }
    .empty strong { display:block; color:#cbd5df; font-size:14px; margin-bottom:7px; }
    #status { color:var(--muted); min-height:20px; font-size:12px; margin-top:12px; }
    #result { display:none; padding:18px; }
    .verdict-wrap { display:flex; align-items:flex-start; justify-content:space-between; gap:18px; padding-bottom:18px; }
    .verdict-line { display:flex; align-items:center; gap:12px; }
    .dot { width:11px; height:11px; border-radius:50%; background:var(--muted); box-shadow:0 0 20px currentColor; }
    .VERIFIED .dot { background:var(--ok); color:var(--ok); }
    .FAILED .dot { background:var(--bad); color:var(--bad); }
    .INCOMPLETE .dot { background:var(--warn); color:var(--warn); }
    .verdict-line strong { font-size:27px; letter-spacing:-.025em; }
    .trust { color:var(--muted); text-align:right; font:650 10px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.08em; }
    .trust b { display:block; color:var(--text); font-size:12px; letter-spacing:.04em; margin-top:3px; }
    .meta { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:0 0 16px; }
    .meta div { background:#0a1016; border:1px solid var(--line-soft); border-radius:10px; padding:11px 12px; min-width:0; }
    .meta label { color:#667587; display:block; font:700 9px/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.09em; margin-bottom:7px; }
    .meta span { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12px; }
    .checks-head { display:flex; align-items:center; justify-content:space-between; padding:11px 0 8px; color:#6f7d8d; font:700 9px/1 ui-monospace,SFMono-Regular,Menlo,monospace; text-transform:uppercase; letter-spacing:.1em; }
    .check { display:grid; grid-template-columns:1fr auto; gap:12px; align-items:center; padding:11px 0; border-top:1px solid var(--line-soft); }
    .check-name { font-size:12px; text-transform:capitalize; color:#c1ccd7; }
    .check strong { font:750 10px/1 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.07em; }
    .PASS { color:var(--ok); } .FAIL { color:var(--bad); } .INCOMPLETE_STATUS { color:var(--warn); }
    .note { margin-top:15px; color:#6f7d8d; font-size:11px; line-height:1.55; }
    .footer { display:flex; justify-content:space-between; gap:20px; margin-top:24px; color:#586676; font:600 10px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; }
    @media(max-width:820px){ .hero,.workbench{grid-template-columns:1fr}.promise{border-left:0;border-top:1px solid var(--line);padding:18px 0 0}.pipeline{grid-template-columns:1fr 1fr}.step:nth-child(2){border-right:0}.step:nth-child(-n+2){border-bottom:1px solid var(--line-soft)} }
    @media(max-width:560px){ .shell{width:min(100% - 20px,1120px);padding-top:18px}.topbar{padding-bottom:22px}.pipeline{grid-template-columns:1fr}.step{border-right:0!important;border-bottom:1px solid var(--line-soft)!important}.step:last-child{border-bottom:0!important}.meta{grid-template-columns:1fr}.verdict-wrap{flex-direction:column}.trust{text-align:left}.footer{flex-direction:column}.actions>*{width:100%} }
  </style>
</head>
<body>
<div class="shell">
  <header class="topbar">
    <div class="brand"><span class="mark"></span><span>Grokking Lab</span></div>
    <div class="version">EXPERIMENT AUDIT / v0.1</div>
  </header>

  <section class="hero">
    <div>
      <div class="eyebrow">Reproducible ML evidence</div>
      <h1>Verify the experiment, not the claim.</h1>
      <div class="lead">Upload a frozen experiment package. Grokking Lab checks the evidence chain, replays the checkpoint where possible, and returns a portable audit result.</div>
    </div>
    <div class="promise">
      <b>DETERMINISTIC CORE</b>
      The audit verdict is produced from artifacts, hashes, configuration and replay checks. Unknown uploaded code is not executed in this MVP.
    </div>
  </section>

  <section class="pipeline" aria-label="Audit pipeline">
    <div class="step"><small>01 / INGEST</small><span>Evidence package</span></div>
    <div class="step"><small>02 / INSPECT</small><span>Config + environment</span></div>
    <div class="step"><small>03 / REPLAY</small><span>Checkpoint verification</span></div>
    <div class="step"><small>04 / VERDICT</small><span>Evidence package</span></div>
  </section>

  <main class="workbench">
    <section class="panel">
      <div class="panel-head"><div class="panel-title">Experiment input</div><div class="panel-kicker">ZIP ONLY / MVP</div></div>
      <div class="upload-body">
        <label id="drop" class="drop">
          <div class="drop-inner">
            <div class="upload-icon">⇧</div>
            <strong>Drop evidence package</strong>
            <span>or tap to choose a ZIP<br>Maximum upload size: 256 MiB</span>
            <input id="file" type="file" accept=".zip,application/zip" />
          </div>
        </label>
        <div id="fileName" class="file-name">No file selected</div>
        <div class="actions">
          <button id="verify" class="primary">RUN EXPERIMENT AUDIT</button>
          <button id="demo" class="secondary">RUN CANONICAL DEMO</button>
        </div>
        <div id="status"></div>
        <div class="safety"><i></i><span>Evidence is unpacked with traversal/symlink guards. Uploaded Python code is not executed.</span></div>
      </div>
    </section>

    <section class="panel status-panel">
      <div class="panel-head"><div class="panel-title">Audit result</div><div class="panel-kicker">MACHINE-READABLE</div></div>
      <div id="empty" class="empty">
        <div><div class="radar"></div><strong>No audit result yet</strong><span>Upload evidence or run the canonical demo.</span></div>
      </div>
      <div id="result">
        <div class="verdict-wrap">
          <div id="verdictRow" class="verdict-line"><span class="dot"></span><strong id="verdict"></strong></div>
          <div class="trust">Audit state<b id="trustText">—</b></div>
        </div>
        <div class="meta">
          <div><label>Experiment</label><span id="experiment"></span></div>
          <div><label>Adapter</label><span id="adapter"></span></div>
        </div>
        <div class="checks-head"><span>Evidence checks</span><span>Status</span></div>
        <div id="checks"></div>
        <div class="actions"><a id="download" class="download" href="#">DOWNLOAD EVIDENCE PACKAGE</a></div>
        <div class="note">VERIFIED = sufficient evidence and checks passed. FAILED = contradictory or invalid evidence. INCOMPLETE = evidence is insufficient for a verified claim.</div>
      </div>
    </section>
  </main>

  <footer class="footer"><span>GROKKING LAB / REPRODUCIBLE ML EXPERIMENT AUDIT</span><span>Deterministic verdict core · Human-readable report</span></footer>
</div>
<script>
const $ = id => document.getElementById(id);
const verifyBtn=$('verify'), demoBtn=$('demo'), statusBox=$('status'), fileInput=$('file'), drop=$('drop');
function busy(on,text=''){ verifyBtn.disabled=on; demoBtn.disabled=on; statusBox.textContent=text; }
function render(data){
  const audit=data.audit;
  $('empty').style.display='none'; $('result').style.display='block';
  $('verdict').textContent=audit.verdict; $('verdictRow').className='verdict-line '+audit.verdict;
  $('trustText').textContent=audit.verdict==='VERIFIED'?'EVIDENCE VERIFIED':audit.verdict==='FAILED'?'EVIDENCE CONFLICT':'MORE EVIDENCE NEEDED';
  $('experiment').textContent=audit.experiment_id; $('adapter').textContent=audit.adapter; $('download').href=data.download_url;
  const checks=$('checks'); checks.replaceChildren();
  for(const item of audit.checks){
    const row=document.createElement('div'); row.className='check';
    const name=document.createElement('span'); name.className='check-name'; name.textContent=item.id.replaceAll('_',' ');
    const state=document.createElement('strong'); state.textContent=item.status; state.className=item.status==='INCOMPLETE'?'INCOMPLETE_STATUS':item.status;
    row.append(name,state); checks.append(row);
  }
}
async function parseResponse(response){ const body=await response.json().catch(()=>({detail:'Invalid server response'})); if(!response.ok) throw new Error(body.detail||'Audit failed'); return body; }
function updateFileName(){ $('fileName').textContent=fileInput.files[0]?fileInput.files[0].name:'No file selected'; }
fileInput.addEventListener('change',updateFileName);
for(const evt of ['dragenter','dragover']) drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add('drag')});
for(const evt of ['dragleave','drop']) drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove('drag')});
drop.addEventListener('drop',e=>{ if(e.dataTransfer.files.length){ fileInput.files=e.dataTransfer.files; updateFileName(); }});
verifyBtn.addEventListener('click',async()=>{
  const file=fileInput.files[0]; if(!file){ statusBox.textContent='Choose an evidence ZIP first.'; return; }
  const form=new FormData(); form.append('file',file);
  try{ busy(true,'Inspecting evidence and replaying checkpoint…'); render(await parseResponse(await fetch('/api/audit',{method:'POST',body:form}))); busy(false,'Audit complete.'); }
  catch(e){ busy(false,'Error: '+e.message); }
});
demoBtn.addEventListener('click',async()=>{
  try{ busy(true,'Running canonical evidence audit…'); render(await parseResponse(await fetch('/api/demo',{method:'POST'}))); busy(false,'Demo audit complete.'); }
  catch(e){ busy(false,'Error: '+e.message); }
});
</script>
</body>
</html>"""


def _state_root() -> Path:
    root = Path(os.environ.get("GROKKINGLAB_STATE_DIR", tempfile.gettempdir())) / "grokkinglab-web"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def _safe_extract_zip(zip_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ValueError(f"ZIP has too many entries ({len(infos)} > {MAX_ZIP_ENTRIES})")
        total = sum(info.file_size for info in infos)
        if total > MAX_EXTRACTED_BYTES:
            raise ValueError("ZIP expands beyond the 512 MiB MVP limit")

        for info in infos:
            name = info.filename.replace("\\", "/")
            parts = PurePosixPath(name).parts
            if not parts or name.startswith("/") or ".." in parts or (parts and ":" in parts[0]):
                raise ValueError(f"unsafe ZIP path: {info.filename}")
            if _is_symlink(info):
                raise ValueError(f"symlinks are not accepted in evidence ZIPs: {info.filename}")
            target = destination.joinpath(*parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)


def _locate_artifact_root(extracted: Path) -> Path:
    if (extracted / "experiment_manifest.json").is_file() and (extracted / "config.json").is_file():
        return extracted
    candidates = [
        path.parent
        for path in extracted.rglob("experiment_manifest.json")
        if (path.parent / "config.json").is_file()
    ]
    unique = sorted({path.resolve() for path in candidates})
    if not unique:
        raise ValueError("No experiment root found (need config.json + experiment_manifest.json)")
    if len(unique) > 1:
        raise ValueError("ZIP contains multiple experiment roots; upload one run per ZIP in MVP v0.1")
    return unique[0]


def _audit_to_job(root: Path, job_dir: Path) -> dict[str, Any]:
    audit = audit_run(root)
    package = job_dir / "grokkinglab_evidence.zip"
    export_evidence_package(root, package)
    return {
        "job_id": job_dir.name,
        "audit": audit,
        "download_url": f"/api/package/{job_dir.name}",
    }


def create_app():
    if FastAPI is None or File is None or HTTPException is None or UploadFile is None or FileResponse is None or HTMLResponse is None:
        raise RuntimeError("Web UI requires: pip install -e '.[web]'")

    app = FastAPI(title="Grokking Lab Experiment Audit", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return HTML

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok", "product": "grokking-lab", "version": "0.1"}

    @app.post("/api/audit")
    async def audit_upload(file: UploadFile = File(...)):
        job_dir = _state_root() / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=False)
        zip_path = job_dir / "upload.zip"
        size = 0
        try:
            with zip_path.open("wb") as stream:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        raise ValueError("Upload exceeds the 256 MiB MVP limit")
                    stream.write(chunk)
            if not zipfile.is_zipfile(zip_path):
                raise ValueError("Upload is not a valid ZIP archive")
            extracted = job_dir / "run"
            extracted.mkdir()
            _safe_extract_zip(zip_path, extracted)
            root = _locate_artifact_root(extracted)
            return _audit_to_job(root, job_dir)
        except ValueError as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"audit failed: {exc}") from exc
        finally:
            await file.close()

    @app.post("/api/demo")
    def audit_demo():
        root = _project_root() / "artifacts" / "p113_seed42_40k"
        if not root.is_dir():
            raise HTTPException(status_code=404, detail="Canonical demo artifacts are not installed")
        job_dir = _state_root() / uuid.uuid4().hex
        job_dir.mkdir(parents=True, exist_ok=False)
        try:
            return _audit_to_job(root, job_dir)
        except Exception as exc:
            shutil.rmtree(job_dir, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"demo audit failed: {exc}") from exc

    @app.get("/api/package/{job_id}")
    def download_package(job_id: str):
        if not job_id or any(ch not in "0123456789abcdef" for ch in job_id) or len(job_id) != 32:
            raise HTTPException(status_code=404, detail="package not found")
        package = _state_root() / job_id / "grokkinglab_evidence.zip"
        if not package.is_file():
            raise HTTPException(status_code=404, detail="package not found")
        return FileResponse(package, media_type="application/zip", filename="grokkinglab_evidence.zip")

    return app


app = create_app()
