const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const cors = require('cors');

const app = express();
const PORT = 5000;

app.use(cors());
app.use(express.json());

const APP_DIR = __dirname;
const PATHS = {
  source: path.join(APP_DIR, '01_pdf_source'),
  target: path.join(APP_DIR, '02_pdf_target'),
  photosExport: path.join(APP_DIR, '03_photos_export'),
  photosEdited: path.join(APP_DIR, '04_photos_edited'),
  pdfMerged: path.join(APP_DIR, '05_pdf_merged'),
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

// Serve static files
app.use('/static/photos/export', express.static(PATHS.photosExport));
app.use('/static/photos/edited', express.static(PATHS.photosEdited));
app.use('/static/pdf-merged', express.static(PATHS.pdfMerged));
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
  activeClients.forEach(c => c.res.write(str));
}

// ----------------------------------------------------
// HELPER FUNCTIONS FOR METADATA & DATE RESOLUTION
// ----------------------------------------------------

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

app.get('/api/stream-logs', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

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
  step1: 'export_pdf_foto.py',
  'step1.5': 'crop_collage_photos.py',
  step2: 'extract_pdf_dates.py',
  step3: 'scheduler.py',
  step4: 'edit_timemark_ide1.py',
  step5: 'merge_pdf_foto.py'
};

app.post('/api/run-step', (req, res) => {
  const { step } = req.body;
  if (isRunning) {
    return res.status(400).json({ error: 'Pipeline is already running' });
  }

  const scriptName = STEP_SCRIPTS[step] || (step === 'all' ? 'all' : null);
  if (!scriptName) {
    return res.status(400).json({ error: 'Invalid step requested' });
  }

  isRunning = true;
  currentStepName = step;
  sendSSEMessage({ type: 'status', is_running: true, step: currentStepName });

  const runSingleScript = (script, callback) => {
    const scriptPath = path.join(PATHS.scripts, script);
    sendSSEMessage({ type: 'log', line: `\n=== Executing ${script} ===\n` });

    const pyProc = spawn('python', [scriptPath], { cwd: APP_DIR });
    activeProcess = pyProc;

    pyProc.stdout.on('data', (data) => {
      const text = data.toString();
      text.split('\n').forEach(line => {
        if (line.trim()) sendSSEMessage({ type: 'log', line });
      });
    });

    pyProc.stderr.on('data', (data) => {
      const text = data.toString();
      text.split('\n').forEach(line => {
        if (line.trim()) sendSSEMessage({ type: 'log', line: `[STDERR] ${line}` });
      });
    });

    pyProc.on('close', (code) => {
      activeProcess = null;
      if (code === 0) {
        sendSSEMessage({ type: 'log', line: `✅ ${script} finished successfully.\n` });
        if (callback) callback(null);
      } else {
        sendSSEMessage({ type: 'log', line: `❌ ${script} exited with code ${code}.\n` });
        if (callback) callback(new Error(`Exit code ${code}`));
      }
    });
  };

  if (step === 'all') {
    const queue = ['export_pdf_foto.py', 'crop_collage_photos.py', 'extract_pdf_dates.py', 'scheduler.py', 'edit_timemark_ide1.py', 'merge_pdf_foto.py'];
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
    runSingleScript(scriptName, (err) => {
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
        } else if (file.toLowerCase().endsWith('.jpg') || file.toLowerCase().endsWith('.jpeg')) {
          list.push(rel.replace(/\\/g, '/'));
        }
      });
    };
    walkSync(rootDir);
    return list;
  };

  const rawList = scanPhotos(PATHS.photosExport, false);
  const editedList = scanPhotos(PATHS.photosEdited, true);

  // Map edited photos back to raw photos for side-by-side comparison
  const gallery = [];
  const editedMap = new Map();

  editedList.forEach(rel => {
    // Rel path example: Tim_1/BTP BD/AXC/ZP 48A BOP/0.jpg
    const parts = rel.split('/');
    if (parts.length >= 2) {
      const key = parts.slice(1).join('/'); // BTP BD/AXC/ZP 48A BOP/0.jpg
      editedMap.set(key, rel);
    }
  });

  rawList.forEach(rel => {
    // Rel path example: BTP BD/AXC/ZP 48A BOP/0.jpg
    const parts = rel.split('/');
    const btp = parts[0] || 'Unknown';
    const category = parts[1] || 'General';
    const detail = parts.slice(2, -1).join('/') || 'Detail';
    const filename = parts[parts.length - 1];

    const editedRel = editedMap.get(rel);
    const group = editedRel ? editedRel.split('/')[0] : 'Tim_1';
    const meta = editedRel ? readPhotoMeta(group, rel) : null;
    const targetDateText = getTargetDateText(rel);

    gallery.push({
      rel,
      btp,
      category,
      detail,
      filename,
      rawUrl: `/static/photos/export/${rel}`,
      editedUrl: editedRel ? `/static/photos/edited/${editedRel}` : null,
      hasEdited: !!editedRel,
      targetDateText,
      lastDateText: meta ? meta.dateText : targetDateText,
      lastYPos: meta ? meta.yPos : 220,
      lastXPos: meta ? meta.xPos : 14
    });
  });

  res.json({ total: gallery.length, photos: gallery });
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

      // Save metadata for this photo
      savePhotoMeta(group, relP, {
        yPos: yPos !== undefined && yPos !== null && yPos !== '' ? parseInt(yPos) : 220,
        xPos: xPos !== undefined && xPos !== null && xPos !== '' ? parseInt(xPos) : 14,
        dateText: photoDateText,
        manualEdit: true,
        updatedAt: new Date().toISOString()
      });
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

