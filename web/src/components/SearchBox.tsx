"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { getSearchSuggestions, type SearchSuggestion } from "@/lib/areas";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
};

export function SearchBox({ value, onChange, onSubmit }: Props) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);

  const suggestions = useMemo(() => getSearchSuggestions(value), [value]);

  useEffect(() => {
    setActiveIndex(0);
  }, [suggestions]);

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const pick = (item: SearchSuggestion) => {
    onChange(item.value);
    onSubmit(item.value);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className="relative">
      <label className="block">
        <span className="sr-only">Search events</span>
        <input
          type="search"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (!open || !suggestions.length) {
              if (e.key === "Enter") onSubmit(value);
              return;
            }
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActiveIndex((i) => (i + 1) % suggestions.length);
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActiveIndex((i) => (i - 1 + suggestions.length) % suggestions.length);
            } else if (e.key === "Enter") {
              e.preventDefault();
              pick(suggestions[activeIndex]);
            } else if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder="Search area, venue, comedy…"
          className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-amber-400/50 focus:outline-none focus:ring-1 focus:ring-amber-400/40"
        />
      </label>

      {open && suggestions.length > 0 && (
        <ul className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-xl border border-white/10 bg-[#141a22] py-1 shadow-xl">
          {suggestions.map((item, index) => (
            <li key={`${item.kind}-${item.value}`}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => pick(item)}
                className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm ${
                  index === activeIndex
                    ? "bg-amber-400/15 text-amber-100"
                    : "text-slate-200 hover:bg-white/5"
                }`}
              >
                <span>{item.label}</span>
                <span className="text-[10px] uppercase tracking-wide text-slate-500">
                  {item.kind === "area" ? "Area" : "Topic"}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
