"use client";

import type { TimeWindow } from "@/lib/types";
import { cn } from "@/lib/utils";

const windows: Array<{ value: TimeWindow; label: string }> = [
  { value: "1D", label: "1D" },
  { value: "7D", label: "7D" },
  { value: "30D", label: "30D" },
  { value: "All", label: "All" }
];

export function TimeWindowTabs({
  selected,
  onChange
}: {
  selected: TimeWindow;
  onChange: (value: TimeWindow) => void;
}) {
  return (
    <div
      className="inline-grid grid-cols-4 rounded-md border bg-muted p-1"
      role="tablist"
      aria-label="Time window"
    >
      {windows.map((window) => (
        <button
          key={window.value}
          type="button"
          role="tab"
          aria-selected={selected === window.value}
          onClick={() => onChange(window.value)}
          className={cn(
            "h-8 rounded-sm px-3 text-sm font-medium text-muted-foreground transition-colors",
            selected === window.value
              ? "bg-white text-foreground shadow-sm"
              : "hover:text-foreground"
          )}
        >
          {window.label}
        </button>
      ))}
    </div>
  );
}
