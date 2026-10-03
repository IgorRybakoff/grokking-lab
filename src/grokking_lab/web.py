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
  <title>Grokking Lab — Experiment Audit</title>
  <style>
    :root { color-scheme: dark; --bg:#091018; --panel:#111a24; --line:#263443; --text:#eef5fb; --muted:#90a4b8; --ok:#62d89f; --bad:#ff7a7a; --warn:#ffd166; --accent:#7ab8ff; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; background:radial-gradient(circle at 50% -10%,#18293a 0,#091018 42%); color:var(--text); min-height:100vh; }
    main { width:min(920px,calc(100% - 32px)); margin:0 auto; padding:64px 0 88px; }
    .eyebrow { color:var(--accent); font-size:12px; letter-spacing:.16em; font-weight:700; }
    h1 { font-size:clamp(36px,7vw,68px); margin:12px 0 14px; letter-spacing:-.045em; line-height:.98; }
    .lead { max-width:700px; color:var(--muted); font-size:18px; line-height:1.6; }
    .panel { margin-top:34px; background:rgba(17,26,36,.88); border:1px solid var(--line); border-radius:22px; padding:24px; box-shadow:0 22px 70px rgba(0,0,0,.25); }
    .drop { border:1px dashed #3b536a; border-radius:16px; padding:34px 20px; text-align:center; background:#0c141d; }
    .drop strong { display:block; font-size:18px; margin-bottom:7px; }
    .drop span { color:var(--muted); font-size:14px; }
    input[type=file] { width:100%; margin-top:18px; color:var(--muted); }
    .actions { display:flex; gap:12px; margin-top:18px; flex-wrap:wrap; }
    button,.download { border:0; border-radius:12px; padding:12px 18px; font-weight:750; font-size:14px; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; justify-content:center; }
    button.primary,.download { background:var(--text); color:#071019; }
    button.secondary { background:#182532; color:var(--text); border:1px solid var(--line); }
    button:disabled { opacity:.55; cursor:progress; }
    #status { color:var(--muted); margin-top:14px; min-height:22px; }
    #result { display:none; }
    .verdict { display:flex; gap:12px; align-items:center; margin-bottom:20px; }
    .dot { width:12px; height:12px; border-radius:50%; background:var(--muted); box-shadow:0 0 24px currentColor; }
    .VERIFIED .dot { background:var(--ok); color:var(--ok); }
    .FAILED .dot { background:var(--bad); color:var(--bad); }
    .INCOMPLETE .dot { background:var(--warn); color:var(--warn); }
    .verdict strong { font-size:26px; }
    .meta { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; margin-bottom:20px; }
    .meta div { background:#0c141d; border:1px solid var(--line); border-radius:12px; padding:12px 14px; }
    .meta label { color:var(--muted); display:block; font-size:11px; text-transform:uppercase; letter-spacing:.08em; margin-bottom:5px; }
    .check { display:grid; grid-template-columns:1fr auto; gap:12px; padding:12px 0; border-top:1px solid var(--line); }
    .check:first-child { border-top:0; }
    .PASS { color:var(--ok); } .FAIL { color:var(--bad); } .INCOMPLETE_STATUS { color:var(--warn); }
    .note { margin-top:26px; color:var(--muted); font-size:13px; line-height:1.55; }
    code { color:#cce3ff; }
    @media(max-width:620px){ main{padding-top:36px}.meta{grid-template-columns:1fr}.panel{padding:18px} }
  </style>
</head>
<body>
<main>
  <div class="eyebrow">GROKKING LAB / MVP v0.1</div>
  <h1>Verify an ML experiment.</h1>
  <div class="lead">Upload a frozen Grokking Lab run or evidence ZIP. The audit checks provenance, configuration, environment, hashes and checkpoint replay, then produces a portable evidence package.</div>

  <section class="panel">
    <div class="drop">
      <strong>Drop an experiment evidence ZIP</strong>
      <span>Unknown code is never executed by this MVP.</span>
      <input id="file" type="file" accept=".zip,application/zip" />
    </div>
    <div class="actions">
      <button id="verify" class="primary">VERIFY EXPERIMENT</button>
      <button id="demo" class="secondary">TRY CANONICAL DEMO</button>
    </div>
    <div id="status"></div>
  </section>

  <section id="result" class="panel">
    <div id="verdictRow" class="verdict"><span class="dot"></span><strong id="verdict"></strong></div>
    <div class="meta">
      <div><label>Experiment</label><span id="experiment"></span></div>
      <div><label>Adapter</label><span id="adapter"></span></div>
    </div>
    <div id="checks"></div>
    <div class="actions"><a id="download" class="download" href="#">DOWNLOAD EVIDENCE PACKAGE</a></div>
    <div class="note">The machine-readable JSON result inside the evidence package is authoritative. <code>FAILED</code> means contradictory evidence; <code>INCOMPLETE</code> means the available artifacts are insufficient for a verified claim.</div>
  </section>
</main>
<script>
const $ = id => document.getElementById(id);
const verifyBtn = $('verify'), demoBtn = $('demo'), statusBox = $('status');
function busy(on, text='') { verifyBtn.disabled=on; demoBtn.disabled=on; statusBox.textContent=text; }
function render(data) {
  const audit=data.audit;
  $('result').style.display='block';
  $('verdict').textContent=audit.verdict;
  $('verdictRow').className='verdict '+audit.verdict;
  $('experiment').textContent=audit.experiment_id;
  $('adapter').textContent=audit.adapter;
  $('download').href=data.download_url;
  const checks=$('checks'); checks.replaceChildren();
  for (const item of audit.checks) {
    const row=document.createElement('div'); row.className='check';
    const name=document.createElement('span'); name.textContent=item.id.replaceAll('_',' ');
    const state=document.createElement('strong'); state.textContent=item.status;
    state.className=item.status==='INCOMPLETE'?'INCOMPLETE_STATUS':item.status;
    row.append(name,state); checks.append(row);
  }
  $('result').scrollIntoView({behavior:'smooth',block:'start'});
}
async function parseResponse(response){ const body=await response.json().catch(()=>({detail:'Invalid server response'})); if(!response.ok) throw new Error(body.detail||'Audit failed'); return body; }
verifyBtn.addEventListener('click',async()=>{
  const file=$('file').files[0]; if(!file){ statusBox.textContent='Choose a ZIP first.'; return; }
  const form=new FormData(); form.append('file',file);
  try { busy(true,'Auditing evidence and replaying checkpoint…'); render(await parseResponse(await fetch('/api/audit',{method:'POST',body:form}))); busy(false,'Audit complete.'); }
  catch(e){ busy(false,'Error: '+e.message); }
});
demoBtn.addEventListener('click',async()=>{
  try { busy(true,'Running canonical demo audit…'); render(await parseResponse(await fetch('/api/demo',{method:'POST'}))); busy(false,'Demo audit complete.'); }
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
