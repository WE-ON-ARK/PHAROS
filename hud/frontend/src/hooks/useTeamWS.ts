import { useEffect, useRef, useState } from "react";
import type { TeamSnapshot } from "../types";

export function useTeamWS(fps: number, enabled: boolean): TeamSnapshot | null {
  const [snapshot, setSnapshot] = useState<TeamSnapshot | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      setSnapshot(null);
      return;
    }
    const wsUrl = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/team?fps=${fps}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onmessage = (e: MessageEvent) => {
      setSnapshot(JSON.parse(e.data as string) as TeamSnapshot);
    };
    ws.onerror = () => setSnapshot(null);
    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [fps, enabled]);

  return snapshot;
}
