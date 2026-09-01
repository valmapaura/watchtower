"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import BouncingDots from "@/components/BouncingDots";

interface ParsedCamera {
  host: string;
  rtsp_port: number;
  username: string;
  password: string;
  rtsp_path: string;
}

/**
 * First-run setup wizard. Guides a non-technical user through:
 *   1. Pasting their camera's stream link (auto-parsed + connection test)
 *   2. Setting a password to protect the app
 *   3. Done
 */
export default function SetupWizard({ onDone }: { onDone: () => void }) {
  const { login } = useAuth();
  const [step, setStep] = useState(1);
  const [link, setLink] = useState("");
  const [cameraName, setCameraName] = useState("");
  const [parsed, setParsed] = useState<ParsedCamera | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    message: string;
    tips: string[];
  } | null>(null);
  const [appPassword, setAppPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleParse = async () => {
    setError(null);
    setTestResult(null);
    try {
      const p = await api.parseRtsp(link);
      setParsed(p);
      setCameraName(p.host || "My camera");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't read that link");
    }
  };

  const handleTest = async () => {
    if (!parsed) return;
    setTesting(true);
    setTestResult(null);
    try {
      // First confirm the backend itself is reachable, so we can tell the
      // user apart from a camera problem.
      try {
        await api.health();
      } catch {
        setTestResult({
          ok: false,
          message: "The Watchtower service isn't running.",
          tips: [
            "Start the Watchtower service, then try again.",
            "This is separate from your camera — your camera may be fine.",
          ],
        });
        setTesting(false);
        return;
      }
      const res = await api.testCamera({
        name: cameraName || "My camera",
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

  const handleAddCamera = async () => {
    if (!parsed) return;
    setBusy(true);
    setError(null);
    try {
      await api.addCamera({
        name: cameraName || "My camera",
        host: parsed.host,
        rtsp_port: parsed.rtsp_port,
        username: parsed.username,
        password: parsed.password,
        rtsp_path: parsed.rtsp_path,
      });
      setStep(3);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't add the camera");
    } finally {
      setBusy(false);
    }
  };

  const handleFinish = async () => {
    setBusy(true);
    setError(null);
    try {
      if (appPassword) {
        await api.changePassword("", appPassword);
        await login(appPassword);
      }
      onDone();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 py-8">
      <div className="w-full max-w-lg">
        {/* Progress dots */}
        <div className="mb-8 flex items-center justify-center gap-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`h-2 w-2 rounded-full ${
                s <= step ? "bg-emerald-500" : "bg-zinc-700"
              }`}
            />
          ))}
        </div>

        <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-8">
          {step === 1 && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">
                Let&apos;s add your camera
              </h1>
              <p className="mt-2 text-sm text-zinc-500">
                Paste the stream link from your camera&apos;s app or manual. It
                usually looks like{" "}
                <code className="rounded bg-zinc-800 px-1.5 py-0.5 text-xs text-emerald-400">
                  rtsp://...
                </code>
              </p>

              <div className="mt-6">
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
                    value={cameraName}
                    onChange={(e) => setCameraName(e.target.value)}
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
              </div>

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

              {testResult?.ok && (
                <button
                  onClick={handleAddCamera}
                  disabled={busy}
                  className="mt-6 w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
                >
                  {busy ? "Adding…" : "Add camera & continue"}
                </button>
              )}
            </>
          )}

          {step === 2 && (
            <>
              <h1 className="text-2xl font-semibold tracking-tight">
                Protect your recordings
              </h1>
              <p className="mt-2 text-sm text-zinc-500">
                Set a password so only you can view your cameras and recordings.
                This is separate from your camera&apos;s password.
              </p>

              <div className="mt-6">
                <label className="text-sm text-zinc-400">App password</label>
                <input
                  type="password"
                  value={appPassword}
                  onChange={(e) => setAppPassword(e.target.value)}
                  placeholder="Choose a password"
                  className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                />
                <p className="mt-1 text-[11px] text-zinc-600">
                  Leave blank to skip for now (not recommended).
                </p>
              </div>

              {error && (
                <div className="mt-4 rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
                  {error}
                </div>
              )}

              <button
                onClick={handleFinish}
                disabled={busy}
                className="mt-6 w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
              >
                {busy ? "Finishing…" : "Finish setup"}
              </button>
            </>
          )}

          {step === 3 && (
            <div className="text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/15 text-2xl text-emerald-400">
                ✓
              </div>
              <h1 className="mt-4 text-2xl font-semibold tracking-tight">
                You&apos;re all set!
              </h1>
              <p className="mt-2 text-sm text-zinc-500">
                Your camera is connected. You can now watch it live and view
                recordings.
              </p>
              <button
                onClick={onDone}
                className="mt-6 w-full rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400"
              >
                Go to Live view
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}