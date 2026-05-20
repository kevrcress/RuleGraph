import { create } from "zustand";

interface User {
  id: string;
  username: string;
  email: string;
  name: string;
  role: string;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
}

const stored = localStorage.getItem("rg_token");
const storedUser = localStorage.getItem("rg_user");

export const useAuthStore = create<AuthState>((set) => ({
  token: stored || null,
  user: storedUser ? JSON.parse(storedUser) : null,
  setAuth: (token, user) => {
    localStorage.setItem("rg_token", token);
    localStorage.setItem("rg_user", JSON.stringify(user));
    set({ token, user });
  },
  clearAuth: () => {
    localStorage.removeItem("rg_token");
    localStorage.removeItem("rg_user");
    set({ token: null, user: null });
  },
}));
