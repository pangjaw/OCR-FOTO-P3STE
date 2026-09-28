const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const cors = require('cors');

const app = express();
const PORT = Number(process.env.PORT) || 5000;

app.use(cors());
app.use(express.json());

const APP_DIR = __dirname;
const PATHS = {
  source: path.join(APP_DIR, '01_pdf_source'),
  target: path.join(APP_DIR, '02_pdf_target'),
  photosExport: path.join(APP_DIR, '03_photos_export'),
  photosEdited: path.join(APP_DIR, '04_photos_edited'),
  pdfMerged: path.join(APP_DIR, '05_pdf_merged'),
  photosTemp: path.join(APP_DIR, '03_photos_cropped_temp'),
  photosTime: path.join(APP_DIR, '04_Time'),
  pdfMergedTime: path.join(APP_DIR, '05_pdf_merged_Time'),
  photosCoord: path.join(APP_DIR, '04_koordinat'),
  pdfMergedCoord: path.join(APP_DIR, '05_koordinat'),
  scripts: path.join(APP_DIR, 'scripts'),
  config: path.join(APP_DIR, 'config'),
  logs: path.join(APP_DIR, 'logs'),
  templates: path.join(APP_DIR, 'templates')
};

// Ensure directories exist
Object.values(PATHS).forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

// Configure Multer Storage for 01_pdf_source and 02_pdf_target
const createStorage = (targetFolder) => multer.diskStorage({
  destination: (req, file, cb) => cb(null, targetFolder),
  filename: (req, file, cb) => cb(null, file.originalname)
});

const uploadSource = multer({ storage: createStorage(PATHS.source) });
const uploadTarget = multer({ storage: createStorage(PATHS.target) });
const uploadTempDir = path.join(APP_DIR, 'tmp_uploads');
if (!fs.existsSync(uploadTempDir)) fs.mkdirSync(uploadTempDir, { recursive: true });
const uploadTemp = multer({ dest: uploadTempDir });

// Serve static files (no-cache for instant live previews)
const noCacheStatic = { maxAge: 0, etag: false, lastModified: false, setHeaders: (res) => res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate') };
app.use('/static/photos/export', express.static(PATHS.photosExport, noCacheStatic));
app.use('/static/photos/edited', express.static(PATHS.photosEdited, noCacheStatic));
app.use('/static/photos/time', express.static(PATHS.photosTime, noCacheStatic));
app.use('/static/photos/coord', express.static(PATHS.photosCoord, noCacheStatic));
app.use('/static/photos/temp', express.static(PATHS.photosTemp, noCacheStatic));
app.use('/static/logs/collage_originals', express.static(path.join(PATHS.logs, 'collage_originals'), noCacheStatic));
app.use('/static/pdf-merged', express.static(PATHS.pdfMerged, noCacheStatic));
app.use('/static/pdf-merged-time', express.static(PATHS.pdfMergedTime, noCacheStatic));
app.use('/static/pdf-merged-coord', express.static(PATHS.pdfMergedCoord, noCacheStatic));
app.use('/static/templates', express.static(PATHS.templates));

// SSE Logging State
let activeClients = [];
let activeProcess = null;
let isRunning = false;
let currentStepName = '';
const logHistory = [];

function sendSSEMessage(dataObj) {
  if (dataObj.type === 'log') {
    logHistory.push(dataObj.line);
    if (logHistory.length > 500) logHistory.shift();
  }
  const str = `data: ${JSON.stringify(dataObj)}\n\n`;
  activeClients = activeClients.filter(c => {
    try {
      if (c.res.writableEnded || c.res.destroyed) return false;
      c.res.write(str);
      return true;
    } catch (err) {
      return false;
    }
  });
}

// Keep-alive heartbeat ping every 15s to prevent browser & TCP timeouts
setInterval(() => {
  const ping = `: ping\n\n`;
  activeClients = activeClients.filter(c => {
    try {
      if (c.res.writableEnded || c.res.destroyed) return false;
      c.res.write(ping);
      return true;
    } catch (err) {
      return false;
    }
  });
}, 15000);

// ----------------------------------------------------
// HELPER FUNCTIONS FOR METADATA & DATE RESOLUTION
// ----------------------------------------------------

const MONTH_MAP = {
  jan: '01', feb: '02', mar: '03', apr: '04', mei: '05', jun: '06',
  jul: '07', agu: '08', agt: '08', aug: '08', sep: '09', okt: '10', nov: '11', des: '12'
};

const parseIndonesianDateToIso = (text) => {
  if (!text) return '';
  const str = String(text).trim();
  const isoMatch = str.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) return isoMatch[0];

  const m = str.match(/\w+,?\s*([A-Za-z]+)\s*(\d{1,2})\s*(\d{4})/);
  if (m) {
    const mon = MONTH_MAP[m[1].toLowerCase().slice(0, 3)] || '01';
    const day = m[2].padStart(2, '0');
    const yr = m[3];
    return `${yr}-${mon}-${day}`;
  }

  const ddmmyyyy = str.match(/(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
  if (ddmmyyyy) {
    const day = ddmmyyyy[1].padStart(2, '0');
    const mon = ddmmyyyy[2].padStart(2, '0');
    const yr = ddmmyyyy[3];
    return `${yr}-${mon}-${day}`;
  }
  return '';
};

// Read target date from date.txt
const getTargetDateText = (relPath) => {
  const folderPath = path.join(PATHS.photosExport, path.dirname(relPath));
  const dateTxtFile = path.join(folderPath, 'date.txt');
  let dateBase = "Jumat, Agt 08 2025";
  if (fs.existsSync(dateTxtFile)) {
    try {
      const txt = fs.readFileSync(dateTxtFile, 'utf-8').trim();
      if (txt) dateBase = txt;
    } catch (e) {}
  }
  
  // Strip any existing time if present in date.txt to avoid duplicate HH:MM
  dateBase = dateBase.replace(/\s+\d{2}:\d{2}.*$/, '').trim();

  const stem = path.basename(relPath, path.extname(relPath));
  let pct = 0;
  if (stem === '50') pct = 50;
  else if (stem === '100') pct = 100;
  
  let duration = 45;
  let totalMin = 7 * 60 + Math.round((pct * duration) / 100);
  let hh = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
  let mm = String(totalMin % 60).padStart(2, '0');
  
  return `${dateBase} ${hh}:${mm}`;
};

// Metadata storage (meta.json) in 04_photos_edited
const getMetaFilePath = (group, relDir) => path.join(PATHS.photosEdited, group, relDir, 'meta.json');
const getCollageMetaFilePath = (relDir) => path.join(PATHS.photosExport, relDir, 'collage_crop.json');

const readPhotoMeta = (group, relPath) => {
  const relDir = path.dirname(relPath);
  const fname = path.basename(relPath);
  const metaFile = getMetaFilePath(group, relDir);
  if (fs.existsSync(metaFile)) {
    try {
      const data = JSON.parse(fs.readFileSync(metaFile, 'utf-8'));
      return data[fname] || null;
    } catch (e) {}
  }
  return null;
};

const savePhotoMeta = (group, relPath, metaObj) => {
  const relDir = path.dirname(relPath);
  const fname = path.basename(relPath);
  const metaFile = getMetaFilePath(group, relDir);
  let data = {};
  if (fs.existsSync(metaFile)) {
    try { data = JSON.parse(fs.readFileSync(metaFile, 'utf-8')); } catch (e) {}
  }
  data[fname] = metaObj;
  fs.mkdirSync(path.dirname(metaFile), { recursive: true });
  fs.writeFileSync(metaFile, JSON.stringify(data, null, 2), 'utf-8');
};

const readJsonFile = (file, fallback) => {
  try { return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf-8')) : fallback; } catch (e) { return fallback; }
};

const saveCollageCropMeta = (crop) => {
  const rel = String(crop.rel || '').replace(/\\/g, '/');
  const relDir = path.dirname(rel);
  const file = getCollageMetaFilePath(relDir);
  const data = readJsonFile(file, { schemaVersion: 1, photos: {} });
  if (!data.photos || typeof data.photos !== 'object' || Array.isArray(data.photos)) data.photos = {};
  const now = new Date().toISOString();
  const existing = data.photos[path.basename(rel)] || {};
  data.photos[path.basename(rel)] = {
    ...existing,
    rel,
    sourcePath: path.join('03_photos_export', rel).replace(/\\/g, '/'),
    cropBox: crop.cropBox,
    cropBoxPct: crop.cropBoxPct || null,
    imageSize: crop.size || null,
    source: 'manual_ui',
    updatedAt: now
  };
  data.updatedAt = now;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf-8');
};

const getTextboxBox = (xPos, yPos, width = 144, height = 16) => [Number(xPos) || 0, Number(yPos) || 0, (Number(xPos) || 0) + width, (Number(yPos) || 0) + height];

const mergeManualMeta = (group, relPath, values, detectorMeta = null) => {
  const previous = readPhotoMeta(group, relPath) || {};
  const x = Number(values.xPos);
  const y = Number(values.yPos);
  const applied = { xPos: Number.isFinite(x) ? x : 14, yPos: Number.isFinite(y) ? y : 220 };
  const initial = previous.initial || (detectorMeta ? {
    ...detectorMeta,
    xPos: detectorMeta.xPos ?? applied.xPos,
    yPos: detectorMeta.yPos ?? applied.yPos,
    detectedAt: detectorMeta.detectedAt || new Date().toISOString()
  } : {
    stage: 'manual_edit_initial_unknown',
    xPos: applied.xPos,
    yPos: applied.yPos,
    textboxBox: getTextboxBox(applied.xPos, applied.yPos),
    detectedAt: new Date().toISOString()
  });
  const next = {
    ...previous,
    initial,
    latestUserCorrection: {
      ...(previous.latestUserCorrection || {}),
      ...applied,
      textboxBox: getTextboxBox(applied.xPos, applied.yPos),
      updatedAt: new Date().toISOString(),
      source: 'manual_ui'
    },
    xPos: applied.xPos,
    yPos: applied.yPos,
    dateText: values.dateText,
    manualEdit: true,
    needCorrection: false,
    updatedAt: new Date().toISOString()
  };
  savePhotoMeta(group, relPath, next);
};

// ----------------------------------------------------
// 1. FILE UPLOAD & MANAGEMENT APIS
// ----------------------------------------------------

app.post('/api/upload/source', uploadSource.array('files'), (req, res) => {
  res.json({ success: true, count: req.files ? req.files.length : 0 });
});

app.post('/api/upload/target', uploadTarget.array('files'), (req, res) => {
  res.json({ success: true, count: req.files ? req.files.length : 0 });
});

app.get('/api/files', (req, res) => {
  const getFileList = (dir) => {
    if (!fs.existsSync(dir)) return [];
    return fs.readdirSync(dir).filter(f => f.toLowerCase().endsWith('.pdf')).map(f => {
      const stats = fs.statSync(path.join(dir, f));
      return {
        name: f,
        size: stats.size,
        modified: stats.mtime
      };
    });
  };

  res.json({
    sourceFiles: getFileList(PATHS.source),
    targetFiles: getFileList(PATHS.target)
  });
});

app.delete('/api/files', (req, res) => {
  const { folder, filename } = req.body;
  if (!['source', 'target'].includes(folder)) {
    return res.status(400).json({ error: 'Invalid folder' });
  }
  const targetDir = folder === 'source' ? PATHS.source : PATHS.target;
  const filePath = path.join(targetDir, filename);
  if (fs.existsSync(filePath)) {
    fs.unlinkSync(filePath);
    return res.json({ success: true });
  }
  res.status(404).json({ error: 'File not found' });
});

app.get('/api/status', (req, res) => {
  res.json({
    is_running: isRunning,
    step: currentStepName,
    active_clients: activeClients.length
  });
});

app.get('/api/stream-logs', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();
  if (req.socket) {
    req.socket.setKeepAlive(true);
    req.socket.setNoDelay(true);
    req.setTimeout(0);
  }

  const clientId = Date.now();
  activeClients.push({ id: clientId, res });

  // Send current running status immediately on connect/refresh
  res.write(`data: ${JSON.stringify({ type: 'status', is_running: isRunning, step: currentStepName })}\n\n`);

  // Send last 50 log lines so terminal isn't blank on refresh
  logHistory.slice(-50).forEach(line => {
    res.write(`data: ${JSON.stringify({ type: 'log', line })}\n\n`);
  });

  req.on('close', () => {
    activeClients = activeClients.filter(c => c.id !== clientId);
  });
});

const STEP_SCRIPTS = {
  step1: { script: 'export_pdf_foto.py', args: [] },
  step1_crop: { script: 'export_pdf_foto.py', args: ['--render-crop'] },
  'step1.5': { script: 'auto_crop_collages.py', args: [] },
  step2: { script: 'extract_pdf_dates.py', args: [] },
  step3: { script: 'scheduler.py', args: [] },
  'step3.5': { script: 'audit_and_correct_personnel.py', args: ['--action', 'auto-correct-batch', '--folder', '02_pdf_target'] },
  step4: { script: 'edit_timemark_ide1.py', args: ['--detector', 'google_vision'] },
  step4_fast: { script: 'fast_update_timemark.py', args: [] },
  step5: { script: 'merge_pdf_foto.py', args: [] },
  // Time pipeline steps (standalone 04_Time and 05_pdf_merged_Time)
  step4_time: { script: 'edit_photo_time_only.py', args: ['--schedule', 'schedule.json'] },
  step5_time: { script: 'merge_pdf_foto.py', args: ['--photos', './04_Time', '--output', './05_pdf_merged_Time'] },
  step6_core_optik: { script: 'correct_serat_optik_cores.py', args: ['--apply', '--folders', '05_pdf_merged'] },
  step6_core_optik_time: { script: 'correct_serat_optik_cores.py', args: ['--apply', '--folders', '05_pdf_merged_Time'] },
  // Coordinate pipeline steps (standalone 04_koordinat and 05_koordinat)
  step4_coord: { script: 'edit_photo_coordinate_only.py', args: ['--schedule', 'schedule.json'] },
  step5_coord: { script: 'merge_pdf_foto.py', args: ['--photos', './04_koordinat', '--output', './05_koordinat'] },
  step6_core_optik_coord: { script: 'correct_serat_optik_cores.py', args: ['--apply', '--folders', '05_koordinat'] }
};

app.post('/api/run-step', (req, res) => {
  const { step, detector } = req.body;
  if (isRunning) {
    return res.status(400).json({ error: 'Pipeline is already running' });
  }

  const isAllStandard = step === 'all';
  const isAllTime = step === 'all_time';
  const isAllCoord = step === 'all_coord';
  const stepConfig = STEP_SCRIPTS[step];

  if (!isAllStandard && !isAllTime && !isAllCoord && !stepConfig) {
    return res.status(400).json({ error: 'Invalid step requested' });
  }

  isRunning = true;
  currentStepName = step;
  sendSSEMessage({ type: 'status', is_running: true, step: currentStepName });

  const runSingleScript = (scriptItem, callback) => {
    const scriptName = typeof scriptItem === 'string' ? scriptItem : scriptItem.script;
    const scriptArgs = Array.isArray(scriptItem && scriptItem.args) ? scriptItem.args : [];
    const scriptPath = path.join(PATHS.scripts, scriptName);
    sendSSEMessage({ type: 'log', line: `\n=== Executing ${scriptName} ${scriptArgs.join(' ')} ===\n` });

    const pyProc = spawn('python', ['-u', scriptPath, ...scriptArgs], {
      cwd: APP_DIR,
      env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
    });
    activeProcess = pyProc;

    const recentStderr = [];

    pyProc.stdout.on('data', (data) => {
      const text = data.toString();
      text.split('\n').forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return;
        if (trimmed.startsWith('{"type":"stage"') || trimmed.startsWith('{"type":"quota_exceeded"')) {
          try {
            const parsed = JSON.parse(trimmed);
            sendSSEMessage(parsed);
            return;
          } catch (e) {}
        }
        if (trimmed.startsWith('__SUMMARY__:')) {
          try {
            const sumData = JSON.parse(trimmed.slice(12));
            sendSSEMessage({ type: 'summary', summary: sumData });
            return;
          } catch (e) {}
        }
        sendSSEMessage({ type: 'log', line });
      });
    });

    pyProc.stderr.on('data', (data) => {
      const text = data.toString();
      text.split('\n').forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return;
        // Suppress noisy C-level zbar decoder assertion warnings to keep web UI fast and light
        if (trimmed.includes('zbar') || trimmed.includes('Assertion') || trimmed.includes('seg->finder') || trimmed.includes('part=1') || trimmed.includes('part=0')) return;
        recentStderr.push(trimmed);
        if (recentStderr.length > 15) recentStderr.shift();
        sendSSEMessage({ type: 'log', line: `[STDERR] ${trimmed}` });
      });
    });

    pyProc.on('close', (code) => {
      activeProcess = null;
      if (code === 0) {
        sendSSEMessage({ type: 'log', line: `\n✅ ${scriptName} selesai dengan sukses (Exit code 0).\n` });
        if (callback) callback(null);
      } else {
        let errBanner = `\n============================================================\n`;
        errBanner += `❌ [ERROR] ${scriptName} berhenti dengan kode kesalahan (Exit Code: ${code})\n`;
        if (recentStderr.length > 0) {
          errBanner += `Keterangan Kesalahan:\n`;
          recentStderr.forEach(l => errBanner += `  • ${l}\n`);
        } else {
          errBanner += `Silakan periksa detail error pada baris log di atas atau cek folder logs/.\n`;
        }
        errBanner += `============================================================\n`;
        sendSSEMessage({ type: 'log', line: errBanner });
        if (callback) callback(new Error(`Exit code ${code}`));
      }
    });
  };

  if (isAllStandard) {
    const queue = [
      { script: 'export_pdf_foto.py', args: [] },
      { script: 'auto_crop_collages.py', args: [] },
      { script: 'extract_pdf_dates.py', args: [] },
      { script: 'scheduler.py', args: [] },
      { script: 'audit_and_correct_personnel.py', args: ['--action', 'auto-correct-batch', '--folder', '02_pdf_target'] },
      { script: 'extract_file_personnel.py', args: [] },
      { script: 'edit_timemark_ide1.py', args: detector === 'guide' ? ['--detector', 'guide'] : ['--detector', 'google_vision'] },
      { script: 'merge_pdf_foto.py', args: [] },
      { script: 'correct_serat_optik_cores.py', args: ['--apply', '--folders', '05_pdf_merged'] }
    ];
    const runQueue = (index) => {
      if (index >= queue.length) {
        isRunning = false;
        sendSSEMessage({ type: 'status', is_running: false, step: 'completed' });
        return res.json({ success: true });
      }
      runSingleScript(queue[index], (err) => {
        if (err) {
          isRunning = false;
          sendSSEMessage({ type: 'status', is_running: false, step: 'error' });
          return res.json({ success: false, error: err.message });
        }
        runQueue(index + 1);
      });
    };
    runQueue(0);
  } else if (isAllTime) {
    const queue = [
      { script: 'export_pdf_foto.py', args: [] },
      { script: 'auto_crop_collages.py', args: [] },
      { script: 'extract_pdf_dates.py', args: [] },
      { script: 'scheduler.py', args: [] },
      { script: 'audit_and_correct_personnel.py', args: ['--action', 'auto-correct-batch', '--folder', '02_pdf_target'] },
      { script: 'extract_file_personnel.py', args: [] },
      { script: 'edit_photo_time_only.py', args: ['--schedule', 'schedule.json'] },
      { script: 'merge_pdf_foto.py', args: ['--photos', './04_Time', '--output', './05_pdf_merged_Time'] },
      { script: 'correct_serat_optik_cores.py', args: ['--apply', '--folders', '05_pdf_merged_Time'] }
    ];
    const runQueue = (index) => {
      if (index >= queue.length) {
        isRunning = false;
        sendSSEMessage({ type: 'status', is_running: false, step: 'completed' });
        return res.json({ success: true });
      }
      runSingleScript(queue[index], (err) => {
        if (err) {
          isRunning = false;
          sendSSEMessage({ type: 'status', is_running: false, step: 'error' });
          return res.json({ success: false, error: err.message });
        }
        runQueue(index + 1);
      });
    };
    runQueue(0);
  } else if (isAllCoord) {
    const queue = [
      { script: 'export_pdf_foto.py', args: [] },
      { script: 'auto_crop_collages.py', args: [] },
      { script: 'extract_pdf_dates.py', args: [] },
      { script: 'scheduler.py', args: [] },
      { script: 'audit_and_correct_personnel.py', args: ['--action', 'auto-correct-batch', '--folder', '02_pdf_target'] },
      { script: 'extract_file_personnel.py', args: [] },
      { script: 'edit_photo_coordinate_only.py', args: ['--schedule', 'schedule.json'] },
      { script: 'merge_pdf_foto.py', args: ['--photos', './04_koordinat', '--output', './05_koordinat'] },
      { script: 'correct_serat_optik_cores.py', args: ['--apply', '--folders', '05_koordinat'] }
    ];
    const runQueue = (index) => {
      if (index >= queue.length) {
        isRunning = false;
        sendSSEMessage({ type: 'status', is_running: false, step: 'completed' });
        return res.json({ success: true });
      }
      runSingleScript(queue[index], (err) => {
        if (err) {
          isRunning = false;
          sendSSEMessage({ type: 'status', is_running: false, step: 'error' });
          return res.json({ success: false, error: err.message });
        }
        runQueue(index + 1);
      });
    };
    runQueue(0);
  } else {
    let finalStepConfig = stepConfig;
    if (step === 'step4') {
      const det = detector === 'guide' ? 'guide' : 'google_vision';
      finalStepConfig = { ...stepConfig, args: ['--detector', det] };
    }
    runSingleScript(finalStepConfig, (err) => {
      isRunning = false;
      invalidateGalleryCache();
      sendSSEMessage({ type: 'status', is_running: false, step: err ? 'error' : 'completed' });
      res.json({ success: !err, error: err ? err.message : null });
    });
  }
});

