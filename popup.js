// Sağ altta küçük bir pencere gösterir.
// Kullanım: osascript -l JavaScript popup.js <mesaj> <zamanaşımı_sn> <buton1> [buton2 ...]
// Basılan butonun adını stdout'a yazar; zaman aşımında hiçbir şey yazmaz.
ObjC.import('Cocoa');
ObjC.import('stdlib');

function emit(text) {
  const data = $(text).dataUsingEncoding($.NSUTF8StringEncoding);
  $.NSFileHandle.fileHandleWithStandardOutput.writeData(data);
}

function run(argv) {
  const message = argv[0];
  const timeout = parseFloat(argv[1]);
  const buttons = argv.slice(2);

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

  const W = 460, H = 200, MARGIN = 20;
  const vf = $.NSScreen.mainScreen.visibleFrame;
  const x = vf.origin.x + vf.size.width - W - MARGIN;
  const y = vf.origin.y + MARGIN;

  // 1 = titled, 8 = nonactivating panel
  const win = $.NSPanel.alloc.initWithContentRectStyleMaskBackingDefer(
    $.NSMakeRect(x, y, W, H), 1 | 128, $.NSBackingStoreBuffered, false);
  win.title = '💧 Su Vakti';
  win.level = 3;                      // diğer pencerelerin üstünde
  win.hidesOnDeactivate = false;
  win.collectionBehavior = 1 << 0 | 1 << 8;  // tüm masaüstlerinde görün

  const label = $.NSTextField.labelWithString($(message));
  label.frame = $.NSMakeRect(20, 70, W - 40, H - 70 - 20);
  label.font = $.NSFont.systemFontOfSize(16);
  label.lineBreakMode = 0;
  win.contentView.addSubview(label);

  const bw = (W - 40 - 10 * (buttons.length - 1)) / buttons.length;
  buttons.forEach(function (b, i) {
    const btn = $.NSButton.alloc.initWithFrame($.NSMakeRect(20 + i * (bw + 10), 16, bw, 40));
    btn.title = b;
    btn.bezelStyle = 1;
    btn.target = handler;
    btn.action = 'click:';
    if (i === buttons.length - 1) btn.keyEquivalent = '\r';
    win.contentView.addSubview(btn);
  });

  win.orderFrontRegardless;
  win.makeKeyAndOrderFront(null);

  $.NSTimer.scheduledTimerWithTimeIntervalRepeatsBlock(timeout, false, function () {
    $.exit(0);
  });

  app.run;
}
