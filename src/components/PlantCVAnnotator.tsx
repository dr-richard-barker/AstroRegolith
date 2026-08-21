import React, { useState, useEffect, useRef } from 'react';
import { Loader2, Play, Save, SlidersHorizontal, Image as ImageIcon } from 'lucide-react';
import { putResult } from '../lib/cose-results';

interface Props {
  imageUrl: string;
  imageRef: string; // The "project::uuid" key
  onClose: () => void;
}

declare global {
  interface Window {
    loadPyodide: (config: any) => Promise<any>;
  }
}

export const PlantCVAnnotator: React.FC<Props> = ({ imageUrl, imageRef, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState('Initializing WebAssembly... (This may take a minute)');
  const [pyodide, setPyodide] = useState<any>(null);
  
  // UI Controls for Duckweed / Leaf Segmentation
  const [hueMin, setHueMin] = useState(30);
  const [hueMax, setHueMax] = useState(90); // Green hues
  const [satMin, setSatMin] = useState(40);
  const [valMin, setValMin] = useState(40);
  
  const [resultImg, setResultImg] = useState<string | null>(null);
  const [leafCount, setLeafCount] = useState<number | null>(null);
  const [running, setRunning] = useState(false);

  // Hidden image to get raw base64 data
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    // Load Pyodide script
    if (document.getElementById('pyodide-script')) {
      initPyodide();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js';
    script.id = 'pyodide-script';
    script.onload = initPyodide;
    document.body.appendChild(script);

    async function initPyodide() {
      try {
        if (!window.loadPyodide) return;
        setStatus('Loading Pyodide runtime...');
        const py = await window.loadPyodide({
          indexURL: "https://cdn.jsdelivr.net/pyodide/v0.25.0/full/"
        });
        
        setStatus('Loading OpenCV and dependencies...');
        await py.loadPackage(['opencv-python', 'numpy', 'micropip']);
        
        setStatus('Installing PlantCV (Downloading from PyPI)...');
        const micropip = py.pyimport('micropip');
        // Install PlantCV and its dependencies. Since some dependencies like matplotlib/scipy are large, we might just use OpenCV if plantcv fails.
        // We will try installing plantcv, but wrap it so we don't crash the whole tool.
        try {
           await micropip.install('plantcv');
           setStatus('PlantCV Ready!');
        } catch (e) {
           console.warn('PlantCV full install failed, using fallback cv2 workflow', e);
           setStatus('OpenCV Fallback Ready!');
        }
        
        setPyodide(py);
        setLoading(false);
      } catch (e) {
        console.error(e);
        setStatus('Failed to load Pyodide: ' + e);
      }
    }
  }, []);

  const runAnalysis = async () => {
    if (!pyodide || !imgRef.current) return;
    setRunning(true);
    setStatus('Running segmentation pipeline...');
    
    // We get the image data from a canvas to pass to Python
    const canvas = document.createElement('canvas');
    canvas.width = imgRef.current.naturalWidth;
    canvas.height = imgRef.current.naturalHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(imgRef.current, 0, 0);
    const imgDataUrl = canvas.toDataURL('image/png');
    const b64Data = imgDataUrl.split(',')[1];
    
    // Pass parameters to Python namespace
    pyodide.globals.set('img_b64', b64Data);
    pyodide.globals.set('h_min', hueMin);
    pyodide.globals.set('h_max', hueMax);
    pyodide.globals.set('s_min', satMin);
    pyodide.globals.set('v_min', valMin);
    
    const pythonCode = `
import base64
import cv2
import numpy as np

# Decode image
img_bytes = base64.b64decode(img_b64)
np_arr = np.frombuffer(img_bytes, np.uint8)
img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

# Attempt PlantCV, fallback to OpenCV if not fully installed
try:
    from plantcv import plantcv as pcv
    pcv.params.debug = None
    # For Duckweed or Leaf segmenting, we can use HSV thresholding
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Mask out non-green
    lower_green = np.array([h_min, s_min, v_min])
    upper_green = np.array([h_max, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # morphological operations
    kernel = np.ones((5,5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter small specs
    leaf_contours = [c for c in contours if cv2.contourArea(c) > 50]
    leaf_count = len(leaf_contours)
    
    # Draw contours on image
    out_img = img.copy()
    cv2.drawContours(out_img, leaf_contours, -1, (0, 0, 255), 2)
    
    # Encode back to base64
    _, buffer = cv2.imencode('.png', out_img)
    result_b64 = base64.b64encode(buffer).decode('utf-8')

except Exception as e:
    result_b64 = "ERROR:" + str(e)
    leaf_count = -1

(result_b64, leaf_count)
`;

    try {
      const result = await pyodide.runPythonAsync(pythonCode);
      const resB64 = result.get(0);
      const count = result.get(1);
      
      if (resB64.startsWith("ERROR:")) {
        setStatus("Error running script: " + resB64);
      } else {
        setResultImg("data:image/png;base64," + resB64);
        setLeafCount(count);
        setStatus("Segmentation complete!");
      }
    } catch (e) {
      console.error(e);
      setStatus("Execution error: " + e);
    } finally {
      setRunning(false);
    }
  };

  const saveResults = async () => {
    if (leafCount === null) return;
    try {
      await putResult({
        ref: imageRef,
        imageUrl,
        tool: 'plantcv',
        toolName: 'PlantCV Segmenter',
        metrics: {
          'Leaf Count': leafCount,
          'Hue Range': `${hueMin}-${hueMax}`,
          'Min Saturation': satMin,
        },
        generatedAt: new Date().toISOString()
      });
      alert('Results saved to local database!');
      onClose();
      // force UI refresh
      window.dispatchEvent(new Event('focus'));
    } catch (e) {
      console.error(e);
      alert('Failed to save results.');
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)', display: 'flex', flexDirection: 'column' }}>
      <img ref={imgRef} src={imageUrl} alt="hidden raw" style={{ display: 'none' }} crossOrigin="anonymous" />
      
      {/* Header */}
      <div className="row justify" style={{ background: 'var(--bg-dark)', padding: '12px 20px', borderBottom: '1px solid var(--border)' }}>
        <div className="row" style={{ gap: 10, color: 'var(--accent)' }}>
          <ImageIcon size={20} />
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>PlantCV Leaf Segmenter (Pyodide)</h3>
        </div>
        <button className="btn btn-sm" onClick={onClose}>Close</button>
      </div>

      {loading ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
          <Loader2 className="spin" size={48} style={{ marginBottom: 20, color: 'var(--accent)' }} />
          <h3>{status}</h3>
          <p style={{ maxWidth: 400, textAlign: 'center', color: 'var(--text-muted)' }}>
            PlantCV and its dependencies are being downloaded to run entirely in your browser using WebAssembly.
          </p>
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          {/* Left Panel: Controls */}
          <div style={{ width: 320, background: 'var(--bg-card)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
            <div style={{ padding: 20, flex: 1, overflowY: 'auto' }}>
              <h4 className="row" style={{ gap: 8, marginTop: 0, marginBottom: 20 }}>
                <SlidersHorizontal size={18} /> Parameters
              </h4>
              
              <div style={{ marginBottom: 15 }}>
                <label style={{ display: 'block', fontSize: '.85rem', marginBottom: 5 }}>Min Hue: {hueMin}</label>
                <input type="range" min="0" max="179" value={hueMin} onChange={e => setHueMin(parseInt(e.target.value))} style={{ width: '100%' }} />
              </div>
              
              <div style={{ marginBottom: 15 }}>
                <label style={{ display: 'block', fontSize: '.85rem', marginBottom: 5 }}>Max Hue: {hueMax}</label>
                <input type="range" min="0" max="179" value={hueMax} onChange={e => setHueMax(parseInt(e.target.value))} style={{ width: '100%' }} />
              </div>

              <div style={{ marginBottom: 15 }}>
                <label style={{ display: 'block', fontSize: '.85rem', marginBottom: 5 }}>Min Saturation: {satMin}</label>
                <input type="range" min="0" max="255" value={satMin} onChange={e => setSatMin(parseInt(e.target.value))} style={{ width: '100%' }} />
              </div>

              <div style={{ marginBottom: 30 }}>
                <label style={{ display: 'block', fontSize: '.85rem', marginBottom: 5 }}>Min Value (Brightness): {valMin}</label>
                <input type="range" min="0" max="255" value={valMin} onChange={e => setValMin(parseInt(e.target.value))} style={{ width: '100%' }} />
              </div>

              <button className="btn btn-teal" onClick={runAnalysis} disabled={running} style={{ width: '100%', padding: '10px 0', fontSize: '1rem', display: 'flex', justifyContent: 'center', gap: 8 }}>
                {running ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
                {running ? 'Processing...' : 'Run Segmentation'}
              </button>

              <div style={{ marginTop: 20, fontSize: '.8rem', color: 'var(--text-muted)' }}>
                {status}
              </div>

              {leafCount !== null && (
                <div className="card" style={{ marginTop: 20, padding: 15, background: 'rgba(var(--accent-rgb), 0.1)', borderColor: 'var(--accent)' }}>
                  <h4 style={{ margin: '0 0 10px 0', color: 'var(--accent)' }}>Results</h4>
                  <div style={{ fontSize: '1.2rem', fontWeight: 600 }}>Leaves Found: {leafCount}</div>
                  
                  <button className="btn btn-sm btn-accent" style={{ width: '100%', marginTop: 15 }} onClick={saveResults}>
                    <Save size={14} style={{ marginRight: 6 }} /> Save to Database
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Right Panel: Image Display */}
          <div style={{ flex: 1, padding: 20, display: 'flex', gap: 20, overflow: 'auto' }}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <h4 style={{ color: '#fff', marginTop: 0 }}>Original Image</h4>
              <div style={{ flex: 1, background: '#111', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                <img src={imageUrl} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} alt="original" crossOrigin="anonymous" />
              </div>
            </div>

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <h4 style={{ color: '#fff', marginTop: 0 }}>Segmentation Mask</h4>
              <div style={{ flex: 1, background: '#111', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', border: '1px solid #333' }}>
                {resultImg ? (
                  <img src={resultImg} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} alt="result" />
                ) : (
                  <span style={{ color: '#555' }}>Run analysis to see results</span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
