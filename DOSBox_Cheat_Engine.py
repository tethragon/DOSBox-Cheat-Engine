#!/usr/bin/env python3
import http.server
import json
import os
import errno
import urllib.request
import urllib.parse
import threading
import time
import webbrowser
import socket

# ==============================================================================
# ⚠️ EDIT THE VERSION NUMBER HERE ⚠️ 
# Αλλάζεις μόνο αυτόν τον αριθμό και ενημερώνεται αυτόματα παντού στην εφαρμογή!
# ==============================================================================
APP_VERSION = "v23"
# ==============================================================================

PORT = 5000
MEM_SIZE = 0xA0000
DOSBOX_API_DEFAULT = "http://127.0.0.1:8086/api/v1/memory"

# ================== FRONTEND UI (HTML/CSS/JS) ==================
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DOSBox Cheat Engine {{APP_VERSION}}</title>
    <style>
        :root {
            --bg-color: #1e1e2e;
            --panel-bg: #2a2b3d;
            --accent-color: #00ffcc;
            --text-color: #cdd6f4;
            --border-color: #45475a;
            --danger-color: #f38ba8;
            --success-color: #a6e3a1;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        header {
            background: #181825;
            padding: 10px 20px;
            border-bottom: 2px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 { font-size: 1.2rem; color: var(--accent-color); }
        .top-bar {
            padding: 15px;
            background: var(--panel-bg);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        input, select, button {
            background-color: #313244;
            color: var(--text-color);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: 6px;
            outline: none;
            transition: all 0.2s;
        }
        input:focus, select:focus { border-color: var(--accent-color); }
        button {
            cursor: pointer;
            font-weight: bold;
            border: none;
            background: #45475a;
        }
        button:hover { background: #585b70; }
        button.primary { background: var(--accent-color); color: #11111b; }
        button.primary:hover { background: #00e6b8; }
        button.danger { background: var(--danger-color); color: #11111b; }
        
        .container {
            display: flex;
            flex-direction: column;
            flex: 1;
            padding: 15px;
            gap: 15px;
            overflow: hidden;
        }
        .panel {
            background: var(--panel-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            flex: 1;
            overflow: hidden;
        }
        .panel-header {
            padding: 10px 15px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #181825;
        }
        .table-container { flex: 1; overflow-y: auto; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px 15px; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { position: sticky; top: 0; background: #313244; z-index: 10; }
        tr { cursor: pointer; }
        tr:hover { background-color: #313244; }
        tr.selected { background-color: rgba(0, 255, 204, 0.2); }
        tr.selected:hover { background-color: rgba(0, 255, 204, 0.3); }
        
        .status-bar {
            padding: 8px 15px;
            background: #181825;
            border-top: 1px solid var(--border-color);
            font-size: 0.9rem;
            color: #a6adc8;
        }
        .modal-bg {
            display: none; position: fixed; top:0; left:0; width:100%; height:100%;
            background: rgba(0,0,0,0.7); justify-content: center; align-items: center; z-index: 100;
        }
        .modal {
            background: var(--panel-bg); padding: 20px; border-radius: 8px;
            min-width: 300px; border: 1px solid var(--accent-color);
        }
        .modal h3 { margin-bottom: 15px; color: var(--accent-color); }
        .btn-group { display: flex; gap: 10px; margin-top: 15px; justify-content: flex-end; }
    </style>
</head>
<body>

    <header>
        <h1>DOSBox Cheat Engine {{APP_VERSION}}</h1>
        <div>
            <button onclick="saveTable()">Save Table</button>
            <button onclick="document.getElementById('fileInput').click()">Load Table</button>
            <!-- Hidden file input for Load functionality -->
            <input type="file" id="fileInput" accept=".json" style="display: none;">
            <button onclick="showInstructions()">Help</button>
        </div>
    </header>

    <div class="top-bar">
        <label>API URL:</label>
        <input type="text" id="apiUrl" value="http://127.0.0.1:8086/api/v1/memory" style="width: 350px;">
        <label>Type:</label>
        <select id="dataType">
            <option value="1">8-bit (uint8)</option>
            <option value="2" selected>16-bit (uint16)</option>
            <option value="4">32-bit (uint32)</option>
        </select>
        
        <input type="number" id="searchVal" placeholder="Value" style="width: 120px;" onkeydown="if(event.key==='Enter') doSearch()">
        <button class="primary" id="btnFirst" onclick="firstScan()">First Scan</button>
        <button id="btnNext" onclick="nextScan()" disabled>Next Scan</button>
        <button onclick="resetScan()">Reset</button>
    </div>

    <div class="container">
        <div class="panel" style="flex: 1.2;">
            <div class="panel-header">
                <span>Search Results (<span id="matchCount">0</span>)</span>
                <button class="primary" onclick="addToCheatTable()">⬇ Add to Cheat Table</button>
            </div>
            <div class="table-container">
                <table id="scanTable">
                    <thead>
                        <tr>
                            <th>Address (Linear)</th>
                            <th>Address (Seg:Off)</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody id="scanBody"></tbody>
                </table>
            </div>
        </div>

        <div class="panel" style="flex: 1.8;">
            <div class="panel-header">
                <span>Cheat Table</span>
                <div style="display: flex; align-items: center; gap: 10px;">
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 0.9em; cursor: pointer;" title="Toggle background memory polling">
                        <input type="checkbox" id="autoRefresh" checked> Live Update
                    </label>
                    <button onclick="toggleFreeze()">Toggle Active (Freeze)</button>
                    <button onclick="editDesc()">Edit Desc</button>
                    <button onclick="editVal()">Edit Value</button>
                    <button class="danger" onclick="deleteCheat()">Remove</button>
                </div>
            </div>
            <div class="table-container">
                <table id="cheatTable">
                    <thead>
                        <tr>
                            <th style="width: 60px;">Active</th>
                            <th>Description</th>
                            <th>Address</th>
                            <th>Type</th>
                            <th>Value</th>
                        </tr>
                    </thead>
                    <tbody id="cheatBody"></tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="status-bar" id="statusBar">Ready. Perform First Scan.</div>

    <!-- Simple Modal for inputs -->
    <div class="modal-bg" id="modalBg">
        <div class="modal">
            <h3 id="modalTitle">Input</h3>
            <input type="text" id="modalInput" style="width: 100%;" onkeydown="if(event.key === 'Enter') confirmModal()">
            <div class="btn-group">
                <button onclick="closeModal()">Cancel</button>
                <button class="primary" onclick="confirmModal()">OK</button>
            </div>
        </div>
    </div>

    <!-- Help Modal -->
    <div class="modal-bg" id="helpModalBg">
        <div class="modal" style="max-width: 600px;">
            <h3>Instructions</h3>
            <div style="line-height: 1.6; margin-bottom: 20px; color: var(--text-color); font-size: 0.95rem;">
                <p style="color: var(--accent-color); font-weight: bold; margin-bottom: 5px;">DOSBox Cheat Engine {{APP_VERSION}}</p>
                <p style="margin-bottom: 15px;">Program Architect: George Petrakis</p>
                <ol style="margin-left: 20px; display: flex; flex-direction: column; gap: 10px;">
                    <li><strong>Requirements:</strong><br>
                        - DOSBox Staging version 0.83 or newer is REQUIRED.<br>
                        - Older versions of DOSBox or DOSBox Staging are NOT supported.
                    </li>
                    <li><strong>DOSBox Configuration:</strong><br>
                        - You must enable the web server API in your DOSBox Staging configuration file (dosbox-staging.conf).<br>
                        - Open the file, find the <code>[webserver]</code> section, and set <code>webserver_enabled = on</code>.<br>
                        - The default local address is usually http://127.0.0.1:8086.
                    </li>
                    <li><strong>Basic Usage:</strong><br>
                        - Search for a value using 'First Scan'.<br>
                        - Change the value in-game and use 'Next Scan' to narrow down the results.<br>
                        - Add addresses to the Cheat Table (bottom panel) to save, modify, or freeze them.
                    </li>
                </ol>
            </div>
            <div class="btn-group" style="justify-content: flex-end;">
                <button class="primary" onclick="document.getElementById('helpModalBg').style.display='none'">Close</button>
            </div>
        </div>
    </div>

    <!-- Confirm Modal -->
    <div class="modal-bg" id="confirmModalBg">
        <div class="modal">
            <h3 id="confirmModalTitle">Confirm</h3>
            <p id="confirmModalText" style="margin-bottom: 20px; color: var(--text-color);"></p>
            <div class="btn-group">
                <button onclick="closeConfirmModal()">Cancel</button>
                <button class="danger" onclick="executeConfirmModal()">Remove</button>
            </div>
        </div>
    </div>

<script>
    const MEM_SIZE = 0xA0000;
    let rawMemory = new Uint8Array(MEM_SIZE);
    let view = new DataView(rawMemory.buffer);
    let matches = [];
    let cheatItems = [];
    let isScanning = false;

    const scanBody = document.getElementById('scanBody');
    const cheatBody = document.getElementById('cheatBody');
    const statusBar = document.getElementById('statusBar');

    // Safe UUID generator
    function uuidv4() {
        if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Modal helpers
    let modalCallback = null;
    function openModal(title, defaultVal, callback) {
        document.getElementById('modalTitle').innerText = title;
        document.getElementById('modalInput').value = defaultVal;
        document.getElementById('modalBg').style.display = 'flex';
        modalCallback = callback;
        setTimeout(() => {
            const input = document.getElementById('modalInput');
            input.focus();
            input.select();
        }, 50);
    }
    function closeModal() { document.getElementById('modalBg').style.display = 'none'; modalCallback = null; }
    function confirmModal() {
        const val = document.getElementById('modalInput').value;
        if (modalCallback) modalCallback(val);
        closeModal();
    }

    // Confirm Modal helpers
    let confirmActionCallback = null;
    function openConfirmModal(title, text, callback) {
        document.getElementById('confirmModalTitle').innerText = title;
        document.getElementById('confirmModalText').innerText = text;
        document.getElementById('confirmModalBg').style.display = 'flex';
        confirmActionCallback = callback;
    }
    function closeConfirmModal() { 
        document.getElementById('confirmModalBg').style.display = 'none'; 
        confirmActionCallback = null; 
    }
    function executeConfirmModal() {
        if (confirmActionCallback) confirmActionCallback();
        closeConfirmModal();
    }

    function handleApiError() {
        statusBar.innerText = "Connection Error: DOSBox API not found.";
        alert("Failed to connect to DOSBox Staging.\\n\\nPlease ensure DOSBox is running and the Web Server API is enabled in your dosbox-staging.conf.\\n\\nOpening instructions for more details...");
        showInstructions();
    }

    function getStatusUrl() {
        return document.getElementById('apiUrl').value;
    }

    async function fetchMemory() {
        const url = `/api/mem?url=${encodeURIComponent(getStatusUrl())}`;
        let resp;
        try { resp = await fetch(url); } catch(e) { throw new Error("API_ERROR"); }
        if (!resp.ok) throw new Error("API_ERROR");
        const buf = await resp.arrayBuffer();
        rawMemory = new Uint8Array(buf);
        view = new DataView(rawMemory.buffer);
    }

    async function writeMemory(offset, val, size) {
        const url = `/api/mem/${hex(offset)}?url=${encodeURIComponent(getStatusUrl())}`;
        let payload;
        if (size === 1) payload = new Uint8Array([val & 0xFF]);
        else if (size === 2) { let b = new ArrayBuffer(2); new DataView(b).setUint16(0, val, true); payload = new Uint8Array(b); }
        else { let b = new ArrayBuffer(4); new DataView(b).setUint32(0, val, true); payload = new Uint8Array(b); }
        
        await fetch(url, { method: 'PUT', body: payload });
    }

    function hex(n) { return '0x' + n.toString(16).toUpperCase(); }

    function handleRowSelection(event, tr, tbody) {
        if (!event.ctrlKey && !event.metaKey && !event.shiftKey) {
            // Normal click: Deselect all others, select current
            Array.from(tbody.querySelectorAll('tr.selected')).forEach(row => row.classList.remove('selected'));
            tr.classList.add('selected');
        } else if ((event.ctrlKey || event.metaKey) && !event.shiftKey) {
            // Ctrl-click: Toggle current row
            tr.classList.toggle('selected');
        } else if (event.shiftKey) {
            // Shift-click: Range selection
            window.getSelection().removeAllRanges(); // Prevent ugly text selection
            const rows = Array.from(tbody.children);
            const targetIndex = rows.indexOf(tr);
            let lastSelectedIndex = rows.findIndex(r => r.classList.contains('last-clicked'));
            if (lastSelectedIndex === -1) lastSelectedIndex = targetIndex;
            
            const start = Math.min(lastSelectedIndex, targetIndex);
            const end = Math.max(lastSelectedIndex, targetIndex);
            
            if (!event.ctrlKey && !event.metaKey) {
                rows.forEach(r => r.classList.remove('selected'));
            }
            
            for (let i = start; i <= end; i++) {
                rows[i].classList.add('selected');
            }
        }
        
        // Remember the last clicked row for future shift-clicks
        Array.from(tbody.querySelectorAll('tr.last-clicked')).forEach(r => r.classList.remove('last-clicked'));
        tr.classList.add('last-clicked');
    }

    // --- SCAN LOGIC ---
    async function firstScan() {
        const val = parseInt(document.getElementById('searchVal').value);
        if (isNaN(val)) return alert("Invalid value");
        
        isScanning = true;
        statusBar.innerText = "Downloading memory snapshot...";
        try {
            await fetchMemory();
            const size = parseInt(document.getElementById('dataType').value);
            matches = [];
            
            for (let off = 0; off <= rawMemory.length - size; off++) {
                let v = size === 1 ? view.getUint8(off) : size === 2 ? view.getUint16(off, true) : view.getUint32(off, true);
                if (v === val) matches.push(off);
            }
            
            document.getElementById('btnNext').disabled = false;
            document.getElementById('dataType').disabled = true;
            statusBar.innerText = `First Scan complete: Found ${matches.length} addresses.`;
            renderScanTable();
        } catch (e) { handleApiError(); }
        isScanning = false;
    }

    async function nextScan() {
        if (isScanning) return;
        const val = parseInt(document.getElementById('searchVal').value);
        if (isNaN(val)) return alert("Invalid value");
        
        isScanning = true;
        statusBar.innerText = "Filtering results...";
        try {
            await fetchMemory();
            const size = parseInt(document.getElementById('dataType').value);
            matches = matches.filter(off => {
                let v = size === 1 ? view.getUint8(off) : size === 2 ? view.getUint16(off, true) : view.getUint32(off, true);
                return v === val;
            });
            statusBar.innerText = `Next Scan complete: ${matches.length} addresses remaining.`;
            renderScanTable();
        } catch (e) { handleApiError(); }
        isScanning = false;
    }

    function doSearch() {
        if (document.getElementById('btnNext').disabled) firstScan();
        else nextScan();
    }

    function resetScan() {
        matches = [];
        document.getElementById('btnNext').disabled = true;
        document.getElementById('dataType').disabled = false;
        scanBody.innerHTML = '';
        document.getElementById('matchCount').innerText = '0';
        statusBar.innerText = "Scan reset. Ready for a new First Scan.";
    }

    function renderScanTable() {
        scanBody.innerHTML = '';
        document.getElementById('matchCount').innerText = matches.length;
        const limit = Math.min(matches.length, 500);
        for (let i = 0; i < limit; i++) {
            const off = matches[i];
            const size = parseInt(document.getElementById('dataType').value);
            const v = size === 1 ? view.getUint8(off) : size === 2 ? view.getUint16(off, true) : view.getUint32(off, true);
            
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${hex(off)}</td><td>0x${(off >> 4).toString(16).toUpperCase()}:0x${(off & 0xF).toString(16).toUpperCase()}</td><td>${v}</td>`;
            tr.onclick = (e) => handleRowSelection(e, tr, scanBody);
            scanBody.appendChild(tr);
        }
    }

    // --- CHEAT TABLE LOGIC ---
    function addToCheatTable() {
        const selectedRows = scanBody.querySelectorAll('tr.selected');
        if (selectedRows.length === 0) return alert("Select addresses from search results first.");
        
        const size = parseInt(document.getElementById('dataType').value);
        selectedRows.forEach(tr => {
            const off = parseInt(tr.children[0].innerText, 16);
            if (!cheatItems.some(c => c.offset === off)) {
                cheatItems.push({
                    id: uuidv4(),
                    desc: "No description",
                    offset: off,
                    size: size,
                    frozen: false,
                    value: parseInt(tr.children[2].innerText)
                });
            }
        });
        renderCheatTable();
        statusBar.innerText = "Added to Cheat Table.";
    }

    function renderCheatTable() {
        cheatBody.innerHTML = '';
        cheatItems.forEach(c => {
            const tr = document.createElement('tr');
            tr.dataset.id = c.id;
            const active = c.frozen ? '[ X ]' : '[   ]';
            const typeStr = c.size === 1 ? '8-bit' : c.size === 2 ? '16-bit' : '32-bit';
            tr.innerHTML = `<td>${active}</td><td ondblclick="promptEditDesc('${c.id}')" title="Double-click to edit">${c.desc}</td><td>${hex(c.offset)}</td><td>${typeStr}</td><td ondblclick="promptEditVal('${c.id}')" title="Double-click to edit">${c.value}</td>`;
            tr.onclick = (e) => handleRowSelection(e, tr, cheatBody);
            cheatBody.appendChild(tr);
        });
    }

    function getSelectedCheats() {
        return Array.from(cheatBody.querySelectorAll('tr.selected')).map(tr => tr.dataset.id);
    }

    function toggleFreeze() {
        const ids = getSelectedCheats();
        if(ids.length === 0) return;
        cheatItems.forEach(c => { if (ids.includes(c.id)) c.frozen = !c.frozen; });
        renderCheatTable();
    }

    function promptEditDesc(id) {
        const c = cheatItems.find(x => x.id === id);
        if (!c) return;
        openModal('Edit Description', c.desc, (newDesc) => {
            if(newDesc) { c.desc = newDesc; renderCheatTable(); }
        });
    }

    function editDesc() {
        const ids = getSelectedCheats();
        if(ids.length > 0) promptEditDesc(ids[0]);
    }

    function promptEditVal(id) {
        const c = cheatItems.find(x => x.id === id);
        if (!c) return;
        openModal('Edit Value', c.value, async (newValStr) => {
            const newVal = parseInt(newValStr);
            if (!isNaN(newVal)) {
                c.value = newVal;
                try { await writeMemory(c.offset, newVal, c.size); } catch(e) { alert("Write error"); }
                renderCheatTable();
            }
        });
    }

    function editVal() {
        const ids = getSelectedCheats();
        if(ids.length > 0) promptEditVal(ids[0]);
    }

    function deleteCheat() {
        const ids = getSelectedCheats();
        if(ids.length === 0) return;
        
        openConfirmModal('Remove Cheat(s)', `Are you sure you want to remove ${ids.length} selected item(s)?`, () => {
            cheatItems = cheatItems.filter(c => !ids.includes(c.id));
            renderCheatTable();
        });
    }

    // --- FILE I/O (HTML5 File API - Λειτουργεί σαν Desktop App) ---
    function saveTable() {
        if (cheatItems.length === 0) return alert("Cheat table is empty.");
        
        // Δημιουργούμε το αρχείο και το κατεβάζουμε
        const dataStr = JSON.stringify(cheatItems, null, 4);
        const blob = new Blob([dataStr], {type: "application/json"});
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = "cheats.json"; // Προεπιλεγμένο όνομα αρχείου
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        statusBar.innerText = "Cheat table saved to disk.";
    }

    // Όταν ο χρήστης επιλέξει αρχείο από το κουμπί Load
    const fileInput = document.getElementById('fileInput');

    fileInput.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            try {
                const data = JSON.parse(e.target.result);
                if (Array.isArray(data)) {
                    // Μετατροπή / Sanitize δεδομένων για συμβατότητα με παλαιότερα JSON
                    cheatItems = data.map(c => ({
                        id: c.id || uuidv4(),
                        desc: String(c.desc || "No description"),
                        offset: Number(c.offset !== undefined ? c.offset : (c.address !== undefined ? c.address : 0)),
                        size: Number(c.size) || 2,
                        frozen: Boolean(c.frozen),
                        value: Number(c.value !== undefined ? c.value : 0)
                    }));
                    renderCheatTable();
                    statusBar.innerText = `Loaded ${cheatItems.length} cheats from file.`;
                } else {
                    alert("Invalid file format: Not an array.");
                }
            } catch(err) {
                alert("Error parsing JSON file: " + err.message);
            } finally {
                // Ασφαλής καθαρισμός ΜΕΤΑ την ανάγνωση για να επιτρέπεται επαναφόρτωση
                fileInput.value = '';
            }
        };
        reader.onerror = function() {
            alert("Failed to read the file.");
            fileInput.value = '';
        };
        reader.readAsText(file);
    });

    // --- BACKGROUND LOOPS ---
    setInterval(async () => {
        if (isScanning || cheatItems.length === 0) return;
        if (!document.getElementById('autoRefresh').checked) return;
        try {
            await fetchMemory();
            cheatItems.forEach(c => {
                if (!c.frozen) {
                    let v = c.size === 1 ? view.getUint8(c.offset) : c.size === 2 ? view.getUint16(c.offset, true) : view.getUint32(c.offset, true);
                    c.value = v;
                    const tr = cheatBody.querySelector(`tr[data-id="${c.id}"]`);
                    if (tr) tr.children[4].innerText = v;
                }
            });
            if (statusBar.innerText.includes("Warning:")) statusBar.innerText = "Connected to DOSBox.";
        } catch(e) {
            statusBar.innerText = "Warning: DOSBox connection lost.";
        }
    }, 1000);

    setInterval(async () => {
        const frozen = cheatItems.filter(c => c.frozen);
        for (const c of frozen) {
            try { await writeMemory(c.offset, c.value, c.size); } catch(e) {}
        }
    }, 150);

    function showInstructions() {
        document.getElementById('helpModalBg').style.display = 'flex';
    }

    // --- SHUTDOWN SIGNAL (BEACON) ---
    // Στέλνει σήμα τερματισμού στον Python server όταν κλείνει η καρτέλα
    window.addEventListener('pagehide', function() {
        navigator.sendBeacon('/api/shutdown');
    });
</script>
</body>
</html>"""

# ================== BACKEND SERVER (STANDARD LIBRARY) ==================

class ReusableHTTPServer(http.server.ThreadingHTTPServer):
    # Το allow_reuse_address λύνει το πρόβλημα του "Address already in use" στο Linux
    allow_reuse_address = True

class CheatServerHandler(http.server.BaseHTTPRequestHandler):
    
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html_output = INDEX_HTML.replace('{{APP_VERSION}}', APP_VERSION)
            self.wfile.write(html_output.encode('utf-8'))
            
        elif path == '/api/mem':
            dosbox_url = query.get('url', [DOSBOX_API_DEFAULT])[0]
            try:
                req = urllib.request.Request(f"{dosbox_url.rstrip('/')}/0/{hex(MEM_SIZE)}")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'application/octet-stream')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/shutdown':
            self.send_response(200)
            self._send_cors_headers()
            self.end_headers()
            print("\nBrowser tab closed. Shutting down server...")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path.startswith('/api/mem/'):
            offset = path.split('/api/mem/')[1]
            dosbox_url = query.get('url', [DOSBOX_API_DEFAULT])[0]
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length)
            try:
                req = urllib.request.Request(f"{dosbox_url.rstrip('/')}/{offset}", data=data, method='PUT')
                req.add_header('Content-Type', 'application/octet-stream')
                with urllib.request.urlopen(req, timeout=3) as resp:
                    self.send_response(resp.status)
                    self._send_cors_headers()
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def run_app():
    global PORT
    server = None
    
    # Δοκιμάζουμε θύρες ξεκινώντας από την προεπιλεγμένη (PORT) μέχρι να βρούμε ελεύθερη
    while server is None:
        try:
            server = ReusableHTTPServer(("127.0.0.1", PORT), CheatServerHandler)
        except OSError as e:
            if e.errno == errno.EADDRINUSE: # Cross-platform check for "Address already in use"
                print(f"Port {PORT} is in use, trying {PORT + 1}...")
                PORT += 1
            else:
                raise # Διαφορετικό σφάλμα δικτύου, σταματάμε
                
    url = f"http://127.0.0.1:{PORT}"
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)
        
    threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"Starting DOSBox Scanner Server at {url}")
    print("Press CTRL+C to stop the server.")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()

if __name__ == '__main__':
    run_app()
