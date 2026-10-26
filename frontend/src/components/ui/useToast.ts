import { createContext, useContext } from "react";

export type ToastInput = { title: string; detail?: string };

export const ToastContext = createContext<(t: ToastInput) => void>(() => {});

/** Show a short notice: notify({ title, detail }). Needs ToastProvider above (it is in AppShell). */
export const useToast = () => useContext(ToastContext);
