import { createBrowserRouter } from "react-router-dom";

import AppShell from "./components/layout/AppShell";
import HomePage from "./pages/HomePage";
import NotFoundPage from "./pages/NotFoundPage";
import WorkflowPage from "./pages/WorkflowPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <HomePage /> },
      { path: "/automations/:key", element: <WorkflowPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
