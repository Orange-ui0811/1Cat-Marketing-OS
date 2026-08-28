import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import RuntimeLab from './RuntimeLab'
import MarketingWorkflow from './MarketingWorkflow'
import './styles.css'
import './runtime-lab.css'
import './marketing-workflow.css'

const requestedView = new URLSearchParams(window.location.search).get('view')
const runtimeMode = import.meta.env.VITE_RUNTIME_MODE === 'api' && requestedView === 'runtime'
const workflowMode = import.meta.env.VITE_RUNTIME_MODE === 'api' && requestedView === 'workflow'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    {workflowMode ? <MarketingWorkflow /> : runtimeMode ? <RuntimeLab /> : <App />}
  </React.StrictMode>,
)
