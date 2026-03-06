import { Github, Sparkles, ArrowRight, Code, Zap, Globe } from "lucide-react";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-black flex flex-col items-center relative overflow-hidden">
      {/* Background Glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[600px] bg-gradient-to-b from-blue-600/10 to-transparent pointer-events-none" />

      {/* Hero Section */}
      <div className="max-w-5xl w-full px-6 pt-32 pb-20 z-10 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-blue-400 text-sm font-medium mb-8">
          <Sparkles className="w-4 h-4" />
          <span>New: Phase 3 Alpha is here</span>
        </div>

        <h1 className="text-7xl font-extrabold tracking-tight text-white mb-8">
          Build anything with <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">Axel</span>
        </h1>

        <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-12 leading-relaxed">
          The world's first context-aware AI coding assistant that works directly on your GitHub repositories. No setup, no limits.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/login"
            className="inline-flex items-center justify-center px-8 py-4 text-lg font-bold text-black bg-white rounded-2xl hover:bg-gray-200 transition-all hover:scale-105 group shadow-2xl shadow-white/10"
          >
            Get Started Free
            <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <a
            href="http://localhost:3500/auth/github"
            className="inline-flex items-center justify-center px-8 py-4 text-lg font-bold text-white bg-white/5 border border-white/10 rounded-2xl hover:bg-white/10 transition-all"
          >
            <Github className="mr-3 h-5 w-5" />
            Continue with GitHub
          </a>
        </div>
      </div>

      {/* Features Grid */}
      <div className="max-w-6xl w-full px-6 py-20 grid grid-cols-1 md:grid-cols-3 gap-8">
        {[
          { icon: Globe, title: "Codebase RAG", desc: "Our AI understands your whole project, not just the open file." },
          { icon: Zap, title: "Mobile Ready", desc: "Scaffold React Native and Mobile apps with a single command." },
          { icon: Code, title: "Pure Browser", desc: "A full development environment in your tab. No local dependencies." }
        ].map((feature, i) => (
          <div key={i} className="p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-white/20 transition-colors group">
            <feature.icon className="w-10 h-10 text-blue-500 mb-6 group-hover:scale-110 transition-transform" />
            <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
            <p className="text-gray-400 leading-relaxed">{feature.desc}</p>
          </div>
        ))}
      </div>

      {/* Footer */}
      <footer className="mt-auto py-10 border-t border-white/5 w-full text-center">
        <p className="text-gray-600 text-sm">© 2026 Axel Engineering. All code pushed to GitHub.</p>
      </footer>
    </main>
  );
}
