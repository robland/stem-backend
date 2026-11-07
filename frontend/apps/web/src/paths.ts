export const paths = {
  home: "/",
  challenges: "/defis",
  scan: "/scanner",
  scanUpload: (uploadId: string) => `/scanner/${uploadId}`,
  /** `enonce` : énoncé d'origine (relancer la génération) ; `tentative` : tentative à reprendre. */
  exercise: (exerciseId: string, query: { enonce?: string; tentative?: string } = {}) => {
    const search = new URLSearchParams(
      Object.entries(query).filter(([, v]) => v) as [string, string][],
    ).toString();
    return `/parcours/${exerciseId}${search ? `?${search}` : ""}`;
  },
  progress: "/progres",
  profile: "/profil",
  login: "/connexion",
  register: "/inscription",
} as const;

export const patterns = {
  scanUpload: "/scanner/:uploadId",
  exercise: "/parcours/:exerciseId",
} as const;