app.post('/api/stop', (req, res) => {
  if (activeProcess) {
    activeProcess.kill('SIGTERM');
    activeProcess = null;
  }
  isRunning = false;
  sendSSEMessage({ type: 'status', is_running: false, step: 'stopped' });
  sendSSEMessage({ type: 'log', line: '🛑 Pipeline stopped by user.\n' });
  res.json({ success: true });
});

app.post('/api/pipeline/resume', (req, res) => {
  const { action } = req.body;
  if (!activeProcess) {
    return res.status(400).json({ error: 'No active pipeline process to resume' });
  }
  if (action === 'continue_guide' || action === 'stop') {
    try {
      activeProcess.stdin.write(action + '\n');
      sendSSEMessage({ type: 'log', line: `\n[ACTION] Resuming pipeline with action: ${action}\n` });
      return res.json({ success: true, action });
    } catch (e) {
      return res.status(500).json({ error: e.message });
    }
  }
  return res.status(400).json({ error: 'Invalid action' });
});

// ----------------------------------------------------
// 3. DUAL PHOTO GALLERY & COMPARISON APIS
// ----------------------------------------------------

let galleryCache = null;
let galleryCacheTimestamp = 0;
const GALLERY_CACHE_TTL = 4000;

function invalidateGalleryCache() {
  galleryCache = null;
  galleryCacheTimestamp = 0;
}

function fastScanPhotos(rootDir, collectBackups = false) {
  const list = [];
  const backupSet = new Set();
  if (!fs.existsSync(rootDir)) return { list, backupSet };

  const walk = (dir, rel = '') => {
    let entries = [];
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      const r = rel ? `${rel}/${entry.name}` : entry.name;
      if (entry.isDirectory()) {
        walk(full, r);
      } else if (entry.isFile()) {
        const lower = entry.name.toLowerCase();
        if (collectBackups && lower.endsWith('.original_backup.jpg')) {
          backupSet.add(r.replace(/\\/g, '/'));
        } else if ((lower.endsWith('.jpg') || lower.endsWith('.jpeg')) && !lower.endsWith('.unedited')) {
          list.push(r.replace(/\\/g, '/'));
        }
      }
    }
  };
  walk(rootDir);
  return { list, backupSet };
}

// Cached schedule Tim resolver
let scheduleTimCache = null;
let scheduleTimCacheMtime = 0;
const getScheduledTim = (relDir) => {
  try {
    const schedPath = path.join(APP_DIR, 'schedule.json');
    if (fs.existsSync(schedPath)) {
      const stat = fs.statSync(schedPath);
      if (scheduleTimCache === null || stat.mtimeMs !== scheduleTimCacheMtime) {
        scheduleTimCache = new Map();
        scheduleTimCacheMtime = stat.mtimeMs;
        const schedData = JSON.parse(fs.readFileSync(schedPath, 'utf8'));
        (schedData.schedules || []).forEach(s => {
          const key = `${s.btp || ''}/${s.category || ''}/${s.identifier || ''}`.replace(/\\/g, '/');
          if (s.tim) scheduleTimCache.set(key, `Tim_${s.tim}`);
        });
      }
    }
  } catch (e) {}
  return scheduleTimCache ? (scheduleTimCache.get(relDir) || null) : null;
};

app.get('/api/photos/gallery', (req, res) => {
  if (galleryCache && (Date.now() - galleryCacheTimestamp < GALLERY_CACHE_TTL)) {
    return res.json(galleryCache);
  }

  const rawData = fastScanPhotos(PATHS.photosExport, true);
  const editedData = fastScanPhotos(PATHS.photosEdited, false);
  const croppedData = fastScanPhotos(PATHS.photosTemp, false);
  const croppedSet = new Set(croppedData.list);

  const croppedManifest = readJsonFile(path.join(PATHS.logs, 'auto_crop_manifest.json'), { collages: [] });
  const collageSet = new Set(
    Array.isArray(croppedManifest.collages)
      ? croppedManifest.collages.map(c => (c.rel_path || '').toLowerCase())
      : []
  );

  const editedMap = new Map();
  const editedFileSet = new Set(editedData.list);
  const editedFolderCounts = new Map();

  editedData.list.forEach(rel => {
    const parts = rel.split('/');
    if (parts.length < 2) return;
    const rawRel = parts.slice(1).join('/');
    if (!editedMap.has(rawRel)) {
      editedMap.set(rawRel, rel);
    }
    if (parts.length >= 3) {
      const tim = parts[0];
      const relDir = parts.slice(1, -1).join('/');
      if (!editedFolderCounts.has(relDir)) {
        editedFolderCounts.set(relDir, {});
      }
      const counts = editedFolderCounts.get(relDir);
      counts[tim] = (counts[tim] || 0) + 1;
    }
  });

  // Helper to determine single consistent Tim group for an entire relDir
  const folderGroupCache = new Map();
  const getFolderTimGroup = (relDir) => {
    if (folderGroupCache.has(relDir)) return folderGroupCache.get(relDir);

    const counts = editedFolderCounts.get(relDir) || {};
    const schedTim = getScheduledTim(relDir);

    let chosenTim = null;
    if (schedTim && counts[schedTim]) {
      chosenTim = schedTim;
    } else {
      let maxCount = -1;
      for (const [tim, count] of Object.entries(counts)) {
        if (count > maxCount) {
          maxCount = count;
          chosenTim = tim;
        }
      }
    }
    if (!chosenTim) chosenTim = schedTim || 'Tim_1';
    folderGroupCache.set(relDir, chosenTim);
    return chosenTim;
  };

  const folderDateCache = new Map();
  const getCachedDateBase = (relDir) => {
    if (folderDateCache.has(relDir)) return folderDateCache.get(relDir);
    const dateTxtFile = path.join(PATHS.photosExport, relDir, 'date.txt');
    let dateBase = "Jumat, Agt 08 2025";
    if (fs.existsSync(dateTxtFile)) {
      try {
        const txt = fs.readFileSync(dateTxtFile, 'utf-8').trim();
        if (txt) dateBase = txt.replace(/\s+\d{2}:\d{2}.*$/, '').trim() || dateBase;
      } catch (e) {}
    }
    folderDateCache.set(relDir, dateBase);
    return dateBase;
  };

  const folderMetaCache = new Map();
  const getCachedFolderMeta = (group, relDir) => {
    const key = `${group}/${relDir}`;
    if (folderMetaCache.has(key)) return folderMetaCache.get(key);
    const metaFile = getMetaFilePath(group, relDir);
    let data = null;
    if (fs.existsSync(metaFile)) {
      try { data = JSON.parse(fs.readFileSync(metaFile, 'utf-8')); } catch (e) {}
    }
    folderMetaCache.set(key, data);
    return data;
  };

  const gallery = [];
  rawData.list.forEach(rel => {
    const parts = rel.split('/');
    const btp = parts[0] || 'Unknown';
    const category = parts[1] || 'General';
    const detail = parts.slice(2, -1).join('/') || 'Detail';
    const filename = parts[parts.length - 1];
    const relDir = path.dirname(rel);
    const group = getFolderTimGroup(relDir);

    let editedRel = null;
    const primaryEditedRel = `${group}/${rel}`;
    if (editedFileSet.has(primaryEditedRel)) {
      editedRel = primaryEditedRel;
    } else {
      const otherRel = editedMap.get(rel);
      if (otherRel) editedRel = otherRel;
    }

    const folderMeta = editedRel ? getCachedFolderMeta(group, relDir) : null;
    const meta = folderMeta ? (folderMeta[filename] || null) : null;

    const dateBase = getCachedDateBase(relDir);
    const stem = path.basename(rel, path.extname(rel));
    let pct = 0;
    if (stem === '50') pct = 50;
    else if (stem === '100') pct = 100;
    const totalMin = 7 * 60 + Math.round((pct * 45) / 100);
    const hh = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
    const mm = String(totalMin % 60).padStart(2, '0');
    const targetDateText = `${dateBase} ${hh}:${mm}`;
    const isoDate = parseIndonesianDateToIso(targetDateText);

    let modifiedMs = 0;
    if (meta && meta.updatedAt) {
      const metaMs = new Date(meta.updatedAt).getTime();
      if (Number.isFinite(metaMs)) modifiedMs = metaMs;
    }
    const modifiedAt = modifiedMs > 0 ? new Date(modifiedMs).toISOString() : null;
    const folderKey = `${group}/${relDir}`;
    const hasCropped = croppedSet.has(rel);
    const isCollage = hasCropped || collageSet.has(rel.toLowerCase());
    const backupRel = `${relDir}/${stem}.original_backup.jpg`.replace(/\\/g, '/');
    const hasBackup = rawData.backupSet.has(backupRel);

    gallery.push({
      rel, btp, category, detail, filename, timGroup: group, folderKey, modifiedAt, modifiedMs,
      folderModifiedMs: modifiedMs,
      rawUrl: `/static/photos/export/${rel}`,
      editedUrl: editedRel ? `/static/photos/edited/${editedRel}` : null,
      croppedUrl: hasCropped ? `/static/photos/temp/${rel}` : null,
      hasEdited: !!editedRel,
      hasCropped,
      isCollage,
      hasBackup,
      targetDateText,
      isoDate,
      lastDateText: meta ? meta.dateText : targetDateText,
      lastYPos: meta ? meta.yPos : 220,
      lastXPos: meta ? meta.xPos : 14,
      detector: meta && meta.detector ? meta.detector : (meta && meta.stage === 'stage_google_vision' ? 'google_vision' : (meta ? 'guide' : null)),
      stage: meta ? meta.stage : null,
      needCorrection: !!(meta && meta.needCorrection),
      manualEdit: !!(meta && meta.manualEdit)
    });
  });

  const responseData = { total: gallery.length, photos: gallery };
  galleryCache = responseData;
  galleryCacheTimestamp = Date.now();
  res.json(responseData);
});

app.get('/api/photos/folders', (req, res) => {
  const folders = [];
  const roots = fs.readdirSync(PATHS.photosEdited, { withFileTypes: true })
    .filter(entry => entry.isDirectory() && /^Tim_\d+$/.test(entry.name));

  const walk = (dir, relDir = '') => {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const jpgs = entries.filter(entry => entry.isFile() && /\.jpe?g$/i.test(entry.name));
    if (jpgs.length > 0) {
      const files = jpgs.map(entry => {
        const rel = path.relative(PATHS.photosEdited, path.join(dir, entry.name)).replace(/\\/g, '/');
        const stat = fs.statSync(path.join(dir, entry.name));
        return { filename: entry.name, rel, modifiedMs: stat.mtimeMs, url: `/static/photos/edited/${rel}` };
      }).sort((a, b) => a.filename.localeCompare(b.filename, undefined, { numeric: true }));
      const relativeFolder = path.relative(PATHS.photosEdited, dir).replace(/\\/g, '/');
      folders.push({ folder: relativeFolder, files, modifiedMs: Math.max(...files.map(file => file.modifiedMs)) });
    }
    entries.filter(entry => entry.isDirectory()).forEach(entry => walk(path.join(dir, entry.name), `${relDir}/${entry.name}`));
  };

  roots.forEach(root => walk(path.join(PATHS.photosEdited, root.name), root.name));
  folders.sort((a, b) => b.modifiedMs - a.modifiedMs || a.folder.localeCompare(b.folder));
  res.json({ total: folders.length, folders });
});

// GET /api/photos/raw-preview — serve source photo (cropped temp if exists, else raw export)
app.get('/api/photos/raw-preview', (req, res) => {
  const rel = String(req.query.rel || '').replace(/\\/g, '/');
  if (!rel || rel.startsWith('/') || rel.split('/').includes('..')) {
    return res.status(400).json({ error: 'Invalid rel path' });
  }
  const tempFile = path.join(PATHS.photosTemp, rel);
  if (fs.existsSync(tempFile)) {
    return res.sendFile(tempFile);
  }
  const rawFile = path.join(PATHS.photosExport, rel);
  if (!fs.existsSync(rawFile)) return res.status(404).json({ error: 'Photo not found' });
  res.sendFile(rawFile);
});

// GET /api/photos/clean-cropped-preview — get clean unwatermarked cropped photo (cropped on demand to temp)
app.get('/api/photos/clean-cropped-preview', (req, res) => {
  const rel = String(req.query.rel || '').replace(/\\/g, '/');
  if (!rel || rel.startsWith('/') || rel.split('/').includes('..')) {
    return res.status(400).json({ error: 'Invalid rel path' });
  }

  const tempFile = path.join(PATHS.photosTemp, rel);
  if (fs.existsSync(tempFile)) {
    return res.sendFile(tempFile);
  }

  const script = path.join(PATHS.scripts, 'crop_single_temp.py');
  const pyProc = spawn('python', [script, '--rel', rel, '--photos-dir', PATHS.photosExport, '--temp-dir', PATHS.photosTemp], { cwd: APP_DIR });

  pyProc.on('close', () => {
    if (fs.existsSync(tempFile)) {
      return res.sendFile(tempFile);
    }
    const rawFile = path.join(PATHS.photosExport, rel);
    if (fs.existsSync(rawFile)) {
      return res.sendFile(rawFile);
    }
    res.status(404).json({ error: 'Photo not found' });
  });
});

const safePhotoRel = (value) => {
  const rel = String(value || '').replace(/\\/g, '/');
  if (!rel || rel.startsWith('/') || rel.split('/').includes('..') || !/\.(jpe?g|png)$/i.test(rel)) return null;
  const root = path.resolve(PATHS.photosExport);
  const file = path.resolve(root, rel);
  return file.startsWith(root + path.sep) ? { rel, file } : null;
};

