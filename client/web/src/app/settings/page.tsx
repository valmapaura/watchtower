"use client";

import { useEffect, useState } from "react";
import Shell from "@/components/Shell";
import InfoTip from "@/components/InfoTip";
import { api, type CameraSettings, type Settings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getSettings()
      .then((data) => {
        if (!cancelled) setSettings(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load settings");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const updateCamera = (index: number, patch: Partial<CameraSettings>) => {
    setSettings((prev) => {
      if (!prev) return prev;
      const cameras = prev.cameras.map((c, i) => (i === index ? { ...c, ...patch } : c));
      return { ...prev, cameras };
    });
  };

  const save = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await api.updateSettings({
        retention_days: settings.retention_days,
        max_storage_gb: settings.max_storage_gb,
        notifications_enabled: settings.notifications_enabled,
        cameras: settings.cameras,
      });
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Shell>
        <div className="mx-auto max-w-3xl px-4 py-6 sm:px-8 sm:py-8">
          <div className="h-8 w-40 animate-pulse rounded bg-zinc-900" />
          <div className="mt-6 h-64 animate-pulse rounded-xl bg-zinc-900" />
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-8 sm:py-8">
        <header className="mb-6 sm:mb-8">
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-zinc-500">
            Tune how your cameras record. Tap the{" "}
            <span className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-zinc-700/60 text-[10px] font-semibold text-zinc-300">
              ?
            </span>{" "}
            icons to learn what each option does.
          </p>
        </header>

        {error && (
          <div className="mb-6 rounded-lg border border-red-900/50 bg-red-950/40 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {settings && (
          <div className="space-y-6">
            {/* General */}
            <section className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6">
              <h2 className="text-sm font-semibold text-zinc-200">Recording storage</h2>
              <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Field label="Keep recordings for (days)">
                  <input
                    type="number"
                    min={0}
                    value={settings.retention_days}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        retention_days: Number(e.target.value),
                      })
                    }
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                  />
                  <InfoTip title="How long recordings are kept">
                    Recordings older than this are deleted automatically to save
                    space. Set to 0 to keep everything forever.
                  </InfoTip>
                </Field>
                <Field label="Max space to use (GB)">
                  <input
                    type="number"
                    min={0}
                    step={1}
                    value={settings.max_storage_gb}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        max_storage_gb: Number(e.target.value),
                      })
                    }
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                  />
                  <InfoTip title="How much disk space to use">
                    When recordings fill up this much space, the oldest ones are
                    deleted first to make room. Set to 0 for no limit.
                  </InfoTip>
                </Field>
                <Field label="Get notified when motion is detected">
                  <label className="flex cursor-pointer items-center gap-3 pt-2">
                    <input
                      type="checkbox"
                      checked={settings.notifications_enabled}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          notifications_enabled: e.target.checked,
                        })
                      }
                      className="h-4 w-4 accent-emerald-500"
                    />
                    <span className="text-sm text-zinc-400">
                      Send me a notification
                    </span>
                  </label>
                  <InfoTip title="Motion alerts">
                    Get a pop-up on your computer when your camera spots movement.
                  </InfoTip>
                </Field>
              </div>
            </section>

            {/* Cameras */}
            {settings.cameras.map((cam, i) => (
              <section
                key={cam.name}
                className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6"
              >
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-zinc-200">{cam.name}</h2>
                  <span className="text-xs text-zinc-500">{cam.host}</span>
                </div>

                <div className="mt-5">
                  <div className="flex items-center justify-between">
                    <label className="text-sm text-zinc-400">
                      How easily motion triggers a recording
                      <InfoTip title="Motion sensitivity">
                        How much movement is needed before your camera starts
                        recording. If you miss events, make it more sensitive. If
                        you get too many clips (e.g. from trees or traffic), make
                        it less sensitive.
                      </InfoTip>
                    </label>
                    <span className="rounded-md bg-zinc-800 px-2 py-0.5 font-mono text-xs text-emerald-400">
                      {cam.sensitivity.toFixed(3)}
                    </span>
                  </div>
                  <input
                    type="range"
                    min={0.005}
                    max={0.1}
                    step={0.001}
                    value={cam.sensitivity}
                    onChange={(e) =>
                      updateCamera(i, { sensitivity: Number(e.target.value) })
                    }
                    className="mt-3 w-full accent-emerald-500"
                  />
                  <div className="mt-1 flex justify-between text-[11px] text-zinc-600">
                    <span>More sensitive</span>
                    <span>Less sensitive</span>
                  </div>
                </div>

                <div className="mt-5">
                  <label className="text-sm text-zinc-400">
                    What should trigger a recording?
                    <InfoTip title="Detection mode">
                      <strong>Motion</strong> records whenever anything moves.
                      <br />
                      <strong>Smart detection</strong> uses AI to recognise people,
                      vehicles, and animals — so a swaying tree won&apos;t set it
                      off.
                    </InfoTip>
                  </label>
                  <select
                    value={cam.detector}
                    onChange={(e) => updateCamera(i, { detector: e.target.value })}
                    className="mt-1.5 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                  >
                    <option value="motion">Motion — record when anything moves</option>
                    <option value="object">Smart — recognise people, vehicles, animals</option>
                  </select>
                </div>

                {cam.detector === "object" && (
                  <div className="mt-5">
                    <label className="text-sm text-zinc-400">
                      What to look for
                      <InfoTip title="What to detect">
                        Choose what you want your camera to notice. Only the things
                        you pick will trigger a recording.
                      </InfoTip>
                    </label>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {[
                        { id: "person", label: "People" },
                        { id: "vehicle", label: "Vehicles" },
                        { id: "animal", label: "Animals" },
                        { id: "bicycle", label: "Bicycles" },
                      ].map((cat) => {
                        const checked = cam.detect_categories.includes(cat.id);
                        return (
                          <button
                            key={cat.id}
                            type="button"
                            onClick={() => {
                              const next = checked
                                ? cam.detect_categories.filter((c) => c !== cat.id)
                                : [...cam.detect_categories, cat.id];
                              updateCamera(i, { detect_categories: next });
                            }}
                            className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                              checked
                                ? "border-emerald-500 bg-emerald-500/15 text-emerald-300"
                                : "border-zinc-700 text-zinc-400 hover:bg-zinc-800"
                            }`}
                          >
                            {cat.label}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <Field label="Record before motion (s)">
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={cam.pre_seconds}
                      onChange={(e) =>
                        updateCamera(i, { pre_seconds: Number(e.target.value) })
                      }
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                    />
                    <InfoTip title="Record before motion">
                      How much footage to keep from just before motion starts, so
                      you don&apos;t miss what led up to it.
                    </InfoTip>
                  </Field>
                  <Field label="Record after motion (s)">
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={cam.post_seconds}
                      onChange={(e) =>
                        updateCamera(i, { post_seconds: Number(e.target.value) })
                      }
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                    />
                    <InfoTip title="Record after motion">
                      How long to keep recording after motion stops, so you catch
                      the tail end of what happened.
                    </InfoTip>
                  </Field>
                  <Field label="Shortest clip (s)">
                    <input
                      type="number"
                      min={0}
                      step={0.5}
                      value={cam.min_duration}
                      onChange={(e) =>
                        updateCamera(i, { min_duration: Number(e.target.value) })
                      }
                      className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-emerald-500"
                    />
                    <InfoTip title="Shortest clip">
                      Very brief blips (like a bird flying past) are ignored unless
                      they last at least this long.
                    </InfoTip>
                  </Field>
                </div>

                <label className="mt-5 flex cursor-pointer items-center gap-3">
                  <input
                    type="checkbox"
                    checked={cam.snapshot_on_motion}
                    onChange={(e) =>
                      updateCamera(i, { snapshot_on_motion: e.target.checked })
                    }
                    className="h-4 w-4 accent-emerald-500"
                  />
                  <span className="text-sm text-zinc-400">
                    Save a photo when motion is detected
                  </span>
                  <InfoTip title="Save a photo">
                    Also save a still photo at the moment motion starts, handy for
                    a quick glance without opening the video.
                  </InfoTip>
                </label>
              </section>
            ))}

            <div className="flex items-center gap-4">
              <button
                onClick={save}
                disabled={saving}
                className="rounded-lg bg-emerald-500 px-5 py-2 text-sm font-medium text-zinc-950 transition-colors hover:bg-emerald-400 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save changes"}
              </button>
              {saved && <span className="text-sm text-emerald-400">Saved ✓</span>}
            </div>
          </div>
        )}
      </div>
    </Shell>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-sm text-zinc-400">{label}</label>
      <div className="mt-1.5">{children}</div>
    </div>
  );
}