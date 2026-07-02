import ActionTab from './components/ActionTab'
import { Toaster } from "./components/ui/sonner"

function App() {
  return (
    <>
      <main className="max-w-2xl mx-auto p-8 h-screen flex flex-col gap-8">
        <h1 className="text-2xl font-bold">RAG Chatbot</h1>
        <ActionTab/>
      </main>
      <Toaster/>
    </>
  )
}

export default App