// Sağ altta renkli, dikkat çekici ama odak ÇALMAYAN bir bildirim kartı gösterir
// (su_hatirlatici.py tarafından çağrılır).
// Kullanım: osascript -l JavaScript popup.js <tema> <mesaj> <zamanaşımı_sn> <buton1> [buton2 ...]
//   tema: su (mavi) | doldur (turuncu) | ozet (yeşil)
//   mesaj: ilk satır başlık, "Bugün: X / Y L" içeren satır ilerleme çubuğu, kalanı gövde metni
// Basılan butonun adını stdout'a yazar; zaman aşımında hiçbir şey yazmaz.
ObjC.import('Cocoa');
ObjC.import('stdlib');

const THEMES = {
  su:     { color: [0.04, 0.45, 0.95], icon: '💧' },
  doldur: { color: [0.96, 0.46, 0.05], icon: '🚰' },
  ozet:   { color: [0.10, 0.62, 0.35], icon: '🎉' },
};

function emit(text) {
  const data = $(text).dataUsingEncoding($.NSUTF8StringEncoding);
  $.NSFileHandle.fileHandleWithStandardOutput.writeData(data);
}

function rgba(r, g, b, a) {
  return $.NSColor.colorWithSRGBRedGreenBlueAlpha(r, g, b, a);
}

function label(text, x, y, w, h, size, bold, alpha) {
  const f = $.NSTextField.labelWithString($(text));
  f.frame = $.NSMakeRect(x, y, w, h);
  f.font = bold ? $.NSFont.boldSystemFontOfSize(size) : $.NSFont.systemFontOfSize(size);
  f.textColor = rgba(1, 1, 1, alpha);
  f.lineBreakMode = 0;
  return f;
}

function box(x, y, w, h, color, radius) {
  const v = $.NSBox.alloc.initWithFrame($.NSMakeRect(x, y, w, h));
  v.boxType = 4;           // NSBoxCustom
  v.titlePosition = 0;     // başlık yok
  v.borderWidth = 0;
  v.fillColor = color;
  v.cornerRadius = radius;
  return v;
}

function run(argv) {
  const theme = THEMES[argv[0]] || THEMES.su;
  const lines = argv[1].split('\n');
  const timeout = parseFloat(argv[2]);
  const buttons = argv.slice(3);

  const title = lines[0];
  const progressLine = lines.find(function (l) { return /^Bugün:/.test(l); }) || '';
  const body = lines.slice(1).filter(function (l) { return l !== progressLine && l.trim() !== ''; }).join('\n');
  const m = progressLine.match(/([\d.]+)\s*\/\s*([\d.]+)/);
  const fraction = m ? Math.max(0, Math.min(1, parseFloat(m[1]) / parseFloat(m[2]))) : 0;

  const app = $.NSApplication.sharedApplication;
  app.setActivationPolicy($.NSApplicationActivationPolicyAccessory);

  ObjC.registerSubclass({
    name: 'SuHandler',
    methods: {
      'click:': {
        types: ['void', ['id']],
        implementation: function (sender) {
          emit(ObjC.unwrap(sender.title));
          $.exit(0);
        },
      },
    },
  });
  const handler = $.SuHandler.alloc.init;

  const W = 480, H = 230, MARGIN = 20, PAD = 24;
  const vf = $.NSScreen.mainScreen.visibleFrame;
  const x = vf.origin.x + vf.size.width - W - MARGIN;
  const y = vf.origin.y + MARGIN;

  // 0 = çerçevesiz (klavye odağı alamaz), 128 = nonactivating panel
  const win = $.NSPanel.alloc.initWithContentRectStyleMaskBackingDefer(
    $.NSMakeRect(x, y, W, H), 0 | 128, $.NSBackingStoreBuffered, false);
  win.opaque = false;
  win.backgroundColor = $.NSColor.clearColor;
  win.hasShadow = true;
  win.level = 3;                             // diğer pencerelerin üstünde
  win.hidesOnDeactivate = false;
  win.collectionBehavior = 1 << 0 | 1 << 8;  // tüm masaüstlerinde görün

  const root = win.contentView;
  root.wantsLayer = true;
  root.layer.backgroundColor = rgba(theme.color[0], theme.color[1], theme.color[2], 1).CGColor;
  root.layer.cornerRadius = 20;
  root.layer.masksToBounds = true;

  root.addSubview(label(theme.icon, PAD, H - 92, 70, 70, 54, false, 1));
  root.addSubview(label(title, PAD + 76, H - 62, W - PAD * 2 - 76, 32, 23, true, 1));
  root.addSubview(label(body, PAD + 76, H - 122, W - PAD * 2 - 76, 56, 15, false, 0.92));

  // Günlük hedef ilerleme çubuğu
  if (m) {
    root.addSubview(label(progressLine, PAD, 100, W - PAD * 2, 20, 13, true, 0.95));
    root.addSubview(box(PAD, 86, W - PAD * 2, 8, rgba(1, 1, 1, 0.30), 4));
    if (fraction > 0) root.addSubview(box(PAD, 86, (W - PAD * 2) * fraction, 8, rgba(1, 1, 1, 1), 4));
  }

  const bw = (W - PAD * 2 - 12 * (buttons.length - 1)) / buttons.length;
  buttons.forEach(function (b, i) {
    const primary = i === buttons.length - 1;
    const bx = PAD + i * (bw + 12);
    root.addSubview(box(bx, 22, bw, 46, primary ? rgba(1, 1, 1, 1) : rgba(1, 1, 1, 0.25), 12));
    const btn = $.NSButton.alloc.initWithFrame($.NSMakeRect(bx, 22, bw, 46));
    btn.bordered = false;
    btn.title = b;
    const fg = primary ? rgba(theme.color[0], theme.color[1], theme.color[2], 1) : rgba(1, 1, 1, 1);
    btn.font = $.NSFont.boldSystemFontOfSize(16);
    btn.contentTintColor = fg;
    btn.target = handler;
    btn.action = 'click:';
    root.addSubview(btn);
  });

  // Klavye odağını asla alma: kullanıcı yazarken tuşlar kendi uygulamasına gitsin
  // (odak alırsa tuşlar bu pencereye düşer ve bip sesi çıkar). Sadece fare ile kullanılır.
  win.becomesKeyOnlyIfNeeded = true;
  win.orderFrontRegardless;

  $.NSTimer.scheduledTimerWithTimeIntervalRepeatsBlock(timeout, false, function () {
    $.exit(0);
  });

  app.run;
}