const readImageSize = (file) => {
  const data = fs.readFileSync(file);
  if (data[0] === 0xff && data[1] === 0xd8) {
    let i = 2;
    while (i + 9 < data.length) {
      if (data[i] !== 0xff) { i++; continue; }
      const marker = data[i + 1];
      const len = data.readUInt16BE(i + 2);
      if (marker >= 0xc0 && marker <= 0xc3) return [data.readUInt16BE(i + 5), data.readUInt16BE(i + 7)];
      i += 2 + len;
    }
  }
  if (data.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return [data.readUInt32BE(16), data.readUInt32BE(20)];
  throw new Error('Unsupported image format');
};

const yoloFromLabel = (label, size) => {
  const p = String(label || '').trim().split(/\s+/).map(Number);
  if (p.length < 5 || p.some(Number.isNaN)) return null;
  const [w, h] = size;
  const [xc, yc, nw, nh] = p.slice(1, 5);
  return [Math.round((xc - nw / 2) * w), Math.round((yc - nh / 2) * h), Math.round((xc + nw / 2) * w), Math.round((yc + nh / 2) * h)];
};

app.get('/api/guidelines', (req, res) => {
  const selected = safePhotoRel(req.query.rel);
  if (selected) {
    if (!fs.existsSync(selected.file)) return res.status(404).json({ error: 'Photo not found' });
    const size = readImageSize(selected.file);
    const labelFile = selected.file.replace(/\.[^.]+$/, '.txt');
    const label = fs.existsSync(labelFile) ? fs.readFileSync(labelFile, 'utf8').trim() : '';
    return res.json({ rel: selected.rel, imageSize: size, bbox: yoloFromLabel(label, size), label, imageUrl: `/static/photos/export/${selected.rel}` });
  }
  const photos = [];
  const walk = (dir, relDir = '') => fs.readdirSync(dir, { withFileTypes: true }).forEach(entry => {
    const full = path.join(dir, entry.name);
    const rel = path.posix.join(relDir, entry.name);
    if (entry.isDirectory()) return walk(full, rel);
    if (!/\.(jpe?g|png)$/i.test(entry.name)) return;
    const size = readImageSize(full);
    const labelFile = full.replace(/\.[^.]+$/, '.txt');
    const label = fs.existsSync(labelFile) ? fs.readFileSync(labelFile, 'utf8').trim() : '';
    photos.push({ rel, imageSize: size, bbox: yoloFromLabel(label, size), imageUrl: `/static/photos/export/${rel}` });
  });
  if (fs.existsSync(PATHS.photosExport)) walk(PATHS.photosExport);
  res.json({ total: photos.length, photos });
});

app.post('/api/guidelines', (req, res) => {
  const selected = safePhotoRel(req.body && req.body.rel);
  if (!selected || !fs.existsSync(selected.file)) return res.status(400).json({ error: 'Invalid photo path' });
  const size = readImageSize(selected.file);
  const box = Array.isArray(req.body.bbox) ? req.body.bbox.map(Number) : [];
  if (box.length !== 4 || box.some(Number.isNaN)) return res.status(400).json({ error: 'bbox [x1,y1,x2,y2] is required' });
  const [w, h] = size;
  const [x1, y1, x2, y2] = [Math.max(0, Math.min(box[0], w)), Math.max(0, Math.min(box[1], h)), Math.max(0, Math.min(box[2], w)), Math.max(0, Math.min(box[3], h))];
  if (x2 <= x1 || y2 <= y1) return res.status(400).json({ error: 'bbox must have positive width and height' });
  const label = `0 ${((x1 + x2) / 2 / w).toFixed(6)} ${((y1 + y2) / 2 / h).toFixed(6)} ${((x2 - x1) / w).toFixed(6)} ${((y2 - y1) / h).toFixed(6)}\n`;
  fs.writeFileSync(selected.file.replace(/\.[^.]+$/, '.txt'), label, 'utf8');
  res.json({ success: true, rel: selected.rel, imageSize: size, bbox: [x1, y1, x2, y2], label });
});

app.post('/api/photos/manual-edit', async (req, res) => {
  const { rawRelPath, dateText, yPos, xPos, timGroup, applyToFolder, applyDateToFolder, isTextEdit } = req.body;
  if (!rawRelPath || !dateText) {
    return res.status(400).json({ error: 'rawRelPath and dateText are required' });
  }

  const normalizedRel = rawRelPath.replace(/\\/g, '/');
  const relDir = path.dirname(normalizedRel);
  const schedTim = getScheduledTim(relDir);
  const group = (timGroup && timGroup !== 'Tim_1') ? timGroup : (schedTim || timGroup || 'Tim_1');
  const pyScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');
  const folderPath = path.join(PATHS.photosExport, relDir);

  // Jika aksi adalah edit teks (isTextEdit: true), HANYA ubah seluruh folder jika applyDateToFolder === true!
  let shouldApplyToAll = false;
  if (isTextEdit === true) {
    shouldApplyToAll = (applyDateToFolder === true);
  } else {
    shouldApplyToAll = (applyToFolder === true);
  }

  let targetRelPaths = [normalizedRel];
  if (shouldApplyToAll && fs.existsSync(folderPath) && fs.statSync(folderPath).isDirectory()) {
    const files = fs.readdirSync(folderPath).filter(f => f.toLowerCase().endsWith('.jpg') && !f.includes('.original_backup.') && !f.includes('.swap_tmp'));
    if (files.length > 0) {
      targetRelPaths = files.map(f => `${relDir}/${f}`.replace(/\\/g, '/'));
    }
  }

  const helperCalculateDate = (baseDate, photoStem) => {
    // Normalize any duplicated trailing times e.g. "Kamis, Agt 14 2025 07:00 07:00" -> "Kamis, Agt 14 2025 07:00"
    baseDate = (baseDate || "").trim();
    const dupMatch = baseDate.match(/^(.*?\s\d{2}:\d{2})(?:\s+\d{2}:\d{2})+$/);
    if (dupMatch) baseDate = dupMatch[1];

    const m = baseDate.match(/^(.*?\d{4})\s+(\d{2}):(\d{2})$/);
    if (!m) return baseDate;
    let [_, datePart, hh, mm] = m;
    let totalMin = parseInt(hh) * 60 + parseInt(mm);
    let pct = 0;
    if (photoStem === '50') pct = 50;
    else if (photoStem === '100') pct = 100;
    let duration = 45;
    totalMin += Math.round((pct * duration) / 100);
    let newHH = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
    let newMM = String(totalMin % 60).padStart(2, '0');
    return `${datePart} ${newHH}:${newMM}`;
  };

  let errors = [];
  for (let relP of targetRelPaths) {
    const inputFile = path.join(PATHS.photosExport, relP);
    const outputFile = path.join(PATHS.photosEdited, group, relP);
    fs.mkdirSync(path.dirname(outputFile), { recursive: true });

    const stem = path.basename(relP, '.jpg');
    let photoDateText = dateText;
    if (relP !== normalizedRel) {
      // Ini adalah foto saudara
      if (applyDateToFolder) {
        photoDateText = helperCalculateDate(dateText, stem);
      } else {
        // Jangan ganti teks tanggal foto saudara jika applyDateToFolder tidak aktif
        const existingMeta = readPhotoMeta(group, relP);
        if (existingMeta && existingMeta.dateText) {
          photoDateText = existingMeta.dateText;
        } else {
          const dateBase = getCachedDateBase(relDir);
          let pct = 0;
          if (stem === '50') pct = 50;
          else if (stem === '100') pct = 100;
          const totalMin = 7 * 60 + Math.round((pct * 45) / 100);
          const hh = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
          const mm = String(totalMin % 60).padStart(2, '0');
          photoDateText = `${dateBase} ${hh}:${mm}`;
        }
      }
    }

    const args = [
      pyScript,
      '--input', inputFile,
      '--single-out', outputFile,
      '--date', photoDateText
    ];

    if (yPos !== undefined && yPos !== null && yPos !== '') {
      args.push('--y-override', String(yPos));
    }
    if (xPos !== undefined && xPos !== null && xPos !== '') {
      args.push('--x-override', String(xPos));
    }

    try {
      await new Promise((resolve, reject) => {
        let stderrChunks = [];
        const pyProc = spawn('python', args, { cwd: APP_DIR });
        pyProc.stderr.on('data', (d) => stderrChunks.push(d));
        pyProc.on('close', (code) => {
          if (code === 0) {
            // Retry: Windows may not have file visible immediately after close
            let retries = 8, delay = 50;
            const check = () => {
              if (fs.existsSync(outputFile)) resolve();
              else if (retries-- > 0) setTimeout(check, delay);
              else {
                const stderrStr = Buffer.concat(stderrChunks).toString().slice(-500);
                reject(new Error(`Exit 0 but output not found after retries: ${outputFile} | stderr: ${stderrStr}`));
              }
            };
            check();
          } else {
            const stderrStr = Buffer.concat(stderrChunks).toString().slice(-500);
            reject(new Error(`Exit ${code}: ${stderrStr}`));
          }
        });
        pyProc.on('error', (err) => reject(new Error(`Spawn failed: ${err.message}`)));
      });

      // Delete .unedited flag file if present
      const uneditedFlag = outputFile + '.unedited';
      if (fs.existsSync(uneditedFlag)) {
        try { fs.unlinkSync(uneditedFlag); } catch (e) {}
      }

      const detectorSidecar = `${outputFile}.detector.json`;
      const detectorMeta = readJsonFile(detectorSidecar, null);
      if (fs.existsSync(detectorSidecar)) {
        try { fs.unlinkSync(detectorSidecar); } catch (e) {}
      }

      // Preserve detector position and replace only the latest user correction.
      mergeManualMeta(group, relP, {
        yPos: yPos !== undefined && yPos !== null && yPos !== '' ? parseInt(yPos) : 220,
        xPos: xPos !== undefined && xPos !== null && xPos !== '' ? parseInt(xPos) : 14,
        dateText: photoDateText
      }, detectorMeta);

      // Sync manual edit to all other Tim_N folders where this asset exists
      try {
        if (fs.existsSync(PATHS.photosEdited)) {
          const allTims = fs.readdirSync(PATHS.photosEdited).filter(d => d.startsWith('Tim_') && d !== group);
          for (const otherTim of allTims) {
            const otherFolder = path.join(PATHS.photosEdited, otherTim, relDir);
            if (fs.existsSync(otherFolder)) {
              const otherOutputFile = path.join(PATHS.photosEdited, otherTim, relP);
              fs.copyFileSync(outputFile, otherOutputFile);
              // Also sync backup if present
              const srcBackup = outputFile.replace(/\.jpg$/i, '.original_backup.jpg');
              const dstBackup = otherOutputFile.replace(/\.jpg$/i, '.original_backup.jpg');
              if (fs.existsSync(srcBackup)) {
                fs.copyFileSync(srcBackup, dstBackup);
              }
              // Also sync meta.json
              const srcMeta = path.join(PATHS.photosEdited, group, relDir, 'meta.json');
              const dstMeta = path.join(otherFolder, 'meta.json');
              if (fs.existsSync(srcMeta)) {
                fs.copyFileSync(srcMeta, dstMeta);
              }
            }
          }
        }
      } catch (e) {
        console.error('Error syncing edited photo to other Tim folders:', e);
      }
    } catch (err) {
      errors.push(`${relP}: ${err.message}`);
    }
  }

  if (errors.length > 0) {
    return res.status(500).json({ error: errors.join('; ') });
  }

  invalidateGalleryCache();
  const editedUrl = `/static/photos/edited/${group}/${normalizedRel}`;
  res.json({ success: true, editedUrl: `${editedUrl}?t=${Date.now()}` });
});

// ----------------------------------------------------
// TIME ONLY GALLERY & MANUAL EDIT APIS (04_Time)
// ----------------------------------------------------

const getTargetTimeOnlyText = (relPath) => {
  const stem = path.basename(relPath, path.extname(relPath));
  let pct = 0;
  if (stem === '50') pct = 50;
  else if (stem === '100') pct = 100;
  let duration = 45;
  let totalMin = 7 * 60 + Math.round((pct * duration) / 100);
  let hh = String(Math.floor(totalMin / 60) % 24).padStart(2, '0');
  let mm = String(totalMin % 60).padStart(2, '0');
  return `${hh}:${mm}`;
};

app.get('/api/photos/time-gallery', (req, res) => {
  const scanPhotos = (rootDir) => {
    const list = [];
    if (!fs.existsSync(rootDir)) return list;

    const walkSync = (dir, relPath = '') => {
      const files = fs.readdirSync(dir);
      files.forEach(file => {
        const fullPath = path.join(dir, file);
        const rel = path.join(relPath, file);
        if (fs.statSync(fullPath).isDirectory()) {
          walkSync(fullPath, rel);
        } else if ((file.toLowerCase().endsWith('.jpg') || file.toLowerCase().endsWith('.jpeg')) && !fs.existsSync(`${fullPath}.unedited`)) {
          list.push(rel.replace(/\\/g, '/'));
        }
      });
    };
    walkSync(rootDir);
    return list;
  };

  const rawList = scanPhotos(PATHS.photosExport);
  const timeList = scanPhotos(PATHS.photosTime);

  const timeMap = new Map();
  timeList.forEach(rel => {
    const parts = rel.split('/');
    if (parts.length < 2) return;
    const rawRel = parts.slice(1).join('/');
    const fullPath = path.join(PATHS.photosTime, rel);
    if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isFile()) return;
    timeMap.set(rawRel, rel);
  });

  const croppedManifest = readJsonFile(path.join(PATHS.logs, 'auto_crop_manifest.json'), { collages: [] });
  const collageSet = new Set(
    Array.isArray(croppedManifest.collages)
      ? croppedManifest.collages.map(c => (c.rel_path || '').toLowerCase())
      : []
  );

  const gallery = [];
  rawList.forEach(rel => {
    const parts = rel.split('/');
    const btp = parts[0] || 'Unknown';
    const category = parts[1] || 'General';
    const detail = parts.slice(2, -1).join('/') || 'Detail';
    const filename = parts[parts.length - 1];
    const timeRel = timeMap.get(rel);
    const group = timeRel ? timeRel.split('/')[0] : 'Tim_1';

    let meta = null;
    if (timeRel) {
      const metaFile = path.join(PATHS.photosTime, path.dirname(timeRel), 'meta.json');
      if (fs.existsSync(metaFile)) {
        try {
          const folderMeta = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
          meta = folderMeta[filename] || null;
        } catch (e) {}
      }
    }

    const timePath = timeRel ? path.join(PATHS.photosTime, timeRel) : null;
    const rawPath = path.join(PATHS.photosExport, rel);
    const timeStats = timePath && fs.existsSync(timePath) ? fs.statSync(timePath) : null;
    const rawStats = fs.existsSync(rawPath) ? fs.statSync(rawPath) : null;

    let modifiedMs = 0;
    if (timeStats && Number.isFinite(timeStats.mtimeMs)) {
      modifiedMs = timeStats.mtimeMs;
    }
    if (meta && meta.updatedAt) {
      const metaMs = new Date(meta.updatedAt).getTime();
      if (Number.isFinite(metaMs) && metaMs > modifiedMs) modifiedMs = metaMs;
    }
    const modifiedAt = modifiedMs > 0 ? new Date(modifiedMs).toISOString() : (rawStats ? rawStats.mtime.toISOString() : null);
    const folderKey = `${group}/${rel.substring(0, rel.lastIndexOf('/'))}`;
    const targetTimeText = meta ? meta.timeText : getTargetTimeOnlyText(rel);
    const targetDateText = getTargetDateText(rel);
    const isoDate = parseIndonesianDateToIso(targetDateText);
    const hasCropped = fs.existsSync(path.join(PATHS.photosTemp, rel));
    const isCollage = hasCropped || collageSet.has(rel.toLowerCase());
    const stem = path.basename(rel, path.extname(rel));
    const backupRel = path.join(path.dirname(rel), `${stem}.original_backup.jpg`).replace(/\\/g, '/');
    const hasBackup = fs.existsSync(path.join(PATHS.photosExport, backupRel));

    gallery.push({
      rel, btp, category, detail, filename, timGroup: group, folderKey, modifiedAt, modifiedMs,
      folderModifiedMs: modifiedMs,
      rawUrl: `/static/photos/export/${rel}`,
      timeUrl: timeRel ? `/static/photos/time/${timeRel}` : null,
      croppedUrl: hasCropped ? `/static/photos/temp/${rel}` : null,
      hasTimeEdited: !!timeRel,
      hasCropped,
      isCollage,
      hasBackup,
      timeText: targetTimeText,
      targetDateText,
      isoDate,
      xPos: meta ? meta.xPos : null,
      yPos: meta ? meta.yPos : null,
      fontSize: meta ? meta.fontSize : 18,
      opacity: meta ? meta.opacity : 140
    });
  });

  res.json({ total: gallery.length, photos: gallery });
});

app.post('/api/photos/time-manual-edit', async (req, res) => {
  const { rawRelPath, timeText, yPos, xPos, fontSize, opacity, timGroup, applyToFolder } = req.body;
  if (!rawRelPath) {
    return res.status(400).json({ error: 'rawRelPath is required' });
  }

  const group = timGroup || 'Tim_1';
  const timNum = parseInt(group.replace(/\D+/g, '')) || 1;
  const pyScript = path.join(PATHS.scripts, 'edit_photo_time_only.py');

  const normalizedRel = rawRelPath.replace(/\\/g, '/');
  const relDir = path.dirname(normalizedRel);
  const folderPath = path.join(PATHS.photosExport, relDir);

  let targetRelPaths = [normalizedRel];
  if (applyToFolder && fs.existsSync(folderPath) && fs.statSync(folderPath).isDirectory()) {
    const files = fs.readdirSync(folderPath).filter(f => f.toLowerCase().endsWith('.jpg'));
    if (files.length > 0) {
      targetRelPaths = files.map(f => `${relDir}/${f}`.replace(/\\/g, '/'));
    }
  }

  let errors = [];
  for (let relP of targetRelPaths) {
    const args = [
      pyScript,
      '--input', relP,
      '--tim-filter', String(timNum)
    ];

    if (timeText) {
      args.push('--time-override', String(timeText).trim());
    }
    if (yPos !== undefined && yPos !== null && yPos !== '') {
      args.push('--y-override', String(yPos));
    }
    if (xPos !== undefined && xPos !== null && xPos !== '') {
      args.push('--x-override', String(xPos));
    }
    if (fontSize !== undefined && fontSize !== null && fontSize !== '') {
      args.push('--font-size', String(fontSize));
    }
    if (opacity !== undefined && opacity !== null && opacity !== '') {
      args.push('--opacity', String(opacity));
    }

    try {
      await new Promise((resolve, reject) => {
        let stderrChunks = [];
        const pyProc = spawn('python', args, { cwd: APP_DIR });
        pyProc.stderr.on('data', (d) => stderrChunks.push(d));
        pyProc.on('close', (code) => {
          if (code === 0) {
            try {
              if (fs.existsSync(PATHS.photosTime)) {
                const outputFile = path.join(PATHS.photosTime, group, relP);
                const allTims = fs.readdirSync(PATHS.photosTime).filter(d => d.startsWith('Tim_') && d !== group);
                for (const otherTim of allTims) {
                  const otherFolder = path.join(PATHS.photosTime, otherTim, relDir);
                  if (fs.existsSync(otherFolder)) {
                    const otherOutputFile = path.join(PATHS.photosTime, otherTim, relP);
                    if (fs.existsSync(outputFile)) fs.copyFileSync(outputFile, otherOutputFile);
                    const srcMeta = path.join(PATHS.photosTime, group, relDir, 'meta.json');
                    const dstMeta = path.join(otherFolder, 'meta.json');
                    if (fs.existsSync(srcMeta)) fs.copyFileSync(srcMeta, dstMeta);
                  }
                }
              }
            } catch (e) {}
            resolve();
          } else {
            reject(new Error(Buffer.concat(stderrChunks).toString() || `Exit code ${code}`));
          }
        });
      });
    } catch (err) {
      errors.push(`${relP}: ${err.message}`);
    }
  }

  if (errors.length > 0) {
    return res.status(500).json({ error: errors.join('; ') });
  }

  const timeUrl = `/static/photos/time/${group}/${normalizedRel}`;
  res.json({ success: true, count: targetRelPaths.length, timeUrl: `${timeUrl}?t=${Date.now()}` });
});

app.get('/api/pdfs/time', (req, res) => {
  if (!fs.existsSync(PATHS.pdfMergedTime)) {
    return res.json({ pdfs: [] });
  }

  const pdfs = [];
  function scanDir(dir, prefix = '') {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        scanDir(path.join(dir, entry.name), prefix + entry.name + '/');
      } else if (entry.name.toLowerCase().endsWith('.pdf')) {
        pdfs.push({
          filename: prefix + entry.name,
          url: `/static/pdf-merged-time/${prefix}${entry.name}`
        });
      }
    }
  }
  scanDir(PATHS.pdfMergedTime);

  res.json({ pdfs });
});

// ----------------------------------------------------
// COORDINATE APIS (04_koordinat & 05_koordinat)
// ----------------------------------------------------

const getCoordMapping = () => {
  const mapFile = path.join(PATHS.config, 'asset_koordinat_mapping.json');
  if (!fs.existsSync(mapFile)) return {};
  try {
    return JSON.parse(fs.readFileSync(mapFile, 'utf8'));
  } catch (e) {
    return {};
  }
};

const resolveAssetCoordinate = (identifier, mapping) => {
  if (!mapping || !mapping.by_identifier) return null;
  const clean = String(identifier || '').replace(/_\d{2}-\d{2}$/, '').trim().toUpperCase();
  if (mapping.by_identifier[clean]) return mapping.by_identifier[clean].coordinate;
  const jplClean = clean.replace(/\bJPL\s+0+(\d+)/i, 'JPL $1');
  if (mapping.by_identifier[jplClean]) return mapping.by_identifier[jplClean].coordinate;
  const jplZero = clean.replace(/\bJPL\s+(\d)\b/i, 'JPL 0$1');
  if (mapping.by_identifier[jplZero]) return mapping.by_identifier[jplZero].coordinate;
  return null;
};

app.get('/api/photos/coord-gallery', (req, res) => {
  const scanPhotos = (rootDir) => {
    const list = [];
    if (!fs.existsSync(rootDir)) return list;

    const walkSync = (dir, relPath = '') => {
      const files = fs.readdirSync(dir);
      files.forEach(file => {
        const fullPath = path.join(dir, file);
        const rel = path.join(relPath, file);
        if (fs.statSync(fullPath).isDirectory()) {
          walkSync(fullPath, rel);
        } else if ((file.toLowerCase().endsWith('.jpg') || file.toLowerCase().endsWith('.jpeg')) && !fs.existsSync(`${fullPath}.unedited`)) {
          list.push(rel.replace(/\\/g, '/'));
        }
      });
    };
    walkSync(rootDir);
    return list;
  };

  const rawList = scanPhotos(PATHS.photosExport);
  const coordList = scanPhotos(PATHS.photosCoord);

  const coordMap = new Map();
  coordList.forEach(rel => {
    const parts = rel.split('/');
    if (parts.length < 2) return;
    const rawRel = parts.slice(1).join('/');
    const fullPath = path.join(PATHS.photosCoord, rel);
    if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isFile()) return;
    coordMap.set(rawRel, rel);
  });

  const croppedManifest = readJsonFile(path.join(PATHS.logs, 'auto_crop_manifest.json'), { collages: [] });
  const collageSet = new Set(
    Array.isArray(croppedManifest.collages)
      ? croppedManifest.collages.map(c => (c.rel_path || '').toLowerCase())
      : []
  );

  const mapping = getCoordMapping();
  const gallery = [];

  rawList.forEach(rel => {
    const parts = rel.split('/');
    const btp = parts[0] || 'Unknown';
    const category = parts[1] || 'General';
    const detail = parts.slice(2, -1).join('/') || 'Detail';
    const filename = parts[parts.length - 1];
    const coordRel = coordMap.get(rel);
    const group = coordRel ? coordRel.split('/')[0] : 'Tim_1';

    let meta = null;
    if (coordRel) {
      const metaFile = path.join(PATHS.photosCoord, path.dirname(coordRel), 'meta.json');
      if (fs.existsSync(metaFile)) {
        try {
          const folderMeta = JSON.parse(fs.readFileSync(metaFile, 'utf8'));
          meta = folderMeta.photos ? folderMeta.photos[filename] : null;
        } catch (e) {}
      }
    }

    const coordPath = coordRel ? path.join(PATHS.photosCoord, coordRel) : null;
    const rawPath = path.join(PATHS.photosExport, rel);
    const coordStats = coordPath && fs.existsSync(coordPath) ? fs.statSync(coordPath) : null;
    const rawStats = fs.existsSync(rawPath) ? fs.statSync(rawPath) : null;

    let modifiedMs = 0;
    if (coordStats && Number.isFinite(coordStats.mtimeMs)) {
      modifiedMs = coordStats.mtimeMs;
    }
    if (meta && meta.updatedAt) {
      const metaMs = new Date(meta.updatedAt).getTime();
      if (Number.isFinite(metaMs) && metaMs > modifiedMs) modifiedMs = metaMs;
    }
    const modifiedAt = modifiedMs > 0 ? new Date(modifiedMs).toISOString() : (rawStats ? rawStats.mtime.toISOString() : null);
    const folderKey = `${group}/${rel.substring(0, rel.lastIndexOf('/'))}`;
    const defaultCoord = resolveAssetCoordinate(detail, mapping);
    const coordText = meta ? meta.coordText : (defaultCoord || '-');
    const targetDateText = getTargetDateText(rel);
    const isoDate = parseIndonesianDateToIso(targetDateText);
    const hasCropped = fs.existsSync(path.join(PATHS.photosTemp, rel));
    const isCollage = hasCropped || collageSet.has(rel.toLowerCase());
    const stem = path.basename(rel, path.extname(rel));
    const backupRel = path.join(path.dirname(rel), `${stem}.original_backup.jpg`).replace(/\\/g, '/');
    const hasBackup = fs.existsSync(path.join(PATHS.photosExport, backupRel));

    gallery.push({
      rel, btp, category, detail, filename, timGroup: group, folderKey, modifiedAt, modifiedMs,
      folderModifiedMs: modifiedMs,
      rawUrl: `/static/photos/export/${rel}`,
      coordUrl: coordRel ? `/static/photos/coord/${coordRel}` : null,
      croppedUrl: hasCropped ? `/static/photos/temp/${rel}` : null,
      hasCoordEdited: !!coordRel,
      hasCropped,
      isCollage,
      hasBackup,
      coordText,
      targetDateText,
      isoDate,
      xPos: meta ? meta.xPos : 8,
      yPos: meta ? meta.yPos : 8,
      fontSize: meta ? meta.fontSize : 14,
      opacity: meta ? meta.opacity : 140
    });
  });

  res.json({ total: gallery.length, photos: gallery });
});

