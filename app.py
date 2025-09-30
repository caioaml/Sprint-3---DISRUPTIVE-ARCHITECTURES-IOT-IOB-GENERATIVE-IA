# app.py
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import sqlite3
from datetime import datetime
import os

DB = "detections.db"

def init_db():
    """Inicializa banco de dados"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS detections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        vaga_id TEXT,
        xmin REAL, ymin REAL, xmax REAL, ymax REAL,
        confidence REAL,
        class TEXT,
        placa TEXT,
        ts_send REAL,
        ts_received TEXT
    )""")
    conn.commit()
    conn.close()
    print("Banco de dados inicializado")

def insert_detection(vaga_id, bbox, conf, cls, placa, ts_send=None):
    """Insere detecção no banco"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    xmin, ymin, xmax, ymax = bbox
    c.execute("""
      INSERT INTO detections (vaga_id, xmin, ymin, xmax, ymax, confidence, class, placa, ts_send, ts_received)
      VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (vaga_id, xmin, ymin, xmax, ymax, conf, cls, placa, ts_send, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    

def latest_by_vaga():
    """Retorna última detecção de cada vaga"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
      SELECT vaga_id, xmin,ymin,xmax,ymax,confidence,class,placa,ts_received
      FROM detections
      WHERE id IN (SELECT MAX(id) FROM detections GROUP BY vaga_id)
      ORDER BY ts_received DESC
    """)
    rows = c.fetchall()
    conn.close()
    res = {}
    for r in rows:
        vaga = r[0] or "unknown"
        res[vaga] = {
            "bbox": [r[1], r[2], r[3], r[4]],
            "confidence": r[5],
            "class": r[6],
            "placa": r[7] if r[7] else "Nao identificada",
            "ts": r[8],
            "ocupada": True
        }
    return res

