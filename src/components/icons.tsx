import React from "react";

interface IconProps {
  size?: number;
  color?: string;
  style?: React.CSSProperties;
}

const Icon = ({ children, size = 24, color = "currentColor", style, viewBox = "0 0 24 24" }: IconProps & { children: React.ReactNode; viewBox?: string }) => (
  <svg width={size} height={size} viewBox={viewBox} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={style}>
    {children}
  </svg>
);

/* ─── Document & File ─── */
export const IconDoc = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </Icon>
);

export const IconUpload = (p: IconProps) => (
  <Icon {...p}>
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="17 8 12 3 7 8" />
    <line x1="12" y1="3" x2="12" y2="15" />
  </Icon>
);

export const IconFolder = (p: IconProps) => (
  <Icon {...p}>
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2Z" />
  </Icon>
);

export const IconSave = (p: IconProps) => (
  <Icon {...p}>
    <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z" />
    <polyline points="17 21 17 13 7 13 7 21" />
    <polyline points="7 3 7 8 15 8" />
  </Icon>
);

/* ─── Learning ─── */
export const IconBrain = (p: IconProps) => (
  <Icon {...p}>
    <path d="M12 2a6 6 0 0 0-6 6c0 1.6.6 3 1.7 4.1L12 16l4.3-3.9A6 6 0 0 0 18 8a6 6 0 0 0-6-6Z" />
    <path d="M12 16v6" />
    <path d="M8 22h8" />
    <path d="M9 8h0" />
    <path d="M15 8h0" />
  </Icon>
);

export const IconFlashcard = (p: IconProps) => (
  <Icon {...p}>
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="M12 8v8" />
    <path d="M8 12h8" />
  </Icon>
);

export const IconQuiz = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9 11l3 3L22 4" />
    <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
  </Icon>
);

export const IconCheck = (p: IconProps) => (
  <Icon {...p}>
    <polyline points="20 6 9 17 4 12" />
  </Icon>
);

/* ─── Finance & Rewards ─── */
export const IconCoin = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 6v12" />
    <path d="M15 9.5a3 3 0 0 0-3-1.5H10a3 3 0 0 0 0 4h4a3 3 0 0 1 0 4h-4a3 3 0 0 1-3-1.5" />
  </Icon>
);

export const IconFire = (p: IconProps) => (
  <Icon {...p} viewBox="0 0 24 24">
    <path d="M12 2c.5 2.5 2 4.5 2 6.5a4 4 0 1 1-8 0C6 6 9 4.5 10 2c.3-.5.8-.5 1 0l1 0Z" fill={p.color || "currentColor"} stroke="none" />
    <path d="M8.5 14.5A4 4 0 0 0 12 22a4 4 0 0 0 4-4c0-2-1-3.5-2-5" stroke={p.color || "currentColor"} fill="none" strokeWidth="2" />
  </Icon>
);

/* ─── Tools ─── */
export const IconCompress = (p: IconProps) => (
  <Icon {...p}>
    <polyline points="4 14 10 14 10 20" />
    <polyline points="20 10 14 10 14 4" />
    <line x1="14" y1="10" x2="21" y2="3" />
    <line x1="3" y1="21" x2="10" y2="14" />
  </Icon>
);

export const IconMerge = (p: IconProps) => (
  <Icon {...p}>
    <path d="M8 6H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h3" />
    <path d="M16 6h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3" />
    <line x1="12" y1="2" x2="12" y2="22" />
  </Icon>
);

export const IconConvert = (p: IconProps) => (
  <Icon {...p}>
    <polyline points="17 1 21 5 17 9" />
    <path d="M3 11V9a4 4 0 0 1 4-4h14" />
    <polyline points="7 23 3 19 7 15" />
    <path d="M21 13v2a4 4 0 0 1-4 4H3" />
  </Icon>
);

export const IconExtract = (p: IconProps) => (
  <Icon {...p}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
    <polyline points="14 2 14 8 20 8" />
    <path d="M9 15l2 2 4-4" />
  </Icon>
);

/* ─── Navigation & UI ─── */
export const IconChevronRight = (p: IconProps) => (
  <Icon {...p} size={p.size || 16}>
    <polyline points="9 18 15 12 9 6" />
  </Icon>
);

export const IconChevronLeft = (p: IconProps) => (
  <Icon {...p} size={p.size || 18}>
    <polyline points="15 18 9 12 15 6" />
  </Icon>
);

export const IconRefresh = (p: IconProps) => (
  <Icon {...p}>
    <polyline points="23 4 23 10 17 10" />
    <polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </Icon>
);

export const IconLightbulb = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9 18h6" />
    <path d="M10 22h4" />
    <path d="M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2Z" />
  </Icon>
);

export const IconSearch = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="8" />
    <line x1="21" y1="21" x2="16.65" y2="16.65" />
  </Icon>
);

export const IconAlertTriangle = (p: IconProps) => (
  <Icon {...p}>
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </Icon>
);

export const IconInbox = (p: IconProps) => (
  <Icon {...p}>
    <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
    <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" />
  </Icon>
);

/* ─── Media ─── */
export const IconCamera = (p: IconProps) => (
  <Icon {...p}>
    <path d="M23 7l-7 5 7 5V7z" />
    <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
  </Icon>
);

export const IconImage = (p: IconProps) => (
  <Icon {...p}>
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <circle cx="8.5" cy="8.5" r="1.5" />
    <polyline points="21 15 16 10 5 21" />
  </Icon>
);
