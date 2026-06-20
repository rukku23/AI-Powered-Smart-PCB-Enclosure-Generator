import { useEffect, useState } from "react";

export default function ThermalScoreCard({ thermalReport }) {
    if (!thermalReport) return null;

    const {
        thermal_health_score: score,
        verdict,
        slot_count,
        vent_face,
        required_area_cm2,
        implemented_area_cm2,
        passive_cooling_ok,
        recommendation,
        chimney_needed,
    } = thermalReport;

    // Colour based on score
    const scoreColor = (
        score >= 85 ? "#22c55e" :
        score >= 70 ? "#06b6d4" :
        score >= 50 ? "#f59e0b" : "#ef4444"
    );

    // SVG arc for gauge
    const radius = 40;
    const circumference = 2 * Math.PI * radius;
    const dashOffset = circumference - (score / 100) * circumference;

    return (
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-4 mt-3">
            <h3 className="text-sm font-semibold text-zinc-300 mb-3">
                Thermal Analysis
            </h3>

            <div className="flex items-center gap-4 mb-4">
                {/* Score gauge */}
                <div className="relative w-24 h-24">
                    <svg viewBox="0 0 100 100" className="transform -rotate-90">
                        <circle cx="50" cy="50" r={radius}
                            fill="none" stroke="#27272a" strokeWidth="10"/>
                        <circle cx="50" cy="50" r={radius}
                            fill="none" stroke={scoreColor} strokeWidth="10"
                            strokeDasharray={circumference}
                            strokeDashoffset={dashOffset}
                            strokeLinecap="round"
                            style={{ transition: "stroke-dashoffset 0.8s ease" }}
                        />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-2xl font-bold"
                              style={{ color: scoreColor }}>{score}</span>
                        <span className="text-xs text-zinc-500">/100</span>
                    </div>
                </div>

                {/* Verdict */}
                <div className="flex-1">
                    <div className={`text-sm font-medium ${
                        passive_cooling_ok ? "text-green-400" : "text-amber-400"
                    }`}>
                        {passive_cooling_ok ? "✓ Passive OK" : "⚠ Active Needed"}
                    </div>
                    <div className="text-xs text-zinc-400 mt-1">{verdict}</div>
                </div>
            </div>

            {/* Metrics */}
            <div className="space-y-2 text-xs">
                <div className="flex justify-between">
                    <span className="text-zinc-500">Vent slots generated</span>
                    <span className="text-zinc-200 font-mono">{slot_count}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-zinc-500">Vent face</span>
                    <span className="text-zinc-200 font-mono">{vent_face}</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-zinc-500">Area implemented</span>
                    <span className="text-zinc-200 font-mono">{implemented_area_cm2?.toFixed(1)} cm²</span>
                </div>
                <div className="flex justify-between">
                    <span className="text-zinc-500">Area required</span>
                    <span className="text-zinc-200 font-mono">{required_area_cm2?.toFixed(1)} cm²</span>
                </div>
                {chimney_needed && (
                    <div className="flex justify-between">
                        <span className="text-zinc-500">Chimney vent</span>
                        <span className="text-amber-400 font-mono">✓ Added</span>
                    </div>
                )}
            </div>

            {/* Recommendation */}
            <div className="mt-3 p-2 bg-zinc-800 rounded text-xs text-zinc-400">
                {recommendation}
            </div>
        </div>
    );
}
