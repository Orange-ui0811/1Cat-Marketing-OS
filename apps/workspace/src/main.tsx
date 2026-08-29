import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import RuntimeLab from './RuntimeLab'
import MarketingWorkflow from './MarketingWorkflow'
import ServerWorkspace from './ServerWorkspace'
import { RuntimeWorkspaceProvider } from './RuntimeWorkspaceContext'
import './styles.css'
import './runtime-lab.css'
import './marketing-workflow.css'
import './server-workspace.css'

const requestedView = new URLSearchParams(window.location.search).get('view')
const runtimeMode = import.meta.env.VITE_RUNTIME_MODE === 'api' && requestedView === 'runtime'
const standaloneServerMode = import.meta.env.VITE_RUNTIME_MODE === 'api' && requestedView === 'workflow'
const apiWorkspaceMode = import.meta.env.VITE_RUNTIME_MODE === 'api' && !runtimeMode && !standaloneServerMode

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {runtimeMode
      ? <RuntimeLab />
      : standaloneServerMode
        ? <ServerWorkspace />
        : apiWorkspaceMode
          ? <RuntimeWorkspaceProvider><App /></RuntimeWorkspaceProvider>
          : requestedView === 'workflow' ? <MarketingWorkflow /> : <App />}
  </React.StrictMode>,
)
