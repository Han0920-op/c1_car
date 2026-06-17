// app.js - WebSocket handling, dual 2D canvas, tracked depth click, 3D mode detection

(function () {
  'use strict';

  const socket = io();

  let currentTab = '2d';
  let trackedPoint = null;  // {x, y} sticky tracked pixel

  const webTimestamps = [];

  // DOM
  const rgbCanvas = document.getElementById('canvas-rgb');
  const rgbCtx = rgbCanvas.getContext('2d');
  const depthCanvas = document.getElementById('canvas-depth');
  const depthCtx = depthCanvas.getContext('2d');

  const connDot = document.getElementById('conn-dot');
  const connText = document.getElementById('conn-text');
  const overlayRgb = document.getElementById('overlay-rgb');
  const overlayDepth = document.getElementById('overlay-depth');
  const overlay3d = document.getElementById('overlay-3d');
  const pickInfo = document.getElementById('pick-info');

  // Offscreen images
  const rgbImg = new Image();
  const depthImg = new Image();
  let rgbReady = false, depthReady = false;
  let latestTrackedDepth = null;

  rgbImg.onload = () => { rgbReady = true; drawRgb(); };
  depthImg.onload = () => { depthReady = true; drawDepth(); };

  // ---- Tabs (2D / 3D) ----
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTab = btn.dataset.tab;
      document.getElementById('view-2d').classList.toggle('active', currentTab === '2d');
      document.getElementById('view-3d').classList.toggle('active', currentTab === '3d');

      // Enable/disable pointcloud push based on tab
      socket.emit('enable_pointcloud', { enabled: currentTab === '3d' });

      if (currentTab === '3d' && window.PointCloudViewer) {
        window.PointCloudViewer.onShow();
      } else {
        drawRgb(); drawDepth();
      }
    });
  });

  // ---- Depth canvas click -> set tracked point ----
  depthCanvas.addEventListener('click', (e) => {
    const rect = depthCanvas.getBoundingClientRect();
    const sx = depthCanvas.width / rect.width;
    const sy = depthCanvas.height / rect.height;
    const px = Math.round((e.clientX - rect.left) * sx);
    const py = Math.round((e.clientY - rect.top) * sy);
    trackedPoint = { x: px, y: py };
    socket.emit('set_tracked_point', { x: px, y: py });
  });

  // Clear tracked point on right-click
  depthCanvas.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    trackedPoint = null;
    latestTrackedDepth = null;
    socket.emit('set_tracked_point', { x: null, y: null });
    pickInfo.innerHTML = '在 Depth 画面点击查询坐标';
    drawDepth();
  });

  // ---- Drawing ----
  function drawRgb() {
    if (!rgbReady) return;
    if (rgbCanvas.width !== rgbImg.naturalWidth) {
      rgbCanvas.width = rgbImg.naturalWidth;
      rgbCanvas.height = rgbImg.naturalHeight;
    }
    rgbCtx.drawImage(rgbImg, 0, 0, rgbCanvas.width, rgbCanvas.height);
  }

  function drawDepth() {
    if (!depthReady) return;
    if (depthCanvas.width !== depthImg.naturalWidth) {
      depthCanvas.width = depthImg.naturalWidth;
      depthCanvas.height = depthImg.naturalHeight;
    }
    depthCtx.drawImage(depthImg, 0, 0, depthCanvas.width, depthCanvas.height);

    if (trackedPoint) {
      const { x, y } = trackedPoint;
      depthCtx.strokeStyle = '#ffd43b';
      depthCtx.lineWidth = 2;
      depthCtx.beginPath();
      depthCtx.moveTo(x - 12, y); depthCtx.lineTo(x + 12, y);
      depthCtx.moveTo(x, y - 12); depthCtx.lineTo(x, y + 12);
      depthCtx.stroke();

      if (latestTrackedDepth !== null && latestTrackedDepth !== undefined) {
        const depthLabel = latestTrackedDepth.toFixed(3) + 'm';
        const xyLabel = `X:${x} Y:${y}`;

        depthCtx.font = '14px monospace';
        const tw = Math.max(depthCtx.measureText(depthLabel).width, depthCtx.measureText(xyLabel).width);
        let tx = x + 16, ty = y - 20;
        if (tx + tw > depthCanvas.width) tx = x - tw - 16;
        if (ty < 32) ty = y + 32;

        // Background box
        depthCtx.fillStyle = 'rgba(0,0,0,0.75)';
        depthCtx.fillRect(tx - 4, ty - 16, tw + 8, 36);

        // Text: XY on top, depth below
        depthCtx.fillStyle = '#ffd43b';
        depthCtx.fillText(xyLabel, tx, ty);
        depthCtx.fillText(depthLabel, tx, ty + 16);
      } else {
        // Tracked point set but depth invalid: show "无效"
        const depthLabel = '无效';
        const xyLabel = `X:${x} Y:${y}`;

        depthCtx.font = '14px monospace';
        const tw = Math.max(depthCtx.measureText(depthLabel).width, depthCtx.measureText(xyLabel).width);
        let tx = x + 16, ty = y - 20;
        if (tx + tw > depthCanvas.width) tx = x - tw - 16;
        if (ty < 32) ty = y + 32;

        depthCtx.fillStyle = 'rgba(0,0,0,0.75)';
        depthCtx.fillRect(tx - 4, ty - 16, tw + 8, 36);

        depthCtx.fillStyle = '#fa5252';  // red for invalid
        depthCtx.fillText(xyLabel, tx, ty);
        depthCtx.fillText(depthLabel, tx, ty + 16);
      }
    }
  }

  // ---- Socket events ----
  socket.on('connect', () => {
    connDot.classList.add('connected');
    connText.textContent = '已连接';
    // Re-send state on reconnect
    socket.emit('enable_pointcloud', { enabled: currentTab === '3d' });
    if (trackedPoint) {
      socket.emit('set_tracked_point', trackedPoint);
    }
  });

  socket.on('disconnect', () => {
    connDot.classList.remove('connected');
    connText.textContent = '已断开';
  });

  socket.on('frame', (msg) => {
    const now = performance.now();
    webTimestamps.push(now);
    while (webTimestamps.length > 50) webTimestamps.shift();

    if (msg.rgb) rgbImg.src = 'data:image/jpeg;base64,' + msg.rgb;
    if (msg.depth) depthImg.src = 'data:image/jpeg;base64,' + msg.depth;

    // Update tracked depth if present
    if (msg.tracked_xy) {
      if (msg.tracked_depth !== null && msg.tracked_depth !== undefined) {
        latestTrackedDepth = msg.tracked_depth;
        pickInfo.innerHTML = `X: ${msg.tracked_xy.x}, Y: ${msg.tracked_xy.y}<br>深度: ${msg.tracked_depth.toFixed(3)} m`;
      } else {
        latestTrackedDepth = null;
        pickInfo.innerHTML = `X: ${msg.tracked_xy.x}, Y: ${msg.tracked_xy.y}<br>深度: 无效`;
      }
    }

    // FPS sidebar
    document.getElementById('fps-rgb').textContent = msg.fps.rgb.toFixed(1);
    document.getElementById('fps-depth').textContent = msg.fps.depth.toFixed(1);
    document.getElementById('fps-pc').textContent = msg.fps.pointcloud.toFixed(1);
    document.getElementById('fps-web').textContent = webFps().toFixed(1);

    // Overlay FPS
    overlayRgb.textContent = `RGB: ${msg.fps.rgb.toFixed(1)} FPS`;
    overlayDepth.textContent = `Depth: ${msg.fps.depth.toFixed(1)} FPS`;
    overlay3d.textContent = `点云: ${msg.fps.pointcloud.toFixed(1)} FPS | Web: ${webFps().toFixed(1)} FPS`;

    if (msg.pointcloud && window.PointCloudViewer) {
      window.PointCloudViewer.update(msg.pointcloud);
    }
  });

  function webFps() {
    if (webTimestamps.length < 2) return 0;
    const span = (webTimestamps[webTimestamps.length - 1] - webTimestamps[0]) / 1000;
    return span > 0 ? (webTimestamps.length - 1) / span : 0;
  }
})();
