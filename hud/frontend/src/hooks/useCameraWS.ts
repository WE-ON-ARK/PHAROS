import { useEffect, useRef, useState } from "react";
import type { CameraMessage } from "../types";

// Streams the live webcam HUD from the backend /ws/camera endpoint.
// Returns the latest message (annotated frame + metrics) or an error string.
export function useCameraWS(
  fps: number,
  enabled: boolean
): { message: CameraMessage | null; error: string | null } {
  const [message, setMessage] = useState<CameraMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      setMessage(null);
      setError(null);
      return;
    }
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/camera?fps=${fps}`);
    wsRef.current = ws;

    ws.onmessage = (e: MessageEvent) => {
      const msg = JSON.parse(e.data as string) as CameraMessage;
      if (msg.error) {
        setError(msg.error);
        return;
      }
      setError(null);
      setMessage(msg);
    };
    ws.onerror = () => setError("connection to camera stream failed");

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [fps, enabled]);

  return { message, error };
}
