import type { TimePreset } from "./types";

const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;

function istNow(): Date {
  const now = new Date();
  return new Date(now.getTime() + IST_OFFSET_MS + now.getTimezoneOffset() * 60_000);
}

function toIsoWithOffset(date: Date): string {
  const shifted = new Date(date.getTime() - IST_OFFSET_MS - date.getTimezoneOffset() * 60_000);
  return shifted.toISOString();
}

export function timeRangeForPreset(preset: TimePreset): { from?: string; to?: string } {
  if (preset === "all") return {};

  const now = istNow();

  if (preset === "tonight") {
    const end = new Date(now);
    if (now.getHours() >= 6) {
      end.setDate(end.getDate() + 1);
    }
    end.setHours(6, 0, 0, 0);
    return { from: toIsoWithOffset(now), to: toIsoWithOffset(end) };
  }

  // This weekend: Fri 6pm → Sun 11:59pm (IST-relative clock)
  const day = now.getDay(); // 0 Sun .. 6 Sat
  const start = new Date(now);
  const end = new Date(now);

  const daysUntilFriday = (5 - day + 7) % 7;
  if (day === 0) {
    start.setHours(0, 0, 0, 0);
  } else if (day === 6) {
    start.setHours(18, 0, 0, 0);
  } else {
    start.setDate(start.getDate() + (daysUntilFriday === 0 && now.getHours() >= 18 ? 0 : daysUntilFriday));
    start.setHours(18, 0, 0, 0);
  }

  const daysUntilSunday = (7 - start.getDay()) % 7;
  end.setTime(start.getTime());
  end.setDate(end.getDate() + (start.getDay() <= 0 ? 0 : daysUntilSunday || (7 - start.getDay())));
  if (end.getDay() !== 0) {
    end.setDate(end.getDate() + (7 - end.getDay()));
  }
  end.setHours(23, 59, 59, 999);

  if (end < now) {
    start.setDate(start.getDate() + 7);
    end.setDate(end.getDate() + 7);
  }

  return { from: toIsoWithOffset(start), to: toIsoWithOffset(end) };
}

export function formatEventTime(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
