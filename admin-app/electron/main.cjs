/**
 * Electron main process — MortgageSesame Admin App
 *
 * On launch:
 * 1. Spawns the FastAPI backend as a child process (looks for .venv or system python)
 * 2. Waits for backend to be ready (polls /health)
 * 3. Opens the BrowserWindow pointing at the built React app
 * 4. On quit — kills the backend process cleanly
 */

const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')
const fs = require('fs')

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const BACKEND_PORT = 8000
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`

let mainWindow = null
let backendProcess = null

/* ── Backend launcher ─────────────────────────────────────────────────── */
function getBackendDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend')
  }
  return path.join(__dirname, '..', '..', 'backend')
}

function getPythonPath(backendDir) {
  const candidates = [
    path.join(backendDir, '.venv', 'bin', 'python'),
    path.join(backendDir, '.venv', 'bin', 'python3'),
    '/usr/local/bin/python3',
    '/usr/bin/python3',
    'python3',
    'python',
  ]
  for (const p of candidates) {
    if (fs.existsSync(p)) return p
  }
  return 'python3'
}

function launchBackend() {
  const backendDir = getBackendDir()
  const python = getPythonPath(backendDir)

  console.log(`[backend] Launching from ${backendDir} using ${python}`)

  backendProcess = spawn(python, ['-m', 'uvicorn', 'main:app', '--port', String(BACKEND_PORT), '--host', '127.0.0.1'], {
    cwd: backendDir,
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
  })

  backendProcess.stdout.on('data', d => console.log('[backend]', d.toString().trim()))
  backendProcess.stderr.on('data', d => console.error('[backend]', d.toString().trim()))
  backendProcess.on('exit', code => console.log(`[backend] exited with code ${code}`))
}

function waitForBackend(retries = 30, delay = 1000) {
  return new Promise((resolve, reject) => {
    const attempt = (n) => {
      http.get(`${BACKEND_URL}/health`, res => {
        if (res.statusCode === 200) resolve()
        else if (n > 0) setTimeout(() => attempt(n - 1), delay)
        else reject(new Error('Backend did not start'))
      }).on('error', () => {
        if (n > 0) setTimeout(() => attempt(n - 1), delay)
        else reject(new Error('Backend did not start'))
      })
    }
    attempt(retries)
  })
}

/* ── Window ───────────────────────────────────────────────────────────── */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#1f1f1f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '..', 'public', 'icon.png'),
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5174')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.on('closed', () => { mainWindow = null })
}

/* ── IPC handlers ─────────────────────────────────────────────────────── */
ipcMain.handle('get-backend-url', () => BACKEND_URL)
ipcMain.handle('get-app-version', () => app.getVersion())

/* ── App lifecycle ────────────────────────────────────────────────────── */
app.whenReady().then(async () => {
  launchBackend()

  try {
    await waitForBackend()
    console.log('[app] Backend ready — opening window')
  } catch (err) {
    console.error('[app] Backend failed to start:', err.message)
    dialog.showErrorBox(
      'Backend Error',
      'MortgageSesame backend could not start.\n\nMake sure Python 3.10+ and dependencies are installed.\nRun: cd backend && pip install -r requirements.txt'
    )
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) {
    console.log('[app] Killing backend process...')
    backendProcess.kill('SIGTERM')
  }
})
