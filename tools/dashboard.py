"""LIVE BROWSER DASHBOARD for the operator's open DLMM positions. Read-only.

Serves one page on localhost that he keeps open on a monitor. It polls itself every
15s and makes the state impossible to miss:

  IN RANGE       calm green
  ABOVE range    amber, "idle, re-range" -- benign, position is 100% SOL
  BELOW floor    FULL-SCREEN RED, flashing, siren, browser notification
                 (20% of positions that end below their floor finish green)

Why a server and not a plain .html file: the Meteora API cannot be fetched from a
file:// page, and this also lets the page reuse the exact same book() logic the
terminal monitor uses, so the two can never disagree.

    python3 tools/dashboard.py [port=8787]     then open http://localhost:8787
"""
import json, os, sys, threading, time, importlib.util
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.argv = [sys.argv[0]]
_s = importlib.util.spec_from_file_location("mp", os.path.join(ROOT, "tools", "monitor_positions.py"))
mp = importlib.util.module_from_spec(_s); _s.loader.exec_module(mp)

WALLET = None
CACHE = {"t": 0, "data": None}
LOCK = threading.Lock()


def state():
    """Cached 20s so a browser refresh loop cannot hammer the API."""
    with LOCK:
        if time.time() - CACHE["t"] < 20 and CACHE["data"] is not None:
            return CACHE["data"]
    b = mp.book(WALLET)
    if b is None:
        out = {"ok": False, "error": "poll failed", "positions": []}
    else:
        pos = []
        for a, v in sorted(b.items(), key=lambda kv: kv[1]["pnl"]):
            pos.append({"pool": mp.name(a), "addr": a, "dep": v["dep"],
                        "pct": v["pct"], "oor": v["oor"], "side": v.get("side")})
        out = {"ok": True, "positions": pos,
               "dep": sum(p["dep"] for p in pos),
               "pnl_pct": (100 * sum(b[p["addr"]]["pnl"] for p in pos) /
                           max(sum(p["dep"] for p in pos), 1e-9)) if pos else 0.0}
    out["at"] = time.strftime("%H:%M:%S UTC", time.gmtime())
    with LOCK:
        CACHE["t"], CACHE["data"] = time.time(), out
    return out


PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<title>Meteoran</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0b0f0d;color:#e8f0ea;font:16px/1.5 ui-sans-serif,system-ui,sans-serif;padding:26px}
body.alarm{animation:flash .9s infinite}
@keyframes flash{0%,100%{background:#0b0f0d}50%{background:#5b1114}}
h1{font-size:15px;letter-spacing:.18em;text-transform:uppercase;color:#7f9c8c;font-weight:600}
.big{font-size:clamp(40px,9vw,92px);font-weight:800;letter-spacing:-.03em;line-height:1.05;margin:14px 0 4px}
.sub{color:#8fa89b;font-size:14px}
.card{border:1px solid #24352c;border-radius:12px;padding:18px 20px;margin-top:16px;background:#111815}
.card.ok{border-left:5px solid #3ddc91}
.card.idle{border-left:5px solid #e0a94a}
.card.bad{border-left:5px solid #ff4d4f;background:#2a1113}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:14px;flex-wrap:wrap}
.name{font-size:23px;font-weight:700}
.tag{font:600 11px/1 ui-monospace,monospace;letter-spacing:.1em;padding:6px 10px;border-radius:999px}
.t-ok{background:#11321f;color:#3ddc91}.t-idle{background:#332711;color:#e0a94a}
.t-bad{background:#4a1416;color:#ff8d8f}
.num{font:700 26px ui-monospace,monospace;font-variant-numeric:tabular-nums}
.pos{color:#3ddc91}.neg{color:#ff6b6e}
.note{margin-top:10px;font-size:14px;color:#a9bdb2}
.bad .note{color:#ffc9ca}
footer{margin-top:22px;color:#5f7468;font-size:12px}
</style></head><body>
<h1>Meteoran — live positions</h1>
<div class="big" id="hdr">…</div>
<div class="sub" id="sub"></div>
<div id="list"></div>
<footer id="foot">polling every 15s · read-only · closing is always your click</footer>
<script>
let alarming=false, actx=null;
function siren(){
  try{ actx=actx||new (window.AudioContext||window.webkitAudioContext)();
    const o=actx.createOscillator(), g=actx.createGain();
    o.connect(g); g.connect(actx.destination); o.type='sawtooth';
    const t=actx.currentTime; o.frequency.setValueAtTime(680,t);
    o.frequency.linearRampToValueAtTime(320,t+.5);
    g.gain.setValueAtTime(.22,t); g.gain.linearRampToValueAtTime(0,t+.55);
    o.start(t); o.stop(t+.6);
  }catch(e){}
}
if('Notification' in window && Notification.permission==='default') Notification.requestPermission();
function notify(t,b){ try{ if(Notification.permission==='granted') new Notification(t,{body:b,requireInteraction:true}); }catch(e){} }

async function tick(){
  let d; try{ d=await (await fetch('/api/state',{cache:'no-store'})).json(); }
  catch(e){ document.getElementById('sub').textContent='dashboard cannot reach its own server'; return; }
  const L=document.getElementById('list'); L.innerHTML='';
  if(!d.ok){ document.getElementById('hdr').textContent='POLL FAILED';
    document.getElementById('sub').textContent='State unknown — this is NOT the same as "no positions".'; return; }
  const bad=d.positions.filter(p=>p.oor&&p.side==='below');
  const idle=d.positions.filter(p=>p.oor&&p.side!=='below');
  if(!d.positions.length){
    document.getElementById('hdr').textContent='NO POSITIONS';
    document.getElementById('sub').textContent='Capital is idle. Nothing to watch.';
  } else if(bad.length){
    document.getElementById('hdr').innerHTML='<span class="neg">BELOW FLOOR</span>';
    document.getElementById('sub').textContent=bad.length+' position(s) holding the token. Only 20% of these finish green.';
  } else if(idle.length){
    document.getElementById('hdr').textContent='IDLE';
    document.getElementById('sub').textContent='Above range — no loss, but earning nothing. Re-range to restart fees.';
  } else {
    document.getElementById('hdr').innerHTML='IN RANGE <span class="'+(d.pnl_pct>=0?'pos':'neg')+'">'+(d.pnl_pct>=0?'+':'')+d.pnl_pct.toFixed(2)+'%</span>';
    document.getElementById('sub').textContent=d.dep.toFixed(3)+' SOL deployed and earning.';
  }
  for(const p of d.positions){
    const k=p.oor?(p.side==='below'?'bad':'idle'):'ok';
    const tag=k==='bad'?'BELOW FLOOR — CLOSE':(k==='idle'?'ABOVE — RE-RANGE':'IN RANGE');
    const note=k==='bad'?'You are holding the token and earning nothing. Do not wait for the bounce.'
      :(k==='idle'?'Price passed your ceiling. Position is 100% SOL and idle.'
      :'Earning fees while price stays inside your range.');
    L.insertAdjacentHTML('beforeend',
      `<div class="card ${k}"><div class="row"><span class="name">${p.pool}</span>
       <span class="tag t-${k}">${tag}</span></div>
       <div class="row" style="margin-top:8px"><span class="num">${p.dep.toFixed(3)} SOL</span>
       <span class="num ${p.pct>=0?'pos':'neg'}">${p.pct>=0?'+':''}${p.pct.toFixed(2)}%</span></div>
       <div class="note">${note}</div></div>`);
  }
  document.getElementById('foot').textContent='updated '+d.at+' · polling every 15s · read-only';
  document.title=(bad.length?'🔴 BELOW FLOOR':(idle.length?'🟠 idle':'🟢 in range'))+' — Meteoran';
  if(bad.length && !alarming){ alarming=true; document.body.classList.add('alarm');
    notify('BELOW FLOOR', bad.map(p=>p.pool+' '+p.pct.toFixed(1)+'%').join(', ')); }
  if(bad.length) siren();
  if(!bad.length && alarming){ alarming=false; document.body.classList.remove('alarm'); }
}
tick(); setInterval(tick,15000);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(state()).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json")
        else:
            body = PAGE.encode()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store"); self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    wf = os.path.join(ROOT, "data", "operator_wallet.txt")
    WALLET = open(wf).read().strip() if os.path.exists(wf) else None
    if not WALLET: sys.exit("no wallet in data/operator_wallet.txt")
    print(f"  dashboard -> http://localhost:{port}   wallet {WALLET[:8]}…")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