app.post('/api/photos/coord-manual-edit', async (req, res) => {
  const { rawRelPath, coordText, yPos, xPos, fontSize, opacity, timGroup, applyToFolder } = req.body;
  if (!rawRelPath) {
    return res.status(400).json({ error: 'rawRelPath is required' });
  }

  const group = timGroup || 'Tim_1';
  const timNum = parseInt(group.replace(/\D+/g, '')) || 1;
  const pyScript = path.join(PATHS.scripts, 'edit_photo_coordinate_only.py');

  const normalizedRel = rawRelPath.replace(/\\/g, '/');
  const relDir = path.dirname(normalizedRel);
  const folderPath = path.join(PATHS.photosExport, relDir);

  let targetRelPaths = [normalizedRel];
  if (applyToFolder && fs.existsSync(folderPath) && fs.statSync(folderPath).isDirectory()) {
    const files = fs.readdirSync(folderPath).filter(f => f.toLowerCase().endsWith('.jpg'));
    if (files.length > 0) {
      targetRelPaths = files.map(f => `${relDir}/${f}`.replace(/\\/g, '/'));
    }
  }

  let errors = [];
  for (let relP of targetRelPaths) {
    const args = [
      pyScript,
      '--input', relP,
      '--tim-filter', String(timNum)
    ];

    if (coordText) {
      args.push('--coord-override', String(coordText).trim());
    }
    if (yPos !== undefined && yPos !== null && yPos !== '') {
      args.push('--y-override', String(yPos));
    }
    if (xPos !== undefined && xPos !== null && xPos !== '') {
      args.push('--x-override', String(xPos));
    }
    if (fontSize !== undefined && fontSize !== null && fontSize !== '') {
      args.push('--font-size', String(fontSize));
    }
    if (opacity !== undefined && opacity !== null && opacity !== '') {
      args.push('--opacity', String(opacity));
    }

    try {
      await new Promise((resolve, reject) => {
        let stderrChunks = [];
        const pyProc = spawn('python', args, { cwd: APP_DIR });
        pyProc.stderr.on('data', (d) => stderrChunks.push(d));
        pyProc.on('close', (code) => {
          if (code === 0) {
            try {
              if (fs.existsSync(PATHS.photosCoord)) {
                const outputFile = path.join(PATHS.photosCoord, group, relP);
                const allTims = fs.readdirSync(PATHS.photosCoord).filter(d => d.startsWith('Tim_') && d !== group);
                for (const otherTim of allTims) {
                  const otherFolder = path.join(PATHS.photosCoord, otherTim, relDir);
                  if (fs.existsSync(otherFolder)) {
                    const otherOutputFile = path.join(PATHS.photosCoord, otherTim, relP);
                    if (fs.existsSync(outputFile)) fs.copyFileSync(outputFile, otherOutputFile);
                    const srcMeta = path.join(PATHS.photosCoord, group, relDir, 'meta.json');
                    const dstMeta = path.join(otherFolder, 'meta.json');
                    if (fs.existsSync(srcMeta)) fs.copyFileSync(srcMeta, dstMeta);
                  }
                }
              }
            } catch (e) {}
            resolve();
          } else {
            reject(new Error(Buffer.concat(stderrChunks).toString() || `Exit code ${code}`));
          }
        });
      });
    } catch (err) {
      errors.push(`${relP}: ${err.message}`);
    }
  }

  if (errors.length > 0) {
    return res.status(500).json({ error: errors.join('; ') });
  }

  const coordUrl = `/static/photos/coord/${group}/${normalizedRel}`;
  res.json({ success: true, count: targetRelPaths.length, coordUrl: `${coordUrl}?t=${Date.now()}` });
});

app.get('/api/pdfs/coord', (req, res) => {
  if (!fs.existsSync(PATHS.pdfMergedCoord)) {
    return res.json({ pdfs: [] });
  }

  const pdfs = [];
  function scanDir(dir, prefix = '') {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        scanDir(path.join(dir, entry.name), prefix + entry.name + '/');
      } else if (entry.name.toLowerCase().endsWith('.pdf')) {
        pdfs.push({
          filename: prefix + entry.name,
          url: `/static/pdf-merged-coord/${prefix}${entry.name}`
        });
      }
    }
  }
  scanDir(PATHS.pdfMergedCoord);

  res.json({ pdfs });
});

// GET /api/schedule — spreadsheet data from schedule.json
app.get('/api/schedule', (req, res) => {
  const schedFile = path.join(APP_DIR, 'schedule.json');
  if (!fs.existsSync(schedFile)) return res.json({ total: 0, schedules: [] });
  try {
    const data = JSON.parse(fs.readFileSync(schedFile, 'utf8'));
    const list = (data.schedules || []).map((s, idx) => {
      const photos = s.photos || {};
      const t0Iso = photos['0.jpg'] || '';
      const t50Iso = photos['50.jpg'] || '';
      const t100Iso = photos['100.jpg'] || '';
      const t0 = t0Iso ? t0Iso.slice(11, 16) : '07:00';
      const t50 = t50Iso ? t50Iso.slice(11, 16) : '07:22';
      const t100 = t100Iso ? t100Iso.slice(11, 16) : '07:45';
      const isoDate = s.iso_date || (s.date ? parseIndonesianDateToIso(s.date) : (t0Iso ? t0Iso.slice(0, 10) : ''));
      return {
        no: idx + 1,
        tim: `Tim ${s.tim || 1}`,
        timNum: s.tim || 1,
        date: s.date || '',
        isoDate,
        btp: s.btp || 'BTP JAK',
        category: s.category || '',
        identifier: s.identifier || s.pdf_stem || '',
        duration: s.waktu_menit || 45,
        t0,
        t50,
        t100,
        timeRange: `${t0} – ${t100}`,
        file: s.file || ''
      };
    });
    res.json({ total: list.length, schedules: list });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// GET /api/schedule/export-excel — export to formatted Excel and download
app.get('/api/schedule/export-excel', (req, res) => {
  const pyScript = path.join(PATHS.scripts, 'export_schedule_excel.py');
  const excelFile = path.join(PATHS.logs, 'jadwal_perawatan_gabungan.xlsx');
  const pyProc = spawn('python', [pyScript], { cwd: APP_DIR });
  
  pyProc.on('close', (code) => {
    if (code === 0 && fs.existsSync(excelFile)) {
      res.download(excelFile, 'jadwal_perawatan_gabungan.xlsx');
    } else {
      res.status(500).json({ error: 'Gagal membuat berkas Excel jadwal' });
    }
  });
});

// ─── TABLO EXCEL EXPORT API ───

// POST /api/schedule/export-tablo — supports mode 'pipeline' or 'custom'
app.post('/api/schedule/export-tablo', (req, res) => {
  const { mode, customPath } = req.body || {};
  const isCustom = mode === 'custom';

  if (isCustom) {
    if (!customPath || !fs.existsSync(customPath)) {
      return res.status(400).json({ success: false, error: `Folder kustom '${customPath}' tidak ditemukan di komputer.` });
    }
  }

  const pyScript = path.join(PATHS.scripts, 'export_tablo_excel.py');
  const args = [pyScript, '--output-dir', PATHS.logs];
  if (isCustom) {
    args.push('--mode', 'custom', '--folder', customPath);
  } else {
    args.push('--mode', 'pipeline');
  }

  const pyProc = spawn('python', args, { cwd: APP_DIR });
  let stderr = '';
  let stdout = '';
  pyProc.stdout.on('data', d => { stdout += d.toString(); });
  pyProc.stderr.on('data', d => { stderr += d.toString(); });

  pyProc.on('close', (code) => {
    const match = stdout.match(/\[OUTPUT_FILE\]\s*(.+)/);
    const resolvedPath = match ? match[1].trim() : null;
    if (code === 0 && resolvedPath && fs.existsSync(resolvedPath)) {
      const outFileName = path.basename(resolvedPath);
      return res.json({
        success: true,
        fileName: outFileName,
        downloadUrl: `/api/schedule/export-tablo/download?file=${encodeURIComponent(outFileName)}`
      });
    } else {
      return res.status(500).json({
        success: false,
        error: stderr || stdout || `Gagal membuat berkas Tablo Excel (Exit code ${code})`
      });
    }
  });
});

// GET /api/schedule/export-tablo/download — download generated Tablo file
app.get('/api/schedule/export-tablo/download', (req, res) => {
  const reqFile = req.query.file;
  if (!reqFile) {
    return res.status(400).json({ error: 'Parameter file diperlukan' });
  }
  const safeName = path.basename(reqFile);
  const filePath = path.join(PATHS.logs, safeName);
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'Berkas Tablo tidak ditemukan' });
  }

  res.setHeader('Content-Disposition', `attachment; filename="${safeName}"`);
  res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  const fileStream = fs.createReadStream(filePath);
  fileStream.pipe(res);
});

// GET /api/schedule/export-tablo — 1-click direct download fallback (pipeline mode)
app.get('/api/schedule/export-tablo', (req, res) => {
  const pyScript = path.join(PATHS.scripts, 'export_tablo_excel.py');
  const args = [pyScript, '--mode', 'pipeline', '--output-dir', PATHS.logs];

  const pyProc = spawn('python', args, { cwd: APP_DIR });
  let stdout = '';
  let stderr = '';
  pyProc.stdout.on('data', d => { stdout += d.toString(); });
  pyProc.stderr.on('data', d => { stderr += d.toString(); });

  pyProc.on('close', (code) => {
    const match = stdout.match(/\[OUTPUT_FILE\]\s*(.+)/);
    const resolvedPath = match ? match[1].trim() : null;
    if (code === 0 && resolvedPath && fs.existsSync(resolvedPath)) {
      const outFileName = path.basename(resolvedPath);
      res.setHeader('Content-Disposition', `attachment; filename="${outFileName}"`);
      res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
      fs.createReadStream(resolvedPath).pipe(res);
    } else {
      res.status(500).json({ error: stderr || stdout || 'Gagal membuat berkas Tablo Excel' });
    }
  });
});

// ─── OUTPUT CLEANER API ───

function getDirItemStats(dirPath, isFile = false) {
  if (isFile) {
    if (fs.existsSync(dirPath)) {
      const s = fs.statSync(dirPath);
      return { count: 1, bytes: s.size, exists: true };
    }
    return { count: 0, bytes: 0, exists: false };
  }
  if (!fs.existsSync(dirPath)) {
    return { count: 0, bytes: 0, exists: false };
  }
  let count = 0;
  let bytes = 0;
  const walk = (d) => {
    try {
      const entries = fs.readdirSync(d, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.name === '.gitkeep') continue;
        const full = path.join(d, entry.name);
        if (entry.isDirectory()) {
          walk(full);
        } else if (entry.isFile()) {
          count++;
          try {
            bytes += fs.statSync(full).size;
          } catch (e) {}
        }
      }
    } catch (e) {}
  };
  walk(dirPath);
  return { count, bytes, exists: true };
}

function cleanDirContents(dirPath) {
  if (!fs.existsSync(dirPath)) return 0;
  let deletedCount = 0;
  try {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name === '.gitkeep') continue;
      const full = path.join(dirPath, entry.name);
      if (entry.isDirectory()) {
        deletedCount += countDirFiles(full);
        fs.rmSync(full, { recursive: true, force: true });
      } else if (entry.isFile()) {
        fs.unlinkSync(full);
        deletedCount++;
      }
    }
  } catch (e) {
    console.error(`Error cleaning directory ${dirPath}:`, e);
  }
  return deletedCount;
}

function countDirFiles(dirPath) {
  let count = 0;
  const walk = (d) => {
    try {
      const entries = fs.readdirSync(d, { withFileTypes: true });
      for (const entry of entries) {
        if (entry.name === '.gitkeep') continue;
        if (entry.isDirectory()) walk(path.join(d, entry.name));
        else if (entry.isFile()) count++;
      }
    } catch (e) {}
  };
  walk(dirPath);
  return count;
}

// GET /api/cleaner/status — returns stats of all cleanable output targets
app.get('/api/cleaner/status', (req, res) => {
  const schedFile = path.join(APP_DIR, 'schedule.json');
  const targets = {
    schedule: { key: 'schedule', label: 'Jadwal (schedule.json)', path: 'schedule.json', ...getDirItemStats(schedFile, true), isFile: true, category: 'schedule', icon: '📅' },
    photos_export: { key: 'photos_export', label: 'Foto Ekstraksi Mentah (03_photos_export)', path: '03_photos_export', ...getDirItemStats(PATHS.photosExport), isFile: false, category: 'photos', icon: '📂' },
    photos_temp: { key: 'photos_temp', label: 'Foto Crop Kolase Sementara (03_photos_cropped_temp)', path: '03_photos_cropped_temp', ...getDirItemStats(PATHS.photosTemp), isFile: false, category: 'photos', icon: '✂️' },
    photos_edited: { key: 'photos_edited', label: 'Foto Hasil Edit Timemark (04_photos_edited)', path: '04_photos_edited', ...getDirItemStats(PATHS.photosEdited), isFile: false, category: 'photos', icon: '🖼️' },
    photos_time: { key: 'photos_time', label: 'Foto Hasil Edit Jam (04_Time)', path: '04_Time', ...getDirItemStats(PATHS.photosTime), isFile: false, category: 'photos', icon: '⏰' },
    pdf_merged: { key: 'pdf_merged', label: 'PDF Hasil Gabung Reguler (05_pdf_merged)', path: '05_pdf_merged', ...getDirItemStats(PATHS.pdfMerged), isFile: false, category: 'pdf', icon: '📑' },
    pdf_merged_time: { key: 'pdf_merged_time', label: 'PDF Hasil Gabung Edit Jam (05_pdf_merged_Time)', path: '05_pdf_merged_Time', ...getDirItemStats(PATHS.pdfMergedTime), isFile: false, category: 'pdf', icon: '🕒' },
    logs: { key: 'logs', label: 'Log, Laporan & Cache Excel (logs/)', path: 'logs', ...getDirItemStats(PATHS.logs), isFile: false, category: 'logs', icon: '📊' }
  };

  const totalFiles = Object.values(targets).reduce((sum, t) => sum + t.count, 0);
  const totalBytes = Object.values(targets).reduce((sum, t) => sum + t.bytes, 0);

  res.json({ totalFiles, totalBytes, targets });
});

// POST /api/cleaner/clean — cleans specified output targets or all
app.post('/api/cleaner/clean', (req, res) => {
  const { targets = [], cleanAll = false } = req.body;
  const schedFile = path.join(APP_DIR, 'schedule.json');

  let results = {};
  let totalDeleted = 0;

  const doCleanTarget = (key) => {
    if (key === 'schedule') {
      if (fs.existsSync(schedFile)) {
        try {
          fs.unlinkSync(schedFile);
          results.schedule = { deleted: 1, success: true };
          totalDeleted += 1;
        } catch (e) {
          results.schedule = { deleted: 0, success: false, error: e.message };
        }
      } else {
        results.schedule = { deleted: 0, success: true, message: 'Already clean' };
      }
    } else if (key === 'photos_export') {
      const d = cleanDirContents(PATHS.photosExport);
      results.photos_export = { deleted: d, success: true };
      totalDeleted += d;
    } else if (key === 'photos_temp') {
      const d = cleanDirContents(PATHS.photosTemp);
      results.photos_temp = { deleted: d, success: true };
      totalDeleted += d;
    } else if (key === 'photos_edited') {
      const d = cleanDirContents(PATHS.photosEdited);
      results.photos_edited = { deleted: d, success: true };
      totalDeleted += d;
    } else if (key === 'photos_time') {
      const d = cleanDirContents(PATHS.photosTime);
      results.photos_time = { deleted: d, success: true };
      totalDeleted += d;
    } else if (key === 'pdf_merged') {
      const d = cleanDirContents(PATHS.pdfMerged);
      results.pdf_merged = { deleted: d, success: true };
      totalDeleted += d;
    } else if (key === 'pdf_merged_time') {
      const d = cleanDirContents(PATHS.pdfMergedTime);
      results.pdf_merged_time = { deleted: d, success: true };
      totalDeleted += d;
    } else if (key === 'logs') {
      const d = cleanDirContents(PATHS.logs);
      results.logs = { deleted: d, success: true };
      totalDeleted += d;
    }
  };

  if (cleanAll) {
    ['schedule', 'photos_export', 'photos_temp', 'photos_edited', 'photos_time', 'pdf_merged', 'pdf_merged_time', 'logs'].forEach(doCleanTarget);
  } else {
    targets.forEach(doCleanTarget);
  }

  res.json({ success: true, totalDeleted, results });
});

app.get('/api/photos/analyze-misposition', (req, res) => {
  const reportFile = path.join(PATHS.logs, 'misposition_audit_report.json');
  const force = req.query.force === 'true';

  if (!force && fs.existsSync(reportFile)) {
    try {
      const summary = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
      return res.json(summary);
    } catch (e) {}
  }

  const pyScript = path.join(PATHS.scripts, 'analyzer.py');
  const pyProc = spawn('python', [pyScript], { cwd: APP_DIR });
  
  pyProc.on('close', (code) => {
    if (fs.existsSync(reportFile)) {
      try {
        const summary = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
        return res.json(summary);
      } catch (e) {}
    }
    res.status(500).json({ error: 'Failed to generate audit report' });
  });
});

app.get('/api/audit/master-data', (req, res) => {
  const reportFile = path.join(PATHS.logs, 'master_audit_report.json');
  const force = req.query.force === 'true';

  if (!force && fs.existsSync(reportFile)) {
    try {
      const summary = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
      return res.json(summary);
    } catch (e) {}
  }

  const pyScript = path.join(PATHS.scripts, 'master_audit.py');
  const pyProc = spawn('python', [pyScript], { cwd: APP_DIR });

  pyProc.on('close', (code) => {
    if (fs.existsSync(reportFile)) {
      try {
        const summary = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
        return res.json(summary);
      } catch (e) {}
    }
    res.status(500).json({ error: 'Failed to generate master audit report' });
  });
});

