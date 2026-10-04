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
except ImportError:  # pragma: no cover
    FastAPI = File = HTTPException = UploadFile = None  # type: ignore[assignment]
    FileResponse = HTMLResponse = None  # type: ignore[assignment]

MAX_UPLOAD_BYTES = 256 * 1024 * 1024
MAX_EXTRACTED_BYTES = 512 * 1024 * 1024
MAX_ZIP_ENTRIES = 5000

HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="theme-color" content="#070b10" />
  <title>Grokking Lab — Experiment Audit</title>
  <style>
    :root{color-scheme:dark;--bg:#070b10;--panel:#0d131a;--line:#24303d;--soft:#18222d;--text:#f4f7fa;--muted:#8f9dad;--accent:#a8c7ff;--ok:#78e6ad;--bad:#ff8f8f;--warn:#f5d26f}
    *{box-sizing:border-box} body{margin:0;min-height:100vh;background:radial-gradient(circle at 50% -20%,#162130 0,var(--bg) 43%);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .shell{width:min(1120px,calc(100% - 32px));margin:0 auto;padding:28px 0 70px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;padding-bottom:34px}.brand{display:flex;align-items:center;gap:11px;font-weight:760}.mark{width:28px;height:28px;border:1px solid #44607c;border-radius:8px;display:grid;place-items:center;position:relative}.mark:before,.mark:after{content:"";position:absolute;border:1px solid #7999ba;inset:6px;transform:rotate(45deg)}.mark:after{inset:10px;border-color:#b7d0e9}
    .tools{display:flex;align-items:center;gap:12px}.version{color:var(--muted);font:600 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace}.lang{display:flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}.lang button{min-height:32px;padding:0 10px;border:0;background:#101820;color:var(--muted);font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace;cursor:pointer}.lang button.active{background:var(--text);color:#071019}
    .hero{display:grid;grid-template-columns:1.18fr .82fr;gap:34px;align-items:end;padding:24px 0 36px}.eyebrow{color:var(--accent);font:700 11px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.15em;text-transform:uppercase}h1{font-size:clamp(42px,7vw,80px);line-height:.96;letter-spacing:-.055em;margin:14px 0 18px;max-width:800px}.lead{color:#aab6c3;font-size:18px;line-height:1.62;max-width:760px}.promise{border-left:1px solid var(--line);padding-left:24px;color:var(--muted);line-height:1.6;font-size:14px}.promise b{display:block;color:var(--text);font-size:12px;margin-bottom:8px;letter-spacing:.05em}
    .pipeline{display:grid;grid-template-columns:repeat(4,1fr);margin:8px 0 28px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:#091018}.step{padding:14px 16px;border-right:1px solid var(--soft)}.step:last-child{border-right:0}.step small{display:block;color:#637183;font:700 10px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;margin-bottom:6px}.step span{font-size:13px;font-weight:650}
    .workbench{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}.panel{background:linear-gradient(180deg,#0f161e,#0b1117);border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.34)}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 18px;border-bottom:1px solid var(--soft)}.panel-title{font-size:13px;font-weight:720}.panel-kicker{color:var(--muted);font:600 10px ui-monospace,SFMono-Regular,Menlo,monospace}.body{padding:18px}.drop{position:relative;border:1px dashed #3a5066;border-radius:14px;min-height:238px;display:grid;place-items:center;text-align:center;background:#0a1016;transition:.2s;cursor:pointer}.drop:hover,.drop.drag{border-color:#7897b8;background:#0d151e}.drop-inner{padding:30px}.upload-icon{width:54px;height:54px;margin:0 auto 17px;border:1px solid var(--line);border-radius:15px;display:grid;place-items:center;color:var(--accent);font-size:25px;background:#101820}.drop strong{display:block;font-size:18px;margin-bottom:8px}.drop span{display:block;color:var(--muted);font-size:13px;line-height:1.55}input[type=file]{position:absolute;inset:0;opacity:0;width:100%;cursor:pointer}.file-name{margin-top:12px;min-height:20px;color:#bac6d2;font:600 12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}
    .actions{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}button,.download{border-radius:10px;min-height:43px;padding:0 16px;font-weight:750;font-size:12px;letter-spacing:.03em;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;border:1px solid transparent}.primary,.download{background:var(--text);color:#060b10}.secondary{background:#121b24;color:var(--text);border-color:var(--line)}button:disabled{opacity:.48;cursor:progress}.safety{margin-top:16px;padding-top:14px;border-top:1px solid var(--soft);display:flex;gap:9px;color:var(--muted);font-size:12px;line-height:1.5}.safety i{width:8px;height:8px;margin-top:5px;border-radius:50%;background:var(--ok);flex:none}.status{color:var(--muted);min-height:20px;font-size:12px;margin-top:12px}.empty{min-height:365px;display:grid;place-items:center;padding:30px;text-align:center;color:var(--muted)}.empty strong{display:block;color:#cbd5df;font-size:14px;margin-bottom:7px}.radar{width:108px;height:108px;border:1px solid #263644;border-radius:50%;margin:0 auto 18px;position:relative}.radar:before,.radar:after{content:"";position:absolute;inset:25%;border:1px solid #263644;border-radius:50%}.radar:after{inset:49% 0 auto;border:0;border-top:1px solid #263644;border-radius:0}
    #result{display:none;padding:18px}.verdict-wrap{display:flex;align-items:flex-start;justify-content:space-between;gap:18px;padding-bottom:18px}.verdict-line{display:flex;align-items:center;gap:12px}.dot{width:11px;height:11px;border-radius:50%;background:var(--muted)}.VERIFIED .dot{background:var(--ok)}.FAILED .dot{background:var(--bad)}.INCOMPLETE .dot{background:var(--warn)}.verdict-line strong{font-size:27px}.machine{font:650 10px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--muted);margin-top:5px}.trust{text-align:right;color:var(--muted);font:650 10px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase}.trust b{display:block;color:var(--text);font-size:12px;margin-top:3px}.meta{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}.meta div{background:#0a1016;border:1px solid var(--soft);border-radius:10px;padding:11px 12px}.meta label{color:#667587;display:block;font:700 9px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;margin-bottom:7px}.meta span{font-size:12px}.checks-head{display:flex;justify-content:space-between;padding:11px 0 8px;color:#6f7d8d;font:700 9px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase}.check{display:grid;grid-template-columns:1fr auto;gap:12px;padding:11px 0;border-top:1px solid var(--soft)}.check-name{font-size:12px;color:#c1ccd7}.check strong{font:750 10px ui-monospace,SFMono-Regular,Menlo,monospace}.PASS{color:var(--ok)}.FAIL{color:var(--bad)}.INCOMPLETE_STATUS{color:var(--warn)}.note{margin-top:15px;color:#6f7d8d;font-size:11px;line-height:1.55}.footer{display:flex;justify-content:space-between;gap:20px;margin-top:24px;color:#586676;font:600 10px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
    @media(max-width:820px){.hero,.workbench{grid-template-columns:1fr}.promise{border-left:0;border-top:1px solid var(--line);padding:18px 0 0}.pipeline{grid-template-columns:1fr 1fr}.step:nth-child(2){border-right:0}.step:nth-child(-n+2){border-bottom:1px solid var(--soft)}}@media(max-width:560px){.shell{width:min(100% - 20px,1120px)}.topbar{align-items:flex-start}.tools{flex-direction:column;align-items:flex-end}.pipeline{grid-template-columns:1fr}.step{border-right:0!important;border-bottom:1px solid var(--soft)!important}.step:last-child{border-bottom:0!important}.meta{grid-template-columns:1fr}.verdict-wrap{flex-direction:column}.trust{text-align:left}.actions>*{width:100%}.footer{flex-direction:column}}
  </style>
</head>
<body>
<div class="shell">
<header class="topbar">
  <div class="brand"><span class="mark"></span><span>Grokking Lab</span></div>
  <div class="tools"><div class="version">EXPERIMENT AUDIT / v0.1</div><div class="lang"><button id="enBtn">EN</button><button id="ruBtn">RU</button></div></div>
</header>
<section class="hero">
  <div><div class="eyebrow" data-i18n="eyebrow"></div><h1 data-i18n="headline"></h1><div class="lead" data-i18n="lead"></div></div>
  <div class="promise"><b data-i18n="coreTitle"></b><span data-i18n="coreText"></span></div>
</section>
<section class="pipeline" aria-label="Audit pipeline">
  <div class="step"><small>01 / INGEST</small><span data-i18n="step1"></span></div>
  <div class="step"><small>02 / INSPECT</small><span data-i18n="step2"></span></div>
  <div class="step"><small>03 / REPLAY</small><span data-i18n="step3"></span></div>
  <div class="step"><small>04 / VERDICT</small><span data-i18n="step4"></span></div>
</section>
<main class="workbench">
<section class="panel">
  <div class="panel-head"><div class="panel-title" data-i18n="inputTitle"></div><div class="panel-kicker">ZIP ONLY / MVP</div></div>
  <div class="body">
    <label id="drop" class="drop"><div class="drop-inner"><div class="upload-icon">⇧</div><strong data-i18n="dropTitle"></strong><span data-i18n-html="dropText"></span><input id="file" type="file" accept=".zip,application/zip" /></div></label>
    <div id="fileName" class="file-name"></div>
    <div class="actions"><button id="verify" class="primary" data-i18n="auditBtn"></button><button id="demo" class="secondary" data-i18n="demoBtn"></button></div>
    <div id="status" class="status"></div>
    <div class="safety"><i></i><span data-i18n="safety"></span></div>
  </div>
</section>
<section class="panel">
  <div class="panel-head"><div class="panel-title" data-i18n="resultTitle"></div><div class="panel-kicker">MACHINE-READABLE</div></div>
  <div id="empty" class="empty"><div><div class="radar"></div><strong data-i18n="emptyTitle"></strong><span data-i18n="emptyText"></span></div></div>
  <div id="result">
    <div class="verdict-wrap"><div><div id="verdictRow" class="verdict-line"><span class="dot"></span><strong id="verdictHuman"></strong></div><div id="verdictMachine" class="machine"></div></div><div class="trust"><span data-i18n="auditState"></span><b id="trustText">—</b></div></div>
    <div class="meta"><div><label data-i18n="experiment"></label><span id="experiment"></span></div><div><label data-i18n="adapter"></label><span id="adapter"></span></div></div>
    <div class="checks-head"><span data-i18n="checks"></span><span data-i18n="statusLabel"></span></div><div id="checks"></div>
    <div class="actions"><a id="download" class="download" href="#" data-i18n="download"></a></div><div class="note" data-i18n="note"></div>
  </div>
</section>
</main>
<footer class="footer"><span data-i18n="footer1"></span><span data-i18n="footer2"></span></footer>
</div>
<script>
const $=id=>document.getElementById(id);
const T={
 en:{eyebrow:'Reproducible ML evidence',headline:'Verify the experiment, not the claim.',lead:'Upload a frozen experiment package. Grokking Lab checks the evidence chain, replays the checkpoint where possible, and returns a portable audit result.',coreTitle:'DETERMINISTIC CORE',coreText:'The verdict comes from artifacts, hashes, configuration and replay checks. Unknown uploaded code is not executed.',step1:'Evidence package',step2:'Config + environment',step3:'Checkpoint verification',step4:'Audit verdict',inputTitle:'Experiment input',dropTitle:'Drop evidence package',dropText:'or tap to choose a ZIP<br>Maximum upload size: 256 MiB',auditBtn:'RUN EXPERIMENT AUDIT',demoBtn:'RUN CANONICAL DEMO',safety:'Evidence is unpacked with traversal and symlink guards. Uploaded Python code is not executed.',resultTitle:'Audit result',emptyTitle:'No audit result yet',emptyText:'Upload evidence or run the canonical demo.',auditState:'Audit state',experiment:'Experiment',adapter:'Adapter',checks:'Evidence checks',statusLabel:'Status',download:'DOWNLOAD EVIDENCE PACKAGE',note:'VERIFIED = sufficient evidence and all required checks passed. FAILED = contradictory or invalid evidence. INCOMPLETE = insufficient evidence for a verified conclusion.',footer1:'GROKKING LAB / REPRODUCIBLE ML EXPERIMENT AUDIT',footer2:'Deterministic verdict core · Human-readable report',noFile:'No file selected',chooseZip:'Choose an evidence ZIP first.',working:'Inspecting evidence and replaying checkpoint…',done:'Audit complete.',demoWorking:'Running canonical evidence audit…',demoDone:'Demo audit complete.',error:'Error',trustVerified:'EVIDENCE VERIFIED',trustFailed:'EVIDENCE CONFLICT',trustIncomplete:'MORE EVIDENCE NEEDED',verified:'VERIFIED',failed:'FAILED',incomplete:'INCOMPLETE',pass:'PASS',fail:'FAIL'},
 ru:{eyebrow:'Воспроизводимые доказательства ML',headline:'Проверяйте эксперимент, а не утверждение.',lead:'Загрузите зафиксированный пакет ML-эксперимента. Grokking Lab проверит цепочку доказательств, конфигурацию и контрольные суммы, воспроизведёт checkpoint там, где это возможно, и сформирует переносимый результат аудита.',coreTitle:'ДЕТЕРМИНИРОВАННОЕ ЯДРО',coreText:'Вердикт формируется по артефактам, хэшам, конфигурации и replay-проверкам. Неизвестный загруженный код не выполняется.',step1:'Пакет доказательств',step2:'Конфигурация + среда',step3:'Проверка checkpoint',step4:'Вердикт аудита',inputTitle:'Входные данные эксперимента',dropTitle:'Перетащите пакет доказательств',dropText:'или нажмите, чтобы выбрать ZIP<br>Максимальный размер: 256 МиБ',auditBtn:'ПРОВЕРИТЬ ЭКСПЕРИМЕНТ',demoBtn:'ЗАПУСТИТЬ ЭТАЛОННЫЙ ПРИМЕР',safety:'Пакет распаковывается с защитой от traversal и symlink. Загруженный неизвестный Python-код не выполняется.',resultTitle:'Результат аудита',emptyTitle:'Результата пока нет',emptyText:'Загрузите пакет или запустите эталонный пример.',auditState:'Состояние аудита',experiment:'Эксперимент',adapter:'Адаптер',checks:'Проверки доказательств',statusLabel:'Статус',download:'СКАЧАТЬ ПАКЕТ ДОКАЗАТЕЛЬСТВ',note:'VERIFIED = доказательств достаточно и обязательные проверки пройдены. FAILED = обнаружены противоречивые или недействительные доказательства. INCOMPLETE = данных недостаточно для подтверждённого вывода.',footer1:'GROKKING LAB / АУДИТ ВОСПРОИЗВОДИМОСТИ ML-ЭКСПЕРИМЕНТОВ',footer2:'Детерминированный вердикт · Понятный человеку отчёт',noFile:'Файл не выбран',chooseZip:'Сначала выберите ZIP с доказательствами.',working:'Проверяю доказательства и воспроизвожу checkpoint…',done:'Аудит завершён.',demoWorking:'Запускаю эталонный аудит…',demoDone:'Эталонный аудит завершён.',error:'Ошибка',trustVerified:'ДОКАЗАТЕЛЬСТВА ПОДТВЕРЖДЕНЫ',trustFailed:'ОБНАРУЖЕНО ПРОТИВОРЕЧИЕ',trustIncomplete:'НУЖНЫ ДОПОЛНИТЕЛЬНЫЕ ДАННЫЕ',verified:'ПОДТВЕРЖДЕНО',failed:'НЕ ПРОЙДЕНО',incomplete:'НЕДОСТАТОЧНО ДАННЫХ',pass:'ПРОЙДЕНО',fail:'ОШИБКА'}
};
let lang=localStorage.getItem('grokkinglab_lang')||((navigator.language||'').toLowerCase().startsWith('ru')?'ru':'en');
let lastData=null; const verifyBtn=$('verify'),demoBtn=$('demo'),statusBox=$('status'),fileInput=$('file'),drop=$('drop');
function tr(k){return T[lang][k]||T.en[k]||k}
function humanVerdict(v){return v==='VERIFIED'?tr('verified'):v==='FAILED'?tr('failed'):tr('incomplete')}
function humanStatus(v){return v==='PASS'?tr('pass'):v==='FAIL'?tr('fail'):tr('incomplete')}
function applyLang(){document.documentElement.lang=lang;document.querySelectorAll('[data-i18n]').forEach(el=>el.textContent=tr(el.dataset.i18n));document.querySelectorAll('[data-i18n-html]').forEach(el=>el.innerHTML=tr(el.dataset.i18nHtml));$('enBtn').classList.toggle('active',lang==='en');$('ruBtn').classList.toggle('active',lang==='ru');updateFileName();if(lastData)render(lastData)}
function setLang(next){lang=next;localStorage.setItem('grokkinglab_lang',lang);applyLang()}
$('enBtn').onclick=()=>setLang('en');$('ruBtn').onclick=()=>setLang('ru');
function busy(on,text=''){verifyBtn.disabled=on;demoBtn.disabled=on;statusBox.textContent=text}
function render(data){lastData=data;const audit=data.audit;$('empty').style.display='none';$('result').style.display='block';$('verdictHuman').textContent=humanVerdict(audit.verdict);$('verdictMachine').textContent=audit.verdict;$('verdictRow').className='verdict-line '+audit.verdict;$('trustText').textContent=audit.verdict==='VERIFIED'?tr('trustVerified'):audit.verdict==='FAILED'?tr('trustFailed'):tr('trustIncomplete');$('experiment').textContent=audit.experiment_id;$('adapter').textContent=audit.adapter;$('download').href=data.download_url;const checks=$('checks');checks.replaceChildren();for(const item of audit.checks){const row=document.createElement('div');row.className='check';const name=document.createElement('span');name.className='check-name';name.textContent=item.id.replaceAll('_',' ');const state=document.createElement('strong');state.textContent=humanStatus(item.status)+' · '+item.status;state.className=item.status==='INCOMPLETE'?'INCOMPLETE_STATUS':item.status;row.append(name,state);checks.append(row)}}
async function parseResponse(response){const body=await response.json().catch(()=>({detail:'Invalid server response'}));if(!response.ok)throw new Error(body.detail||'Audit failed');return body}
function updateFileName(){$('fileName').textContent=fileInput.files[0]?fileInput.files[0].name:tr('noFile')}
fileInput.addEventListener('change',updateFileName);for(const evt of ['dragenter','dragover'])drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.add('drag')});for(const evt of ['dragleave','drop'])drop.addEventListener(evt,e=>{e.preventDefault();drop.classList.remove('drag')});drop.addEventListener('drop',e=>{if(e.dataTransfer.files.length){fileInput.files=e.dataTransfer.files;updateFileName()}});
verifyBtn.addEventListener('click',async()=>{const file=fileInput.files[0];if(!file){statusBox.textContent=tr('chooseZip');return}const form=new FormData();form.append('file',file);try{busy(true,tr('working'));render(await parseResponse(await fetch('/api/audit',{method:'POST',body:form})));busy(false,tr('done'))}catch(e){busy(false,tr('error')+': '+e.message)}});
demoBtn.addEventListener('click',async()=>{try{busy(true,tr('demoWorking'));render(await parseResponse(await fetch('/api/demo',{method:'POST'})));busy(false,tr('demoDone'))}catch(e){busy(false,tr('error')+': '+e.message)}});
applyLang();
</script>
</body></html>'''


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
    candidates = [path.parent for path in extracted.rglob("experiment_manifest.json") if (path.parent / "config.json").is_file()]
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
    return {"job_id": job_dir.name, "audit": audit, "download_url": f"/api/package/{job_dir.name}"}


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
