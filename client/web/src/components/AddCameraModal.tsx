"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import BouncingDots from "@/components/BouncingDots";

interface ParsedCamera {
  host: string;
  rtsp_port: number;
  username: string;
  password: string;
  rtsp_path: string;
}

/** Modal to add a camera by pasting its stream link. */
export default function AddCameraModal({
  onClose,
  onAdded,
}: {
  onClose: () => void;
  onAdded: () => void;
}) {
  const [link, setLink] = useState("");
  const [name, setName] = useState("");
  const [parsed, setParsed] = useState<ParsedCamera | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
    tips: string[];
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    setError(null);
    setTestResult(null);
    try {
      const p = await api.parseRtsp(link);
      setParsed(p);
      setName(p.host || "My camera");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't read that link");
    }
  };

  const handleTest = async () => {
    if (!parsed) return;
    setTesting(true);
    setTestResult(null);
    try {
      try {
        await api.health();
      } catch {
        setTestResult({
          ok: false,
          message: "The Watchtower service isn't running.",
          tips: ["Start the Watchtower service, then try again."],
        });
        setTesting(false);
        return;
      }
      const res = await api.testCamera({
        name: name || "My camera",
        host: parsed.host,
        rtsp_port: parsed.rtsp_port,
        username: parsed.username,
        password: parsed.password,
        rtsp_path: parsed.rtsp_path,
      });
      setTestResult(res);
    } catch {
      setTestResult({
        ok: false,
        message: "Couldn't test the connection.",
        tips: ["Make sure the Watchtower service is running."],
      });
    } finally {
      setTesting(false);
    }
  };

  const handleAdd = async () => {
    if (!parsed) return;
    setBusy(true);
    setError(null);
    try {
      await api.addCamera({
        name: name || "My camera",
        host: parsed.host,
        rtsp_port: parsed.rtsp_port,
        username: parsed.username,
        password: parsed.password,
        rtsp_path: parsed.rtsp_path,
      });
      onAdded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't add the camera");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Add a camera</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg px-2 py-1 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
          >
            ✕
          </button>
        </div>
        <p className="mt-1 text-sm text-zinc-500">
          Paste the stream link from your camera&apos;s app or manual.
        </p>

        <div className="mt-4">
          <label className="text-sm text-zinc-400">Stream link</label>
          <input
            type="text"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            placeholder="rtsp://username:password@192.168.1.50:554/live/ch0"
            className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-sm text-zinc-100 outline-none focus:border-emerald-500"
          />
        </div>

        {parsed && (
          <div className="mt-4">
            <label className="text-sm text-zinc-400">Camera name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
            />
            <p className="mt-2 text-xs text-zinc-500">
              Found: <span className="text-zinc-300">{parsed.host}</span>
            </p>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {testResult && (
          <div
            className={`mt-4 rounded-lg border px-4 py-3 text-sm ${
              testResult.ok
                ? "border-emerald-900/50 bg-emerald-950/40 text-emerald-300"
                : "border-amber-900/50 bg-amber-950/40 text-amber-300"
            }`}
          >
            <p>{testResult.message}</p>
            {!testResult.ok && testResult.tips.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-amber-200/80">
                {testResult.tips.map((tip, i) => (
                  <li key={i}>{tip}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="mt-6 flex gap-3">
          <button
            onClick={handleParse}
            disabled={!link}
            className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-50"
          >
            Read link
          </button>
          {parsed && (
            <button
              onClick={handleTest}
              disabled={testing}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                testing
                  ? "border border-emerald-500/60 bg-transparent text-emerald-300"
                  : "bg-emerald-500 text-zinc-950 hover:bg-emerald-400"
              }`}
            >
              {testing ? <BouncingDots /> : "Test connection"}
            </button>
          )}
          {testResult?.ok && (
            <button
              onClick={handleAdd}
              disabled={busy}
              className="ml-auto rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
            >
              {busy ? "Adding…" : "Add camera"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}