// ----------------------------------------------------
// DAFTAR PEGAWAI (EMPLOYEE ROSTER & MULTI-PRESET) APIS
// ----------------------------------------------------
function loadEmployeePresets() {
  const presetsPath = path.join(APP_DIR, 'config', 'employee_presets.json');
  const cfgPath = path.join(APP_DIR, 'config', 'daftar_pegawai.json');
  
  if (fs.existsSync(presetsPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(presetsPath, 'utf-8'));
      if (Array.isArray(data.presets) && data.presets.length > 0) {
        return data;
      }
    } catch (e) {
      console.error('Error reading employee_presets.json:', e);
    }
  }

  // Fallback: create default from daftar_pegawai.json
  let initialData = {
    resor: { nama: "FURQON SUSILO WARDOYO", nipp: "64465", jabatan: "KUPT RESOR STL 1.21 BOGOR" },
    kaur: [
      { nama: "SUTISNA", nipp: "45677", no_sc: "PRP.080175.126093" },
      { nama: "YATIYO", nipp: "49957", no_sc: "PRP.260287.39992" }
    ],
    pnc: [
      { nama: "RAIHAN HERPIAN", nipp: "75276", no_sc: "PRP.170204.72256" },
      { nama: "IWAN SETIAWAN", nipp: "69810", no_sc: "PRP.03071990.36476" },
      { nama: "JUJUN JUNAEDI", nipp: "69699", no_sc: "PRP.02021990.36540" },
      { nama: "DIKA ARMANSYAH", nipp: "72347", no_sc: "PRP.020899.122293" }
    ]
  };
  if (fs.existsSync(cfgPath)) {
    try {
      const parsed = JSON.parse(fs.readFileSync(cfgPath, 'utf-8'));
      if (parsed.resor) initialData.resor = parsed.resor;
      if (Array.isArray(parsed.kaur) && parsed.kaur.length > 0) initialData.kaur = parsed.kaur;
      if (Array.isArray(parsed.pnc) && parsed.pnc.length > 0) initialData.pnc = parsed.pnc;
    } catch (_) {}
  }

  const result = {
    active_preset_id: 'preset_default',
    presets: [
      {
        id: 'preset_default',
        name: 'Resort 1.21 Bogor (Standar)',
        created_at: new Date().toISOString(),
        data: initialData
      }
    ]
  };
  try {
    fs.mkdirSync(path.dirname(presetsPath), { recursive: true });
    fs.writeFileSync(presetsPath, JSON.stringify(result, null, 2), 'utf-8');
  } catch (_) {}
  return result;
}

function saveEmployeePresets(presetsObj) {
  const presetsPath = path.join(APP_DIR, 'config', 'employee_presets.json');
  fs.mkdirSync(path.dirname(presetsPath), { recursive: true });
  fs.writeFileSync(presetsPath, JSON.stringify(presetsObj, null, 2), 'utf-8');
}

function syncActivePresetToDaftarPegawai(activeData) {
  const cfgPath = path.join(APP_DIR, 'config', 'daftar_pegawai.json');
  fs.mkdirSync(path.dirname(cfgPath), { recursive: true });
  fs.writeFileSync(cfgPath, JSON.stringify(activeData, null, 2), 'utf-8');
}

// 1. Get all presets + active preset info
app.get('/api/employees/presets', (req, res) => {
  try {
    const presetsObj = loadEmployeePresets();
    return res.json({
      success: true,
      active_preset_id: presetsObj.active_preset_id,
      presets: presetsObj.presets
    });
  } catch (e) {
    return res.status(500).json({ error: 'Gagal memuat preset pegawai: ' + e.message });
  }
});

// 2. Select and activate a preset
app.post('/api/employees/presets/select', (req, res) => {
  const { presetId } = req.body;
  if (!presetId) {
    return res.status(400).json({ error: 'presetId diperlukan' });
  }
  const presetsObj = loadEmployeePresets();
  const preset = presetsObj.presets.find(p => p.id === presetId);
  if (!preset) {
    return res.status(404).json({ error: 'Preset pegawai tidak ditemukan' });
  }
  presetsObj.active_preset_id = presetId;
  saveEmployeePresets(presetsObj);
  syncActivePresetToDaftarPegawai(preset.data);
  return res.json({
    success: true,
    message: `List pegawai "${preset.name}" berhasil diaktifkan`,
    active_preset_id: presetId,
    preset
  });
});

// 3. Save preset (update existing or create new)
app.post('/api/employees/presets/save', (req, res) => {
  const { presetId, name, data, isNew } = req.body;
  if (!data || !Array.isArray(data.kaur) || !Array.isArray(data.pnc)) {
    return res.status(400).json({ error: 'Data personil tidak valid (kaur dan pnc harus array)' });
  }

  const cleanData = {
    resor: data.resor || { nama: "FURQON SUSILO WARDOYO", nipp: "64465", jabatan: "KUPT RESOR STL 1.21 BOGOR" },
    kaur: data.kaur,
    pnc: data.pnc
  };

  const presetsObj = loadEmployeePresets();

  if (isNew) {
    const newId = 'preset_' + Date.now();
    const newName = (name && name.trim()) ? name.trim() : `List Pegawai ${presetsObj.presets.length + 1}`;
    const newPreset = {
      id: newId,
      name: newName,
      created_at: new Date().toISOString(),
      data: cleanData
    };
    presetsObj.presets.push(newPreset);
    presetsObj.active_preset_id = newId;
    saveEmployeePresets(presetsObj);
    syncActivePresetToDaftarPegawai(cleanData);
    return res.json({
      success: true,
      message: `List baru "${newName}" berhasil disimpan & diaktifkan`,
      active_preset_id: newId,
      presets: presetsObj.presets
    });
  } else {
    const targetId = presetId || presetsObj.active_preset_id;
    const targetPreset = presetsObj.presets.find(p => p.id === targetId);
    if (!targetPreset) {
      return res.status(404).json({ error: 'Preset target tidak ditemukan' });
    }
    targetPreset.data = cleanData;
    if (name && name.trim()) {
      targetPreset.name = name.trim();
    }
    saveEmployeePresets(presetsObj);
    if (presetsObj.active_preset_id === targetId) {
      syncActivePresetToDaftarPegawai(cleanData);
    }
    return res.json({
      success: true,
      message: `Perubahan pada list "${targetPreset.name}" berhasil disimpan`,
      active_preset_id: presetsObj.active_preset_id,
      presets: presetsObj.presets
    });
  }
});

// 4. Rename a preset
app.post('/api/employees/presets/rename', (req, res) => {
  const { presetId, newName } = req.body;
  if (!presetId || !newName || !newName.trim()) {
    return res.status(400).json({ error: 'presetId dan newName diperlukan' });
  }
  const presetsObj = loadEmployeePresets();
  const target = presetsObj.presets.find(p => p.id === presetId);
  if (!target) {
    return res.status(404).json({ error: 'Preset pegawai tidak ditemukan' });
  }
  target.name = newName.trim();
  saveEmployeePresets(presetsObj);
  return res.json({
    success: true,
    message: 'Nama list pegawai berhasil diubah',
    presets: presetsObj.presets
  });
});

// 5. Delete a preset
app.delete('/api/employees/presets/:id', (req, res) => {
  const targetId = req.params.id;
  const presetsObj = loadEmployeePresets();

  if (presetsObj.presets.length <= 1) {
    return res.status(400).json({ error: 'Tidak dapat menghapus list terakhir. Minimal harus ada 1 list pegawai.' });
  }

  const idx = presetsObj.presets.findIndex(p => p.id === targetId);
  if (idx === -1) {
    return res.status(404).json({ error: 'Preset tidak ditemukan' });
  }

  const removed = presetsObj.presets.splice(idx, 1)[0];

  // If deleted preset was active, switch to first remaining
  if (presetsObj.active_preset_id === targetId) {
    presetsObj.active_preset_id = presetsObj.presets[0].id;
    syncActivePresetToDaftarPegawai(presetsObj.presets[0].data);
  }

  saveEmployeePresets(presetsObj);
  return res.json({
    success: true,
    message: `List "${removed.name}" berhasil dihapus`,
    active_preset_id: presetsObj.active_preset_id,
    presets: presetsObj.presets
  });
});

// Existing /api/employees GET & POST for direct compatibility
app.get('/api/employees', (req, res) => {
  const presetsObj = loadEmployeePresets();
  const activePreset = presetsObj.presets.find(p => p.id === presetsObj.active_preset_id) || presetsObj.presets[0];
  return res.json({
    success: true,
    active_preset_id: presetsObj.active_preset_id,
    active_preset_name: activePreset ? activePreset.name : 'Standar',
    resor: (activePreset && activePreset.data.resor) || { nama: "FURQON SUSILO WARDOYO", nipp: "64465", jabatan: "KUPT RESOR STL 1.21 BOGOR" },
    kaur: (activePreset && activePreset.data.kaur) || [],
    pnc: (activePreset && activePreset.data.pnc) || []
  });
});

app.post('/api/employees', (req, res) => {
  const { resor, kaur, pnc, presetId } = req.body;
  if (!Array.isArray(kaur) || !Array.isArray(pnc)) {
    return res.status(400).json({ error: 'Format data tidak valid (kaur dan pnc harus array)' });
  }
  const cleanData = {
    resor: resor || { nama: "FURQON SUSILO WARDOYO", nipp: "64465", jabatan: "KUPT RESOR STL 1.21 BOGOR" },
    kaur,
    pnc
  };
  
  const presetsObj = loadEmployeePresets();
  const targetId = presetId || presetsObj.active_preset_id;
  const targetPreset = presetsObj.presets.find(p => p.id === targetId) || presetsObj.presets[0];
  if (targetPreset) {
    targetPreset.data = cleanData;
  }
  saveEmployeePresets(presetsObj);
  if (presetsObj.active_preset_id === targetId) {
    syncActivePresetToDaftarPegawai(cleanData);
  }
  return res.json({ success: true, message: 'Daftar pegawai berhasil disimpan' });
});

app.get('/api/employees/file-personnel', (req, res) => {
  const cachePath = path.join(PATHS.logs, 'file_personnel_cache.json');
  const extractorPath = path.join(PATHS.scripts, 'extract_file_personnel.py');
  const targetDir = String(req.query.targetDir || '').trim();
  const targetRoot = targetDir && fs.existsSync(targetDir) ? targetDir : '02_pdf_target';
  const outputPath = targetDir
    ? path.join(PATHS.logs, `file_personnel_${Buffer.from(targetRoot).toString('base64url').slice(0, 24)}.json`)
    : cachePath;
  const shouldRefresh = req.query.refresh === '1' || !fs.existsSync(outputPath)
    || (fs.existsSync(outputPath) && fs.statSync(extractorPath).mtimeMs > fs.statSync(outputPath).mtimeMs);

  if (shouldRefresh) {
    const pyScript = path.join(PATHS.scripts, 'extract_file_personnel.py');
    const pyProc = spawn('python', [pyScript, '--target-dir', targetRoot, '--output', outputPath], { cwd: APP_DIR });
    let stderr = '';
    pyProc.stderr.on('data', d => { stderr += d.toString(); });
    pyProc.on('close', (code) => {
      if (code !== 0 || !fs.existsSync(outputPath)) {
        return res.status(500).json({ error: 'Gagal mengekstrak personil berkas: ' + stderr });
      }
      try {
        const raw = fs.readFileSync(outputPath, 'utf-8');
        const data = JSON.parse(raw);
        return res.json({ success: true, ...data });
      } catch (e) {
        return res.status(500).json({ error: 'Gagal membaca cache personil: ' + e.message });
      }
    });
  } else {
    try {
      const raw = fs.readFileSync(outputPath, 'utf-8');
      const data = JSON.parse(raw);
      return res.json({ success: true, ...data });
    } catch (e) {
      return res.status(500).json({ error: 'Gagal membaca cache personil: ' + e.message });
    }
  }
});

app.post('/api/employees/audit', (req, res) => {
  const { mode, customPath } = req.body || {};
  let targetFolder = PATHS.target;
  if (mode === 'custom') {
    if (!customPath || !fs.existsSync(customPath)) {
      return res.status(400).json({ error: 'Folder kustom tidak ditemukan: ' + (customPath || '') });
    }
    targetFolder = customPath;
  }

  const pyScript = path.join(PATHS.scripts, 'audit_and_correct_personnel.py');
  const pyProc = spawn('python', [pyScript, '--action', 'audit', '--folder', targetFolder], { cwd: APP_DIR });

  let stdout = '';
  let stderr = '';
  pyProc.stdout.on('data', d => { stdout += d.toString(); });
  pyProc.stderr.on('data', d => { stderr += d.toString(); });

  pyProc.on('close', code => {
    if (code !== 0) {
      return res.status(500).json({ error: 'Gagal menjalankan audit personil: ' + (stderr || 'Kode exit ' + code) });
    }
    try {
      let data;
      try {
        data = JSON.parse(stdout.trim());
      } catch (_) {
        // MuPDF kadang menulis warning ke stdout sebelum JSON utama.
        const start = stdout.indexOf('{');
        const end = stdout.lastIndexOf('}');
        if (start >= 0 && end > start) {
          data = JSON.parse(stdout.slice(start, end + 1));
        }
      }
      if (!data || typeof data !== 'object') throw new Error('Output JSON audit tidak ditemukan');
      return res.json({ success: true, mode, folder: targetFolder, ...data });
    } catch (e) {
      const detail = stderr ? ` (${stderr.trim().slice(-300)})` : '';
      return res.status(500).json({ error: 'Gagal memproses hasil audit: ' + e.message + detail });
    }
  });
});

app.post('/api/employees/correct-single', (req, res) => {
  const { file, kaur, pnc1, pnc2 } = req.body || {};
  if (!file || !kaur || !pnc1 || !pnc2) {
    return res.status(400).json({ error: 'Parameter file, kaur, pnc1, dan pnc2 harus diisi.' });
  }

  let pdfPath = file;
  if (!path.isAbsolute(pdfPath)) {
    pdfPath = path.join(PATHS.target, file);
  }
  if (!fs.existsSync(pdfPath)) {
    return res.status(404).json({ error: 'Berkas PDF tidak ditemukan: ' + pdfPath });
  }

  const pyScript = path.join(PATHS.scripts, 'audit_and_correct_personnel.py');
  const pyProc = spawn('python', [
    pyScript,
    '--action', 'correct-single',
    '--file', pdfPath,
    '--kaur', kaur,
    '--pnc1', pnc1,
    '--pnc2', pnc2
  ], { cwd: APP_DIR });

  let stdout = '';
  let stderr = '';
  pyProc.stdout.on('data', d => { stdout += d.toString(); });
  pyProc.stderr.on('data', d => { stderr += d.toString(); });

  pyProc.on('close', code => {
    if (code !== 0) {
      return res.status(500).json({ error: 'Gagal mengoreksi personil berkas: ' + (stderr || stdout) });
    }
    if (pdfPath.includes(PATHS.target) || pdfPath.includes('02_pdf_target')) {
      const cachePath = path.join(PATHS.logs, 'file_personnel_cache.json');
      if (fs.existsSync(cachePath)) {
        try { fs.unlinkSync(cachePath); } catch (_) {}
      }
    }
    return res.json({ success: true, message: `Berkas ${path.basename(pdfPath)} berhasil dikoreksi menjadi 1 KAUR & 2 PNC.` });
  });
});

app.post('/api/employees/correct-no-sc', (req, res) => {
  const { mode, customPath } = req.body || {};
  let targetFolder = PATHS.target;
  if (mode === 'custom') {
    if (!customPath || !fs.existsSync(customPath)) {
      return res.status(400).json({ error: 'Folder kustom tidak ditemukan: ' + (customPath || '') });
    }
    targetFolder = customPath;
  }
  const pyScript = path.join(PATHS.scripts, 'audit_and_correct_personnel.py');
  const pyProc = spawn('python', [pyScript, '--action', 'auto-correct-no-sc', '--folder', targetFolder], { cwd: APP_DIR });
  let stdout = '';
  let stderr = '';
  pyProc.stdout.on('data', d => { stdout += d.toString(); });
  pyProc.stderr.on('data', d => { stderr += d.toString(); });
  pyProc.on('close', code => {
    if (code !== 0) return res.status(500).json({ error: 'Gagal mengoreksi nomor SC: ' + (stderr || stdout) });
    try {
      const output = stdout.trim();
      let data;
      try { data = JSON.parse(output); } catch (_) {
        const start = output.indexOf('{');
        const end = output.lastIndexOf('}');
        if (start >= 0 && end > start) data = JSON.parse(output.slice(start, end + 1));
      }
      if (!data || typeof data !== 'object') throw new Error('Output JSON koreksi nomor SC tidak ditemukan');
      res.json({ success: true, ...data });
    } catch (e) {
      res.status(500).json({ error: 'Gagal memproses hasil koreksi nomor SC: ' + e.message + (stderr ? ` (${stderr.trim().slice(-300)})` : '') });
    }
  });
});

app.post('/api/employees/correct-batch', (req, res) => {
  const { mode, customPath } = req.body || {};
  let targetFolder = PATHS.target;
  if (mode === 'custom') {
    if (!customPath || !fs.existsSync(customPath)) {
      return res.status(400).json({ error: 'Folder kustom tidak ditemukan: ' + (customPath || '') });
    }
    targetFolder = customPath;
  }

  const pyScript = path.join(PATHS.scripts, 'audit_and_correct_personnel.py');
  const pyProc = spawn('python', [pyScript, '--action', 'auto-correct-batch', '--folder', targetFolder], { cwd: APP_DIR });

  let stdout = '';
  let stderr = '';
  pyProc.stdout.on('data', d => { stdout += d.toString(); });
  pyProc.stderr.on('data', d => { stderr += d.toString(); });

  pyProc.on('close', code => {
    if (code !== 0) {
      return res.status(500).json({ error: 'Gagal mengoreksi personil otomatis: ' + (stderr || stdout) });
    }
    try {
      const output = stdout.trim();
      let data;
      try {
        data = JSON.parse(output);
      } catch (_) {
        // MuPDF dapat menulis warning ke stdout sebelum JSON utama.
        const start = output.indexOf('{');
        const end = output.lastIndexOf('}');
        if (start >= 0 && end > start) {
          data = JSON.parse(output.slice(start, end + 1));
        }
      }
      if (!data || typeof data !== 'object') throw new Error('Output JSON koreksi massal tidak ditemukan');
      if (targetFolder === PATHS.target || targetFolder.includes('02_pdf_target')) {
        const cachePath = path.join(PATHS.logs, 'file_personnel_cache.json');
        if (fs.existsSync(cachePath)) {
          try { fs.unlinkSync(cachePath); } catch (_) {}
        }
      }
      return res.json({ success: true, ...data });
    } catch (e) {
      const detail = stderr ? ` (${stderr.trim().slice(-300)})` : '';
      return res.status(500).json({ error: 'Gagal memproses hasil koreksi massal: ' + e.message + detail });
    }
  });
});

// ----------------------------------------------------
// AUDIT FILE LAIN — SAFE EXTERNAL FOLDER SESSION
// ----------------------------------------------------
const externalAuditSessions = new Map();

function countPdfFiles(root) {
  let total = 0;
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) total += countPdfFiles(full);
    else if (entry.isFile() && entry.name.toLowerCase().endsWith('.pdf')) total += 1;
  }
  return total;
}

