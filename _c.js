
document.querySelectorAll('b.b').forEach(function(el){
  el.addEventListener('click', function(e){
    e.preventDefault();
    el.classList.toggle('on');
  });
});
(function(){
  var bAll = document.getElementById('all');
  var bNone = document.getElementById('none');
  if (bAll) bAll.onclick = function(){
    document.querySelectorAll('b.b').forEach(function(e){ e.classList.add('on'); });
  };
  if (bNone) bNone.onclick = function(){
    document.querySelectorAll('b.b').forEach(function(e){ e.classList.remove('on'); });
  };
})();

/* ================= 批注 ================= */
(function(){
  var DOC = '5f3b55e9b2b6';
  var KEY = 'pdfmask-notes::' + DOC;
  var IKEY = 'pdfmask-ink::' + DOC;
  var COLORS = ['#fff3a8','#c8f2c8','#c9e4ff','#ffd6e0','#ffe0b3','#e6d9ff'];
  var notes = [];
  try { notes = JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { notes = []; }
  var strokes = [];
  try { strokes = JSON.parse(localStorage.getItem(IKEY) || '[]') || []; } catch (e) { strokes = []; }
  function saveInk(){ try { localStorage.setItem(IKEY, JSON.stringify(strokes)); } catch (e) {} }

  function persist(){
    try { localStorage.setItem(KEY, JSON.stringify(notes)); }
    catch (e) { console.warn('批注保存失败：', e); }
  }
  function find(id){
    for (var i = 0; i < notes.length; i++) if (notes[i].id === id) return notes[i];
    return null;
  }

  function build(n){
    var el = document.createElement('div');
    el.className = 'note';
    el.setAttribute('data-id', n.id);
    el.style.background = n.color;
    el.style.left = (n.x * 100) + '%';
    el.style.top  = (n.y * 100) + '%';

    var bar = document.createElement('div');
    bar.className = 'nb';
    var dots = document.createElement('div');
    dots.className = 'dots';
    COLORS.forEach(function(c){
      var d = document.createElement('i');
      d.style.background = c;
      d.title = '换成这个颜色';
      d.addEventListener('click', function(){
        n.color = c; el.style.background = c; persist();
      });
      dots.appendChild(d);
    });
    var del = document.createElement('button');
    del.className = 'dx'; del.type = 'button'; del.textContent = '\u00d7';
    del.title = '删除这条批注';
    del.addEventListener('click', function(){ dropWithUndo(n); });
    bar.appendChild(dots);
    bar.appendChild(del);

    var body = document.createElement('div');
    body.className = 'nt';
    body.contentEditable = 'true';
    body.spellcheck = false;
    body.textContent = n.text || '';
    var timer;
    body.addEventListener('input', function(){
      n.text = body.textContent;
      clearTimeout(timer);
      timer = setTimeout(persist, 400);
    });
    body.addEventListener('blur', function(){
      n.text = body.textContent;
      if (!n.text.trim()) drop(n.id); else persist();
    });

    el.appendChild(bar);
    el.appendChild(body);

    /* 按住顶部工具条拖动 */
    var drag = null;
    bar.addEventListener('pointerdown', function(ev){
      if (ev.target.closest('.dots') || ev.target.closest('.dx')) return;
      ev.preventDefault();
      var page = el.closest('.page');
      var pr = page.getBoundingClientRect();
      var nr = el.getBoundingClientRect();
      drag = { ox: ev.clientX - nr.left, oy: ev.clientY - nr.top, page: page, pr: pr, bar: bar };
      bar.setPointerCapture(ev.pointerId);
    });
    bar.addEventListener('pointermove', function(ev){
      if (!drag) return;
      var x = ev.clientX - drag.pr.left - drag.ox;
      var y = ev.clientY - drag.pr.top - drag.oy;
      x = Math.max(0, Math.min(drag.pr.width - 60, x));
      y = Math.max(0, Math.min(drag.pr.height - 26, y));
      el.style.left = x + 'px';
      el.style.top = y + 'px';
    });
    bar.addEventListener('pointerup', function(){
      if (!drag) return;
      var pr = drag.pr;
      var r = el.getBoundingClientRect();
      n.x = Math.max(0, Math.min(0.95, (r.left - pr.left) / pr.width));
      n.y = Math.max(0, Math.min(0.95, (r.top - pr.top) / pr.height));
      el.style.left = (n.x * 100) + '%';
      el.style.top = (n.y * 100) + '%';
      drag = null;
      persist();
    });

    return el;
  }

  function add(n, focus){
    var page = document.getElementById('p' + n.page);
    if (!page) return;
    var el = build(n);
    page.appendChild(el);
    if (focus) setTimeout(function(){
      var t = el.querySelector('.nt');
      t.focus();
      var s = window.getSelection && window.getSelection();
      if (s) s.removeAllRanges();
    }, 30);
  }

  function dropWithUndo(n){
    var copy = JSON.parse(JSON.stringify(n));
    drop(copy.id);
    pushOp({
      do: function(){ drop(copy.id); },
      undo: function(){
        if (!find(copy.id)) { notes.push(copy); add(copy, false); persist(); }
      }
    });
  }

  function drop(id){
    var n = find(id);
    if (n) { notes.splice(notes.indexOf(n), 1); persist(); }
    var el = document.querySelector('.note[data-id="' + id + '"]');
    if (el) el.remove();
  }

  function redraw(){
    document.querySelectorAll('.note').forEach(function(e){ e.remove(); });
    notes.forEach(function(n){ add(n, false); });
  }

  /* 双击新建（双击到文字上时交给「涂黑」菜单处理） */
  var mainEl = document.querySelector('main');
  if (mainEl) mainEl.addEventListener('dblclick', function(e){
    if (document.body.classList.contains('draw')) return;
    if (e.target.closest('.note')) return;
    var s = window.getSelection && window.getSelection();
    if (s && !s.isCollapsed) return;          // 选中了词 → 让划选菜单出场
    var page = e.target.closest('.page');
    if (!page) return;
    var pr = page.getBoundingClientRect();
    var n = {
      id: 'n' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      page: parseInt(page.id.slice(1), 10),
      x: Math.min(0.7, Math.max(0.01, (e.clientX - pr.left) / pr.width)),
      y: Math.min(0.93, Math.max(0.01, (e.clientY - pr.top) / pr.height)),
      color: COLORS[0],
      text: ''
    };
    notes.push(n);
    persist();
    add(n, true);
    pushOp({
      do: function(){ if (!find(n.id)) { notes.push(n); add(n, false); persist(); } },
      undo: function(){ drop(n.id); }
    });
    var s = window.getSelection && window.getSelection();
    if (s) s.removeAllRanges();
    e.preventDefault();
  });

  /* 导出 / 导入 / 清空 */
  var bExp = document.getElementById('exp');
  var bImp = document.getElementById('imp');
  var bClr = document.getElementById('clr');
  var fImp = document.getElementById('impf');
  if (bExp) bExp.onclick = function(){
    if (!notes.length && !strokes.length && !Object.keys(overrides).length) {
      alert('还没有批注、涂鸦或手动涂黑'); return;
    }
    var d = new Date();
    var name = '批注_' + d.getFullYear() + ('0' + (d.getMonth() + 1)).slice(-2) + ('0' + d.getDate()).slice(-2) + '.json';
    var a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(
      { version: 3, notes: notes, strokes: strokes, masks: overrides }, null, 1)],
      { type: 'application/json' }));
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
  if (bImp) bImp.onclick = function(){ if (fImp) fImp.click(); };
  if (fImp) fImp.addEventListener('change', function(e){
    var f = e.target.files && e.target.files[0];
    if (!f) return;
    var fr = new FileReader();
    fr.onload = function(){
      var data, addNotes = [], addInk = [], addMasks = null;
      try { data = JSON.parse(fr.result); } catch (err) { alert('这个文件不是有效的备份'); return; }
      if (Array.isArray(data)) addNotes = data;                 // 旧版：只有批注
      else if (data && typeof data === 'object') {
        if (Array.isArray(data.notes)) addNotes = data.notes;
        if (Array.isArray(data.strokes)) addInk = data.strokes;
        if (data.masks && typeof data.masks === 'object') addMasks = data.masks;
      } else { alert('这个文件不是有效的备份'); return; }
      var n = 0;
      addNotes.forEach(function(x){
        if (!x || !x.id || !x.page) return;
        var old = find(x.id);
        if (old) { old.x = x.x; old.y = x.y; old.color = x.color; old.text = x.text; }
        else notes.push(x);
        n++;
      });
      var k = 0;
      addInk.forEach(function(x){
        if (!x || !x.p || !x.pts || !x.pts.length) return;
        if (x.id && strokes.some(function(s){ return s.id === x.id; })) return;
        strokes.push(x);
        k++;
      });
      var mk = 0;
      if (addMasks) {
        Object.keys(addMasks).forEach(function(key){
          overrides[key] = addMasks[key];
          mk++;
        });
        saveMasks();
        applyOverrides();
      }
      persist();
      saveInk();
      redraw();
      repaintAll();
      ensureVisible();
      alert('已导入：批注 ' + n + ' 条，涂鸦 ' + k + ' 笔'
            + (mk ? '，手动涂黑 ' + mk + ' 段' : ''));
    };
    fr.readAsText(f);
    e.target.value = '';
  });
  if (bClr) bClr.onclick = function(){
    if (!notes.length) { alert('还没有批注'); return; }
    if (!confirm('确定删除全部 ' + notes.length + ' 条批注？删除后无法恢复')) return;
    notes = [];
    persist();
    redraw();
  };

  /* ================= 手绘涂鸦 ================= */
  var PKEY = 'pdfmask-pen::' + DOC;
  var penPref = { on: false, c: '#e23b2e', w: 0.0035 };
  try {
    var savedPen = JSON.parse(localStorage.getItem(PKEY) || 'null');
    if (savedPen && typeof savedPen === 'object'){
      penPref.on = !!savedPen.on;
      if (savedPen.c) penPref.c = savedPen.c;
      if (savedPen.w) penPref.w = savedPen.w;
    }
  } catch (e) {}
  var inkColor = penPref.c;
  var inkWidth = penPref.w;
  var eraserOn = false;
  var drawOn = false;
  var inkTimer = null;
  function savePenPref(){
    try { localStorage.setItem(PKEY, JSON.stringify({ on: drawOn, c: inkColor, w: inkWidth })); } catch (e) {}
  }

  function pnoOf(el){ return parseInt(el.id.slice(1), 10); }
  function newInkId(){ return 'i' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function hasInk(pno){
    for (var i = 0; i < strokes.length; i++) if (strokes[i].p === pno) return true;
    return false;
  }
  function laterSaveInk(){ clearTimeout(inkTimer); inkTimer = setTimeout(saveInk, 500); }

  function paint(cv, el){
    var r = el.getBoundingClientRect();
    if (r.width < 4) return;
    var dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(r.width * dpr);
    cv.height = Math.round(r.height * dpr);
    cv.style.width = r.width + 'px';
    cv.style.height = r.height + 'px';
    var ctx = cv.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, r.width, r.height);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    var pno = pnoOf(el);
    for (var i = 0; i < strokes.length; i++){
      var s = strokes[i];
      if (s.p !== pno || !s.pts || s.pts.length < 4) continue;
      ctx.strokeStyle = s.c;
      ctx.lineWidth = Math.max(1, s.w * r.width);
      ctx.beginPath();
      ctx.moveTo(s.pts[0] * r.width, s.pts[1] * r.height);
      for (var j = 2; j < s.pts.length; j += 2){
        ctx.lineTo(s.pts[j] * r.width, s.pts[j + 1] * r.height);
      }
      ctx.stroke();
    }
    cv.dataset.w = String(Math.round(r.width));
  }

  function repaintAll(){
    document.querySelectorAll('.page canvas.ink').forEach(function(cv){
      if (cv.parentNode) paint(cv, cv.parentNode);
    });
  }

  function ready(el, force){
    bindPageInk(el);                     // 事件先挂上（幂等），和有没有画布无关
    var pno = pnoOf(el);
    var cv = el.querySelector('canvas.ink');
    if (!drawOn && !force && !hasInk(pno)){
      if (cv) cv.remove();
      return null;
    }
    if (!cv){
      cv = document.createElement('canvas');
      cv.className = 'ink';
      el.appendChild(cv);
    }
    bindPageInk(el);
    paint(cv, el);           /* 每次进入视口都重绘，保证撤销/导入后画面正确 */
    return cv;
  }

  function ensureVisible(){
    document.querySelectorAll('.page').forEach(function(el){
      var r = el.getBoundingClientRect();
      if (r.bottom > -320 && r.top < window.innerHeight + 320) ready(el);
    });
  }

  function currentPage(){
    var mid = window.innerHeight / 2, best = null, bestD = 1e9;
    document.querySelectorAll('.page').forEach(function(el){
      var r = el.getBoundingClientRect();
      if (r.bottom < 70 || r.top > window.innerHeight - 70) return;
      var d = Math.abs((r.top + r.bottom) / 2 - mid);
      if (d < bestD){ bestD = d; best = el; }
    });
    return best;
  }

  /* ---- 操作栈：画 / 擦 / 清页 / 涂黑 / 批注 都能撤销（Ctrl+Z）和重做（Ctrl+Y） ---- */
  var opStack = [], redoStack = [];

  function pushOp(op){
    opStack.push(op);
    if (opStack.length > 150) opStack.shift();
    redoStack.length = 0;                 // 有了新动作，redo 作废
  }
  function refreshAfterOp(){
    saveInk();
    saveMasks();
    repaintAll();
    ensureVisible();
  }
  function doUndo(){
    var op = opStack.pop();
    if (!op) return false;
    try { op.undo(); } catch (e) {}
    redoStack.push(op);
    refreshAfterOp();
    return true;
  }
  function doRedo(){
    var op = redoStack.pop();
    if (!op) return false;
    try { op.do(); } catch (e) {}
    opStack.push(op);
    refreshAfterOp();
    return true;
  }

  /// 绘制事件绑在「页」上：这样画笔模式、Ctrl+拖动都能触发同一个入口
  function bindPageInk(el){
    if (el._inkBound) return;
    el._inkBound = true;
    var cur = null, rect = null, cv = null;

    function pos(ev){
      return { x: (ev.clientX - rect.left) / rect.width,
               y: (ev.clientY - rect.top) / rect.height };
    }
    function allowed(e){
      if (e.button !== 0) return false;
      if (e.target.closest && (e.target.closest('.note') || e.target.closest('#pen'))) return false;
      return drawOn || e.ctrlKey;                    // 画笔模式 或 按住 Ctrl
    }
    function eraseAt(x, y){
      var pno = pnoOf(el);
      var rad = Math.max(0.014, inkWidth * 4);
      for (var i = strokes.length - 1; i >= 0; i--){
        var s = strokes[i];
        if (s.p !== pno) continue;
        for (var j = 0; j < s.pts.length; j += 2){
          var dx = s.pts[j] - x, dy = s.pts[j + 1] - y;
          if (dx * dx + dy * dy < rad * rad){
            var gone = strokes.splice(i, 1)[0];
            pushOp({
              do: function(){ strokes = strokes.filter(function(q){ return q.id !== gone.id; }); },
              undo: function(){
                if (!strokes.some(function(q){ return q.id === gone.id; })) strokes.push(gone);
              }
            });
            saveInk();
            paint(cv, el);
            return;
          }
        }
      }
    }

    el.addEventListener('pointerdown', function(e){
      if (!allowed(e)) return;
      if (document.body.classList.contains('quickdraw') && !drawOn && !e.ctrlKey) return;
      cv = ready(el, true);
      if (!cv) return;
      e.preventDefault();
      if (!drawOn) document.body.classList.add('quickdraw');
      try { el.setPointerCapture(e.pointerId); } catch (err) {}
      rect = cv.getBoundingClientRect();
      var p = pos(e);
      if (eraserOn){ cur = null; eraseAt(p.x, p.y); return; }
      var st = { id: newInkId(), p: pnoOf(el), c: inkColor, w: inkWidth, pts: [p.x, p.y] };
      cur = st;
      strokes.push(st);
      pushOp({
        do: function(){
          if (!strokes.some(function(s){ return s.id === st.id; })) strokes.push(st);
        },
        undo: function(){
          strokes = strokes.filter(function(s){ return s.id !== st.id; });
        }
      });
      var ctx = cv.getContext('2d');
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.strokeStyle = st.c;
      ctx.lineWidth = Math.max(1, st.w * rect.width);
      ctx.beginPath();
      ctx.moveTo(p.x * rect.width, p.y * rect.height);
      ctx.lineTo(p.x * rect.width + 0.02, p.y * rect.height);
      ctx.stroke();
    });

    el.addEventListener('pointermove', function(e){
      if (!rect || !cv) return;
      var p = pos(e);
      if (eraserOn){
        if (e.buttons) eraseAt(p.x, p.y);
        return;
      }
      if (!cur) return;
      var n = cur.pts.length;
      var lx = cur.pts[n - 2], ly = cur.pts[n - 1];
      if (Math.abs(p.x - lx) < 0.0009 && Math.abs(p.y - ly) < 0.0009) return;
      var ctx = cv.getContext('2d');
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.strokeStyle = cur.c;
      ctx.lineWidth = Math.max(1, cur.w * rect.width);
      ctx.beginPath();
      ctx.moveTo(lx * rect.width, ly * rect.height);
      ctx.lineTo(p.x * rect.width, p.y * rect.height);
      ctx.stroke();
      cur.pts.push(p.x, p.y);
      laterSaveInk();
    });

    function end(){
      if (cur){ cur = null; saveInk(); }
      rect = null;
    }
    el.addEventListener('pointerup', end);
    el.addEventListener('pointercancel', end);
  }

  function setEraser(on){
    eraserOn = on;
    document.body.classList.toggle('eraser', on);
    var eb = document.getElementById('eraserBtn');
    if (eb) eb.classList.toggle('act', on);
  }

  function setDraw(on){
    drawOn = on;
    document.body.classList.toggle('draw', on);
    var b = document.getElementById('penBtn');
    if (b) b.classList.toggle('act', on);
    if (!on){
      setEraser(false);
      document.body.classList.remove('quickdraw');
      document.querySelectorAll('.page canvas.ink').forEach(function(cv){
        if (!hasInk(pnoOf(cv.parentNode))) cv.remove();
      });
    }
    savePenPref();
    ensureVisible();
  }

  var penBtn = document.getElementById('penBtn');
  if (penBtn) penBtn.onclick = function(){ setDraw(!drawOn); };
  var penX = document.getElementById('exitPen2');
  if (penX) penX.onclick = function(){ setDraw(false); };

  document.querySelectorAll('#pen .pc').forEach(function(d){
    d.addEventListener('click', function(){
      inkColor = d.dataset.c;
      document.querySelectorAll('#pen .pc').forEach(function(x){ x.classList.remove('act'); });
      d.classList.add('act');
      setEraser(false);
      savePenPref();
    });
  });
  document.querySelectorAll('#pen .pw').forEach(function(b){
    b.addEventListener('click', function(){
      inkWidth = parseFloat(b.dataset.w);
      document.querySelectorAll('#pen .pw').forEach(function(x){ x.classList.remove('act'); });
      b.classList.add('act');
      setEraser(false);
      savePenPref();
    });
  });
  var eraserBtn = document.getElementById('eraserBtn');
  if (eraserBtn) eraserBtn.onclick = function(){ setEraser(!eraserOn); };

  var undoInk = document.getElementById('undoInk');
  if (undoInk) undoInk.onclick = function(){
    if (!doUndo()) alert('没有可撤销的操作了');
  };
  var redoInk = document.getElementById('redoInk');
  if (redoInk) redoInk.onclick = function(){
    if (!doRedo()) alert('没有可重做的操作了');
  };
  var clrInk = document.getElementById('clrInk');
  if (clrInk) clrInk.onclick = function(){
    var el = currentPage();
    if (!el) return;
    var pno = pnoOf(el);
    if (!hasInk(pno)){ alert('第 ' + pno + ' 页还没有手绘'); return; }
    if (!confirm('清掉第 ' + pno + ' 页的手绘？（可按 Ctrl+Z 撤回）')) return;
    var removed = strokes.filter(function(s){ return s.p === pno; });
    var keep = strokes.filter(function(s){ return s.p !== pno; });
    pushOp({
      do: function(){ strokes = keep.slice(); },
      undo: function(){ strokes = keep.concat(removed); }
    });
    strokes = keep.slice();
    saveInk();
    repaintAll();
  };
  var clrInkAll = document.getElementById('clrInkAll');
  if (clrInkAll) clrInkAll.onclick = function(){
    if (!strokes.length){ alert('还没有手绘'); return; }
    if (!confirm('清掉全部 ' + strokes.length + ' 笔手绘？（可按 Ctrl+Z 撤回）')) return;
    var all = strokes.slice();
    pushOp({
      do: function(){ strokes = []; },
      undo: function(){ strokes = all.slice(); }
    });
    strokes = [];
    saveInk();
    repaintAll();
    ensureVisible();
  };

  /* Ctrl+Z 撤销 / Ctrl+Y（或 Ctrl+Shift+Z）重做 —— 涂黑、批注、手绘全都算 */
  document.addEventListener('keydown', function(e){
    if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
    var ae = document.activeElement;
    if (ae && (ae.isContentEditable || ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
    var k = (e.key || '').toLowerCase();
    if (k === 'z' && !e.shiftKey){
      if (!opStack.length) return;
      e.preventDefault(); doUndo();
    } else if (k === 'y' || (k === 'z' && e.shiftKey)){
      if (!redoStack.length) return;
      e.preventDefault(); doRedo();
    }
  });

  /* ================= 划选涂黑：把选中的文字盖住 / 放开 ================= */
  var MKEY = 'pdfmask-mask::' + DOC;
  var FMT = ["仿宋 13.6", "仿宋 13.6 下划线", "黑体 13.6", "黑体 15.9"] || [];          // 格式名表，下标就是元素的 data-f
  var overrides = {};
  try { overrides = JSON.parse(localStorage.getItem(MKEY) || '{}') || {}; } catch (e) { overrides = {}; }
  function saveMasks(){
    try { localStorage.setItem(MKEY, JSON.stringify(overrides)); } catch (e) {}
  }

  function blockKey(el){
    var page = el.closest('.page');
    if (!page) return '';
    return 'p' + page.id.slice(1) + '-' + el.getAttribute('data-b');
  }

  /** 读回段落的字符（含每个字当前是否被遮），填空横线记成 hole */
  function readBlock(el){
    var out = [];
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, null);
    var node;
    while ((node = walker.nextNode())) {
      if (node.nodeType === 1) {
        if (node.tagName === 'I' && node.classList.contains('cl')) {
          out.push({ hole: true, w: node.style.width });
        }
        continue;                       // 元素本身不是字符，字符在它的文本子节点里
      }
      var holder = node.parentNode;
      var masked = !!(holder && holder.closest && holder.closest('b.b'));
      var fmtEl = holder && holder.closest ? holder.closest('[data-f]') : null;
      var fid = fmtEl ? (parseInt(fmtEl.getAttribute('data-f'), 10) || 0) : 0;
      var text = node.nodeValue;
      for (var i = 0; i < text.length; i++) {
        out.push({ c: text[i], masked: masked, f: fid });
      }
    }
    return out;
  }

  function escHtml(s){
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /** 把字符写回段落（按「格式 + 是否遮住」分组，规则和生成时一致） */
  function writeBlock(el, chars){
    var out = [], buf = '', cur = null;
    function flush(){
      if (!buf) return;
      var fid = cur[0], masked = cur[1];
      if (!masked) {
        out.push(fid === 0 ? escHtml(buf)
                           : '<span data-f="' + fid + '">' + escHtml(buf) + '</span>');
      } else {
        var core = buf.replace(/^ +| +$/g, '');
        if (!core) { out.push(escHtml(buf)); }
        else {
          var lead = buf.length - buf.replace(/^ +/, '').length;
          var trail = buf.length - buf.replace(/ +$/, '').length;
          out.push(buf.slice(0, lead)
                   + '<b class="b"' + (fid ? ' data-f="' + fid + '"' : '') + '>'
                   + escHtml(core) + '</b>'
                   + buf.slice(buf.length - trail));
        }
      }
      buf = '';
    }
    for (var i = 0; i < chars.length; i++) {
      var ch = chars[i];
      if (ch.hole) {
        flush();
        out.push('<i class="cl" style="width:' + (ch.w || '2em') + '"></i>');
        continue;
      }
      var key = [ch.f || 0, ch.masked ? 1 : 0];
      if (cur === null) { cur = key; }
      else if (key[0] !== cur[0] || key[1] !== cur[1]) { flush(); cur = key; }
      buf += ch.c;
    }
    flush();
    el.innerHTML = out.join('');
  }

  /** 可视字符序号 → chars 数组下标（跳过填空横线） */
  function visToArr(chars, vis){
    var v = 0;
    for (var i = 0; i < chars.length; i++) {
      if (chars[i].hole) continue;
      if (v === vis) return i;
      v++;
    }
    return chars.length;
  }

  /** 节点内某个位置对应的「可视字符偏移」 */
  function offsetOf(el, container, offset){
    if (!container || container.nodeType !== 3) return -1;
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    var total = 0, node;
    while ((node = walker.nextNode())) {
      if (node === container) return total + offset;
      total += node.nodeValue.length;
    }
    return -1;
  }

  /** 兜底：边界落在元素节点上（例如三击选中整段）时按相交的文本节点取整 */
  function fallbackSpan(el, range){
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null);
    var idx = 0, start = -1, end = -1, node;
    while ((node = walker.nextNode())) {
      var len = node.nodeValue.length;
      if (range.intersectsNode(node)) {
        if (start < 0) start = idx;
        end = idx + len;
      }
      idx += len;
    }
    return start < 0 ? null : { start: start, end: end };
  }

  function spanInBlock(el, range){
    var s = offsetOf(el, range.startContainer, range.startOffset);
    var e = offsetOf(el, range.endContainer, range.endOffset);
    if (s >= 0 && e > s) return { start: s, end: e };
    return fallbackSpan(el, range);
  }

  /* ---- 浮动小菜单 ---- */
  var selMenu = document.createElement('div');
  selMenu.id = 'selmenu';
  selMenu.innerHTML = '<span class="fmtlabel"></span>'
                    + '<button data-act="mask">涂黑</button>'
                    + '<button data-act="unmask">取消涂黑</button>'
                    + '<span class="vsep"></span>'
                    + '<button data-act="fmask" title="全文所有相同格式的文字一起涂黑">同格式涂黑</button>'
                    + '<button data-act="funmask" title="全文所有相同格式的文字一起取消涂黑">同格式取消</button>';
  document.body.appendChild(selMenu);

  function hideMenu(){ selMenu.classList.remove('show'); }

  function showMenu(rect, fmtId){
    selMenu.classList.add('show');
    var lb = selMenu.querySelector('.fmtlabel');
    if (lb) {
      var name = (typeof fmtId === 'number' && FMT[fmtId]) ? FMT[fmtId] : '';
      lb.textContent = name;
      lb.style.display = name ? '' : 'none';
    }
    var top = rect.top - 42;
    if (top < 8) top = rect.bottom + 10;
    selMenu.style.top = Math.max(6, top) + 'px';
    selMenu.style.left = Math.min(window.innerWidth - 80,
                                  Math.max(80, rect.left + rect.width / 2)) + 'px';
  }

  function selectionInfo(){
    var sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
    var range = sel.getRangeAt(0);
    var startEl = range.startContainer.nodeType === 1
      ? range.startContainer : range.startContainer.parentNode;
    var endEl = range.endContainer.nodeType === 1
      ? range.endContainer : range.endContainer.parentNode;
    if (!startEl || !endEl || !startEl.closest || !endEl.closest) return null;
    if (startEl.closest('.note') || endEl.closest('.note')) return null;
    if (!startEl.closest('.page') || !endEl.closest('.page')) return null;
    var rect = range.getBoundingClientRect();
    if (!rect || (!rect.width && !rect.height)) return null;
    var holder = range.startContainer.nodeType === 1
      ? range.startContainer : range.startContainer.parentNode;
    var fmtEl = holder && holder.closest ? holder.closest('[data-f]') : null;
    var fmtId = fmtEl ? (parseInt(fmtEl.getAttribute('data-f'), 10) || 0) : 0;
    return { range: range, rect: rect, fmt: fmtId };
  }

  document.addEventListener('selectionchange', function(){
    if (document.body.classList.contains('draw')) { hideMenu(); return; }
    if (altDown) { hideMenu(); return; }        // Alt 模式：松手直接生效，不弹菜单
    var info = selectionInfo();
    if (info) showMenu(info.rect, info.fmt); else hideMenu();
  });

  selMenu.addEventListener('mousedown', function(e){ e.preventDefault(); });  // 别把选区点没了
  selMenu.addEventListener('click', function(e){
    var act = e.target.getAttribute && e.target.getAttribute('data-act');
    if (!act) return;
    var info = selectionInfo();
    hideMenu();
    if (!info) return;
    if (act === 'mask' || act === 'unmask') {
      applyMask(info.range, act === 'mask');
      return;
    }
    var n = applyFormatMask(info.fmt, act === 'fmask');
    var sel = window.getSelection();
    if (sel) sel.removeAllRanges();
    var name = FMT[info.fmt] || '该格式';
    toast(n ? ('已把 ' + n + ' 段「' + name + '」' + (act === 'fmask' ? '涂黑' : '取消涂黑'))
            : ('全文没有其他「' + name + '」的文字'));
  });

  /* ---- 按住 Alt 划选 = 直接涂黑 / 取消（选区里过半已遮就放开，否则涂黑） ---- */
  var altDown = false;
  document.addEventListener('keydown', function(e){ if (e.key === 'Alt') altDown = true; });
  document.addEventListener('keyup', function(e){ if (e.key === 'Alt') altDown = false; });
  window.addEventListener('blur', function(){ altDown = false; });

  function altApply(range){
    var masked = 0, total = 0;
    document.querySelectorAll('.page [data-b]').forEach(function(el){
      if (!range.intersectsNode(el)) return;
      var span = spanInBlock(el, range);
      if (!span || span.end <= span.start) return;
      var chars = readBlock(el);
      var a = visToArr(chars, span.start), b = visToArr(chars, span.end);
      for (var i = a; i < b; i++) {
        if (chars[i].hole) continue;
        total++;
        if (chars[i].masked) masked++;
      }
    });
    if (!total) return;
    var wantMask = (masked * 2 < total);        // 还没遮住一半 → 涂黑；反之放开
    applyMask(range, wantMask);
    var sel = window.getSelection();
    if (sel) sel.removeAllRanges();
    toast('已把选中的 ' + total + ' 个字' + (wantMask ? '涂黑' : '取消涂黑') + '（可 Ctrl+Z 撤销）');
  }

  document.addEventListener('pointerdown', function(e){
    if (e.altKey) altDown = true;        // 只按 Alt 没被 keydown 收到时兜底
  }, true);

  document.addEventListener('pointerup', function(e){
    if (!altDown && !e.altKey) { altDown = false; return; }
    if (document.body.classList.contains('draw')) { altDown = false; return; }
    var info = selectionInfo();
    if (info) altApply(info.range);
    altDown = false;                     // 用完即弃，避免影响后续点击
  });

  function applyMask(range, mask){
    var targets = [];
    document.querySelectorAll('.page [data-b]').forEach(function(el){
      if (range.intersectsNode(el)) targets.push(el);
    });
    if (!targets.length) return;

    var changes = [];
    targets.forEach(function(el){
      var span = spanInBlock(el, range);
      if (!span || span.end <= span.start) return;
      var chars = readBlock(el);
      var before = bitsOf(chars);
      var a = visToArr(chars, span.start);
      var b = visToArr(chars, span.end);
      for (var i = a; i < b; i++) {
        if (!chars[i].hole) chars[i].masked = mask;
      }
      writeBlock(el, chars);
      var after = bitsOf(chars);
      if (before === after) return;
      var key = blockKey(el);
      overrides[key] = after;
      changes.push({ key: key, el: el, before: before, after: after });
    });
    if (!changes.length) return;
    pushMaskOp(changes);
    var sel = window.getSelection();
    if (sel) sel.removeAllRanges();
  }

  /** 按格式批量涂黑 / 取消：全文所有同格式的文字一起处理 */
  function applyFormatMask(fmtId, mask){
    var changes = [];
    document.querySelectorAll('.page [data-b]').forEach(function(el){
      var chars = readBlock(el);
      var before = bitsOf(chars);
      var hit = false;
      for (var i = 0; i < chars.length; i++) {
        if (chars[i].hole) continue;
        if ((chars[i].f || 0) === fmtId) { chars[i].masked = mask; hit = true; }
      }
      if (!hit) return;
      writeBlock(el, chars);
      var after = bitsOf(chars);
      if (before === after) return;
      var key = blockKey(el);
      overrides[key] = after;
      changes.push({ key: key, el: el, before: before, after: after });
    });
    pushMaskOp(changes);
    return changes.length;
  }

  /** 屏幕下方的一句轻提示 */
  function toast(msg){
    var t = document.getElementById('toast');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast';
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(t._timer);
    t._timer = setTimeout(function(){ t.classList.remove('show'); }, 2000);
  }

  function bitsOf(chars){
    return chars.map(function(c){ return c.hole ? '' : (c.masked ? '1' : '0'); }).join('');
  }

  /** 把一段位图套用到某个段落上 */
  function applyBits(el, bits){
    var chars = readBlock(el);
    var v = 0;
    for (var i = 0; i < chars.length; i++) {
      if (chars[i].hole) continue;
      if (v < bits.length) chars[i].masked = bits.charAt(v) === '1';
      v++;
    }
    writeBlock(el, chars);
  }

  var _elByKey = {};
  function elOf(key){
    var m = /^p(\d+)-(\d+)$/.exec(key);
    if (!m) return null;
    var page = document.getElementById('p' + m[1]);
    return page ? page.querySelector('[data-b="' + m[2] + '"]') : null;
  }
  function setBits(key, el, bits){
    overrides[key] = bits;
    if (el) _elByKey[key] = el;
    applyBits(el || elOf(key), bits);
    saveMasks();
  }
  function pushMaskOp(changes){
    if (!changes.length) return;
    saveMasks();
    pushOp({
      do: function(){
        changes.forEach(function(c){ setBits(c.key, c.el, c.after); });
      },
      undo: function(){
        changes.forEach(function(c){ setBits(c.key, c.el, c.before); });
      }
    });
  }

  /** 打开页面时，把用户以前手动改过的段落复原 */
  function applyOverrides(){
    Object.keys(overrides).forEach(function(key){
      var m = /^p(\d+)-(\d+)$/.exec(key);
      if (!m) return;
      var page = document.getElementById('p' + m[1]);
      if (!page) return;
      var el = page.querySelector('[data-b="' + m[2] + '"]');
      if (!el) return;
      applyBits(el, overrides[key] || '');
    });
  }

  document.addEventListener('keydown', function(e){
    if (e.key === 'Control') document.body.classList.add('quickdraw');
  });
  document.addEventListener('keyup', function(e){
    if (e.key !== 'Control') return;
    document.body.classList.remove('quickdraw');
    if (!drawOn){
      document.querySelectorAll('.page canvas.ink').forEach(function(cv){
        if (!hasInk(pnoOf(cv.parentNode))) cv.remove();
      });
    }
  });

  var scrollT;
  window.addEventListener('scroll', function(){
    hideMenu();
    clearTimeout(scrollT);
    scrollT = setTimeout(ensureVisible, 160);
  }, { passive: true });
  var sizeT;
  window.addEventListener('resize', function(){
    clearTimeout(sizeT);
    sizeT = setTimeout(function(){ repaintAll(); ensureVisible(); }, 220);
  });

  /* 恢复上次用过的画笔设置：颜色 / 粗细 / 是否开着画笔模式 */
  document.querySelectorAll('#pen .pc').forEach(function(d){
    d.classList.toggle('act', d.getAttribute('data-c') === inkColor);
  });
  document.querySelectorAll('#pen .pw').forEach(function(b){
    b.classList.toggle('act', parseFloat(b.getAttribute('data-w')) === inkWidth);
  });
  if (penPref.on) setDraw(true); else ensureVisible();

  applyOverrides();          // 恢复用户手动涂黑 / 放开过的段落

  notes.forEach(function(n){ add(n, false); });
})();
