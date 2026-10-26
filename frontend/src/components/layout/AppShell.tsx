import { Outlet } from "react-router-dom";

import { ToastProvider } from "../ui/Toast";
import TopBar from "./TopBar";

/** Full-window frame: fixed top bar, then the page filling the rest. Nothing here scrolls. */
export default function AppShell() {
  return (
    <ToastProvider>
      <div className="flex h-full flex-col">
        <TopBar />
        <main className="flex min-h-0 flex-1 flex-col px-6 pt-5 pb-6">
          <Outlet />
        </main>
      </div>
    </ToastProvider>
  );
}