app.post('/api/external-audit/prepare', (req, res) => {
  try {
    const requestedInput = String(req.body?.inputFolder || '').trim();
    const mode = req.body?.mode === 'overwrite' ? 'overwrite' : 'copy';
    const requestedOutput = String(req.body?.outputFolder || '').trim();
    if (!requestedInput) return res.status(400).json({ error: 'Folder input wajib diisi.' });
    const inputFolder = path.resolve(requestedInput);
    if (!fs.existsSync(inputFolder) || !fs.statSync(inputFolder).isDirectory()) {
      return res.status(400).json({ error: `Folder input tidak ditemukan: ${inputFolder}` });
    }
    const totalPdf = countPdfFiles(inputFolder);
    if (!totalPdf) return res.status(400).json({ error: 'Folder input tidak memiliki file PDF.' });

    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    let workingFolder;
    let backupFolder = '';
    if (mode === 'copy') {
      if (!requestedOutput) return res.status(400).json({ error: 'Folder output wajib diisi untuk mode Folder Baru.' });
      workingFolder = path.resolve(requestedOutput);
      if (workingFolder === inputFolder || workingFolder.startsWith(inputFolder + path.sep)) {
        return res.status(400).json({ error: 'Folder output harus berada di luar folder input.' });
      }
      if (fs.existsSync(workingFolder) && fs.readdirSync(workingFolder).length) {
        return res.status(400).json({ error: `Folder output harus kosong atau belum ada: ${workingFolder}` });
      }
      fs.cpSync(inputFolder, workingFolder, { recursive: true, force: false, errorOnExist: true });
    } else {
      if (req.body?.confirmText !== 'TIMPA SUMBER') {
        return res.status(400).json({ error: 'Konfirmasi Timpa Sumber tidak valid.' });
      }
      workingFolder = inputFolder;
      backupFolder = `${inputFolder}_BACKUP_${stamp}`;
      fs.cpSync(inputFolder, backupFolder, { recursive: true, force: false, errorOnExist: true });
      if (countPdfFiles(backupFolder) !== totalPdf) {
        fs.rmSync(backupFolder, { recursive: true, force: true });
        return res.status(500).json({ error: 'Backup tidak lengkap. Sumber belum diubah.' });
      }
    }

    const sessionId = `external_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    externalAuditSessions.set(sessionId, { inputFolder, workingFolder, backupFolder, mode, totalPdf });
    return res.json({ success: true, sessionId, inputFolder, workingFolder, backupFolder, mode, totalPdf });
  } catch (error) {
    return res.status(500).json({ error: `Gagal menyiapkan folder kerja: ${error.message}` });
  }
});

app.post('/api/external-audit/correct-dates', (req, res) => {
  const session = externalAuditSessions.get(String(req.body?.sessionId || ''));
  if (!session) return res.status(404).json({ error: 'Sesi AUDIT FILE LAIN tidak ditemukan. Pilih folder kembali.' });
  const tempOutput = `${session.workingFolder}_DATE_TEMP_${Date.now()}`;
  runPdfDateTool(session.workingFolder, tempOutput, (err, result) => {
    if (err) {
      fs.rmSync(tempOutput, { recursive: true, force: true });
      return res.status(500).json({ error: err.message });
    }
    try {
      if (result.failed) throw new Error(`${result.failed} PDF gagal dikoreksi`);
      if (fs.existsSync(tempOutput)) {
        fs.cpSync(tempOutput, session.workingFolder, { recursive: true, force: true });
        fs.rmSync(tempOutput, { recursive: true, force: true });
      }
      runPdfDateTool(session.workingFolder, '', (auditErr, auditResult) => {
        if (auditErr) return res.status(500).json({ error: auditErr.message });
        return res.json({ ...auditResult, corrected: result.corrected, workingFolder: session.workingFolder });
      });
    } catch (error) {
      fs.rmSync(tempOutput, { recursive: true, force: true });
      return res.status(500).json({ error: `Gagal menerapkan koreksi tanggal: ${error.message}` });
    }
  });
});

app.post('/api/schedule/audit', (req, res) => {
  const { mode = 'pipeline', folderPath = '' } = req.body || {};
  const isExternal = mode === 'external';
  const pdfDir = isExternal ? path.resolve(String(folderPath).trim()) : null;
  const schedulePath = isExternal ? path.join(PATHS.logs, 'schedule_audit_temp.json') : path.join(APP_DIR, 'schedule.json');
  if (isExternal && (!fs.existsSync(pdfDir) || !fs.statSync(pdfDir).isDirectory())) {
    return res.status(400).json({ success: false, error: `Folder PDF tidak ditemukan: ${pdfDir}` });
  }
  const finish = () => {
    try {
      const raw = JSON.parse(fs.readFileSync(schedulePath, 'utf8'));
      const schedules = (raw.schedules || []).map((s, idx) => {
        const photos = s.photos || {};
        const t0 = photos['0.jpg'] ? photos['0.jpg'].slice(11, 16) : '';
        const t50 = photos['50.jpg'] ? photos['50.jpg'].slice(11, 16) : '';
        const t100 = photos['100.jpg'] ? photos['100.jpg'].slice(11, 16) : '';
        return { no: idx + 1, file: s.file || '', date: s.date || '', isoDate: s.iso_date || '', tim: `Tim ${s.tim || 1}`, timNum: s.tim || 1,
          btp: s.btp || '', category: s.category || '', identifier: s.identifier || s.pdf_stem || '', duration: s.waktu_menit || 0,
          t0, t50, t100, timeRange: t0 && t100 ? `${t0} – ${t100}` : '', pdf_path: s.pdf_path || '',
          personnel: s.personnel || [],
          personnel_override: s.personnel_override || (Array.isArray(s.personnel) ? s.personnel.join(', ') : '') };
      });
      return res.json({ success: true, mode, folder: pdfDir || PATHS.source, schedule_file: schedulePath, total: schedules.length,
        tim1: schedules.filter(s => s.timNum === 1).length, tim2: schedules.filter(s => s.timNum === 2).length, schedules });
    } catch (e) {
      return res.status(500).json({ success: false, error: `Gagal membaca hasil audit jadwal: ${e.message}` });
    }
  };
  if (!isExternal) return finish();
  const scheduler = path.join(PATHS.scripts, 'scheduler.py');
  const proc = spawn('python', [scheduler, '--pdf-dir', pdfDir, '--photos-dir', PATHS.photosExport,
    '--mapping', path.join(PATHS.config, 'asset_waktu_mapping.json'), '--data-acuan',
    path.join(PATHS.config, 'data_acuan_tenaga_gabungan.json'), '--output', schedulePath], { cwd: APP_DIR });
  let stderr = '';
  proc.stderr.on('data', data => { stderr += data.toString(); });
  proc.on('close', code => code === 0 && fs.existsSync(schedulePath)
    ? finish()
    : res.status(500).json({ success: false, error: `Gagal membuat audit jadwal: ${stderr || `exit ${code}`}` }));
});

app.post('/api/schedule/export-dinasan-audit', (req, res) => {
  const requested = typeof req.body?.schedulePath === 'string' ? req.body.schedulePath : '';
  const schedulePath = path.resolve(requested);
  const allowedRoot = path.resolve(APP_DIR);
  if (!requested || !schedulePath.startsWith(allowedRoot) || !fs.existsSync(schedulePath)) {
    return res.status(400).json({ error: 'Schedule audit tidak valid atau sudah tidak tersedia.' });
  }
  try {
    const data = JSON.parse(fs.readFileSync(schedulePath, 'utf8'));
    const overrides = req.body?.overrides && typeof req.body.overrides === 'object' ? req.body.overrides : {};
    for (const item of data.schedules || []) {
      const key = item.pdf_path || item.file || '';
      if (overrides[key]) item.personnel_override = String(overrides[key]).slice(0, 500);
    }
    const tempSchedule = path.join(PATHS.logs, `schedule_export_${Date.now()}.json`);
    fs.writeFileSync(tempSchedule, JSON.stringify(data, null, 2), 'utf8');
    const iso = data.schedules?.find(item => /^\d{4}-\d{2}-\d{2}$/.test(item.iso_date))?.iso_date;
    if (!iso) return res.status(422).json({ error: 'Tidak ada tanggal valid pada schedule audit.' });
    const [year, month] = iso.split('-');
    const months = ['JANUARI','FEBRUARI','MARET','APRIL','MEI','JUNI','JULI','AGUSTUS','SEPTEMBER','OKTOBER','NOVEMBER','DESEMBER'];
    const outputName = `DAFTAR_DINASAN_PEGAWAI_${months[Number(month) - 1]}_${year}.xlsx`;
    const outputPath = path.join(PATHS.logs, outputName);
    const exporter = path.join(PATHS.scripts, 'export_dinasan_excel.py');
    const proc = spawn('python', [exporter, '--month', `${year}-${month}`, '--schedule', tempSchedule,
      '--config', path.join(PATHS.config, 'daftar_pegawai.json'), '--output', outputPath], { cwd: APP_DIR });
    let stderr = '';
    proc.stderr.on('data', data => { stderr += data.toString(); });
    proc.on('close', code => {
      try { fs.unlinkSync(tempSchedule); } catch (_) {}
      if (code !== 0 || !fs.existsSync(outputPath)) return res.status(500).json({ error: `Gagal membuat Excel Dinasan: ${stderr || `exit ${code}`}` });
      return res.download(outputPath, outputName);
    });
  } catch (e) {
    return res.status(500).json({ error: `Gagal membaca schedule audit: ${e.message}` });
  }
});

app.post('/api/schedule/export-dinasan-excel', (req, res) => {
  const folderPath = typeof req.body?.folderPath === 'string' ? req.body.folderPath.trim() : '';
  const withPersonnel = Boolean(req.body?.withPersonnel);
  if (!folderPath) return res.status(400).json({ error: 'Path folder PDF wajib diisi' });
  const pdfDir = path.resolve(folderPath);
  if (!fs.existsSync(pdfDir) || !fs.statSync(pdfDir).isDirectory()) {
    return res.status(400).json({ error: `Folder tidak ditemukan: ${pdfDir}` });
  }

  const scheduler = path.join(PATHS.scripts, 'scheduler.py');
  const tempSchedule = path.join(PATHS.logs, 'schedule_external_temp.json');
  const args = [scheduler, '--pdf-dir', pdfDir, '--photos-dir', PATHS.photosExport,
    '--mapping', path.join(PATHS.config, 'asset_waktu_mapping.json'),
    '--data-acuan', path.join(PATHS.config, 'data_acuan_tenaga_gabungan.json'),
    '--output', tempSchedule];
  const proc = spawn('python', args, { cwd: APP_DIR });
  let stderr = '';
  proc.stderr.on('data', data => { stderr += data.toString(); });
  proc.on('close', (code) => {
    if (code !== 0 || !fs.existsSync(tempSchedule)) {
      return res.status(500).json({ error: `Gagal membuat schedule: ${stderr || `exit ${code}`}` });
    }
    try {
      const schedule = JSON.parse(fs.readFileSync(tempSchedule, 'utf8'));
      const iso = schedule.schedules?.find(item => /^\d{4}-\d{2}-\d{2}$/.test(item.iso_date))?.iso_date;
      if (!iso) return res.status(422).json({ error: 'Tidak ada tanggal valid pada PDF terpilih' });
      const [year, month] = iso.split('-');
      const months = ['JANUARI','FEBRUARI','MARET','APRIL','MEI','JUNI','JULI','AGUSTUS','SEPTEMBER','OKTOBER','NOVEMBER','DESEMBER'];
      const scheduleName = `schedule_${months[Number(month) - 1]}_${year}.json`;
      const schedulePath = path.join(PATHS.logs, scheduleName);
      fs.renameSync(tempSchedule, schedulePath);
      const outputName = `DAFTAR_DINASAN_PEGAWAI${withPersonnel ? '_DENGAN_PERSONIL' : ''}_${months[Number(month) - 1]}_${year}.xlsx`;
      const outputPath = path.join(PATHS.logs, outputName);
      const exporter = path.join(PATHS.scripts, 'export_dinasan_excel.py');
      const exportArgs = [exporter, '--month', `${year}-${month}`, '--schedule', schedulePath,
        '--config', path.join(PATHS.config, 'daftar_pegawai.json'), '--output', outputPath];
      if (withPersonnel) exportArgs.push('--with-personnel');
      const exportProc = spawn('python', exportArgs, { cwd: APP_DIR });
      let exportErr = '';
      exportProc.stderr.on('data', data => { exportErr += data.toString(); });
      exportProc.on('close', exportCode => {
        if (exportCode !== 0 || !fs.existsSync(outputPath)) {
          return res.status(500).json({ error: `Gagal membuat Excel Dinasan: ${exportErr || `exit ${exportCode}`}` });
        }
        res.download(outputPath, outputName);
      });
    } catch (err) {
      res.status(500).json({ error: `Gagal memproses schedule: ${err.message}` });
    }
  });
});

app.post('/api/schedule/export-asset-data', (req, res) => {
  const { mode = 'pipeline', folderPath = '' } = req.body || {};
  const external = mode === 'external';
  const pdfDir = external ? path.resolve(String(folderPath).trim()) : PATHS.target;
  if (!fs.existsSync(pdfDir) || !fs.statSync(pdfDir).isDirectory()) {
    return res.status(400).json({ error: `Folder PDF tidak ditemukan: ${pdfDir}` });
  }

  const stamp = Date.now();
  const schedulePath = external ? path.join(PATHS.logs, `asset_schedule_${stamp}.json`) : path.join(APP_DIR, 'schedule.json');
  const runExporter = () => {
    let schedule;
    try {
      schedule = JSON.parse(fs.readFileSync(schedulePath, 'utf8'));
    } catch (err) {
      return res.status(500).json({ error: `Schedule tidak dapat dibaca: ${err.message}` });
    }
    const iso = schedule.schedules?.find(item => /^\d{4}-\d{2}-\d{2}$/.test(item.iso_date))?.iso_date;
    const months = ['JANUARI','FEBRUARI','MARET','APRIL','MEI','JUNI','JULI','AGUSTUS','SEPTEMBER','OKTOBER','NOVEMBER','DESEMBER'];
    const outputName = iso
      ? `DATA_ASET_${months[Number(iso.slice(5, 7)) - 1]}_${iso.slice(0, 4)}.xlsx`
      : `DATA_ASET_${stamp}.xlsx`;
    const outputPath = path.join(PATHS.logs, outputName);
    const script = path.join(PATHS.scripts, 'export_asset_data_excel.py');
    const proc = spawn('python', [script, '--schedule', schedulePath, '--pdf-dir', pdfDir, '--output', outputPath], { cwd: APP_DIR });
    let stderr = '';
    proc.stderr.on('data', data => { stderr += data.toString(); });
    proc.on('close', code => {
      if (external) { try { fs.unlinkSync(schedulePath); } catch (_) {} }
      if (code !== 0 || !fs.existsSync(outputPath)) {
        return res.status(500).json({ error: `Gagal membuat Excel data aset: ${stderr || `exit ${code}`}` });
      }
      res.download(outputPath, outputName);
    });
  };

  if (!external) {
    if (!fs.existsSync(schedulePath)) return res.status(404).json({ error: 'schedule.json belum tersedia. Jalankan Step 3.' });
    return runExporter();
  }
  const scheduler = path.join(PATHS.scripts, 'scheduler.py');
  const proc = spawn('python', [scheduler, '--pdf-dir', pdfDir, '--photos-dir', PATHS.photosExport,
    '--mapping', path.join(PATHS.config, 'asset_waktu_mapping.json'), '--data-acuan',
    path.join(PATHS.config, 'data_acuan_tenaga_gabungan.json'), '--output', schedulePath], { cwd: APP_DIR });
  let stderr = '';
  proc.stderr.on('data', data => { stderr += data.toString(); });
  proc.on('close', code => code === 0 && fs.existsSync(schedulePath)
    ? runExporter()
    : res.status(500).json({ error: `Gagal membaca aset folder: ${stderr || `exit ${code}`}` }));
});

function runPdfDateTool(inputDir, outputDir, callback) {
  const script = path.join(PATHS.scripts, 'correct_pdf_dates.py');
  const args = [script, '--input', inputDir];
  if (outputDir) args.push('--output', outputDir);
  const proc = spawn('python', args, { cwd: APP_DIR, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
  let stdout = '';
  let stderr = '';
  proc.stdout.on('data', data => { stdout += data.toString(); });
  proc.stderr.on('data', data => { stderr += data.toString(); });
  proc.on('close', code => {
    let result;
    try {
      result = JSON.parse(stdout.trim().split(/\r?\n/).filter(Boolean).pop() || '{}');
    } catch (err) {
      return callback(new Error(`Hasil audit tidak valid: ${stderr || stdout || err.message}`));
    }
    if (code !== 0 || !result.success) {
      return callback(new Error(result.error || stderr || `exit ${code}`));
    }
    callback(null, result);
  });
}

app.post('/api/pdf-dates/audit', (req, res) => {
  const { mode = 'pipeline', folderPath = '' } = req.body || {};
  const inputDir = mode === 'external' ? path.resolve(String(folderPath).trim()) : PATHS.target;
  if (!fs.existsSync(inputDir) || !fs.statSync(inputDir).isDirectory()) {
    return res.status(400).json({ error: `Folder PDF tidak ditemukan: ${inputDir}` });
  }
  runPdfDateTool(inputDir, '', (err, result) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(result);
  });
});

app.post('/api/pdf-dates/correct', (req, res) => {
  const { mode = 'pipeline', folderPath = '' } = req.body || {};
  const inputDir = mode === 'external' ? path.resolve(String(folderPath).trim()) : PATHS.target;
  if (!fs.existsSync(inputDir) || !fs.statSync(inputDir).isDirectory()) {
    return res.status(400).json({ error: `Folder PDF tidak ditemukan: ${inputDir}` });
  }
  runPdfDateTool(inputDir, inputDir, (err, result) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(result);
  });
});

app.get('/api/schedule/export-dinasan-excel', (req, res) => {
  const withPersonnel = req.query.withPersonnel === '1';
  const pyScript = path.join(PATHS.scripts, 'export_dinasan_excel.py');
  const outputName = `DAFTAR_DINASAN_PEGAWAI${withPersonnel ? '_DENGAN_PERSONIL' : ''}.xlsx`;
  const outputPath = path.join(PATHS.logs, outputName);
  const args = [pyScript, '--output', outputPath];
  if (withPersonnel) args.push('--with-personnel');
  const pyProc = spawn('python', args, { cwd: APP_DIR });
  let stderr = '';
  pyProc.stderr.on('data', data => { stderr += data.toString(); });
  pyProc.on('close', (code) => {
    if (code !== 0) return res.status(500).json({ error: `Gagal membuat Excel Dinasan: ${stderr}` });
    if (fs.existsSync(outputPath)) {
      return res.download(outputPath, outputName);
    }
    const logFiles = fs.readdirSync(PATHS.logs).filter(f => f.startsWith('DAFTAR_DINASAN_PEGAWAI') && f.endsWith('.xlsx'));
    if (logFiles.length === 0) return res.status(404).json({ error: 'File Excel dinasan tidak ditemukan di logs' });
    logFiles.sort((a, b) => fs.statSync(path.join(PATHS.logs, b)).mtimeMs - fs.statSync(path.join(PATHS.logs, a)).mtimeMs);
    res.download(path.join(PATHS.logs, logFiles[0]), logFiles[0]);
  });
});

// ----------------------------------------------------
// PDF VIEW & SYSTEM OPEN ENDPOINTS
// ----------------------------------------------------

// GET /api/pdf/view-target — stream PDF target (02_pdf_target or custom path)
app.get('/api/pdf/view-target', (req, res) => {
  const { file, path: customPath } = req.query;
  let targetPath = '';

  if (customPath && typeof customPath === 'string') {
    const norm = path.normalize(customPath.trim());
    if (fs.existsSync(norm) && fs.statSync(norm).isFile()) {
      targetPath = norm;
    }
  }

  if (!targetPath && file && typeof file === 'string') {
    const safeName = path.basename(file.trim());
    const candidate = path.join(PATHS.target, safeName);
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      targetPath = candidate;
    }
  }

  if (!targetPath || !fs.existsSync(targetPath)) {
    return res.status(404).send('Berkas PDF Target tidak ditemukan di sistem.');
  }

  const filename = path.basename(targetPath);
  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `inline; filename="${encodeURIComponent(filename)}"`);
  const stream = fs.createReadStream(targetPath);
  stream.on('error', () => {
    if (!res.headersSent) res.status(500).send('Gagal membaca berkas PDF.');
  });
  stream.pipe(res);
});

// GET /api/pdf/view-source — stream PDF source (01_pdf_source)
app.get('/api/pdf/view-source', (req, res) => {
  const { file } = req.query;
  if (!file || typeof file !== 'string') return res.status(400).send('Nama file tidak valid.');
  const safeName = path.basename(file.trim());
  const candidate = path.join(PATHS.source, safeName);
  if (!fs.existsSync(candidate) || !fs.statSync(candidate).isFile()) {
    return res.status(404).send('Berkas PDF Source tidak ditemukan di sistem.');
  }

  res.setHeader('Content-Type', 'application/pdf');
  res.setHeader('Content-Disposition', `inline; filename="${encodeURIComponent(safeName)}"`);
  const stream = fs.createReadStream(candidate);
  stream.on('error', () => {
    if (!res.headersSent) res.status(500).send('Gagal membaca berkas PDF.');
  });
  stream.pipe(res);
});

// POST /api/pdf/open-system — open PDF in OS default application (Adobe Reader, etc.)
app.post('/api/pdf/open-system', (req, res) => {
  const { file, path: customPath } = req.body || {};
  let targetPath = '';

  if (customPath && typeof customPath === 'string') {
    const norm = path.normalize(customPath.trim());
    if (fs.existsSync(norm) && fs.statSync(norm).isFile()) {
      targetPath = norm;
    }
  }

  if (!targetPath && file && typeof file === 'string') {
    const safeName = path.basename(file.trim());
    const candidate = path.join(PATHS.target, safeName);
    if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) {
      targetPath = candidate;
    }
  }

  if (!targetPath || !fs.existsSync(targetPath)) {
    return res.status(404).json({ success: false, error: 'Berkas PDF Target tidak ditemukan di sistem.' });
  }

  const { exec } = require('child_process');
  const winCmd = `cmd.exe /c start "" "${targetPath.replace(/"/g, '\\"')}"`;
  exec(winCmd, (err) => {
    if (err) {
      return res.status(500).json({ success: false, error: 'Gagal membuka berkas di sistem: ' + err.message });
    }
    return res.json({ success: true, message: `Membuka berkas ${path.basename(targetPath)} di aplikasi sistem.` });
  });
});

