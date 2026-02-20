import { Github } from "lucide-react";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-8 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-3xl w-full text-center space-y-8">
        <div className="space-y-4">
          <h1 className="text-6xl font-bold tracking-tight">
            <span className="text-primary">Axel</span>
          </h1>
          <p className="text-2xl text-muted-foreground">
            AI Coding Assistant in your browser
          </p>
        </div>
        
        <div className="space-y-4 text-lg text-gray-600">
          <p>
            Work with AI directly on your GitHub repositories.
          </p>
          <p>
            No installation required. Everything runs in the cloud.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-8">
          <a
            href="http://localhost:3500/auth/github"
            className="inline-flex items-center justify-center px-6 py-3 text-lg font-medium text-white bg-primary rounded-lg hover:bg-primary/90 transition-colors"
          >
            <Github className="mr-2 h-5 w-5" />
            Sign in with GitHub
          </a>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 pt-16 text-left">
          <div className="space-y-2">
            <h3 className="font-semibold text-lg">Browse Code</h3>
            <p className="text-sm text-gray-600">
              Navigate any public or private GitHub repository directly in your browser.
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-lg">Chat with AI</h3>
            <p className="text-sm text-gray-600">
              Ask questions about your code and get intelligent answers powered by AI.
            </p>
          </div>
          <div className="space-y-2">
            <h3 className="font-semibold text-lg">Edit & Create PRs</h3>
            <p className="text-sm text-gray-600">
              Make changes with AI assistance and create pull requests directly.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
