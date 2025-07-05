import { useRef, useEffect, useImperativeHandle, forwardRef } from "react";
import videojs from "video.js";
import "video.js/dist/video-js.css";

interface VideoPlayerProps {
  src: string;
  onTimestampJump?: (timestamp: number) => void;
  className?: string;
}

const VideoPlayer = forwardRef<HTMLVideoElement, VideoPlayerProps>(({ src, onTimestampJump, className }, ref) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const playerRef = useRef<any>(null);

  useEffect(() => {
    if (videoRef.current && !playerRef.current) {
      playerRef.current = videojs(videoRef.current, {
        controls: true,
        preload: "auto",
        responsive: true,
        fluid: true,
      });
      // Custom control for jumping to timestamp
      if (onTimestampJump) {
        playerRef.current.on("jumpToTimestamp", (_: any, ts: number) => {
          playerRef.current.currentTime(ts);
        });
      }
    }
    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [src, onTimestampJump]);



  // Expose seekTo method for parent
  useImperativeHandle(ref, () => ({
    seekTo: (seconds: number) => {
      if (playerRef.current) {
        playerRef.current.currentTime(seconds);
        playerRef.current.play();
      }
    }
  }) as any);

  return (
    <div className={`video-player-container ${className || ""}`}>
      <video
        ref={videoRef}
        className="video-js vjs-default-skin rounded-lg shadow"
        controls
        preload="auto"
        data-setup="{}"
      >
        <source src={src} type="video/mp4" />
        Your browser does not support the video tag.
      </video>
    </div>
  );
});

export default VideoPlayer;
export type { VideoPlayerProps };