def get_stats():
    """Retorna estatísticas gerais"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM detections")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM detections WHERE placa IS NOT NULL")
    com_placa = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT vaga_id) FROM detections")
    vagas_ocupadas = c.fetchone()[0]
    
    c.execute("""
        SELECT placa, confidence, ts_received 
        FROM detections 
        WHERE placa IS NOT NULL 
        ORDER BY id DESC LIMIT 10
    """)
    ultimas_placas = c.fetchall()
    
    conn.close()
    return {
        "total": total,
        "com_placa": com_placa,
        "vagas_ocupadas": vagas_ocupadas,
        "total_vagas": 4,  # Total de vagas do sistema
        "ultimas_placas": ultimas_placas
    }

app = Flask(__name__)
CORS(app)
init_db()

# Template HTML do Dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MotoMap AI - Dashboard</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            margin: 0;
        }
        h1 {
            color: #4ec9b0;
            text-align: center;
            margin-bottom: 30px;
        }
        .section {
            background: #252526;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
            border-left: 4px solid #4ec9b0;
        }
        h2 {
            color: #569cd6;
            margin-top: 0;
        }
        pre {
            background: #1e1e1e;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border: 1px solid #3e3e42;
            font-size: 13px;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .stat {
            background: #252526;
            padding: 15px 25px;
            border-radius: 5px;
            border-left: 4px solid #ce9178;
            flex: 1;
            min-width: 150px;
        }
        .stat-label {
            color: #858585;
            font-size: 12px;
            margin-bottom: 5px;
        }
        .stat-value {
            color: #ce9178;
            font-size: 24px;
            font-weight: bold;
        }
        .refresh-btn {
            background: #0e639c;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 3px;
            cursor: pointer;
            font-family: inherit;
            margin-bottom: 20px;
            margin-right: 10px;
        }
        .refresh-btn:hover {
            background: #1177bb;
        }
        .clear-btn {
            background: #c00;
        }
        .clear-btn:hover {
            background: #e00;
        }
    </style>
</head>
<body>
    <h1>MotoMap AI - Dashboard</h1>
    
    <button class="refresh-btn" onclick="loadData()">Atualizar</button>
    <button class="refresh-btn clear-btn" onclick="clearData()">Limpar Dados</button>
    
    <div class="stats">
        <div class="stat">
            <div class="stat-label">TOTAL DETECCOES</div>
            <div class="stat-value" id="total">-</div>
        </div>
        <div class="stat">
            <div class="stat-label">TOTAL VAGAS</div>
            <div class="stat-value" id="total_vagas">4</div>
        </div>
        <div class="stat">
            <div class="stat-label">VAGAS OCUPADAS</div>
            <div class="stat-value" id="vagas_ocupadas">-</div>
        </div>
    </div>

    <div class="section">
        <h2>STATUS DAS VAGAS - SETOR 1</h2>
        <pre id="vagas-json">Carregando...</pre>
    </div>

    <div class="section">
        <h2>ULTIMAS DETECCOES (20)</h2>
        <pre id="detections-json">Carregando...</pre>
    </div>

    <div class="section">
        <h2>ESTATISTICAS</h2>
        <pre id="stats-json">Carregando...</pre>
    </div>
    
let intervalTime = 600000; // 10 minutos padrão

// Adicione seletor no HTML
<select onchange="changeInterval(this.value)">
    <option value="3000">3 seg</option>
    <option value="30000">30 seg</option>
    <option value="600000" selected>10 min</option>
</select>

function changeInterval(time) {
    clearInterval(autoRefresh);
    intervalTime = parseInt(time);
    autoRefresh = setInterval(loadData, intervalTime);
}

let autoRefresh = setInterval(loadData, intervalTime);

    <script>
        async function loadData() {
            try {
                const statsRes = await fetch('/api/stats');
                const stats = await statsRes.json();
                document.getElementById('stats-json').textContent = JSON.stringify(stats, null, 2);
                document.getElementById('total').textContent = stats.total || 0;
                document.getElementById('total_vagas').textContent = stats.total_vagas || 4;
                document.getElementById('vagas_ocupadas').textContent = stats.vagas_ocupadas || 0;

                const vagasRes = await fetch('/vagas');
                const vagas = await vagasRes.json();
                
                let vagasFormatado = {};
                for (let [id, data] of Object.entries(vagas)) {
                    vagasFormatado[id] = {
                        "STATUS": "OCUPADA",
                        "PLACA": data.placa || "Nao identificada",
                        "CLASSE": data.class,
                        "CONFIANCA": (data.confidence * 100).toFixed(1) + "%",
                        "TIMESTAMP": data.ts
                    };
                }
                
                document.getElementById('vagas-json').textContent = JSON.stringify(vagasFormatado, null, 2);

                const detectRes = await fetch('/detections');
                const detections = await detectRes.json();
                document.getElementById('detections-json').textContent = JSON.stringify(detections.slice(0, 20), null, 2);
            } catch (error) {
                console.error('Erro:', error);
            }
        }

        async function clearData() {
            if (!confirm('Tem certeza que deseja limpar todos os dados?')) return;
            
            try {
                await fetch('/clear', { method: 'POST' });
                alert('Dados limpos com sucesso!');
                loadData();
            } catch (error) {
                alert('Erro ao limpar dados: ' + error);
            }
        }

        loadData();
        setInterval(loadData, 3000);
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(DASHBOARD_HTML)

@app.route("/detect", methods=["POST"])  
def detect():
    """Endpoint para receber detecções"""
    data = request.json or {}
    bbox = data.get("bbox")
    vaga_id = data.get("vaga_id")
    conf = data.get("confidence", 0.0)
    cls = data.get("class", "")
    placa = data.get("placa")
    ts_send = data.get("ts")

    if not bbox or vaga_id is None:
        return jsonify({"error": "bbox e vaga_id são obrigatórios"}), 400

    insert_detection(vaga_id, bbox, conf, cls, placa, ts_send)
    return jsonify({
        "msg": "saved", 
        "vaga_id": vaga_id, 
        "placa": placa if placa else "não detectada"
    }), 201

@app.route("/vagas", methods=["GET"])
def vagas():
    """Retorna últimas detecções por vaga"""
    return jsonify(latest_by_vaga())

@app.route("/status", methods=["GET"])
def status():
    """Retorna status simplificado das vagas"""
    vagas_data = latest_by_vaga()
    status_vagas = {}
    
    for vaga_id, data in vagas_data.items():
        status_vagas[vaga_id] = {
            "ocupada": True,
            "placa": data.get("placa", "Não identificada"),
            "ts": data.get("ts")
        }
    
    return jsonify(status_vagas)

@app.route("/clear", methods=["POST"])
def clear_database():
    """Limpa todas as detecções do banco"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM detections")
    conn.commit()
    conn.close()
    return jsonify({"msg": "Banco de dados limpo"}), 200

@app.route("/detections", methods=["GET"])
def all_detections():
    """Retorna todas as detecções"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT vaga_id,xmin,ymin,xmax,ymax,confidence,class,placa,ts_send,ts_received 
        FROM detections 
        ORDER BY id DESC 
        LIMIT 200
    """)
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        "vaga_id": r[0], 
        "bbox": [r[1], r[2], r[3], r[4]],
        "confidence": r[5], 
        "class": r[6], 
        "placa": r[7] if r[7] else "Nao identificada", 
        "ts_send": r[8], 
        "ts_received": r[9]
    } for r in rows])

@app.route("/api/stats", methods=["GET"])
def stats():
    """Retorna estatísticas do sistema"""
    return jsonify(get_stats())

if __name__ == "__main__":
    print("="*50)
    print("MotoMap AI - Backend Iniciado")
    print("="*50)
    print("Dashboard: http://127.0.0.1:5000")
    print("API: http://127.0.0.1:5000/detect")
    print("="*50)
    app.run(host="0.0.0.0", port=5000, debug=True)
    
