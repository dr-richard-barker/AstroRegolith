import React, { useRef, useEffect, useState } from 'react';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';

interface Props {
  videoUrl: string;
  title?: string;
  fps?: number;
  onFrameChange?: (frameIndex: number, timestamp: number) => void;
  className?: string;
}

/**
 * Video player supporting both MP4 files and YouTube embeds.
 *
 * For MP4: H.264 with all-intra key frames for frame-level seeking.
 * For YouTube: Renders privacy-enhanced embed iframe.
 */
export const VideoPlayer: React.FC<Props> = ({ videoUrl, title, fps = 30, onFrameChange, className }) => {
  const isYouTubeEmbed = videoUrl.includes('youtube-nocookie.com');
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [frameInfo, setFrameInfo] = useState<{ index: number; timeMs: number } | null>(null);

  // Update frame info when time changes
  useEffect(() => {
    if (!videoRef.current || !onFrameChange) return;
    const frameIndex = Math.round(currentTime * fps);
    const timeMs = currentTime * 1000;
    setFrameInfo({ index: frameIndex, timeMs });
    onFrameChange(frameIndex, currentTime);
  }, [currentTime, fps, onFrameChange]);

  const handlePlayPause = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play().catch(() => {});
    }
    setIsPlaying(!isPlaying);
  };

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const t = (e.target as HTMLVideoElement).currentTime;
    setCurrentTime(t);
  };

  const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLVideoElement>) => {
    const d = (e.target as HTMLVideoElement).duration;
    setDuration(d);
  };

  const handleSeek = (newTime: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleFrameStep = (direction: 1 | -1) => {
    const frameTime = 1 / fps;
    handleSeek(Math.max(0, Math.min(duration, currentTime + direction * frameTime)));
  };

  const formatTime = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    return h > 0 ? `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}` : `${m}:${s.toString().padStart(2, '0')}`;
  };

  if (isYouTubeEmbed) {
    return (
      <div className={`video-player ${className || ''}`} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {title && <h3>{title}</h3>}
        <iframe
          width="100%"
          height="400"
          src={videoUrl}
          title={title || 'YouTube video'}
          frameBorder="0"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          style={{ borderRadius: 6 }}
        />
      </div>
    );
  }

  return (
    <div className={`video-player ${className || ''}`} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {title && <h3>{title}</h3>}

      <div style={{ position: 'relative', width: '100%', background: 'var(--card)', borderRadius: 6, overflow: 'hidden' }}>
        <video
          ref={videoRef}
          src={videoUrl}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
          muted={isMuted}
          style={{ width: '100%', display: 'block' }}
          crossOrigin="anonymous"
        />
      </div>

      {/* Metadata line */}
      {frameInfo && (
        <div style={{ fontSize: '.8rem', color: 'var(--muted)', fontFamily: 'monospace' }}>
          Frame {frameInfo.index} @ {formatTime(frameInfo.timeMs / 1000)} ({(frameInfo.timeMs).toFixed(0)}ms)
        </div>
      )}

      {/* Control bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Play/pause */}
        <button
          className="btn btn-sm"
          onClick={handlePlayPause}
          title={isPlaying ? 'Pause' : 'Play'}
          style={{ padding: '6px 10px' }}
        >
          {isPlaying ? <Pause size={16} /> : <Play size={16} />}
        </button>

        {/* Frame back/forward */}
        <button
          className="btn btn-sm"
          onClick={() => handleFrameStep(-1)}
          title="Previous frame"
          disabled={currentTime <= 0}
          style={{ padding: '6px 10px' }}
        >
          ◀
        </button>
        <button
          className="btn btn-sm"
          onClick={() => handleFrameStep(1)}
          title="Next frame"
          disabled={currentTime >= duration}
          style={{ padding: '6px 10px' }}
        >
          ▶
        </button>

        {/* Timeline */}
        <input
          type="range"
          min={0}
          max={duration || 0}
          value={currentTime}
          onChange={(e) => handleSeek(parseFloat(e.currentTarget.value))}
          style={{ flex: 1, cursor: 'pointer' }}
          title="Seek"
        />

        {/* Time display */}
        <span style={{ fontSize: '.75rem', fontFamily: 'monospace', minWidth: '50px', textAlign: 'right' }}>
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        {/* Mute */}
        <button
          className="btn btn-sm"
          onClick={() => setIsMuted(!isMuted)}
          title={isMuted ? 'Unmute' : 'Mute'}
          style={{ padding: '6px 8px' }}
        >
          {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
        </button>
      </div>

      <style>{`
        .video-player {
          font-size: 0.9rem;
        }
        .video-player button {
          border: 1px solid var(--border);
          background: var(--card);
          color: var(--text);
          cursor: pointer;
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 4px;
          transition: background 0.2s;
        }
        .video-player button:hover:not(:disabled) {
          background: var(--accent, #0066cc);
          color: white;
        }
        .video-player button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .video-player input[type="range"] {
          appearance: none;
          -webkit-appearance: none;
          width: 100%;
          height: 4px;
          border-radius: 2px;
          background: var(--border);
          outline: none;
        }
        .video-player input[type="range"]::-webkit-slider-thumb {
          -webkit-appearance: none;
          appearance: none;
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: var(--accent, #0066cc);
          cursor: pointer;
        }
        .video-player input[type="range"]::-moz-range-thumb {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: var(--accent, #0066cc);
          cursor: pointer;
          border: none;
        }
      `}</style>
    </div>
  );
};
