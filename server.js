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

// Serve static files (no-cache for instant live previews)
const noCacheStatic = { maxAge: 0, etag: false, lastModified: false, setHeaders: (res) => res.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate') };
app.use('/static/photos/export', express.static(PATHS.photosExport, noCacheStatic));
app.use('/static/photos/edited', express.static(PATHS.photosEdited, noCacheStatic));
app.use('/static/photos/time', express.static(PATHS.photosTime, noCacheStatic));
app.use('/static/photos/temp', express.static(PATHS.photosTemp, noCacheStatic));
app.use('/static/logs/collage_originals', express.static(path.join(PATHS.logs, 'collage_originals'), noCacheStatic));
app.use('/static/pdf-merged', express.static(PATHS.pdfMerged));
app.use('/static/pdf-merged-time', express.static(PATHS.pdfMergedTime));
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
  'step1.5': { script: 'auto_crop_collages.py', args: [] },
  step2: { script: 'extract_pdf_dates.py', args: [] },
  step3: { script: 'scheduler.py', args: [] },
  step4: { script: 'edit_timemark_ide1.py', args: [] },
  step5: { script: 'merge_pdf_foto.py', args: [] },
  // Time pipeline steps (standalone 04_Time and 05_pdf_merged_Time)
  step4_time: { script: 'edit_photo_time_only.py', args: ['--schedule', 'schedule.json'] },
  step5_time: { script: 'merge_pdf_foto.py', args: ['--photos', './04_Time', '--output', './05_pdf_merged_Time'] }
};

