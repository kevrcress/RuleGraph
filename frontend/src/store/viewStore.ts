import { create } from "zustand";

type ViewMode = "business" | "technical";

interface ViewState {
  mode: ViewMode;
  setMode: (mode: ViewMode) => void;
  toggle: () => void;
}

const stored = (localStorage.getItem("rg_view") as ViewMode) || "business";

export const useViewStore = create<ViewState>((set, get) => ({
  mode: stored,
  setMode: (mode) => {
    localStorage.setItem("rg_view", mode);
    set({ mode });
  },
  toggle: () => {
    const next = get().mode === "business" ? "technical" : "business";
    localStorage.setItem("rg_view", next);
    set({ mode: next });
  },
}));