app.post('/api/photos/manual-crop', (req, res) => {
  const { rawRelPath, quadrant, cropBox, applyToFolder } = req.body;
  if (!rawRelPath) return res.status(400).json({ error: 'rawRelPath is required' });

  const selectedQuad = quadrant || 'bottom-left';
  const targetPath = path.join(PATHS.photosExport, rawRelPath);
  const targetFolder = path.dirname(targetPath);
  
  let filesToCrop = [];
  if (applyToFolder) {
    if (fs.existsSync(targetFolder)) {
      filesToCrop = fs.readdirSync(targetFolder)
        .filter(f => f.toLowerCase().endsWith('.jpg'))
        .map(f => path.join(targetFolder, f));
    }
  } else {
    filesToCrop = [targetPath];
  }

  if (filesToCrop.length === 0) {
    return res.status(404).json({ error: 'No files found to crop' });
  }

  const pyScript = path.join(PATHS.scripts, 'manual_crop_helper.py');
  let args = [pyScript];

  if (cropBox && Array.isArray(cropBox) && cropBox.length === 4) {
    args.push('--crop-box', cropBox[0].toString(), cropBox[1].toString(), cropBox[2].toString(), cropBox[3].toString());
  } else {
    args.push('--quadrant', selectedQuad);
  }

  args.push('--photos-dir', PATHS.photosExport, '--temp-dir', PATHS.photosTemp);
  args.push('--files', ...filesToCrop);
  const pyProc = spawn('python', args, { cwd: APP_DIR });

  pyProc.on('close', (code) => {
    if (code === 0) {
      filesToCrop.forEach(filePath => {
        const rel = path.relative(PATHS.photosExport, filePath).replace(/\\/g, '/');
        saveCollageCropMeta({ rel, cropBox: cropBox || null, source: 'manual_ui_legacy' });
      });

      // Update logs/cropped_collages.json
      const croppedSetFile = path.join(PATHS.logs, 'cropped_collages.json');
      try {
        const existingList = fs.existsSync(croppedSetFile) ? JSON.parse(fs.readFileSync(croppedSetFile, 'utf-8')) : [];
        const set = new Set(Array.isArray(existingList) ? existingList.map(s => String(s).toLowerCase()) : []);
        filesToCrop.forEach(filePath => {
          const rel = path.relative(PATHS.photosExport, filePath).replace(/\\/g, '/');
          set.add(rel.toLowerCase());
        });
        fs.writeFileSync(croppedSetFile, JSON.stringify(Array.from(set), null, 2), 'utf-8');
      } catch (e) {}

      // Re-run Step 4 (edit_timemark_ide1.py), Step 4 Time (edit_photo_time_only.py), and Step 4 Coord (edit_photo_coordinate_only.py) for this folder
      const editScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');
      const timeScript = path.join(PATHS.scripts, 'edit_photo_time_only.py');
      const coordScript = path.join(PATHS.scripts, 'edit_photo_coordinate_only.py');

      const runProc = (scriptPath, scriptArgs) => new Promise((resolve) => {
        const p = spawn('python', [scriptPath, ...scriptArgs], { cwd: APP_DIR });
        p.on('close', () => resolve());
        p.on('error', () => resolve());
      });

      Promise.all([
        runProc(editScript, ['--input', targetFolder]),
        runProc(timeScript, ['--input', targetFolder]),
        runProc(coordScript, ['--input', targetFolder])
      ]).then(() => {
        res.json({ success: true, count: filesToCrop.length });
      });
    } else {
      res.status(500).json({ error: 'Manual crop python helper failed' });
    }
  });
});

app.post('/api/photos/remove-crop', (req, res) => {
  const { rawRelPath } = req.body;
  if (!rawRelPath) return res.status(400).json({ error: 'rawRelPath is required' });

  const tempFile = path.join(PATHS.photosTemp, rawRelPath);
  const targetFolder = path.dirname(path.join(PATHS.photosExport, rawRelPath));

  if (fs.existsSync(tempFile)) {
    try { fs.unlinkSync(tempFile); } catch (e) {}
  }

  // Update logs/cropped_collages.json
  const croppedSetFile = path.join(PATHS.logs, 'cropped_collages.json');
  if (fs.existsSync(croppedSetFile)) {
    try {
      const list = JSON.parse(fs.readFileSync(croppedSetFile, 'utf-8'));
      const nextList = list.filter(item => item.toLowerCase() !== rawRelPath.toLowerCase().replace(/\\/g, '/'));
      fs.writeFileSync(croppedSetFile, JSON.stringify(nextList, null, 2), 'utf-8');
    } catch (e) {}
  }

  // Re-run Step 4, Step 4 Time, and Step 4 Coord for this folder
  const editScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');
  const timeScript = path.join(PATHS.scripts, 'edit_photo_time_only.py');
  const coordScript = path.join(PATHS.scripts, 'edit_photo_coordinate_only.py');

  const runProc = (scriptPath, scriptArgs) => new Promise((resolve) => {
    const p = spawn('python', [scriptPath, ...scriptArgs], { cwd: APP_DIR });
    p.on('close', () => resolve());
    p.on('error', () => resolve());
  });

  Promise.all([
    runProc(editScript, ['--input', targetFolder]),
    runProc(timeScript, ['--input', targetFolder]),
    runProc(coordScript, ['--input', targetFolder])
  ]).then(() => {
    res.json({ success: true });
  });
});

// ----------------------------------------------------
// 4. SMART PDF PREVIEWER & MERGED PDF LIST APIS
// ----------------------------------------------------

app.get('/api/pdfs', (req, res) => {
  if (!fs.existsSync(PATHS.pdfMerged)) {
    return res.json({ pdfs: [] });
  }

  // Recursively scan for PDFs (merge outputs go into Tim_N subfolders)
  const pdfs = [];
  function scanDir(dir, prefix = '') {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory()) {
        scanDir(path.join(dir, entry.name), prefix + entry.name + '/');
      } else if (entry.name.toLowerCase().endsWith('.pdf')) {
        pdfs.push({
          filename: prefix + entry.name,
          url: `/static/pdf-merged/${prefix}${entry.name}`
        });
      }
    }
  }
  scanDir(PATHS.pdfMerged);

  res.json({ pdfs });
});

// Serve Pixel Inspector Tab
app.get('/pixel-inspector', (req, res) => {
  res.sendFile(path.join(PATHS.templates, 'pixel_inspector.html'));
});

// --- COLLAGE ANALYZER ENDPOINTS ---

// GET /api/photos/scan-collages — scan 03_photos_export for collage photos using Python
app.get('/api/photos/scan-collages', (req, res) => {
  const script = path.join(PATHS.scripts, 'scan_collages_helper.py');
  const proc = spawn('python', [script, '--photos-dir', PATHS.photosExport, '--output', 'json'], { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    try {
      const idx = out.lastIndexOf('__COLLAGES__');
      if (idx === -1) return res.json({ success: false, error: 'No collage data returned', stderr: err });
      const jsonStr = out.slice(idx + '__COLLAGES__'.length).trim();
      const data = JSON.parse(jsonStr);
      res.json({ success: true, collages: data });
    } catch (e) {
      res.json({ success: false, error: e.message, stdout: out, stderr: err });
    }
  });
});

// POST /api/photos/save-crops — crop selected photos and write back to 03_photos_export
app.post('/api/photos/save-crops', (req, res) => {
  const { crops } = req.body; // [{rel, cropBox: [left, upper, right, lower]}]
  if (!Array.isArray(crops) || crops.length === 0) return res.json({ success: false, error: 'No crops provided' });
  const validCrops = crops.filter(c => {
    const rel = String(c.rel || '').replace(/\\/g, '/');
    return rel && !rel.startsWith('/') && !rel.split('/').includes('..') &&
      Array.isArray(c.cropBox) && c.cropBox.length === 4 && c.cropBox.every(Number.isFinite);
  });
  if (validCrops.length !== crops.length) return res.status(400).json({ success: false, error: 'Invalid crop path or cropBox' });

  const script = path.join(PATHS.scripts, 'scan_collages_helper.py');
  const cropsJson = JSON.stringify(validCrops);
  const proc = spawn('python', [script, '--save-crops', '--crops-json', cropsJson, '--photos-dir', PATHS.photosExport], { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    if (code === 0) validCrops.forEach(c => saveCollageCropMeta(c));
    res.json({ success: code === 0, count: code === 0 ? validCrops.length : 0, stdout: out.slice(-500), stderr: err.slice(-300) });
  });
});

// POST /api/photos/restore-crop — restore a cropped photo back to original collage from backup
app.post('/api/photos/restore-crop', (req, res) => {
  const { rel } = req.body;
  if (!rel) return res.json({ success: false, error: 'No rel path provided' });

  const script = path.join(PATHS.scripts, 'scan_collages_helper.py');
  const proc = spawn('python', [script, '--restore', '--restore-rel', rel, '--photos-dir', PATHS.photosExport], { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    const ok = out.includes('__RESTORE_OK__');
    res.json({ success: ok, stdout: out.slice(-400), stderr: err.slice(-200) });
  });
});

// POST /api/photos/reexport-original — re-export fresh original photo from source PDF in 01_pdf_source
app.post('/api/photos/reexport-original', (req, res) => {
  const { rel, render_crop } = req.body;
  if (!rel) return res.json({ success: false, error: 'No rel path provided' });

  const script = path.join(PATHS.scripts, 'reexport_single_asset.py');
  const scriptArgs = [script, '--rel', rel, '--source-dir', PATHS.source, '--photos-dir', PATHS.photosExport, '--logs-dir', PATHS.logs];
  if (render_crop) {
    scriptArgs.push('--render-crop');
  }
  const proc = spawn('python', scriptArgs, { cwd: APP_DIR });
  let out = '';
  let err = '';
  let settled = false;
  const finish = (payload, status = 200) => {
    if (settled) return;
    settled = true;
    res.status(status).json(payload);
  };
  const timeout = setTimeout(() => {
    proc.kill();
    finish({ success: false, error: 'Targeted re-export timeout', stdout: out.slice(-600), stderr: err.slice(-300) }, 504);
  }, 120000);
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    clearTimeout(timeout);
    finish({ success: code === 0, stdout: out.slice(-600), stderr: err.slice(-300) });
  });
  proc.on('error', error => {
    clearTimeout(timeout);
    finish({ success: false, error: error.message, stdout: out.slice(-600), stderr: err.slice(-300) }, 500);
  });
});

// POST /api/photos/run-edit-timemark — run edit_timemark_ide1.py for a single folder
app.post('/api/photos/run-edit-timemark', (req, res) => {
  const { rel, detector } = req.body; // e.g. "BTP BD/PTDS/MSG"
  if (!rel) return res.json({ success: false, error: 'No rel path provided' });

  let folderRel = rel;
  if (folderRel.match(/\.(jpg|png)$/i)) {
    folderRel = path.dirname(folderRel);
  }
  const inputDir = path.join(PATHS.photosExport, folderRel);
  if (!fs.existsSync(inputDir)) return res.json({ success: false, error: `Folder not found: ${inputDir}` });

  const det = detector === 'guide' ? 'guide' : 'google_vision';
  const pyArgs = ['scripts/edit_timemark_ide1.py', '--input', inputDir, '--detector', det];
  const schedPath = path.join(PATHS.logs, 'schedule.json');
  if (fs.existsSync(schedPath)) {
    pyArgs.push('--schedule', schedPath);
  }

  const proc = spawn('python', pyArgs, { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    res.json({ success: code === 0, stdout: out.slice(-600), stderr: err.slice(-300) });
  });
});

// POST /api/photos/run-pixel-inspector — queue a photo through pixel inspector with specific mask
app.post('/api/photos/run-pixel-inspector', (req, res) => {
  const { rel, maskType } = req.body; // maskType: 'red' | 'cyan' | 'custom'
  if (!rel) return res.json({ success: false, error: 'No rel path provided' });

  const maskArg = maskType === 'cyan' ? '--cyan-mask' : maskType === 'custom' ? '--custom-mask' : '--red-mask';
  const inputPath = path.join(PATHS.photosExport, rel);
  if (!fs.existsSync(inputPath)) return res.json({ success: false, error: `File not found: ${inputPath}` });

  const pyArgs = ['scripts/edit_timemark_ide1.py', '--input', inputPath, maskArg];
  const schedPath = path.join(PATHS.logs, 'schedule.json');
  if (fs.existsSync(schedPath)) {
    pyArgs.push('--schedule', schedPath);
  }

  const proc = spawn('python', pyArgs, { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    res.json({ success: code === 0, rel, editedUrl: `/static/photos/edited/Tim_1/${rel}`, stdout: out.slice(-600), stderr: err.slice(-300) });
  });
});

// ----------------------------------------------------
// TARGET FILE MAPPING & PHOTO REPLACEMENT APIS
// ----------------------------------------------------
function expandIdentifierVariants(ident) {
  const set = new Set();
  if (!ident) return [];
  const norm = ident.toUpperCase().trim();
  set.add(norm);
  const baseNoDate = norm.replace(/_\d{2}-\d{2}$/, '').trim();
  set.add(baseNoDate);

  if (baseNoDate === 'ZP 41 BOO') set.add('ZP 41B BOO');
  if (baseNoDate === 'ZP 41B BOO') set.add('ZP 41 BOO');

  if (baseNoDate.includes('JPL 26N')) {
    set.add('JPL 26N CLT');
    set.add('JPL 26N BJD');
    set.add('JPL 26N CLT-BJD');
    set.add('JPL 26N BJD-CLT');
  }

  const m0 = baseNoDate.match(/^(JPL\s+)0?(\d+[A-Z]?)\s+(.*)$/i);
  if (m0) {
    const num = parseInt(m0[2], 10);
    const padNum = String(num).padStart(2, '0');
    set.add(`${m0[1].toUpperCase()}${num} ${m0[3].toUpperCase()}`);
    set.add(`${m0[1].toUpperCase()}${padNum} ${m0[3].toUpperCase()}`);
  }

  const m = baseNoDate.match(/^(JPL\s+(?:BNR|\d+[A-Z]?))\s+([A-Z]{2,3}(?:-[A-Z]{2,3})+)$/i);
  if (m) {
    const prefix = m[1].toUpperCase();
    const stations = m[2].toUpperCase().split('-');
    stations.forEach(st => {
      set.add(`${prefix} ${st}`);
    });
    const sortedStations = stations.slice().sort().join('-');
    const reversedStations = stations.slice().reverse().join('-');
    set.add(`${prefix} ${sortedStations}`);
    set.add(`${prefix} ${reversedStations}`);
  }
  return Array.from(set);
}

function getTargetFileMapping() {
  const schedPath = path.join(APP_DIR, 'schedule.json');
  if (fs.existsSync(schedPath)) {
    try {
      const sched = JSON.parse(fs.readFileSync(schedPath, 'utf8'));
      const targetMap = new Map();
      (sched.schedules || []).forEach(item => {
        const fn = item.file;
        if (!fn) return;
        if (!targetMap.has(fn)) {
          targetMap.set(fn, {
            file: fn,
            category: item.category || '',
            btp: item.btp || '',
            date: item.iso_date || '',
            tim: item.tim || 1,
            identifiers: []
          });
        }
        const entry = targetMap.get(fn);
        const ident = item.identifier;
        const baseIdent = item.base_identifier || ident;
        [ident, baseIdent].forEach(id => {
          if (!id) return;
          expandIdentifierVariants(id).forEach(v => {
            if (!entry.identifiers.includes(v)) entry.identifiers.push(v);
          });
        });
      });
      return Array.from(targetMap.values()).sort((a, b) => a.file.localeCompare(b.file));
    } catch (e) {
      console.error('Error reading schedule.json:', e);
    }
  }

  // Fallback: scan 02_pdf_target
  const list = [];
  if (fs.existsSync(PATHS.target)) {
    const files = fs.readdirSync(PATHS.target).filter(f => f.toLowerCase().endsWith('.pdf'));
    files.sort().forEach(file => {
      list.push({
        file,
        category: '',
        btp: '',
        date: '',
        tim: 1,
        identifiers: []
      });
    });
  }
  return list;
}

app.get('/api/target-mapping', (req, res) => {
  res.json({ success: true, targets: getTargetFileMapping() });
});

function getPhotoTargetMapping() {
  const mapPath = path.join(APP_DIR, 'photo_target_mapping.json');
  if (fs.existsSync(mapPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(mapPath, 'utf8'));
      if (data && data.mapping) return data.mapping;
    } catch (e) {}
  }
  // Fallback: build dynamically from schedule.json
  const schedPath = path.join(APP_DIR, 'schedule.json');
  const mapping = {};
  if (fs.existsSync(schedPath)) {
    try {
      const sched = JSON.parse(fs.readFileSync(schedPath, 'utf8'));
      (sched.schedules || []).forEach(item => {
        const btp = item.btp || 'UNKNOWN';
        const cat = item.category || 'UNKNOWN';
        const ident = item.identifier || '';
        const fn = item.file || '';
        if (!fn || !ident) return;
        const key = `${btp}/${cat}/${ident}`;
        if (!mapping[key]) {
          mapping[key] = { category: cat, btp, identifier: ident, target_files: [] };
        }
        if (!mapping[key].target_files.includes(fn)) {
          mapping[key].target_files.push(fn);
        }
      });
    } catch (e) {}
  }
  return mapping;
}

app.get('/api/photo-targets-mapping', (req, res) => {
  res.json({ success: true, mapping: getPhotoTargetMapping() });
});

// POST /api/photos/replace — ganti foto mentah dan auto Step 4
app.post('/api/photos/replace', uploadTemp.single('image'), (req, res) => {
  const { rel, mode, detector } = req.body;
  if (!rel) {
    if (req.file && fs.existsSync(req.file.path)) fs.unlinkSync(req.file.path);
    return res.status(400).json({ success: false, error: 'rel path is required' });
  }
  if (!req.file) {
    return res.status(400).json({ success: false, error: 'image file is required' });
  }

  const tempPath = req.file.path;
  const pyScript = path.join(PATHS.scripts, 'replace_export_photo.py');
  const pyArgs = [
    pyScript,
    '--action', 'replace',
    '--target', rel,
    '--image', tempPath,
    '--mode', mode || 'tanggal',
    '--detector', detector || 'google_vision'
  ];

  const proc = spawn('python', pyArgs, { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    if (fs.existsSync(tempPath)) {
      try { fs.unlinkSync(tempPath); } catch (e) {}
    }
    invalidateGalleryCache();
    try {
      const result = JSON.parse(out.trim());
      res.json(result);
    } catch (e) {
      res.json({ success: code === 0, stdout: out, stderr: err });
    }
  });
});

// POST /api/photos/revert — revert ke foto mentah original dan auto Step 4
app.post('/api/photos/revert', (req, res) => {
  const { rel, mode, detector } = req.body;
  if (!rel) return res.status(400).json({ success: false, error: 'rel path is required' });

  const pyScript = path.join(PATHS.scripts, 'replace_export_photo.py');
  const pyArgs = [
    pyScript,
    '--action', 'revert',
    '--target', rel,
    '--mode', mode || 'tanggal',
    '--detector', detector || 'google_vision'
  ];

  const proc = spawn('python', pyArgs, { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    invalidateGalleryCache();
    try {
      const result = JSON.parse(out.trim());
      res.json(result);
    } catch (e) {
      res.json({ success: code === 0, stdout: out, stderr: err });
    }
  });
});