app.post('/api/run-step', (req, res) => {
  const { step } = req.body;
  if (isRunning) {
    return res.status(400).json({ error: 'Pipeline is already running' });
  }

  const isAllStandard = step === 'all';
  const isAllTime = step === 'all_time';
  const stepConfig = STEP_SCRIPTS[step];

  if (!isAllStandard && !isAllTime && !stepConfig) {
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
        if (trimmed.startsWith('{"type":"stage"')) {
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
      { script: 'edit_timemark_ide1.py', args: [] },
      { script: 'merge_pdf_foto.py', args: [] }
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
      { script: 'edit_photo_time_only.py', args: ['--schedule', 'schedule.json'] },
      { script: 'merge_pdf_foto.py', args: ['--photos', './04_Time', '--output', './05_pdf_merged_Time'] }
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
    runSingleScript(stepConfig, (err) => {
      isRunning = false;
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

// ----------------------------------------------------
// 3. DUAL PHOTO GALLERY & COMPARISON APIS
// ----------------------------------------------------

app.get('/api/photos/gallery', (req, res) => {
  const scanPhotos = (rootDir, isEdited = false) => {
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

  const rawList = scanPhotos(PATHS.photosExport, false);
  const editedList = scanPhotos(PATHS.photosEdited, true);

  const gallery = [];
  const editedMap = new Map();

  editedList.forEach(rel => {
    const parts = rel.split('/');
    if (parts.length < 2) return;
    const rawRel = parts.slice(1).join('/');
    const fullPath = path.join(PATHS.photosEdited, rel);
    if (!fs.existsSync(fullPath) || !fs.statSync(fullPath).isFile()) return;
    const folder = path.dirname(fullPath);
    const hasManualMeta = fs.existsSync(path.join(folder, 'meta.json'));
    const current = editedMap.get(rawRel);
    const currentPath = current ? path.join(PATHS.photosEdited, current) : null;
    const currentHasManualMeta = currentPath && fs.existsSync(path.join(path.dirname(currentPath), 'meta.json'));
    if (!current || (hasManualMeta && !currentHasManualMeta) ||
      (hasManualMeta === currentHasManualMeta && fs.statSync(fullPath).mtimeMs >= fs.statSync(currentPath).mtimeMs)) {
      editedMap.set(rawRel, rel);
    }
  });

  rawList.forEach(rel => {
    const parts = rel.split('/');
    const btp = parts[0] || 'Unknown';
    const category = parts[1] || 'General';
    const detail = parts.slice(2, -1).join('/') || 'Detail';
    const filename = parts[parts.length - 1];
    const editedRel = editedMap.get(rel);
    const group = editedRel ? editedRel.split('/')[0] : 'Tim_1';
    const meta = editedRel ? readPhotoMeta(group, rel) : null;
    const editedPath = editedRel ? path.join(PATHS.photosEdited, editedRel) : null;
    const rawPath = path.join(PATHS.photosExport, rel);
    const editedStats = editedPath && fs.existsSync(editedPath) ? fs.statSync(editedPath) : null;
    const rawStats = fs.existsSync(rawPath) ? fs.statSync(rawPath) : null;
    let modifiedMs = 0;
    if (editedStats && Number.isFinite(editedStats.mtimeMs)) {
      modifiedMs = editedStats.mtimeMs;
    }
    if (meta && meta.updatedAt) {
      const metaMs = new Date(meta.updatedAt).getTime();
      if (Number.isFinite(metaMs) && metaMs > modifiedMs) modifiedMs = metaMs;
    }
    const modifiedAt = modifiedMs > 0 ? new Date(modifiedMs).toISOString() : (rawStats ? rawStats.mtime.toISOString() : null);
    const folderKey = `${group}/${rel.substring(0, rel.lastIndexOf('/'))}`;
    const targetDateText = getTargetDateText(rel);
    const isoDate = parseIndonesianDateToIso(targetDateText);
    const hasCropped = fs.existsSync(path.join(PATHS.photosTemp, rel));
    const croppedManifest = readJsonFile(path.join(PATHS.logs, 'auto_crop_manifest.json'), { collages: [] });
    const isCollage = hasCropped || (Array.isArray(croppedManifest.collages) && croppedManifest.collages.some(c => (c.rel_path || '').toLowerCase() === rel.toLowerCase()));

    gallery.push({
      rel, btp, category, detail, filename, timGroup: group, folderKey, modifiedAt, modifiedMs,
      folderModifiedMs: modifiedMs,
      rawUrl: `/static/photos/export/${rel}`,
      editedUrl: editedRel ? `/static/photos/edited/${editedRel}` : null,
      croppedUrl: hasCropped ? `/static/photos/temp/${rel}` : null,
      hasEdited: !!editedRel,
      hasCropped,
      isCollage,
      targetDateText,
      isoDate,
      lastDateText: meta ? meta.dateText : targetDateText,
      lastYPos: meta ? meta.yPos : 220,
      lastXPos: meta ? meta.xPos : 14
    });
  });

  res.json({ total: gallery.length, photos: gallery });
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
  const { rawRelPath, dateText, yPos, xPos, timGroup, applyToFolder } = req.body;
  if (!rawRelPath || !dateText) {
    return res.status(400).json({ error: 'rawRelPath and dateText are required' });
  }

  const group = timGroup || 'Tim_1';
  const pyScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');

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
    const photoDateText = helperCalculateDate(dateText, stem);

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
    } catch (err) {
      errors.push(`${relP}: ${err.message}`);
    }
  }

  if (errors.length > 0) {
    return res.status(500).json({ error: errors.join('; ') });
  }

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

    gallery.push({
      rel, btp, category, detail, filename, timGroup: group, folderKey, modifiedAt, modifiedMs,
      folderModifiedMs: modifiedMs,
      rawUrl: `/static/photos/export/${rel}`,
      timeUrl: timeRel ? `/static/photos/time/${timeRel}` : null,
      croppedUrl: hasCropped ? `/static/photos/temp/${rel}` : null,
      hasTimeEdited: !!timeRel,
      hasCropped,
      isCollage,
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
          if (code === 0) resolve();
          else reject(new Error(Buffer.concat(stderrChunks).toString() || `Exit code ${code}`));
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
// DAFTAR PEGAWAI (EMPLOYEE ROSTER) APIS
// ----------------------------------------------------
app.get('/api/employees', (req, res) => {
  const cfgPath = path.join(APP_DIR, 'config', 'daftar_pegawai.json');
  if (fs.existsSync(cfgPath)) {
    try {
      const data = JSON.parse(fs.readFileSync(cfgPath, 'utf-8'));
      return res.json({
        success: true,
        resor: data.resor || { nama: "FURQON SUSILO WARDOYO", nipp: "64465", jabatan: "KUPT RESOR STL 1.21 BOGOR" },
        kaur: data.kaur || [],
        pnc: data.pnc || []
      });
    } catch (e) {
      return res.status(500).json({ error: 'Gagal membaca daftar_pegawai.json' });
    }
  }
  return res.json({
    success: true,
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
  });
});

app.post('/api/employees', (req, res) => {
  const { resor, kaur, pnc } = req.body;
  if (!Array.isArray(kaur) || !Array.isArray(pnc)) {
    return res.status(400).json({ error: 'Format data tidak valid (kaur dan pnc harus array)' });
  }
  const cfgPath = path.join(APP_DIR, 'config', 'daftar_pegawai.json');
  try {
    fs.mkdirSync(path.dirname(cfgPath), { recursive: true });
    const payload = {
      resor: resor || { nama: "FURQON SUSILO WARDOYO", nipp: "64465", jabatan: "KUPT RESOR STL 1.21 BOGOR" },
      kaur,
      pnc
    };
    fs.writeFileSync(cfgPath, JSON.stringify(payload, null, 2), 'utf-8');
    return res.json({ success: true, message: 'Daftar pegawai berhasil disimpan' });
  } catch (e) {
    return res.status(500).json({ error: 'Gagal menyimpan daftar_pegawai.json: ' + e.message });
  }
});

app.get('/api/schedule/export-dinasan-excel', (req, res) => {
  const pyScript = path.join(PATHS.scripts, 'export_dinasan_excel.py');
  const pyProc = spawn('python', [pyScript], { cwd: APP_DIR });

  let stderr = '';
  pyProc.stderr.on('data', data => { stderr += data.toString(); });

  pyProc.on('close', (code) => {
    if (code !== 0) {
      return res.status(500).json({ error: `Gagal membuat Excel Dinasan: ${stderr}` });
    }
    const logFiles = fs.readdirSync(PATHS.logs)
      .filter(f => f.startsWith('DAFTAR_DINASAN_PEGAWAI_') && f.endsWith('.xlsx'));
    
    if (logFiles.length === 0) {
      return res.status(404).json({ error: 'File Excel dinasan tidak ditemukan di logs' });
    }
    logFiles.sort((a, b) => {
      return fs.statSync(path.join(PATHS.logs, b)).mtimeMs - fs.statSync(path.join(PATHS.logs, a)).mtimeMs;
    });

    const targetFile = path.join(PATHS.logs, logFiles[0]);
    res.setHeader('Content-Disposition', `attachment; filename="${logFiles[0]}"`);
    res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    const fileStream = fs.createReadStream(targetFile);
    fileStream.pipe(res);
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

      // Re-run both Step 4 (edit_timemark_ide1.py) and Step 4 Time (edit_photo_time_only.py) for this folder
      const editScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');
      const timeScript = path.join(PATHS.scripts, 'edit_photo_time_only.py');

      const runProc = (scriptPath, scriptArgs) => new Promise((resolve) => {
        const p = spawn('python', [scriptPath, ...scriptArgs], { cwd: APP_DIR });
        p.on('close', () => resolve());
        p.on('error', () => resolve());
      });

      Promise.all([
        runProc(editScript, ['--input', targetFolder]),
        runProc(timeScript, ['--input', targetFolder])
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

  // Re-run both Step 4 (edit_timemark_ide1.py) and Step 4 Time (edit_photo_time_only.py) for this folder
  const editScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');
  const timeScript = path.join(PATHS.scripts, 'edit_photo_time_only.py');

  const runProc = (scriptPath, scriptArgs) => new Promise((resolve) => {
    const p = spawn('python', [scriptPath, ...scriptArgs], { cwd: APP_DIR });
    p.on('close', () => resolve());
    p.on('error', () => resolve());
  });

  Promise.all([
    runProc(editScript, ['--input', targetFolder]),
    runProc(timeScript, ['--input', targetFolder])
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
  const { rel } = req.body;
  if (!rel) return res.json({ success: false, error: 'No rel path provided' });

  const script = path.join(PATHS.scripts, 'reexport_single_asset.py');
  const proc = spawn('python', [script, '--rel', rel, '--source-dir', PATHS.source, '--photos-dir', PATHS.photosExport, '--logs-dir', PATHS.logs], { cwd: APP_DIR });
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
  const { rel } = req.body; // e.g. "BTP BD/PTDS/MSG"
  if (!rel) return res.json({ success: false, error: 'No rel path provided' });

  let folderRel = rel;
  if (folderRel.match(/\.(jpg|png)$/i)) {
    folderRel = path.dirname(folderRel);
  }
  const inputDir = path.join(PATHS.photosExport, folderRel);
  if (!fs.existsSync(inputDir)) return res.json({ success: false, error: `Folder not found: ${inputDir}` });

  const pyArgs = ['scripts/edit_timemark_ide1.py', '--input', inputDir];
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
