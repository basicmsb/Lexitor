"use client";

import { useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import { getAccessToken } from "@/lib/auth-storage";
import type {
  AnalysisItemPublic,
  AnalysisStatus,
  AnalysisSummary,
} from "@/lib/types";

interface SnapshotEvent {
  type: "snapshot";
  analysis_id: string;
  status: AnalysisStatus;
  summary: AnalysisSummary | null;
}

interface ItemEvent {
  type: "item";
  analysis_id: string;
  item: AnalysisItemPublic;
  progress: number;
}

interface CompletedEvent {
  type: "completed";
  analysis_id: string;
  summary: AnalysisSummary;
}

interface ErrorEvent {
  type: "error";
  analysis_id: string;
  error: string;
}

interface State {
  status: AnalysisStatus;
  progress: number;
  items: AnalysisItemPublic[];
  summary: AnalysisSummary | null;
  error: string | null;
  connected: boolean;
}

const initialState: State = {
  status: "pending",
  progress: 0,
  items: [],
  summary: null,
  error: null,
  connected: false,
};

export function useAnalysisStream(analysisId: string | null): State {
  const [state, setState] = useState<State>(initialState);
  const itemsRef = useRef<Map<string, AnalysisItemPublic>>(new Map());

  useEffect(() => {
    if (!analysisId) return;
    setState(initialState);
    itemsRef.current = new Map();

    const token = getAccessToken();
    if (!token) {
      setState((s) => ({ ...s, error: "Niste prijavljeni." }));
      return;
    }

    const url = `${API_BASE_URL}/analyses/${analysisId}/stream?token=${encodeURIComponent(token)}`;
    const source = new EventSource(url);

    source.addEventListener("open", () => {
      setState((s) => ({ ...s, connected: true }));
    });

    source.addEventListener("snapshot", (raw) => {
      const evt = JSON.parse((raw as MessageEvent).data) as SnapshotEvent;
      setState((s) => ({ ...s, status: evt.status, summary: evt.summary }));
    });

    source.addEventListener("started", (raw) => {
      const evt = JSON.parse((raw as MessageEvent).data) as { type: "started"; total: number };
      setState((s) => ({ ...s, status: "running", progress: 0, summary: null, error: null }));
      void evt;
    });

    source.addEventListener("item", (raw) => {
      const evt = JSON.parse((raw as MessageEvent).data) as ItemEvent;
      itemsRef.current.set(evt.item.id, evt.item);
      const sorted = Array.from(itemsRef.current.values()).sort(
        (a, b) => a.position - b.position,
      );
      setState((s) => ({
        ...s,
        status: "running",
        progress: evt.progress,
        items: sorted,
      }));
    });

    source.addEventListener("completed", (raw) => {
      const evt = JSON.parse((raw as MessageEvent).data) as CompletedEvent;
      setState((s) => ({
        ...s,
        status: "complete",
        progress: 100,
        summary: evt.summary,
      }));
      source.close();
    });

    source.addEventListener("error", (raw) => {
      // EventSource fires "error" both for real backend errors and connection drops.
      try {
        const data = (raw as MessageEvent).data;
        if (typeof data === "string" && data.length > 0) {
          const evt = JSON.parse(data) as ErrorEvent;
          setState((s) => ({ ...s, status: "error", error: evt.error }));
          source.close();
          return;
        }
      } catch {
        /* ignore */
      }
      setState((s) => ({ ...s, connected: false }));
    });

    return () => {
      source.close();
    };
  }, [analysisId]);

  return state;
}