// POST /api/photos/swap — tukar dua foto di 03_photos_export dan auto Step 4
app.post('/api/photos/swap', (req, res) => {
  const { sourceRel, targetRel, mode, detector } = req.body;
  if (!sourceRel || !targetRel) {
    return res.status(400).json({ success: false, error: 'sourceRel and targetRel are required' });
  }

  if (sourceRel === targetRel) {
    return res.json({ success: true, message: 'Source and target are the same photo' });
  }

  const pyScript = path.join(PATHS.scripts, 'replace_export_photo.py');
  const pyArgs = [
    pyScript,
    '--action', 'swap',
    '--source', sourceRel,
    '--target', targetRel,
    '--mode', mode || 'tanggal',
    '--detector', detector || 'google_vision'
  ];

  const proc = spawn('python', pyArgs, { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    invalidateGalleryCache();
    try {
      const result = JSON.parse(out.trim());
      res.json(result);
    } catch (e) {
      res.json({ success: code === 0, stdout: out, stderr: err });
    }
  });
});


// ----------------------------------------------------
// KOREKSI JUMLAH CORE SERAT OPTIK APIS
// ----------------------------------------------------
app.post('/api/core-optik/scan', (req, res) => {
  const { mode, customPath, defaultFolders } = req.body || {};
  const pyScript = path.join(PATHS.scripts, 'correct_serat_optik_cores.py');
  const pyArgs = [pyScript, '--scan', '--json'];

  if (mode === 'custom' && customPath && customPath.trim()) {
    pyArgs.push('--folders', customPath.trim());
  } else if (Array.isArray(defaultFolders) && defaultFolders.length > 0) {
    pyArgs.push('--folders', ...defaultFolders);
  } else {
    pyArgs.push('--folders', '05_pdf_merged', '01_pdf_source', '02_pdf_target');
  }

  const pyProc = spawn('python', pyArgs, { cwd: APP_DIR });
  let stdoutData = '';
  let stderrData = '';

  pyProc.stdout.on('data', (d) => stdoutData += d.toString());
  pyProc.stderr.on('data', (d) => stderrData += d.toString());

  pyProc.on('close', (code) => {
    if (code === 0) {
      try {
        const parsed = JSON.parse(stdoutData);
        return res.json({ success: true, items: parsed });
      } catch (err) {
        return res.status(500).json({ success: false, error: 'Gagal parse JSON dari script', raw: stdoutData });
      }
    }
    return res.status(500).json({ success: false, error: stderrData || 'Gagal memindai berkas core optik' });
  });
});

app.post('/api/core-optik/apply', (req, res) => {
  const { mode, customPath, defaultFolders, file } = req.body || {};
  const pyScript = path.join(PATHS.scripts, 'correct_serat_optik_cores.py');
  const pyArgs = [pyScript, '--apply', '--json'];

  if (file && file.trim()) {
    pyArgs.push('--file', file.trim());
  } else if (mode === 'custom' && customPath && customPath.trim()) {
    pyArgs.push('--folders', customPath.trim());
  } else if (Array.isArray(defaultFolders) && defaultFolders.length > 0) {
    pyArgs.push('--folders', ...defaultFolders);
  } else {
    pyArgs.push('--folders', '05_pdf_merged', '01_pdf_source', '02_pdf_target');
  }

  const pyProc = spawn('python', pyArgs, { cwd: APP_DIR });
  let stdoutData = '';
  let stderrData = '';

  pyProc.stdout.on('data', (d) => stdoutData += d.toString());
  pyProc.stderr.on('data', (d) => stderrData += d.toString());

  pyProc.on('close', (code) => {
    if (code === 0) {
      try {
        const parsed = JSON.parse(stdoutData);
        const updatedCount = parsed.filter(i => i.applied).length;
        return res.json({ success: true, updatedCount, items: parsed });
      } catch (err) {
        return res.status(500).json({ success: false, error: 'Gagal parse JSON hasil perbaikan', raw: stdoutData });
      }
    }
    return res.status(500).json({ success: false, error: stderrData || 'Gagal menerapkan koreksi core' });
  });
});

// ----------------------------------------------------
// SELECTIVE SINGLE-PDF RE-MERGE API
// Helper to check if photos exist for a relative path in a base directory
function checkPhotosExistForRel(baseDir, cleanRel) {
  if (!fs.existsSync(baseDir)) return false;
  const parts = String(cleanRel).replace(/\\/g, '/').replace(/^Tim_\d+\//, '').split('/');
  if (parts.length < 3) return false;
  const btp = parts[0];
  const cat = parts[1];
  const ident = parts[2];
  const fileName = parts[3] || '0.jpg';

  // 1. Direct path: baseDir / btp / cat / ident / fileName
  if (fs.existsSync(path.join(baseDir, btp, cat, ident, fileName))) return true;

  // 2. Tim_X subdirectories: baseDir / Tim_N / btp / cat / ident / fileName
  try {
    const entries = fs.readdirSync(baseDir, { withFileTypes: true });
    for (const ent of entries) {
      if (ent.isDirectory() && ent.name.startsWith('Tim_')) {
        if (fs.existsSync(path.join(baseDir, ent.name, btp, cat, ident, fileName))) return true;
      }
    }
  } catch (e) {}
  return false;
}

// ----------------------------------------------------
app.post('/api/pdf/remerge-single', async (req, res) => {
  const { rawRelPath, pdfName, mode, timGroup, mergeAll } = req.body || {};
  let targetPdfName = (pdfName || '').trim();
  const startTime = Date.now();

  const targets = getTargetFileMapping();
  const photoMap = getPhotoTargetMapping();

  let targetPdfList = [];

  if (rawRelPath) {
    const cleanRel = String(rawRelPath).replace(/\\/g, '/').replace(/^Tim_\d+\//, '');
    const parts = cleanRel.split('/');
    if (parts.length >= 3) {
      const btp = parts[0];
      const category = parts[1];
      const identifier = parts[2];
      const fullKey = `${btp}/${category}/${identifier}`;

      if (photoMap[fullKey] && Array.isArray(photoMap[fullKey].target_files) && photoMap[fullKey].target_files.length > 0) {
        targetPdfList = photoMap[fullKey].target_files.slice();
      }
      if (targetPdfList.length === 0) {
        const cleanIdent = identifier.replace(/_\d{2}-\d{2}$/, '');
        const baseKey = `${btp}/${category}/${cleanIdent}`;
        if (photoMap[baseKey] && Array.isArray(photoMap[baseKey].target_files) && photoMap[baseKey].target_files.length > 0) {
          targetPdfList = photoMap[baseKey].target_files.slice();
        }
      }
    }
  }

  // If specific targetPdfName was requested and mergeAll is false
  if (targetPdfName && mergeAll === false) {
    targetPdfList = [targetPdfName];
  } else if (targetPdfList.length === 0 && targetPdfName) {
    targetPdfList = [targetPdfName];
  }

  // Validate targetPdfName against rawRelPath if both are provided
  if (targetPdfName && rawRelPath) {
    const cleanRel = String(rawRelPath).replace(/\\/g, '/').replace(/^Tim_\d+\//, '');
    const parts = cleanRel.split('/');
    if (parts.length >= 3) {
      const category = parts[1];
      const identifier = parts[2];
      const cleanIdent = identifier.replace(/_\d{2}-\d{2}$/, '');
      const tObj = targets.find(t => t.file === targetPdfName);
      if (tObj) {
        const catMismatch = tObj.category && category && tObj.category.toUpperCase() !== category.toUpperCase();
        const identMismatch = tObj.identifiers && tObj.identifiers.length > 0 && !tObj.identifiers.some(id => {
          const vSet = new Set(expandIdentifierVariants(id));
          return expandIdentifierVariants(cleanIdent).some(v => vSet.has(v));
        });
        if (catMismatch || identMismatch) {
          console.log(`[remerge-single] Mismatch detected: provided pdfName '${targetPdfName}' does not match rawRelPath '${rawRelPath}' (${cleanIdent}). Re-resolving...`);
          targetPdfName = '';
          if (mergeAll === false) targetPdfList = [];
        }
      }
    }
  }

  // Fallback single file resolution if targetPdfList is still empty
  if (targetPdfList.length === 0) {
    if (!targetPdfName && rawRelPath) {
      const cleanRel = String(rawRelPath).replace(/\\/g, '/').replace(/^Tim_\d+\//, '');
      const parts = cleanRel.split('/');
      if (parts.length >= 3) {
        const btp = parts[0];
        const category = parts[1];
        const identifier = parts[2];
        const cleanIdent = identifier.replace(/_\d{2}-\d{2}$/, '');
        const cleanRadio = cleanIdent.replace(/^RADIO_/, '');
        const variants = expandIdentifierVariants(cleanIdent);
        if (cleanRadio !== cleanIdent) {
          expandIdentifierVariants(cleanRadio).forEach(v => {
            if (!variants.includes(v)) variants.push(v);
          });
        }

        const preferUnnumbered = (a, b) => {
          const aHasNum = /\s*\(\d+\)\.pdf$/i.test(a.file);
          const bHasNum = /\s*\(\d+\)\.pdf$/i.test(b.file);
          if (!aHasNum && bHasNum) return -1;
          if (aHasNum && !bHasNum) return 1;
          return a.file.localeCompare(b.file);
        };

        let candidates = targets.filter(t => {
          if (category && t.category && t.category.toUpperCase() !== category.toUpperCase()) return false;
          return t.identifiers && t.identifiers.some(id => id.toUpperCase() === cleanIdent.toUpperCase());
        });
        candidates.sort(preferUnnumbered);
        let matchedTarget = candidates[0];

        if (!matchedTarget) {
          candidates = targets.filter(t => {
            if (category && t.category && t.category.toUpperCase() !== category.toUpperCase()) return false;
            return t.identifiers && t.identifiers.some(id => variants.includes(id.toUpperCase()));
          });
          candidates.sort(preferUnnumbered);
          matchedTarget = candidates[0];
        }

        if (!matchedTarget) {
          candidates = targets.filter(t => {
            return t.identifiers && t.identifiers.some(id => variants.includes(id.toUpperCase()));
          });
          candidates.sort(preferUnnumbered);
          matchedTarget = candidates[0];
        }

        if (matchedTarget) {
          targetPdfName = matchedTarget.file;
        }

        if (!targetPdfName && fs.existsSync(PATHS.target)) {
          const targetFiles = fs.readdirSync(PATHS.target).filter(f => f.toLowerCase().endsWith('.pdf'));
          const matched = targetFiles.find(f => {
            const u = f.toUpperCase();
            if (category && !u.includes(category.toUpperCase())) return false;
            return u.includes(cleanIdent.toUpperCase());
          }) || targetFiles.find(f => {
            const u = f.toUpperCase();
            if (category && !u.includes(category.toUpperCase())) return false;
            return variants.some(v => u.includes(v.toUpperCase()));
          }) || targetFiles.find(f => {
            const u = f.toUpperCase();
            return variants.some(v => u.includes(v.toUpperCase()));
          }) || targetFiles.find(f => {
            const u = f.toUpperCase();
            return u.includes(cleanIdent.toUpperCase()) || u.includes(cleanRadio.toUpperCase());
          });
          if (matched) targetPdfName = matched;
        }
      }
    }
    if (targetPdfName) {
      targetPdfList = [targetPdfName];
    }
  }

  // Filter only existing files in PATHS.target
  targetPdfList = targetPdfList.filter(f => fs.existsSync(path.join(PATHS.target, f)));

  if (targetPdfList.length === 0) {
    return res.status(400).json({ success: false, error: 'Tidak dapat menemukan berkas target PDF yang sesuai dengan foto ini.' });
  }

  targetPdfName = targetPdfList[0];

  const pyScript = path.join(PATHS.scripts, 'merge_pdf_foto.py');
  let currentMode = mode === 'time' ? 'time' : (mode === 'coord' ? 'coord' : 'standard');
  let primaryPhotosDir = currentMode === 'time' ? PATHS.photosTime : (currentMode === 'coord' ? PATHS.photosCoord : PATHS.photosEdited);
  let primaryOutputDir = currentMode === 'time' ? PATHS.pdfMergedTime : (currentMode === 'coord' ? PATHS.pdfMergedCoord : PATHS.pdfMerged);
  let altPhotosDir = currentMode === 'time' ? PATHS.photosEdited : (currentMode === 'coord' ? PATHS.photosEdited : PATHS.photosTime);
  let altOutputDir = currentMode === 'time' ? PATHS.pdfMerged : (currentMode === 'coord' ? PATHS.pdfMerged : PATHS.pdfMergedTime);
  let altMode = 'standard';

  // Smart auto-detect if rawRelPath is provided
  if (rawRelPath) {
    if (currentMode === 'coord') {
      const hasCoord = checkPhotosExistForRel(PATHS.photosCoord, rawRelPath);
      if (hasCoord) {
        primaryPhotosDir = PATHS.photosCoord;
        primaryOutputDir = PATHS.pdfMergedCoord;
      }
    } else {
      const hasPrimary = checkPhotosExistForRel(primaryPhotosDir, rawRelPath);
      const hasAlt = checkPhotosExistForRel(altPhotosDir, rawRelPath);
      if (!hasPrimary && hasAlt) {
        sendSSEMessage({ type: 'log', line: `ℹ️ [AUTO-DETECT] Foto ditemukan di folder ${altMode === 'time' ? '04_Time' : '04_photos_edited'}. Mengalihkan ke Mode ${altMode === 'time' ? 'Time' : 'Standar'} secara otomatis.\n` });
        currentMode = altMode;
        primaryPhotosDir = altPhotosDir;
        primaryOutputDir = altOutputDir;
      }
    }
  }

  const runMergeProcess = (pDir, oDir, activeMode) => {
    return new Promise((resolve) => {
      const fileArg = targetPdfList.join(',');
      const args = [
        pyScript,
        '--file', fileArg,
        '--photos', pDir,
        '--output', oDir
      ];

      const modeLabel = activeMode === 'time' ? 'Mode Time' : (activeMode === 'coord' ? 'Mode Koordinat' : 'Mode Standar');
      sendSSEMessage({ type: 'log', line: `\n⚡ [MULTI RE-MERGE] Memproses ${targetPdfList.length} berkas PDF (${modeLabel}):\n${targetPdfList.map(f => '  • ' + f).join('\n')}\n` });

      const pyProc = spawn('python', ['-u', ...args], {
        cwd: APP_DIR,
        env: { ...process.env, PYTHONUNBUFFERED: '1', PYTHONIOENCODING: 'utf-8' }
      });

      let stdoutStr = '';
      let stderrStr = '';
      let summaryObj = null;

      const timeoutTimer = setTimeout(() => {
        try { pyProc.kill(); } catch (e) {}
        sendSSEMessage({ type: 'log', line: `⚠️ [TIMEOUT] Proses merge melebihi batas waktu (120 detik) dan dihentikan otomatis.\n` });
      }, 120000);

      pyProc.stdout.on('data', (d) => {
        const text = d.toString();
        stdoutStr += text;
        text.split('\n').forEach(l => {
          const trimmed = l.trim();
          if (!trimmed) return;
          if (trimmed.startsWith('__SUMMARY__:')) {
            try {
              summaryObj = JSON.parse(trimmed.slice(12));
            } catch (e) {}
            return;
          }
          sendSSEMessage({ type: 'log', line: trimmed });
        });
      });

      pyProc.stderr.on('data', (d) => {
        const text = d.toString();
        stderrStr += text;
        text.split('\n').forEach(l => {
          const trimmed = l.trim();
          if (trimmed) sendSSEMessage({ type: 'log', line: `[STDERR] ${trimmed}` });
        });
      });

      pyProc.on('close', (code) => {
        clearTimeout(timeoutTimer);
        resolve({ code, stdoutStr, stderrStr, summaryObj, pDir, oDir, activeMode });
      });
    });
  };

  // Run primary merge attempt
  let mergeRes = await runMergeProcess(primaryPhotosDir, primaryOutputDir, currentMode);

  // Fallback to alternate directory if photos were not found in primary
  const noPhotosFound = (mergeRes.summaryObj && mergeRes.summaryObj.status && mergeRes.summaryObj.status.includes('no matching edited photos')) ||
                        (mergeRes.stdoutStr && mergeRes.stdoutStr.includes('no matching edited photos'));

  if (mergeRes.code !== 0 && noPhotosFound) {
    sendSSEMessage({ type: 'log', line: `ℹ️ [FALLBACK] Foto tidak ditemukan di ${path.basename(primaryPhotosDir)}, mencoba memeriksa folder ${path.basename(altPhotosDir)}...\n` });
    const altRes = await runMergeProcess(altPhotosDir, altOutputDir, altMode);
    if (altRes.code === 0) {
      mergeRes = altRes;
      currentMode = altMode;
      primaryPhotosDir = altPhotosDir;
      primaryOutputDir = altOutputDir;
    }
  }

  const durationMs = Date.now() - startTime;
  if (mergeRes.code === 0) {
    sendSSEMessage({ type: 'log', line: `✅ [RE-MERGE] Selesai ${targetPdfList.length} berkas dalam ${(durationMs / 1000).toFixed(1)}s: ${targetPdfList.join(', ')}\n` });

    let outputPath = mergeRes.summaryObj && mergeRes.summaryObj.outputPath ? mergeRes.summaryObj.outputPath : '';
    let fileUrl = '';
    const outputs = (mergeRes.summaryObj && mergeRes.summaryObj.outputs) || {};
    const fileUrls = [];

    targetPdfList.forEach(fn => {
      let outP = outputs[fn] || '';
      let u = '';
      if (outP) {
        const relFromOutput = path.relative(primaryOutputDir, outP).replace(/\\/g, '/');
        const baseStatic = (currentMode === 'time') ? `/static/pdf-merged-time/${relFromOutput}` : (currentMode === 'coord' ? `/static/pdf-merged-coord/${relFromOutput}` : `/static/pdf-merged/${relFromOutput}`);
        u = `${baseStatic}?v=${Date.now()}`;
      }
      fileUrls.push({ file: fn, url: u, outputPath: outP });
    });

    if (fileUrls[0] && fileUrls[0].url) {
      fileUrl = fileUrls[0].url;
    }

    return res.json({
      success: true,
      pdfName: targetPdfList[0],
      pdfNames: targetPdfList,
      mergedCount: targetPdfList.length,
      outputPath,
      fileUrl,
      files: fileUrls,
      durationMs,
      mode: currentMode,
      summary: mergeRes.summaryObj
    });
  } else {
    sendSSEMessage({ type: 'log', line: `❌ [RE-MERGE ERROR] Gagal me-merge berkas (Code: ${mergeRes.code})\n` });

    let friendlyError = (mergeRes.stderrStr || '').trim();
    if (!friendlyError && mergeRes.stdoutStr) {
      const failMatch = mergeRes.stdoutStr.match(/❌\s*\[FAIL\]\s*(.+)/);
      if (failMatch) {
        friendlyError = failMatch[1].trim();
      } else if (mergeRes.summaryObj && mergeRes.summaryObj.status) {
        friendlyError = mergeRes.summaryObj.status;
      } else {
        friendlyError = `Proses merge gagal untuk berkas ${targetPdfName}.`;
      }
    }
    if (friendlyError.includes('no matching edited photos found')) {
      friendlyError = `Foto bertimemark untuk dokumen ini belum ditemukan di folder 04_photos_edited maupun 04_Time. Silakan jalankan Step 4 (atau Tempel Jam) terlebih dahulu.`;
    }

    return res.status(500).json({
      success: false,
      error: friendlyError,
      pdfName: targetPdfName
    });
  }
});

// Catch-all: Serve Main Dashboard UI
app.get('*', (req, res) => {
  res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  res.sendFile(path.join(PATHS.templates, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`\n==================================================`);
  console.log(`🚀 OCR Foto Timemark Portable Dashboard is running!`);
  console.log(`👉 Access URL: http://localhost:${PORT}`);
  console.log(`==================================================\n`);
});
