import React, { useState } from 'react';
import { ChatProvider, useChat } from './context/ChatContext';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ChatArea } from './components/chat/ChatArea';
import { SettingsModal } from './components/modals/SettingsModal';
import { SetupGuideModal } from './components/modals/SetupGuideModal';
import { DeleteConfirmModal } from './components/modals/DeleteConfirmModal';
import { ToastContainer } from './components/ui/Toast';
import { DocumentsWorkspace } from './components/documents/DocumentsWorkspace';
import { FactCheckWorkspace } from './components/factcheck/FactCheckWorkspace';
import { TranslationWorkspace } from './components/translation/TranslationWorkspace';
import { Conversation } from './types';

const MainLayout: React.FC = () => {
  const { deleteConversation, activeWorkspaceView } = useChat();
  const [deleteTarget, setDeleteTarget] = useState<Conversation | null>(null);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-midnight-950 text-slate-100">
      {/* Sidebar */}
      <Sidebar onConfirmDelete={(conv) => setDeleteTarget(conv)} />

      {/* Main Workspace Column */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
        <Header />
        {activeWorkspaceView === 'documents' ? (
          <DocumentsWorkspace />
        ) : activeWorkspaceView === 'factcheck' ? (
          <FactCheckWorkspace />
        ) : activeWorkspaceView === 'translation' ? (
          <TranslationWorkspace />
        ) : (
          <ChatArea />
        )}
      </div>

      {/* Global Modals & Notifications */}
      <SettingsModal />
      <SetupGuideModal />
      <DeleteConfirmModal
        conversation={deleteTarget}
        isOpen={Boolean(deleteTarget)}
        onClose={() => setDeleteTarget(null)}
        onConfirm={(id) => deleteConversation(id)}
      />
      <ToastContainer />
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <ChatProvider>
      <MainLayout />
    </ChatProvider>
  );
};

export default App;