app.get('/api/photos/analyze-misposition', (req, res) => {
  const pyScript = path.join(PATHS.scripts, 'analyzer.py');
  const pyProc = spawn('python', [pyScript], { cwd: APP_DIR });
  
  pyProc.on('close', (code) => {
    const reportFile = path.join(PATHS.logs, 'misposition_audit_report.json');
    if (fs.existsSync(reportFile)) {
      try {
        const summary = JSON.parse(fs.readFileSync(reportFile, 'utf-8'));
        return res.json(summary);
      } catch (e) {}
    }
  res.status(500).json({ error: 'Failed to generate audit report' });
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

  args.push('--files', ...filesToCrop);
  const pyProc = spawn('python', args, { cwd: APP_DIR });

  pyProc.on('close', (code) => {
    if (code === 0) {
      // Re-run Step 4 for this photo/folder
      const editScript = path.join(PATHS.scripts, 'edit_timemark_ide1.py');
      const editProc = spawn('python', [editScript, '--input', targetFolder], { cwd: APP_DIR });
      editProc.on('close', () => {
        res.json({ success: true, count: filesToCrop.length });
      });
    } else {
      res.status(500).json({ error: 'Manual crop python helper failed' });
    }
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
  if (!crops || !Array.isArray(crops)) return res.json({ success: false, error: 'No crops provided' });

  const script = path.join(PATHS.scripts, 'scan_collages_helper.py');
  const cropsJson = JSON.stringify(crops);
  const proc = spawn('python', [script, '--save-crops', '--crops-json', cropsJson, '--photos-dir', PATHS.photosExport], { cwd: APP_DIR });
  let out = '';
  let err = '';
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    res.json({ success: code === 0, stdout: out.slice(-500), stderr: err.slice(-300) });
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
  proc.stdout.on('data', d => out += d.toString());
  proc.stderr.on('data', d => err += d.toString());
  proc.on('close', code => {
    res.json({ success: code === 0, stdout: out.slice(-600), stderr: err.slice(-300) });
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
  res.sendFile(path.join(PATHS.templates, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`\n==================================================`);
  console.log(`🚀 OCR Foto Timemark Portable Dashboard is running!`);
  console.log(`👉 Access URL: http://localhost:${PORT}`);
  console.log(`==================================================\n`);
});
