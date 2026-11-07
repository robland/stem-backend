import { createBrowserRouter, type RouteObject } from "react-router-dom";
import { RequireAnonymous, RequireAuth } from "./components/guards";
import { AppLayout } from "./layouts/AppLayout";
import { AuthLayout } from "./layouts/AuthLayout";
import { FocusLayout } from "./layouts/FocusLayout";
import { ChallengesPage } from "./pages/ChallengesPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProgressPage } from "./pages/ProgressPage";
import { RegisterPage } from "./pages/RegisterPage";
import { paths, patterns } from "./paths";

// Écrans lourds (scanner, lecteur et leurs renderers) chargés à la demande : bundle initial plus léger.
const scan = () => import("./pages/ScanPage").then((m) => ({ Component: m.ScanPage }));
const scanReview = () => import("./pages/ScanReviewPage").then((m) => ({ Component: m.ScanReviewPage }));
const exercise = () => import("./pages/ExercisePage").then((m) => ({ Component: m.ExercisePage }));

export const routes: RouteObject[] = [
  {
    element: <RequireAnonymous />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: paths.login, element: <LoginPage /> },
          { path: paths.register, element: <RegisterPage /> },
        ],
      },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: paths.home, element: <HomePage /> },
          { path: paths.challenges, element: <ChallengesPage /> },
          { path: paths.scan, lazy: scan },
          { path: patterns.scanUpload, lazy: scanReview },
          { path: paths.progress, element: <ProgressPage /> },
          { path: paths.profile, element: <ProfilePage /> },
        ],
      },
      { element: <FocusLayout />, children: [{ path: patterns.exercise, lazy: exercise }] },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const router = createBrowserRouter(routes);
