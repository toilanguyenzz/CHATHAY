import { createContext, useContext, useState, ReactNode } from "react";

interface SharedFile {
  file_url: string;
  file_name?: string;
  file_size?: number;
  mime_type?: string;
}

interface SharedFileContextType {
  sharedFile: SharedFile | null;
  setSharedFile: (file: SharedFile | null) => void;
  clearSharedFile: () => void;
}

const SharedFileContext = createContext<SharedFileContextType | null>(null);

export const SharedFileProvider = ({ children }: { children: ReactNode }) => {
  const [sharedFile, setSharedFile] = useState<SharedFile | null>(null);

  const clearSharedFile = () => setSharedFile(null);

  return (
    <SharedFileContext.Provider value={{ sharedFile, setSharedFile, clearSharedFile }}>
      {children}
    </SharedFileContext.Provider>
  );
};

export const useSharedFile = () => {
  const ctx = useContext(SharedFileContext);
  if (!ctx) {
    throw new Error("useSharedFile must be used within SharedFileProvider");
  }
  return ctx;
};
