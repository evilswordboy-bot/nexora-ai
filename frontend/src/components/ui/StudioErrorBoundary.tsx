import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, ChevronDown, ChevronUp } from 'lucide-react';

interface Props {
  children: ReactNode;
  studioName?: string;
  onReset?: () => void;
  onGoHome?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class StudioErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[StudioErrorBoundary] Unhandled render error in ${this.props.studioName || 'Studio'}:`, error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    } else {
      window.location.reload();
    }
  };

  public render() {
    if (this.state.hasError) {
      const studioTitle = this.props.studioName || 'Studio Workspace';

      return (
        <div className="flex-1 h-full min-h-[500px] flex items-center justify-center p-6 bg-slate-950/80">
          <div className="max-w-xl w-full p-6 rounded-2xl bg-slate-900 border border-rose-500/30 shadow-2xl shadow-rose-950/20 text-slate-200">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400 shrink-0">
                <AlertTriangle className="w-6 h-6 animate-pulse" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white tracking-wide">
                  {studioTitle} Temporary Recovery Mode
                </h2>
                <p className="text-xs text-rose-300/80">
                  An unexpected render interruption was safely caught to prevent a blank screen.
                </p>
              </div>
            </div>

            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              NEXORA AI has preserved your application state. You can reload this studio to re-synchronize local data,
              or inspect the technical diagnostic details below.
            </p>

            <div className="flex items-center gap-3 mb-4">
              <button
                onClick={this.handleReset}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shadow-lg shadow-cyan-900/30 transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reload Studio
              </button>

              {this.props.onGoHome && (
                <button
                  onClick={this.props.onGoHome}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                >
                  <Home className="w-3.5 h-3.5" />
                  Return to Chat / Overview
                </button>
              )}

              <button
                onClick={() => this.setState((prev) => ({ showDetails: !prev.showDetails }))}
                className="ml-auto text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition"
              >
                {this.state.showDetails ? (
                  <>
                    Hide Diagnostics <ChevronUp className="w-3 h-3" />
                  </>
                ) : (
                  <>
                    Show Diagnostics <ChevronDown className="w-3 h-3" />
                  </>
                )}
              </button>
            </div>

            {this.state.showDetails && (
              <div className="mt-3 p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] font-mono text-rose-300 max-h-48 overflow-auto whitespace-pre-wrap">
                <div className="font-bold text-rose-400 mb-1">
                  {this.state.error?.name}: {this.state.error?.message}
                </div>
                <div className="text-slate-500">
                  {this.state.error?.stack}
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
