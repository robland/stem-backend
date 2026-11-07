import { createBrowserRouter, type RouteObject } from "react-router-dom";
import { RequireAnonymous, RequireAuth } from "./components/guards";
import { AppLayout } from "./layouts/AppLayout";
import { AuthLayout } from "./layouts/AuthLayout";
import { ChallengesPage } from "./pages/ChallengesPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilePage } from "./pages/ProfilePage";
import { ProgressPage } from "./pages/ProgressPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ExercisePage } from "./pages/ExercisePage";
import { ScanPage } from "./pages/ScanPage";
import { ScanReviewPage } from "./pages/ScanReviewPage";
import { paths, patterns } from "./paths";

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
          { path: paths.scan, element: <ScanPage /> },
          { path: patterns.scanUpload, element: <ScanReviewPage /> },
          { path: patterns.exercise, element: <ExercisePage /> },
          { path: paths.progress, element: <ProgressPage /> },
          { path: paths.profile, element: <ProfilePage /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
];

export const router = createBrowserRouter(routes);
