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
import { RealTimeWorkspace } from './components/realtime/RealTimeWorkspace';
import { VisionStudio } from './components/vision/VisionStudio';
import { ReasoningStudio } from './components/reasoning/ReasoningStudio';
import { RoutingStudio } from './components/routing/RoutingStudio';
import { MemoryStudio } from './components/memory/MemoryStudio';
import { AgentStudio } from './components/agents/AgentStudio';
import { WorkflowStudio } from './components/workflows/WorkflowStudio';
import { ComputerStudio } from './components/computer/ComputerStudio';
import { FileWorkspaceStudio } from './components/files/FileWorkspaceStudio';
import { TerminalCodeStudio } from './components/terminal/TerminalCodeStudio';
import { GitVersionControlStudio } from './components/git/GitVersionControlStudio';
import { EvaluationStudio } from './components/evaluation/EvaluationStudio';
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
        ) : activeWorkspaceView === 'realtime' ? (
          <RealTimeWorkspace />
        ) : activeWorkspaceView === 'vision' ? (
          <VisionStudio />
        ) : activeWorkspaceView === 'reasoning' ? (
          <ReasoningStudio />
        ) : activeWorkspaceView === 'routing' ? (
          <RoutingStudio />
        ) : activeWorkspaceView === 'memory' ? (
          <MemoryStudio />
        ) : activeWorkspaceView === 'agents' ? (
          <AgentStudio />
        ) : activeWorkspaceView === 'workflows' ? (
          <WorkflowStudio />
        ) : activeWorkspaceView === 'computer' ? (
          <ComputerStudio />
        ) : activeWorkspaceView === 'files' ? (
          <FileWorkspaceStudio />
        ) : activeWorkspaceView === 'terminal' ? (
          <TerminalCodeStudio />
        ) : activeWorkspaceView === 'git' ? (
          <GitVersionControlStudio />
        ) : activeWorkspaceView === 'evaluation' ? (
          <EvaluationStudio />
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
