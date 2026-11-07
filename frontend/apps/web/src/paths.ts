export const paths = {
  home: "/",
  challenges: "/defis",
  scan: "/scanner",
  scanUpload: (uploadId: string) => `/scanner/${uploadId}`,
  exercise: (exerciseId: string, extractedId?: string) =>
    `/parcours/${exerciseId}${extractedId ? `?enonce=${extractedId}` : ""}`,
  progress: "/progres",
  profile: "/profil",
  login: "/connexion",
  register: "/inscription",
} as const;

export const patterns = {
  scanUpload: "/scanner/:uploadId",
  exercise: "/parcours/:exerciseId",
} as const;
