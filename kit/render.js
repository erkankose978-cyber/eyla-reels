// usage: node render.js stills t1,t2,...   |  node render.js video out.mp4
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
(async () => {
  const mode = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + __dirname + '/' + (process.argv[4] || 'anim.html'));
  await page.evaluate(() => window.ready);
  const grab = async (t, q) => {
    const d = await page.evaluate(([t, q]) => { window.draw(t); return document.getElementById('c').toDataURL(q ? 'image/jpeg' : 'image/png', 0.95); }, [t, q]);
    return Buffer.from(d.split(',')[1], 'base64');
  };
  if (mode === 'stills') {
    fs.mkdirSync(__dirname + '/stills', { recursive: true });
    for (const t of process.argv[3].split(',').map(Number)) fs.writeFileSync(`${__dirname}/stills/${(process.argv[4]||'anim.html').replace('.html','')}_t${t.toFixed(2)}.png`, await grab(t, false));
  } else {
    const fps = 30, dur = Number(process.argv[5] || 29.0), n = Math.round(fps * dur);
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium', process.argv[3]], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = 0; f < n; f++) {
      const buf = await grab(f / fps, true);
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (f % 100 === 0) console.log('frame', f, '/', n);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
